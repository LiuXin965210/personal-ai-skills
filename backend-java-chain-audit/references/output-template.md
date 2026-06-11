# Java 后端链路梳理输出模板

## 输入参数与扫描边界

- 后端项目：`待填写`
- 接口路径：`待填写`
- MQ topic：`待填写`
- 外围接口递进扫描：`关闭`
- MQ 递进扫描：`关闭`
- 最大递归深度：`3`
- 扫描时间：`待填写`

## 总览表

| 入口类型 | 入口 | 状态 | 调用链摘要 | MySQL表 | Redis key | ES索引 | MongoDB表 | Kafka topic | RabbitMQ queue | RocketMQ topic | 外围接口 | 证据文件 | 备注 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| HTTP | `/path` | 待确认 | Controller -> Service -> Mapper | `table_name` | 无 | 无 | 无 | 无 | 无 | 无 | 无 | `src/main/java/...` | 脚本候选，待人工核对 |

## 入口明细

### 1. `待填写入口`

- 状态：`待确认`
- 调用链：
  1. `Controller.method`
  2. `Service.method`
  3. `Mapper.method`
- MySQL 表：`无`
- Redis key：`无`
- ES 索引：`无`
- MongoDB 表：`无`
- Kafka topic：`无`
- RabbitMQ queue：`无`
- RocketMQ topic：`无`
- 外围接口：`无`
- 证据文件：
  - `path/to/File.java`
- 待确认：
  - `暂无`

### 外围接口

| 完整服务名 | 服务配置/地址证据 | 客户端类/方法 | HTTP方法 | 完整接口路径 | 用途 | 条件 | 状态 |
|---|---|---|---|---|---|---|---|
| `ylh-cloud-service-stock` | `${ylh.cloud.service.stock}/api`；本地目录 `ylh-cloud-service-stock` | `StockFeign.iprpUpdate` | `POST` | `/api/composite/stock/iprp/iprp-update` | 分销订单占库 | 必经 | 已确认 |
| `待确认：消息服务完整名称` | `MessageClient` 未发现服务配置 | `MessageClient.send` | `待确认` | `待确认：未找到 Mapping 或 URL` | 发送通知 | 配置分支 | 待确认 |

外围接口表中禁止使用以下降级写法：

- 用 `stock`、`goods/stock`、`user/member` 代替完整服务名。
- 用 `listStockCostByItemskuIds`、`getDistributionPrice` 等 Java 方法名代替 HTTP 路径。
- 用“库存成本查询接口”“仓库详情/编码接口”“消息中台接口”等概括文字代替具体路径。
- 把多个客户端方法合并成一行模糊描述。

## 跳过清单

| 类型 | 入口 | 原因 | 后续动作 |
|---|---|---|---|
| 外围接口 | `待填写` | 跳过-工程未拉取 | 待手动拉取项目后再处理 |
