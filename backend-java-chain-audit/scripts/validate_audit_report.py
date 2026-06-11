#!/usr/bin/env python3
"""校验完整或精简模式的 Java 后端链路审计报告。"""

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
OVERVIEW_HEADERS = [
    "入口类型",
    "入口",
    "状态",
    "调用链摘要",
    "MySQL表",
    "Redis key",
    "ES索引",
    "MongoDB表",
    "Kafka topic",
    "RabbitMQ queue",
    "RocketMQ topic",
    "外围接口",
]
FULL_OVERVIEW_HEADERS = OVERVIEW_HEADERS + ["证据文件", "备注"]
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


def parse_table(lines: list[str], expected_headers: list[str]) -> tuple[int, list[list[str]]] | None:
    for index, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            continue
        headers = [clean_cell(cell) for cell in line.strip().strip("|").split("|")]
        if headers != expected_headers:
            continue
        rows: list[list[str]] = []
        for row_line in lines[index + 2 :]:
            if not row_line.lstrip().startswith("|"):
                break
            cells = [clean_cell(cell) for cell in row_line.strip().strip("|").split("|")]
            if len(cells) == len(expected_headers):
                rows.append(cells)
        return index + 1, rows
    return None


def validate_compact_external(row_number: int, value: str, status: str) -> list[str]:
    if value == "无":
        return []
    errors: list[str] = []
    for item in value.split("<br>"):
        item = clean_cell(item)
        if "见章节" in item or "见明细" in item:
            errors.append(f"第 {row_number} 行：外围接口不能引用其他章节")
            continue
        pending = "待确认：" in item or "推断：" in item
        if pending:
            if status in {"已完成", "已确认"}:
                errors.append(f"第 {row_number} 行：外围接口存在待确认项，入口状态不能是已完成")
            continue
        parts = item.split(maxsplit=2)
        if len(parts) != 3:
            errors.append(f"第 {row_number} 行：外围接口必须为 完整服务名 HTTP方法 完整路径")
            continue
        service, http_method, path = parts
        if service.lower() in SHORT_SERVICE_NAMES:
            errors.append(f"第 {row_number} 行：外围接口服务名仍是简称 {service}")
        if http_method not in HTTP_METHODS and http_method not in {"Dubbo", "RPC"}:
            errors.append(f"第 {row_number} 行：外围接口 HTTP 方法无效 {http_method}")
        if http_method in HTTP_METHODS and not path.startswith("/"):
            errors.append(f"第 {row_number} 行：外围接口路径必须以 / 开头")
    return errors


def validate_compact_mysql(row_number: int, value: str) -> list[str]:
    if value == "无":
        return [f"第 {row_number} 行：MySQL表必须明确写入和只读分类"]
    errors: list[str] = []
    if "写入：" not in value or "只读：" not in value:
        errors.append(f"第 {row_number} 行：MySQL表必须同时包含 写入： 和 只读：")
    if any(label in value for label in ("核心：", "条件：", "必经：")):
        errors.append(f"第 {row_number} 行：MySQL表不能按核心、条件或必经分类")
    return errors


def validate_compact_redis(row_number: int, value: str) -> list[str]:
    if value == "无":
        return []
    forbidden = ("ttl", "分钟", "小时", "过期", "操作：", "用途：", "类型：")
    lowered = value.lower()
    has_type_label = re.search(r"\btype\s*[:：]", lowered) is not None
    if any(word in lowered for word in forbidden) or has_type_label:
        return [f"第 {row_number} 行：Redis key 只能输出 Key 值，不能包含 TTL、类型或用途"]
    return []


def validate_compact(lines: list[str]) -> list[str]:
    nonempty = [line for line in lines if line.strip()]
    parsed = parse_table(nonempty, OVERVIEW_HEADERS)
    if parsed is None:
        return ["未找到规定格式的总览表"]
    header_line, rows = parsed
    if header_line != 1:
        return ["精简模式不能在总览表前输出标题或说明"]
    if len(nonempty) != len(rows) + 2:
        return ["精简模式只能包含总览表头、分隔行和数据行"]
    if not rows:
        return ["总览表没有数据行"]

    errors: list[str] = []
    for offset, row in enumerate(rows, start=3):
        status = row[2]
        errors.extend(validate_compact_mysql(offset, row[4]))
        errors.extend(validate_compact_redis(offset, row[5]))
        errors.extend(validate_compact_external(offset, row[11], status))
    return errors


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
    parser = argparse.ArgumentParser(description="校验完整或精简模式的 Java 后端链路报告")
    parser.add_argument("report", help="Markdown 报告路径")
    parser.add_argument("--mode", choices=["compact", "full"], default="compact")
    args = parser.parse_args()

    report = Path(args.report).expanduser().resolve()
    if not report.is_file():
        raise SystemExit(f"报告不存在：{report}")

    lines = report.read_text(encoding="utf-8", errors="ignore").splitlines()
    if args.mode == "compact":
        errors = validate_compact(lines)
        if errors:
            print("精简报告校验失败：")
            for error in errors:
                print(f"- {error}")
            return 1
        print("精简报告校验通过")
        return 0

    overview = parse_table(lines, FULL_OVERVIEW_HEADERS)
    if overview is None:
        raise SystemExit("校验失败：未找到规定格式的总览表。")
    overview_header_line, overview_rows = overview
    if not overview_rows:
        raise SystemExit("校验失败：总览表没有数据行。")

    overview_errors: list[str] = []
    for offset, row in enumerate(overview_rows, start=2):
        overview_errors.extend(validate_compact_mysql(overview_header_line + offset, row[4]))
    if overview_errors:
        print("总览表校验失败：")
        for error in overview_errors:
            print(f"- {error}")
        return 1

    parsed = parse_table(lines, EXPECTED_HEADERS)
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
