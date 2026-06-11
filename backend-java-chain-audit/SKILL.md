---
name: backend-java-chain-audit
description: 根据接口路径或消息队列 topic 定位 Java/Spring 后端代码入口，并梳理调用链中的 MySQL 表、中间件资源、外围接口和递进链路，输出包含完整服务名及具体 HTTP 方法和路径的 Markdown 文件。适用于用户提供 HTTP 接口路径或 MQ topic、后端项目地址，并要求扫描 Java 后端工程、识别 Redis/ES/MongoDB/Kafka/RabbitMQ/RocketMQ、Feign/Dubbo/HTTP/RPC 调用，或按开关递归扫描外围接口和 MQ 消费者链路的场景。
---

# Java 后端链路梳理

## 输入要求

- 必须提供后端项目地址，先确认目录存在且可读。
- 必须提供接口路径或消息队列 topic，二者至少一个存在；都提供时分别作为独立起点扫描。
- 外围接口递进扫描默认关闭；只有用户明确开启时，才把识别到的 Feign/Dubbo/HTTP/RPC 外围接口继续作为新入口扫描。
- 消息队列递进扫描默认关闭；只有用户明确开启时，才把识别到的 Kafka/RabbitMQ/RocketMQ topic/queue 继续作为新入口扫描。
- 递归深度只限制“外围接口递进扫描”和“消息队列递进扫描”产生的新入口数量与层级；不开启这两个递进开关时，主接口或主 topic 的自身调用链不受递归深度影响，仍要沿 Controller/Consumer -> Service -> Manager -> Mapper/Client/Producer 等真实业务链路展开到可确认边界。
- 若递进扫描时发现外围接口对应的工程不在本地后端项目中，标记为 `跳过-工程未拉取` 或 `待拉取项目后处理`，不要阻塞主链路输出。

## 工作流程

1. 校验输入：确认项目路径、接口路径或 MQ topic、递进扫描开关。
2. 建立代码索引：优先用 `rg --files` 找 Java、XML、YAML、properties、SQL 文件；排除 `target/`、`build/`、`.git/`、`node_modules/`。
3. 定位主入口：
   - 接口路径：搜索 `@RequestMapping`、`@GetMapping`、`@PostMapping`、`@PutMapping`、`@DeleteMapping`、`@PatchMapping` 和路径常量。
   - MQ topic：搜索 `@KafkaListener`、`@RabbitListener`、`@RocketMQMessageListener`、`KafkaTemplate`、`RabbitTemplate`、`RocketMQTemplate`、配置文件 topic/queue。
4. 跟踪调用链：从 Controller/Consumer 出发，阅读 Service、Manager、Mapper、Repository、Client、Producer、Consumer、XML mapper 和配置文件。不要只停在 wrapper、Feign 接口或工具方法名；要展开真实业务调用链。
5. 记录链路资源：
   - MySQL：表名、Mapper XML、JPA `@Table`、SQL 中的 `from/insert/update/delete/join`。
   - Redis：缓存 key、key prefix、`@Cacheable/@CachePut/@CacheEvict`、`RedisTemplate/StringRedisTemplate`。
   - ES：索引名、`@Document(indexName)`、index alias、ES client 写入/查询。
   - MongoDB：collection/table 名、`@Document(collection)`、`MongoTemplate` collection。
   - Kafka：生产/消费 topic。
   - RabbitMQ：queue、exchange、routingKey，无法确认 queue 时写明只识别到 exchange/routingKey。
   - RocketMQ：生产/消费 topic、tag。
   - 外围接口：Feign、Dubbo、HTTP 工具类、RestTemplate、WebClient、OkHttp、Apache HttpClient、其他 RPC。按 [外围接口解析规则](references/peripheral-interface-resolution.md) 解析服务名、HTTP 方法和完整路径。
6. 递进扫描：
   - 只在外围接口递进扫描或 MQ 递进扫描开启时应用递归深度；主入口内部调用链梳理不按该深度截断。
   - 维护 `visited` 集合，key 使用 `type:value`，例如 `http:/api/order/save`、`kafka:order_topic`。
   - 设置深度上限，默认最多 3 层；用户未要求深度时不要无限扩展。
   - 外围接口递进开启时，对每个外围接口尝试在本地项目中定位入口；找不到对应工程或入口时在该行状态标记为跳过。
   - MQ 递进开启时，对每个 topic/queue 继续定位消费者；找不到消费者时标记 `未找到本地消费者`。
   - 同一个入口重复出现时只保留一次，并在备注中说明被其他入口引用。
7. 交叉核对：脚本扫描结果只能作为候选证据；最终输出前必须人工阅读关键源码，补齐漏掉的 service/self-call/配置常量/MQ producer/consumer 链路，并剔除明显误报。
8. 校验外围接口完整度：逐条检查服务完整名称、客户端类/方法、HTTP 方法和完整接口路径；只有方法名、中文概括或“某某接口”不算完成。
9. 运行 `python3 backend-java-chain-audit/scripts/validate_audit_report.py <报告路径>`；校验失败时补齐报告，不能直接交付。
10. 输出 Markdown 文件：默认写到当前工作目录，文件名建议 `backend-java-chain-audit-<项目名>.md`；用户指定路径时按用户要求。

## 推荐脚本

先运行启发式扫描脚本生成候选 Markdown，再人工核对：

