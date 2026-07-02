#!/usr/bin/env python3
# encoding: utf-8
"""
查询阿里云 SLS 日志的小工具。

可以把这个文件理解成一个很薄的 Java CommandLineRunner：

1. 解析命令行参数（类似 Controller 入参）。
2. 读取 sls_config.json 里的 AccessKey（类似读取 application.yml）。
3. 构造阿里云 SLS SDK 的 GetLogsRequest（类似组装一个请求 DTO）。
4. 调用 LogClient.get_logs()。
5. 把结果打印到标准输出，供 Codex 后续分析。

脚本只负责查日志，不做业务接口调用，不访问数据库，也不修改任何数据。
"""

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

# 技能规则要求每次日志最多返回 10 条，避免一次拉太多线上日志进入上下文。
MAX_LINE = 10

if os.path.isdir(VENDOR_DIR):
    # 优先加载技能自带 vendor 依赖，避免用户机器没有安装 aliyun-log-python-sdk。
    # 类似 Java 里把依赖随工具一起打包，不依赖全局环境。
    sys.path.insert(0, VENDOR_DIR)

from aliyun.log import GetLogsRequest, LogClient


def parse_time(value):
    """把命令行传入的时间转换成 SLS SDK 需要的 Unix 秒级时间戳。"""
    if value is None:
        return None

    value = value.strip()
    if value.isdigit():
        return int(value)

    try:
        # 兼容 ISO 时间，例如 2026-06-08T10:00:00+08:00。
        # datetime.fromisoformat 不能直接识别结尾的 Z，所以先转成 +00:00。
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return int(datetime.fromisoformat(value).timestamp())
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "时间格式必须是 Unix 秒级时间戳，或 ISO 格式，例如 2026-06-08T10:00:00+08:00"
        ) from exc


def load_config(path, required=False):
    """
    读取 JSON 配置文件。

    required=False 时，默认配置不存在也可以继续，让调用方尝试环境变量。
    required=True 时，用户显式指定的配置文件不存在就直接失败。
    """
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
    """
    定义命令行参数。

    argparse 可以类比为 Spring MVC 的参数绑定：把命令行参数绑定到 args 对象上。
    """
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
    """必填参数校验。缺失时退出进程，避免用空 AccessKey 或空参数请求 SLS。"""
    if not value:
        print(f"缺少参数：{name}", file=sys.stderr)
        sys.exit(2)
    return value


def validate_limit(args):
    """
    双重限制日志返回条数。

    1. 限制 SDK 参数 --line。
    2. 限制 SLS 查询语句里的 `limit N`。

    这样即使调用方在 query 中手写 `limit 100`，脚本也会拒绝执行。
    """
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
    """脚本入口。整体流程类似 Java main 方法或 CommandLineRunner.run。"""
    args = build_parser().parse_args()
    validate_limit(args)
    config = load_config(args.config, required=args.config != DEFAULT_CONFIG) if args.config else {}

    # AccessKey 读取优先级：
    # 1. 环境变量，适合 CI 或临时运行。
    # 2. sls_config.json，适合本机固定配置。
    access_key_id = require(
        os.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID") or config.get("access_key_id"),
        "环境变量 ALIBABA_CLOUD_ACCESS_KEY_ID 或配置 access_key_id",
    )
    access_key_secret = require(
        os.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET") or config.get("access_key_secret"),
        "环境变量 ALIBABA_CLOUD_ACCESS_KEY_SECRET 或配置 access_key_secret",
    )

    # 如果调用方没有传 from/to，就按最近 N 分钟查询。
    now = int(time.time())
    from_time = parse_time(args.from_time) if args.from_time is not None else now - args.minutes * 60
    to_time = parse_time(args.to_time) if args.to_time is not None else now

    # LogClient 类似 Java SDK 里的客户端对象；GetLogsRequest 是请求 DTO。
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

    # 真正发起 SLS 查询。这里是脚本唯一的外部读取动作。
    response = client.get_logs(request)
    logs = response.get_logs()

    print(f"completed={response.is_completed()}, count={len(logs)}")
    for log in logs:
        # SDK 返回的 log.contents 是键值对列表，转成普通 dict 更利于模型阅读。
        row = dict(log.contents)
        if args.json:
            # JSON Lines：一行一条日志，方便后续 grep/jq 或模型逐条阅读。
            print(json.dumps(row, ensure_ascii=False))
        else:
            print(row)

    print("------------- Query finished ------------")


if __name__ == "__main__":
    main()
