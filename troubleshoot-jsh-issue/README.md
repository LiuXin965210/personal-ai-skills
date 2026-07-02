# Troubleshoot JSH Issue

根据 requestId、错误信息或接口 URL 查询阿里云 SLS 日志，并通过 GitLab API 按需读取 JSH/YLH 代码，定位异常服务、代码路径和链路断点。

## 适用场景

- 排查 `dev`、`pre`、`prod` 环境接口异常。
- 根据 requestId 定位错误堆栈和上下游调用。
- 根据错误关键字或 URL 检索 service-log/access-log。
- 按工程名 + 生产 tag、commit 或分支读取 GitLab 代码。

## 使用前准备

在技能目录创建本地 `sls_config.json`，可参考 `sls_config.example.json`：

```json
{
  "gitlab": {
    "base_url": "https://git.haier.net",
    "token": "YOUR_GITLAB_PERSONAL_ACCESS_TOKEN"
  },
  "access_key_id": "...",
  "access_key_secret": "..."
}
```

该文件包含敏感信息，不应提交到 Git。GitLab token 只从 `gitlab.token` 读取，不读取环境变量。

## 使用方式

使用 requestId：

```text
使用 troubleshoot-jsh-issue 排查 prod 环境，
requestId 是 xxxxx
```

使用错误信息：

```text
排查 pre 环境错误 message：库存占用失败，
时间大约是 2026-06-11 14:00
```

使用接口 URL：

```text
排查 dev 环境 /api/page/order/create 最近 2 小时的异常
```

指定生产 tag：

```text
排查 prod 环境 requestId xxxxx，工程 jsh-service-purchase-order-sync 的生产 tag 是 v1.2.3
```

生产 tag 必须带工程名/服务名。各工厂/工程的 tag 相互独立，不能只凭 tag 号定位代码。
如果指定 tag 在该工程中不存在，技能会按环境默认分支继续分析：`dev` 用 `dev`，`pre`/`prod` 用 `master`，并在报告中提醒未找到具体 tag 的代码。

## 输出结果

- 查询过程和关键 SLS 证据。
- 异常服务、接口、状态码、耗时和堆栈。
- GitLab 项目、ref、文件、类、方法和行号。
- 服务版本、断点原因、证据缺口和可选 Mermaid 流程图。

## 安全边界

- 仅通过技能附带脚本和阿里云 SLS SDK 查询日志。
- 仅通过技能附带脚本和 GitLab API 按需读取代码文件。
- 不会调用业务 HTTP/RPC 接口、数据库、Redis 或消息队列复现问题。
- 最多递进执行 10 次 SLS 查询，每次最多返回 10 条日志。
- 禁止本地 `code_root`、`git clone`、浅克隆、`git archive` 和仓库临时目录。