```bash
python3 backend-java-chain-audit/scripts/scan_java_chain.py \
  --project /path/to/backend-project \
  --interface /api/order/save \
  --topic order_event_topic \
  --scan-peripheral false \
  --scan-mq false \
  --output backend-java-chain-audit-result.md
```

脚本用途是快速定位入口和候选资源，不代表最终结论。遇到脚本漏扫时，优先通过源码追踪补齐输出；如果漏扫模式可复用，再更新脚本。

人工报告完成后运行质量校验：

```bash
python3 backend-java-chain-audit/scripts/validate_audit_report.py \
  backend-java-chain-audit-result.md
```

## 输出格式

Markdown 文件必须包含：

1. 输入参数与扫描边界：项目路径、入口、递进开关、深度上限、扫描时间。
2. 总览表：以接口或 topic 维度一行输出。
3. 明细：每个入口一节，列出证据文件、调用链摘要、资源清单、待确认项。
4. 跳过清单：外围接口工程未拉取、未找到消费者、权限或路径不可读等。

外围接口明细表必须使用以下字段：

| 完整服务名 | 服务配置/地址证据 | 客户端类/方法 | HTTP方法 | 完整接口路径 | 用途 | 条件 | 状态 |
|---|---|---|---|---|---|---|---|

强制要求：

- `完整服务名` 优先输出真实 Spring 服务名或本地工程目录名，例如 `ylh-cloud-service-stock`，不能只写 `stock`、`goods/stock`、`user/member`。
- `客户端类/方法` 输出调用定义，例如 `StockFeign.listStockCostByItemskuIds`，用于回溯证据，但不能替代接口路径。
- `HTTP方法` 输出 `GET`、`POST`、`PUT`、`DELETE`、`PATCH`；`@RequestMapping` 未声明 method 时写 `未声明（RequestMapping）`，禁止猜测。
- `完整接口路径` 必须拼接客户端类级前缀和方法级路径。例如 `@FeignClient(value="${ylh.cloud.service.stock}/api")` 与 `@PostMapping("/inner/stock/cost/list")` 应输出 `/api/inner/stock/cost/list`。
- 禁止在 `完整接口路径` 中使用方法名、中文概括或模糊集合，例如 `listStockCostByItemskuIds`、`库存成本查询接口`、`仓库详情/编码接口`。
- 一个业务步骤调用多个接口时拆成多行，不要合并成“仓库相关接口”。
- 路径或服务名无法确认时写 `待确认：...`，并在状态列写 `待确认`；存在这种行时，该入口不能标记为 `已完成`。
- 配置只解析到占位符时，同时保留占位符证据和按本地工程目录/命名规则推断的服务名，并明确标记 `推断`，不要把推断写成已确认事实。

总览表字段：

| 入口类型 | 入口 | 状态 | 调用链摘要 | MySQL表 | Redis key | ES索引 | MongoDB表 | Kafka topic | RabbitMQ queue | RocketMQ topic | 外围接口 | 证据文件 | 备注 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

状态建议值：

- `已完成`：脚本候选和人工核对均完成。
- `待确认`：代码中有候选证据，但仍缺少关键配置或真实调用关系。
- `未找到入口`：在当前项目中没有定位到接口或 topic。
- `跳过-工程未拉取`：递进外围接口时，本地项目中不存在对应工程。
- `未找到本地消费者`：MQ 递进开启后没有找到本地 consumer。

资源字段中有多个值时用 `<br>` 分隔；没有识别到时写 `无`，不能留空。无法确认但有候选时写 `待确认：...`。

## 人工核对重点

- Controller 方法调用的 Service 可能通过接口、父类、模板方法、AOP 或事件发布间接进入写链路。
- Service 内部的 `this.xxx()`、同类私有方法、lambda、stream、异步任务和事务回调都要继续展开。
- Mapper XML、MyBatis 注解 SQL、JPA Repository 方法名、QueryDSL、JdbcTemplate 都可能包含真实 MySQL 表。
- Redis/MQ/ES/Mongo 的 key、topic、index、collection 常通过常量、配置属性或枚举拼接，必须追到定义处。
- Feign/Dubbo/HTTP wrapper 不是链路终点；要识别它实际调用的服务名、接口路径、方法名和请求对象。
- Feign 路径必须合并 `@FeignClient` URL/path 前缀、接口级 `@RequestMapping` 和方法级 Mapping；不能遗漏常见的 `/api` 前缀。
- 服务名按配置实际值、本地工程目录、`spring.application.name`、Feign 占位符语义的顺序交叉确认；具体规则见 [外围接口解析规则](references/peripheral-interface-resolution.md)。
- 大仓库中同名方法多时，用类名、包名、注入字段、构造器参数和调用上下文消歧，不要把无关 service 方法串进当前链路。

## 失败处理

- 项目路径不存在：停止并要求用户提供正确路径。
- 起点缺失：停止并要求补充接口路径或 MQ topic。
- 入口未找到：仍输出 Markdown，状态写 `未找到入口`，附上搜索关键词和可能原因。
- 递进扫描遇到缺失工程：记录到跳过清单，状态写 `跳过-工程未拉取`，继续处理其他入口。
- 扫描耗时长：持续等待或分模块处理，不要因慢就提前中断；可先输出已完成入口和待处理入口清单。
