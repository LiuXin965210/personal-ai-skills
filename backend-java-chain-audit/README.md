# Backend Java Chain Audit

根据 HTTP 接口路径或消息队列 Topic，在 Java/Spring 后端工程中定位入口并梳理完整调用链，输出 MySQL 表、Redis Key、中间件资源及外围接口。

## 适用场景

- 查询某个 HTTP 接口读写了哪些数据库表。
- 梳理 Redis、ES、MongoDB、Kafka、RabbitMQ、RocketMQ 资源。
- 确认 Feign、Dubbo、HTTP/RPC 外围调用的完整服务名、HTTP 方法和接口路径。
- 从 MQ Topic 或 Queue 定位消费者并分析后续链路。

## 使用方式

调用时至少提供：

- 后端工程根目录。
- HTTP 接口路径或 MQ Topic，二者至少一个。

```text
使用 backend-java-chain-audit 梳理 ylh-cloud-service-order
/api/page/order/retail/customer/insert-retail-order 接口，
代码根目录在 /path/to/backend/code
```

分析 MQ：

```text
使用 backend-java-chain-audit 扫描 order_create_topic，
项目地址是 /path/to/project
```

## 输出模式

- **精简模式（默认）**：只输出总览表，适合快速查看调用链、表、缓存、MQ 和外围接口。
- **完整模式**：需要在提示词中明确写“完整模式”或“详细报告”，输出调用链证据、资源明细和待确认项。

开启外围接口或 MQ 递进扫描时请明确说明，并可指定深度：

```text
使用完整模式，开启外围接口和 MQ 递进扫描，最大深度 3
```

## 输出结果

默认在当前工作目录生成 Markdown 文件。精简模式会删除证据文件和备注列；MySQL 表按“写入/只读”区分，Redis 只显示 Key。外围 HTTP 调用使用以下格式：

```text
完整服务名 HTTP方法 /完整接口路径
```

例如：

```text
ylh-cloud-service-stock POST /api/composite/stock/iprp/iprp-update
```

## 注意事项

- 扫描脚本只生成候选结果，最终结论还会人工核对关键源码。
- 精简模式仅精简报告，不会缩小代码扫描范围。
- 外围接口递进和 MQ 递进默认关闭。
- 对端工程未拉取或配置值无法确认时，报告会标记为待确认或跳过。
