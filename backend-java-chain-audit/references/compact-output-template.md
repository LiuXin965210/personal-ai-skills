| 入口类型 | 入口 | 状态 | 调用链摘要 | MySQL表 | Redis key | ES索引 | MongoDB表 | Kafka topic | RabbitMQ queue | RocketMQ topic | 外围接口 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HTTP | `/api/order/save` | 已完成 | Controller -> Service -> Mapper/Client | 写入：`trade_order`<br>`trade_order_items`<br>只读：`member_base` | `order_save_{id}` | 无 | 无 | 无 | `order_save_queue` | 无 | `ylh-cloud-service-stock POST /api/composite/stock/iprp/iprp-update`<br>`ylh-cloud-service-fund POST /api/inner/fund/center/transaction-management/insert-fund-center-order-transaction` |
