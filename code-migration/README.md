# Code Migration

以接口、MQ、定时任务或实体类为单位，将 Java 代码从源工程迁移到目标工程，并处理包结构、跨模块依赖、编译验证和迁移记录。

## 适用场景

- 迁移 HTTP 接口、MQ 消费者或生产者。
- 迁移 XXL-Job、DTS 消费者、Entity 或枚举。
- 拆分单体模块或处理跨模块依赖。
- 讨论迁移顺序、代码归属和重构边界。

## 使用前准备

请提供：

- 迁移类型。
- 接口路径、类名、方法名、Topic 或任务名等具体标识。
- 源工程路径和目标工程路径。
- 目标分支或其他工程约束（如有）。

## 使用方式

```text
使用 code-migration 将接口 /api/order/create
从 /path/to/source-project 迁移到 /path/to/target-project，
目标模块是 order/create
```

迁移 MQ：

```text
使用 code-migration 迁移 OrderCreateConsumer，
源工程 /path/to/source，目标工程 /path/to/target
```

仅制定方案：

```text
使用 code-migration 分析这批接口的迁移顺序，先不要修改代码
```

## 默认流程

1. 读取源工程和目标工程规范。
2. 定位入口及其 Service、DAO、DTO、Entity、Enum 等依赖。
3. 识别跨模块 JOIN、事务和公共代码。
4. 按单个接口或消息链路迁移并适度重构。
5. 执行编译和测试验证。
6. 更新迁移备忘录和接口对照信息。

## 注意事项

- 发现跨模块依赖时会先说明处理方案，避免直接复制错误架构。
- 默认以“先跑通迁移”为目标，不提前引入复杂设计模式。
- 不会覆盖或回退工作区中与迁移无关的用户改动。
- 迁移结果是否完整，以目标工程编译、测试和接口核对结果为准。
