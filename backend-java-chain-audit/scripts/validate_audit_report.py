#!/usr/bin/env python3
"""校验链路审计报告中的外围接口是否可复查。"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


EXPECTED_HEADERS = [
    "完整服务名",
    "服务配置/地址证据",
    "客户端类/方法",
    "HTTP方法",
    "完整接口路径",
    "用途",
    "条件",
    "状态",
]
HTTP_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
SHORT_SERVICE_NAMES = {
    "goods",
    "stock",
    "price",
    "user",
    "user/member",
    "goods/stock",
    "base",
    "fund",
    "message/notice",
    "oms openapi",
    "oms order",
}
VAGUE_PATH_WORDS = ("接口", "相关", "详情/", "模板/", "仓库优先级")


def clean_cell(value: str) -> str:
    return value.strip().strip("`").strip()


def parse_table(lines: list[str]) -> tuple[int, list[list[str]]] | None:
    for index, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            continue
        headers = [clean_cell(cell) for cell in line.strip().strip("|").split("|")]
        if headers != EXPECTED_HEADERS:
            continue
        rows: list[list[str]] = []
        for row_line in lines[index + 2 :]:
            if not row_line.lstrip().startswith("|"):
                break
            cells = [clean_cell(cell) for cell in row_line.strip().strip("|").split("|")]
            if len(cells) == len(EXPECTED_HEADERS):
                rows.append(cells)
        return index + 1, rows
    return None


def is_pending(value: str) -> bool:
    return value.startswith("待确认") or value.startswith("推断")


def validate_row(row_number: int, cells: list[str]) -> list[str]:
    service, evidence, client, http_method, path, _, _, status = cells
    errors: list[str] = []
    confirmed = status in {"已确认", "已完成"}

    if confirmed and (service.lower() in SHORT_SERVICE_NAMES or is_pending(service)):
        errors.append("完整服务名仍是简称或待确认值")
    if confirmed and not evidence:
        errors.append("缺少服务配置/地址证据")
    if confirmed and ("." not in client or " " in client):
        errors.append("客户端类/方法必须形如 Class.method")

    rpc_not_applicable = path.startswith("不适用") and http_method.startswith("不适用")
    if confirmed and not rpc_not_applicable:
        if http_method not in HTTP_METHODS and http_method != "未声明（RequestMapping）":
            errors.append("HTTP方法未解析")
        if not path.startswith("/"):
            errors.append("完整接口路径必须以 / 开头")

    if confirmed and any(word in path.lower() for word in VAGUE_PATH_WORDS):
        errors.append("完整接口路径仍是概括文字")
    if confirmed and re.fullmatch(r"[A-Za-z_$][\w$]*", path):
        errors.append("完整接口路径不能使用 Java 方法名")
    if status == "待确认" and not any(is_pending(value) for value in (service, evidence, http_method, path)):
        errors.append("状态为待确认，但未写明具体待确认字段")

    return [f"第 {row_number} 行：{error}" for error in errors]


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 Java 后端链路报告的外围接口表")
    parser.add_argument("report", help="Markdown 报告路径")
    args = parser.parse_args()

    report = Path(args.report).expanduser().resolve()
    if not report.is_file():
        raise SystemExit(f"报告不存在：{report}")

    lines = report.read_text(encoding="utf-8", errors="ignore").splitlines()
    parsed = parse_table(lines)
    if parsed is None:
        raise SystemExit("校验失败：未找到规定格式的外围接口表。")

    header_line, rows = parsed
    if not rows:
        raise SystemExit("校验失败：外围接口表没有数据行。")

    errors: list[str] = []
    for offset, row in enumerate(rows, start=2):
        errors.extend(validate_row(header_line + offset, row))

    if errors:
        print("外围接口表校验失败：")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"外围接口表校验通过：{len(rows)} 行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
