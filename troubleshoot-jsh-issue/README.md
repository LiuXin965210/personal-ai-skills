# Troubleshoot JSH Issue

根据 requestId、错误信息或接口 URL 查询阿里云 SLS 日志，并结合本地 JSH/YLH 代码定位异常服务、代码路径和链路断点。

## 适用场景

- 排查 `dev`、`pre`、`prod` 环境接口异常。
- 根据 requestId 定位错误堆栈和上下游调用。
- 根据错误关键字或 URL 检索 service-log/access-log。
- 核对部署分支、代码版本和异常发生位置。

## 使用前准备

在技能目录创建本地 `sls_config.json`，可参考 `sls_config.example.json`：

```json
{
  "code_root": "/path/to/jsh/code",
  "access_key_id": "...",
  "access_key_secret": "..."
}
```

该文件包含敏感信息，不应提交到 Git。

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

## 输出结果

- 查询过程和关键 SLS 证据。
- 异常服务、接口、状态码、耗时和堆栈。
- 本地代码文件、类和方法。
- 目标分支、版本及代码新鲜度。
- 明确的断点原因、证据缺口和可选 Mermaid 流程图。

## 安全边界

- 仅通过技能附带脚本和阿里云 SLS SDK 查询日志。
- 不会调用业务 HTTP/RPC 接口、数据库、Redis 或消息队列复现问题。
- 最多递进执行 5 次 SLS 查询，每次最多返回 10 条日志。
- 允许在已确认的 Git 仓库中执行 `git fetch` 更新远端引用，但不会执行 `git pull` 或修改工作区。
- `code_root` 无效时只根据日志推理，并明确说明缺少代码证据。
