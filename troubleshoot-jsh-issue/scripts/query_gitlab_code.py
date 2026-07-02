#!/usr/bin/env python3
# encoding: utf-8
"""
通过 GitLab API 读取代码的小工具。

可以把这个文件理解成一个只读的 Java Service：

- load_config / gitlab_config：读取配置，类似读取 application.yml。
- request_json_or_text：统一 HTTP 客户端，类似封装 RestTemplate/WebClient。
- command_xxx：每个子命令对应一个用例方法。
- success / fail：统一响应 DTO，所有输出都是 JSON，方便 Codex 稳定解析。

脚本只调用 GitLab API，不使用本地代码目录，不执行 git clone，不生成仓库临时目录。
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
DEFAULT_CONFIG = os.path.join(SKILL_DIR, "sls_config.json")
DEFAULT_BASE_URL = "https://git.haier.net"


def load_config(path):
    """
    读取 sls_config.json。

    这个技能强制 GitLab token 写在配置文件的 gitlab.token 中，
    所以配置不存在时直接失败，不尝试从环境变量兜底。
    """
    if not os.path.exists(path):
        fail("CONFIG_NOT_FOUND", f"配置文件不存在：{path}", status=2)
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def fail(code, message, status=1, **extra):
    """
    统一失败输出。

    类似 Java 里的 Result.fail(code, message, data)。
    注意这里不会输出 token；extra 只放 HTTP 状态、操作名、GitLab 返回体等排查信息。
    """
    payload = {"ok": False, "error": {"code": code, "message": message}}
    payload.update(extra)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(status)


def success(**payload):
    """统一成功输出，类似 Java 里的 Result.ok(data)。"""
    payload = {"ok": True, **payload}
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def gitlab_config(config):
    """
    从配置对象中取 GitLab 连接信息。

    当前约定：
    {
      "gitlab": {
        "base_url": "https://git.haier.net",
        "token": "..."
      }
    }
    """
    gitlab = config.get("gitlab") or {}
    base_url = (gitlab.get("base_url") or DEFAULT_BASE_URL).rstrip("/")
    token = gitlab.get("token")
    if not token:
        fail("TOKEN_MISSING", "缺少配置 gitlab.token", status=2)
    return base_url, token


def request_json_or_text(base_url, token, method, path, params=None, raw=False):
    """
    统一调用 GitLab API。

    参数含义：
    - base_url：GitLab 站点根地址，例如 https://git.haier.net。
    - token：Personal Access Token，只放到请求头里，不打印。
    - method：目前都是 GET，保留参数是为了结构清晰。
    - path：API path，例如 /api/v4/projects。
    - params：query string 参数，函数内部统一 URL encode。
    - raw：True 表示读取文件原文；False 表示按 JSON 解析。

    返回值固定为三元组：
    (HTTP 状态码, 响应内容, Content-Type)

    这里故意不在 HTTPError 时直接抛异常，而是把 401/403/404 也转成返回值，
    这样上层可以输出结构化错误，告诉用户到底是无权限、找不到项目还是 ref 不存在。
    """
    query = ""
    if params:
        query = "?" + urllib.parse.urlencode(params)
    url = f"{base_url}{path}{query}"

    # urllib 是 Python 标准库，不需要 requests 之类第三方依赖。
    request = urllib.request.Request(url, method=method)
    request.add_header("PRIVATE-TOKEN", token)
    request.add_header("Accept", "application/json" if not raw else "*/*")

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
            content_type = response.headers.get("Content-Type", "")
            if raw:
                # 文件内容可能是 Java、XML、YAML 等文本，不按 JSON 解析。
                return response.status, body.decode("utf-8", errors="replace"), content_type
            if not body:
                return response.status, None, content_type
            return response.status, json.loads(body.decode("utf-8")), content_type
    except urllib.error.HTTPError as exc:
        # GitLab 的 401/403/404 也可能带 JSON body，例如 {"message":"403 Forbidden"}。
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body) if body else None
        except json.JSONDecodeError:
            parsed = body
        return exc.code, parsed, exc.headers.get("Content-Type", "")
    except urllib.error.URLError as exc:
        # 网络不可达、DNS、TLS 等底层异常统一为 NETWORK_ERROR。
        fail("NETWORK_ERROR", str(exc.reason))


def api_error(status_code, body, operation):
    """把 GitLab HTTP 状态转换成更适合排障报告使用的错误码。"""
    if status_code in (401, 403):
        code = "FORBIDDEN" if status_code == 403 else "UNAUTHORIZED"
        message = "GitLab token 无仓库读取权限或已失效"
    elif status_code == 404:
        code = "NOT_FOUND"
        message = "项目、ref 或文件不存在；私有项目也可能因无权限返回 404"
    else:
        code = "GITLAB_API_ERROR"
        message = "GitLab API 调用失败"
    fail(code, message, http_status=status_code, operation=operation, response=body)


def require_success(status_code, body, operation):
    """要求 HTTP 2xx，否则统一输出 GitLab API 错误并退出。"""
    if 200 <= status_code < 300:
        return
    api_error(status_code, body, operation)


def encode_project(project):
    """
    URL encode GitLab project 参数。

    GitLab API 支持项目 ID，也支持 path_with_namespace。
    path_with_namespace 里有斜杠，例如 jsh/backend/demo，必须编码成 jsh%2Fbackend%2Fdemo。
    """
    return urllib.parse.quote(str(project), safe="")


def encode_file_path(path):
    """
    URL encode 文件路径。

    Repository Files API 要求文件路径整体 encode：
    src/main/java/A.java -> src%2Fmain%2Fjava%2FA.java
    """
    return urllib.parse.quote(path, safe="")


def project_ref(args):
    """统一取得项目标识；调用方可以传 project-id，也可以传 project-path。"""
    return args.project_id or args.project_path


def command_search_project(base_url, token, args):
    """
    search-project 子命令。

    用服务名搜索 GitLab 项目。输出只保留排障需要的字段，
    避免把 GitLab 项目完整响应全部塞进上下文。
    """
    status_code, body, _ = request_json_or_text(
        base_url,
        token,
        "GET",
        "/api/v4/projects",
        params={"search": args.query, "simple": "false", "per_page": args.per_page},
    )
    require_success(status_code, body, "search-project")

    projects = []
    for item in body or []:
        # 这里相当于把 GitLab Project DTO 映射成我们自己的轻量 DTO。
        projects.append(
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "path": item.get("path"),
                "path_with_namespace": item.get("path_with_namespace"),
                "default_branch": item.get("default_branch"),
                "visibility": item.get("visibility"),
                "web_url": item.get("web_url"),
            }
        )
    success(operation="search-project", query=args.query, count=len(projects), projects=projects)


def command_verify_ref(base_url, token, args):
    """
    verify-ref 子命令。

    GitLab 的 ref 可能是 branch、tag 或 commit SHA。
    生产排查时 tag/commit 比 master 更可信，所以先验证用户或日志给出的 ref 是否存在。
    """
    project = encode_project(project_ref(args))
    encoded_ref = urllib.parse.quote(args.ref, safe="")

    # 依次按 branch、tag、commit 校验。任何一种成功，就认为 ref 可用。
    checks = [
        ("branch", f"/api/v4/projects/{project}/repository/branches/{encoded_ref}"),
        ("tag", f"/api/v4/projects/{project}/repository/tags/{encoded_ref}"),
        ("commit", f"/api/v4/projects/{project}/repository/commits/{encoded_ref}"),
    ]

    failures = []
    for ref_type, path in checks:
        status_code, body, _ = request_json_or_text(base_url, token, "GET", path)
        if 200 <= status_code < 300:
            success(
                operation="verify-ref",
                project=project_ref(args),
                ref=args.ref,
                ref_type=ref_type,
                result=body,
            )
            return
        failures.append({"ref_type": ref_type, "http_status": status_code, "response": body})
        if status_code in (401, 403):
            # 权限问题没有必要继续尝试其它类型，直接失败。
            api_error(status_code, body, "verify-ref")

    fail(
        "REF_NOT_FOUND",
        "指定 ref 不是可访问的 branch、tag 或 commit",
        project=project_ref(args),
        ref=args.ref,
        failures=failures,
    )


def command_search_code(base_url, token, args):
    """
    search-code 子命令。

    调 GitLab 项目内搜索 API，在指定 ref 上查类名、方法名、日志文本等符号。
    注意它不是全文下载仓库，而是让 GitLab 服务端帮我们搜。
    """
    project = encode_project(project_ref(args))
    status_code, body, _ = request_json_or_text(
        base_url,
        token,
        "GET",
        f"/api/v4/projects/{project}/search",
        params={
            "scope": "blobs",
            "search": args.query,
            "ref": args.ref,
            "per_page": args.per_page,
        },
    )
    require_success(status_code, body, "search-code")

    results = []
    for item in body or []:
        # GitLab search API 的结果里可能包含片段内容；这里不输出片段，避免上下文过大。
        results.append(
            {
                "filename": item.get("filename"),
                "path": item.get("path"),
                "ref": item.get("ref"),
                "startline": item.get("startline"),
                "project_id": item.get("project_id"),
            }
        )
    success(
        operation="search-code",
        project=project_ref(args),
        ref=args.ref,
        query=args.query,
        count=len(results),
        results=results,
    )


def command_get_file(base_url, token, args):
    """
    get-file 子命令。

    读取指定文件，并可只返回某个行号范围。
    这对大 Java 文件很重要：排查时通常只需要方法附近几十行，不需要整文件。
    """
    project = encode_project(project_ref(args))
    encoded_path = encode_file_path(args.path)
    status_code, text, content_type = request_json_or_text(
        base_url,
        token,
        "GET",
        f"/api/v4/projects/{project}/repository/files/{encoded_path}/raw",
        params={"ref": args.ref},
        raw=True,
    )
    require_success(status_code, text, "get-file")

    # splitlines() 不保留换行符，返回结果更像 IDE 里的“行号 + 行内容”。
    lines = text.splitlines()
    start = args.start_line if args.start_line is not None else 1
    end = args.end_line if args.end_line is not None else len(lines)
    if start < 1:
        fail("INVALID_LINE_RANGE", "--start-line 必须大于 0", status=2)
    if end < start:
        fail("INVALID_LINE_RANGE", "--end-line 必须大于等于 --start-line", status=2)

    selected = []
    for number in range(start, min(end, len(lines)) + 1):
        # 行号从 1 开始，符合 IDE 和异常堆栈里的行号习惯。
        selected.append({"line": number, "text": lines[number - 1]})

    success(
        operation="get-file",
        project=project_ref(args),
        ref=args.ref,
        path=args.path,
        content_type=content_type,
        total_lines=len(lines),
        start_line=start,
        end_line=end,
        lines=selected,
    )


def build_parser():
    """
    定义命令行接口。

    脚本支持两种 --config 写法：
    1. python scripts/query_gitlab_code.py --config sls_config.json search-project ...
    2. python scripts/query_gitlab_code.py search-project --config sls_config.json ...

    这是为了兼容不同人的命令习惯。
    """
    parser = argparse.ArgumentParser(description="Query GitLab repository metadata and files.")
    parser.add_argument("--config", default=DEFAULT_CONFIG, help=f"JSON 配置文件路径，默认读取 {DEFAULT_CONFIG}")

    config_parent = argparse.ArgumentParser(add_help=False)
    config_parent.add_argument("--config", default=argparse.SUPPRESS, help=f"JSON 配置文件路径，默认读取 {DEFAULT_CONFIG}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    search_project = subparsers.add_parser("search-project", parents=[config_parent], help="按项目名或服务名搜索 GitLab 项目")
    search_project.add_argument("--query", required=True)
    search_project.add_argument("--per-page", type=int, default=20)

    verify_ref = subparsers.add_parser("verify-ref", parents=[config_parent], help="校验 branch、tag 或 commit 是否存在")
    add_project_args(verify_ref)
    verify_ref.add_argument("--ref", required=True)

    search_code = subparsers.add_parser("search-code", parents=[config_parent], help="在指定项目和 ref 下搜索代码")
    add_project_args(search_code)
    search_code.add_argument("--ref", required=True)
    search_code.add_argument("--query", required=True)
    search_code.add_argument("--per-page", type=int, default=20)

    get_file = subparsers.add_parser("get-file", parents=[config_parent], help="读取指定文件，支持行号范围")
    add_project_args(get_file)
    get_file.add_argument("--ref", required=True)
    get_file.add_argument("--path", required=True)
    get_file.add_argument("--start-line", type=int)
    get_file.add_argument("--end-line", type=int)

    return parser


def add_project_args(parser):
    """多个子命令都需要项目标识；项目 ID 和项目路径二选一。"""
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--project-id")
    group.add_argument("--project-path")


def main():
    """脚本入口。解析参数、读取配置，再分发到对应子命令。"""
    parser = build_parser()
    args = parser.parse_args()
    config = load_config(args.config)
    base_url, token = gitlab_config(config)

    if args.command == "search-project":
        command_search_project(base_url, token, args)
    elif args.command == "verify-ref":
        command_verify_ref(base_url, token, args)
    elif args.command == "search-code":
        command_search_code(base_url, token, args)
    elif args.command == "get-file":
        command_get_file(base_url, token, args)
    else:
        parser.error(f"未知命令：{args.command}")


if __name__ == "__main__":
    main()
