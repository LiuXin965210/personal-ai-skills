#!/usr/bin/env python3
# encoding: utf-8

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
VENDOR_DIR = os.path.join(SCRIPT_DIR, "vendor")
DEFAULT_CONFIG = os.path.join(SKILL_DIR, "sls_config.json")
MAX_LINE = 10

if os.path.isdir(VENDOR_DIR):
    sys.path.insert(0, VENDOR_DIR)

from aliyun.log import GetLogsRequest, LogClient


def parse_time(value):
    if value is None:
        return None

    value = value.strip()
    if value.isdigit():
        return int(value)

    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return int(datetime.fromisoformat(value).timestamp())
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "时间格式必须是 Unix 秒级时间戳，或 ISO 格式，例如 2026-06-08T10:00:00+08:00"
        ) from exc


def load_config(path, required=False):
    if not path:
        return {}
    if not os.path.exists(path):
        if required:
            print(f"配置文件不存在：{path}", file=sys.stderr)
            sys.exit(2)
        return {}
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Query Alibaba Cloud SLS logs with GetLogs."
    )
    parser.add_argument("--config", default=DEFAULT_CONFIG, help=f"JSON 配置文件路径，默认读取 {DEFAULT_CONFIG}；脚本使用其中的 AccessKey")
    parser.add_argument("--endpoint", required=True, help="例如 cn-hangzhou.log.aliyuncs.com")
    parser.add_argument("--project", required=True, help="SLS Project 名称")
    parser.add_argument("--logstore", required=True, help="SLS Logstore 名称")
    parser.add_argument("--query", required=True, help="SLS 查询/分析语句")
    parser.add_argument("--topic", default="", help="SLS topic，可为空")
    parser.add_argument("--from-time", help="开始时间：Unix 秒级时间戳或 ISO 时间")
    parser.add_argument("--to-time", help="结束时间：Unix 秒级时间戳或 ISO 时间")
    parser.add_argument("--minutes", type=int, required=True, help="未指定 from/to 时查询最近 N 分钟")
    parser.add_argument("--line", type=int, default=MAX_LINE, help=f"返回条数，最大 {MAX_LINE}")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--reverse", dest="reverse", action="store_true", default=True, help="普通查询时按时间倒序，默认启用")
    parser.add_argument("--forward", dest="reverse", action="store_false", help="普通查询时按时间正序")
    parser.add_argument("--json", action="store_true", help="以 JSON Lines 输出每条日志")
    return parser


def require(value, name):
    if not value:
        print(f"缺少参数：{name}", file=sys.stderr)
        sys.exit(2)
    return value


def validate_limit(args):
    if args.line > MAX_LINE:
        print(f"--line 最大只能是 {MAX_LINE}，当前是 {args.line}", file=sys.stderr)
        sys.exit(2)
    if args.line < 1:
        print("--line 必须大于 0", file=sys.stderr)
        sys.exit(2)

    limits = [int(value) for value in re.findall(r"\blimit\s+(\d+)\b", args.query, flags=re.IGNORECASE)]
    over_limit = [value for value in limits if value > MAX_LINE]
    if over_limit:
        print(f"query 中的 limit 最大只能是 {MAX_LINE}，当前包含 {over_limit[0]}", file=sys.stderr)
        sys.exit(2)


def main():
    args = build_parser().parse_args()
    validate_limit(args)
    config = load_config(args.config, required=args.config != DEFAULT_CONFIG) if args.config else {}

    access_key_id = require(
        os.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID") or config.get("access_key_id"),
        "环境变量 ALIBABA_CLOUD_ACCESS_KEY_ID 或配置 access_key_id",
    )
    access_key_secret = require(
        os.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET") or config.get("access_key_secret"),
        "环境变量 ALIBABA_CLOUD_ACCESS_KEY_SECRET 或配置 access_key_secret",
    )

    now = int(time.time())
    from_time = parse_time(args.from_time) if args.from_time is not None else now - args.minutes * 60
    to_time = parse_time(args.to_time) if args.to_time is not None else now

    client = LogClient(args.endpoint, access_key_id, access_key_secret)
    request = GetLogsRequest(
        args.project,
        args.logstore,
        from_time,
        to_time,
        args.topic,
        query=args.query,
        line=args.line,
        offset=args.offset,
        reverse=args.reverse,
    )

    print(f"endpoint={args.endpoint}")
    print(f"project={args.project}, logstore={args.logstore}, topic={args.topic!r}")
    print(f"time={from_time}..{to_time}, query={args.query!r}")
    print("------------- Query started -------------")

    response = client.get_logs(request)
    logs = response.get_logs()

    print(f"completed={response.is_completed()}, count={len(logs)}")
    for log in logs:
        row = dict(log.contents)
        if args.json:
            print(json.dumps(row, ensure_ascii=False))
        else:
            print(row)

    print("------------- Query finished ------------")


if __name__ == "__main__":
    main()
