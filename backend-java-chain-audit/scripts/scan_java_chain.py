#!/usr/bin/env python3
"""Heuristic scanner for Java backend endpoint/topic dependency reports."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


SKIP_DIRS = {".git", "target", "build", ".gradle", ".idea", "node_modules", "out"}
TEXT_EXTS = {".java", ".xml", ".yml", ".yaml", ".properties", ".sql"}


@dataclass
class Row:
    entry_type: str
    entry: str
    status: str = "待确认"
    summary: str = ""
    mysql_write: set[str] = field(default_factory=set)
    mysql_read: set[str] = field(default_factory=set)
    redis: set[str] = field(default_factory=set)
    es: set[str] = field(default_factory=set)
    mongo: set[str] = field(default_factory=set)
    kafka: set[str] = field(default_factory=set)
    rabbit: set[str] = field(default_factory=set)
    rocketmq: set[str] = field(default_factory=set)
    external: set[str] = field(default_factory=set)
    evidence: set[str] = field(default_factory=set)
    note: str = ""


def parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return value.lower() in {"1", "true", "yes", "y", "on", "开启", "是"}


def iter_source_files(project: Path) -> list[Path]:
    files: list[Path] = []
    for root, dirs, names in os.walk(project):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in names:
            path = Path(root) / name
            if path.suffix.lower() in TEXT_EXTS:
                files.append(path)
    return files


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def rel(path: Path, project: Path) -> str:
    try:
        return str(path.relative_to(project))
    except ValueError:
        return str(path)


def normalize_interface(value: str) -> str:
    value = value.strip().strip('"').strip("'")
    if not value:
        return value
    return value if value.startswith("/") else "/" + value


def string_literals(text: str) -> set[str]:
    return set(re.findall(r'"([^"\n]{2,200})"', text)) | set(re.findall(r"'([^'\n]{2,200})'", text))


def find_entry_files(files: Iterable[Path], needle: str, entry_type: str) -> list[Path]:
    result = []
    tokens = {needle, normalize_interface(needle)}
    if entry_type != "HTTP":
        tokens.add(needle.strip())
    for path in files:
        text = read_text(path)
        if entry_type in {"HTTP", "外部接口"}:
            if contains_mapping_http_path(text, normalize_interface(needle)):
                result.append(path)
            continue
        if any(t and t in text for t in tokens):
            result.append(path)
            continue
    return result


def contains_mapping_http_path(text: str, needle: str) -> bool:
    class_paths = [normalize_interface(v) for v in extract_mapping_values(text, r"RequestMapping")]
    method_paths: list[str] = []
    for mapping in ["RequestMapping", "GetMapping", "PostMapping", "PutMapping", "DeleteMapping", "PatchMapping"]:
        method_paths.extend(normalize_interface(v) for v in extract_mapping_values(text, mapping))
    if needle in class_paths or needle in method_paths:
        return True
    prefixes = class_paths or [""]
    suffixes = method_paths or [""]
    for prefix in prefixes:
        for suffix in suffixes:
            if normalize_interface(prefix.rstrip("/") + "/" + suffix.lstrip("/")) == needle:
                return True
    return False


def extract_mapping_values(text: str, annotation: str) -> list[str]:
    values: list[str] = []
    for match in re.finditer(rf"@{annotation}\s*\(([^)]*)\)", text, flags=re.DOTALL):
        body = match.group(1)
        values.extend(v for v in string_literals(body) if v.startswith("/"))
    return values


def extract_mysql(text: str) -> tuple[set[str], set[str]]:
    writes = set()
    reads = set()
    for pattern in [
        r"\binsert\s+into\s+([a-zA-Z_][\w.]*)",
        r"\bupdate\s+([a-zA-Z_][\w.]*)",
        r"\bdelete\s+from\s+([a-zA-Z_][\w.]*)",
        r"\breplace\s+into\s+([a-zA-Z_][\w.]*)",
    ]:
        writes.update(re.findall(pattern, text, flags=re.IGNORECASE))
    for pattern in [
        r"\bfrom\s+([a-zA-Z_][\w.]*)",
        r"\bjoin\s+([a-zA-Z_][\w.]*)",
    ]:
        reads.update(re.findall(pattern, text, flags=re.IGNORECASE))
    return clean_values(writes), clean_values(reads)


def extract_redis(text: str) -> set[str]:
    found = set()
    for pattern in [
        r'@Cache(?:able|Put|Evict)\s*\([^)]*(?:value|cacheNames)\s*=\s*"([^"]+)"',
        r"(?:RedisTemplate|StringRedisTemplate|redisTemplate|stringRedisTemplate)[\s\S]{0,240}?\"([^\"]{2,120})\"",
        r"\b(?:REDIS|CACHE|KEY|PREFIX)_[A-Z0-9_]*\s*=\s*\"([^\"]+)\"",
    ]:
        found.update(re.findall(pattern, text))
    return clean_values(found)


def extract_es(text: str) -> set[str]:
    found = set()
    for pattern in [
        r'@Document\s*\([^)]*indexName\s*=\s*"([^"]+)"',
        r"\b(?:index|setIndex|indexName)\s*\(\s*\"([^\"]+)\"",
        r"\b(?:ES|ELASTIC|INDEX)_[A-Z0-9_]*\s*=\s*\"([^\"]+)\"",
    ]:
        found.update(re.findall(pattern, text))
    return clean_values(found)


def extract_mongo(text: str) -> set[str]:
    found = set()
    for pattern in [
        r'@Document\s*\([^)]*collection\s*=\s*"([^"]+)"',
        r"\bMongoTemplate[\s\S]{0,240}?\"([^\"]{2,120})\"",
        r"\b(?:MONGO|COLLECTION)_[A-Z0-9_]*\s*=\s*\"([^\"]+)\"",
    ]:
        found.update(re.findall(pattern, text))
    return clean_values(found)


def extract_kafka(text: str) -> set[str]:
    found = set()
    for pattern in [
        r'@KafkaListener\s*\([^)]*topics?\s*=\s*\{?\s*"([^"]+)"',
        r"\bKafkaTemplate[\s\S]{0,240}?\.send\s*\(\s*\"([^\"]+)\"",
        r"\b(?:KAFKA|TOPIC)_[A-Z0-9_]*\s*=\s*\"([^\"]+)\"",
    ]:
        found.update(re.findall(pattern, text))
    return clean_values(found)


def extract_rabbit(text: str) -> set[str]:
    found = set()
    for pattern in [
        r'@RabbitListener\s*\([^)]*queues?\s*=\s*\{?\s*"([^"]+)"',
        r"\bRabbitTemplate[\s\S]{0,240}?convertAndSend\s*\(\s*\"([^\"]+)\"",
        r"\b(?:RABBIT|QUEUE|ROUTING_KEY|EXCHANGE)_[A-Z0-9_]*\s*=\s*\"([^\"]+)\"",
    ]:
        found.update(re.findall(pattern, text))
    return clean_values(found)


def extract_rocketmq(text: str) -> set[str]:
    found = set()
    for pattern in [
        r'@RocketMQMessageListener\s*\([^)]*topic\s*=\s*"([^"]+)"',
        r"\bRocketMQTemplate[\s\S]{0,240}?(?:syncSend|asyncSend|send)\s*\(\s*\"([^\"]+)\"",
        r"\b(?:ROCKET|ROCKETMQ)_[A-Z0-9_]*\s*=\s*\"([^\"]+)\"",
    ]:
        found.update(re.findall(pattern, text))
    return clean_values(found)


def extract_external(text: str) -> set[str]:
    found = set()
    for pattern in [
        r'@FeignClient\s*\([^)]*(?:name|value|contextId|url)\s*=\s*"([^"]+)"',
        r'@(?:DubboReference|Reference)\s*\([^)]*(?:interfaceName|url|group|version)\s*=\s*"([^"]+)"',
        r"\.(?:getForObject|postForObject|postForEntity|exchange|execute|uri|url)\s*\(\s*\"(https?://[^\"]+|/[a-zA-Z0-9_./{}-]+)\"",
        r"\b(?:HTTP|URL|RPC|FEIGN|DUBBO)_[A-Z0-9_]*\s*=\s*\"([^\"]+)\"",
    ]:
        found.update(re.findall(pattern, text))
    return clean_values(found)


def clean_values(values: Iterable[str]) -> set[str]:
    cleaned = set()
    for value in values:
        if isinstance(value, tuple):
            value = next((v for v in value if v), "")
        value = value.strip().strip("`").strip()
        if not value or value.startswith("${"):
            continue
        if len(value) > 160:
            continue
        cleaned.add(value)
    return cleaned


def summarize_files(paths: list[Path], project: Path) -> str:
    names = []
    for path in paths[:8]:
        text = read_text(path)
        cls = re.search(r"\b(?:class|interface)\s+(\w+)", text)
        meth = re.search(r"\b(public|private|protected)\s+[\w<>, ?]+\s+(\w+)\s*\(", text)
        label = cls.group(1) if cls else path.name
        if meth:
            label += "." + meth.group(2)
        names.append(label)
    return " -> ".join(dict.fromkeys(names)) or "未能自动生成调用链摘要"


def scan_entry(project: Path, files: list[Path], entry_type: str, entry: str) -> Row:
    entry = normalize_interface(entry) if entry_type == "HTTP" else entry.strip()
    row = Row(entry_type=entry_type, entry=entry)
    entry_files = find_entry_files(files, entry, entry_type)
    if not entry_files:
        row.status = "未找到入口" if entry_type != "外部接口" else "跳过-工程未拉取"
        row.note = "当前项目未找到入口或对应工程未拉取"
        return row

    row.evidence.update(rel(p, project) for p in entry_files[:20])
    row.summary = summarize_files(entry_files, project)
    candidate_text = "\n".join(read_text(p) for p in entry_files[:40])
    mysql_write, mysql_read = extract_mysql(candidate_text)
    row.mysql_write.update(mysql_write)
    row.mysql_read.update(mysql_read)
    row.redis.update(extract_redis(candidate_text))
    row.es.update(extract_es(candidate_text))
    row.mongo.update(extract_mongo(candidate_text))
    row.kafka.update(extract_kafka(candidate_text))
    row.rabbit.update(extract_rabbit(candidate_text))
    row.rocketmq.update(extract_rocketmq(candidate_text))
    row.external.update(extract_external(candidate_text))
    row.note = "脚本启发式候选，需人工源码核对"
    return row


def cell(values: Iterable[str] | str) -> str:
    if isinstance(values, str):
        return values or "无"
    items = sorted(v for v in values if v)
    return "<br>".join(f"`{v}`" for v in items[:30]) if items else "无"


def compact_external_cell(values: Iterable[str]) -> str:
    items = sorted(v for v in values if v)
    if not items:
        return "无"
    result = []
    for value in items[:30]:
        if value.startswith("/"):
            result.append(f"`待确认：完整服务名 待确认：HTTP方法 {value}`")
        else:
            result.append(f"`待确认：{value} 的完整服务名、HTTP方法和完整路径`")
    return "<br>".join(result)


def mysql_cell(row: Row) -> str:
    writes = "<br>".join(f"`{v}`" for v in sorted(row.mysql_write)[:30]) or "无"
    reads = "<br>".join(f"`{v}`" for v in sorted(row.mysql_read)[:30]) or "无"
    return f"写入：{writes}<br>只读：{reads}"


def overview_lines(rows: list[Row], compact: bool) -> list[str]:
    if compact:
        lines = [
            "| 入口类型 | 入口 | 状态 | 调用链摘要 | MySQL表 | Redis key | ES索引 | MongoDB表 | Kafka topic | RabbitMQ queue | RocketMQ topic | 外围接口 |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
    else:
        lines = [
            "| 入口类型 | 入口 | 状态 | 调用链摘要 | MySQL表 | Redis key | ES索引 | MongoDB表 | Kafka topic | RabbitMQ queue | RocketMQ topic | 外围接口 | 证据文件 | 备注 |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
    for row in rows:
        external = compact_external_cell(row.external) if compact else cell(row.external)
        values = [
            row.entry_type,
            f"`{row.entry}`",
            row.status,
            row.summary or "无",
            mysql_cell(row),
            cell(row.redis),
            cell(row.es),
            cell(row.mongo),
            cell(row.kafka),
            cell(row.rabbit),
            cell(row.rocketmq),
            external,
        ]
        if not compact:
            values.extend([cell(row.evidence), row.note or "无"])
        lines.append(
            "| "
            + " | ".join(values)
            + " |"
        )
    return lines


def write_markdown(
    output: Path,
    project: Path,
    interfaces: list[str],
    topics: list[str],
    scan_peripheral: bool,
    scan_mq: bool,
    max_depth: int,
    rows: list[Row],
    output_mode: str,
) -> None:
    if output_mode == "compact":
        output.write_text("\n".join(overview_lines(rows, compact=True)) + "\n", encoding="utf-8")
        return

    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Java 后端链路梳理",
        "",
        "## 输入参数与扫描边界",
        "",
        f"- 后端项目：`{project}`",
        f"- 接口路径：{cell(interfaces)}",
        f"- MQ topic：{cell(topics)}",
        f"- 外围接口递进扫描：`{'开启' if scan_peripheral else '关闭'}`",
        f"- MQ 递进扫描：`{'开启' if scan_mq else '关闭'}`",
        f"- 最大递归深度：`{max_depth}`",
        f"- 扫描时间：`{now}`",
        "",
        "## 总览表",
        "",
    ]
    lines.extend(overview_lines(rows, compact=False))
    lines.extend(["", "## 跳过清单", "", "| 类型 | 入口 | 原因 | 后续动作 |", "|---|---|---|---|"])
    skipped = [r for r in rows if r.status.startswith("跳过") or r.status in {"未找到入口", "未找到本地消费者"}]
    if skipped:
        for row in skipped:
            action = "待手动拉取项目后再处理" if row.status.startswith("跳过") else "检查路径/topic 或补充工程"
            lines.append(f"| {row.entry_type} | `{row.entry}` | {row.status} | {action} |")
    else:
        lines.append("| 无 | 无 | 无 | 无 |")
    lines.extend(["", "## 备注", "", "- 本文件由启发式静态扫描生成，最终结论必须结合人工源码追踪核对。"])
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan Java backend endpoint/topic dependencies into Markdown.")
    parser.add_argument("--project", required=True, help="Backend project directory")
    parser.add_argument("--interface", action="append", default=[], help="HTTP interface path, repeatable")
    parser.add_argument("--topic", action="append", default=[], help="MQ topic/queue, repeatable")
    parser.add_argument("--scan-peripheral", default="false", help="Whether to recursively scan external interfaces")
    parser.add_argument("--scan-mq", default="false", help="Whether to recursively scan MQ topics/queues")
    parser.add_argument("--max-depth", type=int, default=3, help="Maximum recursive depth")
    parser.add_argument(
        "--output-mode",
        choices=["compact", "full"],
        default="compact",
        help="Output mode: compact overview table (default) or full candidate report",
    )
    parser.add_argument("--output", default="backend-java-chain-audit-result.md", help="Output markdown file")
    args = parser.parse_args()

    project = Path(args.project).expanduser().resolve()
    if not project.exists() or not project.is_dir():
        raise SystemExit(f"项目路径不存在或不可读：{project}")
    if not args.interface and not args.topic:
        raise SystemExit("必须提供 --interface 或 --topic，至少一个。")

    files = iter_source_files(project)
    scan_peripheral = parse_bool(args.scan_peripheral)
    scan_mq = parse_bool(args.scan_mq)
    queue: deque[tuple[str, str, int]] = deque()
    for item in args.interface:
        queue.append(("HTTP", normalize_interface(item), 0))
    for item in args.topic:
        queue.append(("MQ", item.strip(), 0))

    rows: list[Row] = []
    visited: set[str] = set()
    while queue:
        entry_type, entry, depth = queue.popleft()
        key = f"{entry_type}:{entry}"
        if key in visited:
            continue
        visited.add(key)

        row = scan_entry(project, files, entry_type, entry)
        if entry_type == "MQ" and depth > 0 and row.status == "未找到入口":
            row.status = "未找到本地消费者"
            row.note = "递进扫描未在当前项目找到本地消费者"
        rows.append(row)
        if depth >= args.max_depth:
            continue

        if scan_peripheral:
            for external in sorted(row.external):
                next_type = "外部接口"
                queue.append((next_type, external, depth + 1))
        if scan_mq:
            for topic in sorted(row.kafka | row.rabbit | row.rocketmq):
                queue.append(("MQ", topic, depth + 1))

    output = Path(args.output).expanduser().resolve()
    write_markdown(
        output,
        project,
        args.interface,
        args.topic,
        scan_peripheral,
        scan_mq,
        args.max_depth,
        rows,
        args.output_mode,
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
