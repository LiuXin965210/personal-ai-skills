#!/usr/bin/env python3
"""Fetch MySQL table schemas for entity-sync."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse


def parse_jdbc_url(jdbc_url: str) -> dict[str, Any]:
    if not jdbc_url.startswith("jdbc:mysql://"):
        raise ValueError("Only jdbc:mysql:// URLs are supported")

    parsed = urlparse(jdbc_url.removeprefix("jdbc:"))
    database = unquote(parsed.path.lstrip("/").split("/", 1)[0])
    if not parsed.hostname or not database:
        raise ValueError("JDBC URL must include host and database")

    query = parse_qs(parsed.query)
    charset = query.get("characterEncoding", ["utf8mb4"])[0] or "utf8mb4"
    if charset.lower().replace("-", "") == "utf8":
        charset = "utf8mb4"

    return {
        "host": parsed.hostname,
        "port": parsed.port or 3306,
        "database": database,
        "charset": charset,
    }


def load_driver():
    try:
        import pymysql  # type: ignore

        return "pymysql", pymysql
    except ImportError:
        pass

    try:
        import mysql.connector  # type: ignore

        return "mysql.connector", mysql.connector
    except ImportError:
        pass

    raise RuntimeError(
        "Missing MySQL Python driver. Install one of: python3 -m pip install PyMySQL mysql-connector-python"
    )


def fetch_schema(args: argparse.Namespace) -> list[dict[str, Any]]:
    config = parse_jdbc_url(args.jdbc_url)
    password = args.password or os.environ.get(args.password_env or "") or ""
    if args.prompt_password and not password:
        password = getpass.getpass("MySQL password: ")

    driver_name, driver = load_driver()
    if driver_name == "pymysql":
        conn = driver.connect(
            host=config["host"],
            port=config["port"],
            user=args.user,
            password=password,
            database=config["database"],
            charset="utf8mb4",
            cursorclass=driver.cursors.DictCursor,
        )
    else:
        conn = driver.connect(
            host=config["host"],
            port=config["port"],
            user=args.user,
            password=password,
            database=config["database"],
            charset="utf8mb4",
            use_unicode=True,
        )

    placeholders = ", ".join(["%s"] * len(args.table))
    sql = f"""
SELECT
    TABLE_NAME,
    COLUMN_NAME,
    COLUMN_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT,
    COLUMN_COMMENT,
    ORDINAL_POSITION
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = %s
  AND TABLE_NAME IN ({placeholders})
ORDER BY TABLE_NAME, ORDINAL_POSITION
"""

    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, [config["database"], *args.table])
            rows = cursor.fetchall()
    finally:
        conn.close()

    result: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["NULLABLE_TEXT"] = "允许为空" if item.get("IS_NULLABLE") == "YES" else "不允许为空"
        result.append(item)
    return result


def print_markdown(rows: list[dict[str, Any]]) -> None:
    print("| 表名 | 字段 | 类型 | 是否允许为空 | 默认值 | 注释 |")
    print("|------|------|------|--------------|--------|------|")
    for row in rows:
        default = "" if row.get("COLUMN_DEFAULT") is None else str(row["COLUMN_DEFAULT"])
        comment = row.get("COLUMN_COMMENT") or ""
        print(
            "| {table} | `{column}` | `{typ}` | {nullable} | {default} | {comment} |".format(
                table=row.get("TABLE_NAME", ""),
                column=row.get("COLUMN_NAME", ""),
                typ=row.get("COLUMN_TYPE", ""),
                nullable=row.get("NULLABLE_TEXT", ""),
                default=default,
                comment=str(comment).replace("|", "\\|"),
            )
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch MySQL table schemas from INFORMATION_SCHEMA.COLUMNS.")
    parser.add_argument("--jdbc-url", required=True, help="Spring JDBC URL, e.g. jdbc:mysql://host:3306/db")
    parser.add_argument("--user", required=True, help="MySQL username")
    parser.add_argument("--password", default="", help="MySQL password. Prefer --password-env or --prompt-password.")
    parser.add_argument("--password-env", default="", help="Environment variable that contains the MySQL password")
    parser.add_argument("--prompt-password", action="store_true", help="Prompt for password when it is not provided")
    parser.add_argument("--table", action="append", required=True, help="Table name. Repeat for multiple tables.")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args()

    rows = fetch_schema(args)
    if args.format == "json":
        print(json.dumps(rows, ensure_ascii=False, indent=2, default=str))
    else:
        print_markdown(rows)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
