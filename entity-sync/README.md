# Entity Sync

对比 Java Entity 与 MySQL 表结构，识别字段、类型、注释、默认值和枚举说明差异，并生成同步建议或修改代码。

## 适用场景

- 检查 Entity 和数据库字段是否一致。
- 同步单个 Entity 或整个工程的实体类。
- 排查字段缺失、类型不匹配、注释不一致。
- 检查枚举字段说明和废弃字段。

## 使用前准备

- 提供工程目录或 Entity 文件路径。
- 工程配置中应包含数据库连接信息；如果使用环境变量，需要保证当前环境可读取。
- 若无法自动获取连接信息，可提供 JDBC URL、用户名和密码。
- 操作生产数据库前需要明确确认。

## 使用方式

同步单个实体：

```text
使用 entity-sync 检查 /path/to/project 中的 TradeOrder.java，
对比数据库表结构并给出差异报告
```

扫描整个工程：

```text
使用 entity-sync 同步 /path/to/project 下所有实体类，
先只输出差异，不修改代码
```

已知表名时可以明确指定：

```text
同步 TradeOrder.java，对应表名是 trade_order
```

## 检查内容

- Entity 缺少或多出的字段。
- Java 类型与数据库字段类型不匹配。
- 字段注释、可空性和默认值差异。
- `@Table`、`@TableName`、`@Column`、`@TableField` 映射。
- 父类继承字段、枚举值说明和 `@Deprecated` 字段。

## 注意事项

- 支持 MyBatis、MyBatis-Plus 和 JPA，MySQL 版本要求 5.6 及以上。
- 查询表结构时使用 `utf8mb4`，避免中文注释乱码。
- 数据库密码不会写入报告，但仍应避免在公共会话中直接暴露生产凭据。
- 建议先要求“只输出差异”，确认后再修改 Entity 或生成 DDL。
