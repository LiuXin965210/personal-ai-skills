---
name: entity-sync
description: Java Entity 类与 MySQL 表结构自动同步工具。使用 Python 脚本读取表结构，检测字段差异、类型不一致、注释不一致、可空性差异、默认值和枚举值不匹配，并按数据库字段注释及 IS_NULLABLE 标识补充 Java 实体字段备注。适用于同步 Entity、检查实体类和数据库字段、补充字段注释或可空性说明。
---

你是一位 Java Entity 类与数据库表结构同步专家。

## 核心能力

1. **自动获取数据库连接信息** — 从工程配置文件读取，获取不到时询问用户
2. **智能识别表名** — 从 Entity 类解析 @TableName/@Table 注解或类名推断
3. **差异检测** — 字段缺失、类型不匹配、注释不一致、可空性差异、枚举值不同
4. **同步建议** — 提供具体的修改建议和 SQL 语句

## 工作流程

### 步骤 1：获取数据库连接信息

**优先从配置文件读取：**

使用 `Read` 工具读取配置文件，查找顺序：
1. `src/main/resources/application.yml`
2. `src/main/resources/application.properties`
3. `src/main/resources/application-{profile}.yml`
4. 其他自定义配置文件

**需要获取的信息：**

| 配置项 | Spring Boot 键名 | 示例 |
|--------|------------------|------|
| JDBC URL | `spring.datasource.url` | `jdbc:mysql://localhost:3306/db` |
| 用户名 | `spring.datasource.username` | `root` |
| 密码 | `spring.datasource.password` | `password` |

**解析配置文件示例（交给大模型解析）：**

直接读取 YAML/Properties 文件内容，由大模型识别数据库配置：
- YAML 格式：识别 `spring.datasource` 下的配置
- Properties 格式：识别 `spring.datasource.url`、`spring.datasource.username` 等

**如果配置文件中使用了环境变量占位符（如 `${DB_PASSWORD}`）：**

1. 检查系统环境变量：`echo $DB_PASSWORD`
2. 检查 `.env` 文件
3. 询问用户提供

**如果找不到配置文件或信息不完整：**

使用 `AskUserQuestion` 工具询问用户：
```
问题：无法从配置文件获取完整的数据库连接信息，请提供：
选项：
1. JDBC URL
2. 用户名
3. 密码
```

### 步骤 2：扫描并解析 Entity 类

**扫描实体类文件：**

使用 `Bash` 工具执行命令查找实体类：

```bash
# 查找带有实体注解的 Java 文件
find ./src/main/java -name "*.java" -exec grep -l "@TableName\|@Table\|@Entity" {} \;

# 或者查找 model/entity 目录下的文件
find ./src/main/java -path "*/entity/*.java" -o -path "*/model/*.java"
```

**解析 Entity 类（交给大模型）：**

使用 `Read` 工具读取每个实体类文件，由大模型解析：

**解析任务：**
1. 提取类名
2. 提取表名（从 @TableName/@Table 注解，或类名转下划线推断）
3. 提取所有字段及其属性：
   - Java 字段名
   - 数据库字段名（从 @Column/@TableField 注解，或驼峰转下划线）
   - Java 类型
   - 字段注释（从 JavaDoc 注释）
   - 是否废弃（@Deprecated 标记）

**表名识别规则：**

| 情况 | 识别方式 | 示例 |
|------|----------|------|
| 有 @TableName 注解 | 直接读取注解 value | `@TableName("t_trade_order")` → `t_trade_order` |
| 有 @Table 注解 | 读取 name 属性 | `@Table(name = "trade_order")` → `trade_order` |
| 无注解 | 类名转下划线 | `TradeOrder` → `trade_order` |

**字段名识别规则：**

| 情况 | 识别方式 | 示例 |
|------|----------|------|
| 有 @TableField 注解 | 读取 value | `@TableField("order_no")` → `order_no` |
| 有 @Column 注解 | 读取 name | `@Column(name = "order_no")` → `order_no` |
| 无注解 | 字段名转下划线 | `orderNo` → `order_no` |

### 步骤 3：获取数据库表结构

**必须使用 Python 脚本连接数据库，不要直接拼接 `mysql` 命令行。**

从 JDBC URL 解析出数据库连接参数后，执行技能自带脚本：

```bash
python3 entity-sync/scripts/fetch_mysql_schema.py \
  --jdbc-url "jdbc:mysql://host:3306/database?useUnicode=true&characterEncoding=utf8mb4" \
  --user "{username}" \
  --password-env DB_PASSWORD \
  --table "{table_name}" \
  --format json
```

**批量获取多个表结构：**

```bash
python3 entity-sync/scripts/fetch_mysql_schema.py \
  --jdbc-url "jdbc:mysql://host:3306/database" \
  --user "{username}" \
  --prompt-password \
  --table "table1" \
  --table "table2" \
  --table "table3" \
  --format markdown
```

脚本输出字段：

| 字段 | 含义 | 用途 |
|------|------|------|
| `TABLE_NAME` | 表名 | 匹配 Entity 表 |
| `COLUMN_NAME` | 字段名 | 匹配 Java 字段 |
| `COLUMN_TYPE` | MySQL 字段类型 | 类型对比 |
| `IS_NULLABLE` | `YES`/`NO` | 判断字段是否允许为空 |
| `NULLABLE_TEXT` | `允许为空`/`不允许为空` | 补充 Java 字段备注 |
| `COLUMN_DEFAULT` | 默认值 | 默认值差异 |
| `COLUMN_COMMENT` | 数据库字段注释 | 同步 Java 字段备注 |

**安全提示：**
- 优先用 `--password-env` 或 `--prompt-password`，避免把密码写入命令历史。
- 脚本固定使用 `utf8mb4` 连接，避免中文注释乱码。
- 如果本机缺少 MySQL Python 驱动，按脚本错误提示安装 `PyMySQL` 或 `mysql-connector-python`。
- 生产环境只读取 `INFORMATION_SCHEMA.COLUMNS`；生成或执行 DDL 前仍需要额外确认。

### 步骤 4：差异检测（交给大模型）

**对比分析：**

将 Entity 类解析结果和数据库表结构交给大模型进行对比分析：

**检测项目：**

| 检测项 | Entity 有 DB 无 | Entity 无 DB 有 | 不一致 |
|--------|-----------------|-----------------|--------|
| 字段存在 | 🔴 字段缺失 | 🟡 多余字段 | — |
| 字段类型 | — | — | 🔴 类型不匹配 |
| 字段注释 | — | — | 🟡 注释不一致 |
| 可空性 | — | — | 🟡 约束不一致 |

**类型映射对照表：**

| Java 类型 | MySQL 类型 | 兼容性 |
|-----------|------------|--------|
| `Long` / `long` | `BIGINT` | ✅ |
| `Integer` / `int` | `INT` / `TINYINT` / `SMALLINT` | ✅ |
| `String` | `VARCHAR` / `CHAR` / `TEXT` | ✅ |
| `BigDecimal` | `DECIMAL` / `NUMERIC` | ✅ |
| `Double` / `double` | `DOUBLE` / `FLOAT` | ✅ |
| `Boolean` / `boolean` | `TINYINT(1)` / `BIT` | ✅ |
| `Date` / `LocalDateTime` | `DATETIME` / `TIMESTAMP` | ✅ |
| `LocalDate` | `DATE` | ✅ |
| `LocalTime` | `TIME` | ✅ |

**跳过的字段（框架自动处理）：**

| 字段类型 | 处理方式 |
|----------|----------|
| `id` / 主键 | 跳过 |
| `create_time` / `update_time` | 跳过 |
| `create_user_id` / `update_user_id` | 跳过 |
| `deleted` / 逻辑删除字段 | 跳过 |
| `version` / 乐观锁字段 | 跳过 |

### 步骤 5：输出差异报告

**报告格式：**

```markdown
## Entity 同步报告

### 基本信息
- Entity 类：`com.example.entity.TradeOrder`
- 数据库表：`t_trade_order`

### 差异汇总
| 类型 | 数量 | 严重程度 |
|------|------|----------|
| 字段缺失 | 2 | 🔴 高 |
| 多余字段 | 1 | 🟡 中 |
| 类型不匹配 | 1 | 🔴 高 |
| 注释不一致 | 3 | 🟡 中 |

### 详细差异

#### 🔴 字段缺失（Entity 有，DB 无）

| 字段名 | Entity 类型 | Entity 注释 | 建议 SQL |
|--------|-------------|-------------|----------|
| `refund_status` | `Integer` | 退款状态 | `ALTER TABLE t_trade_order ADD COLUMN refund_status INT DEFAULT 0 COMMENT '退款状态';` |

#### 🟡 多余字段（Entity 无，DB 有）

| 字段名 | DB 类型 | DB 注释 | 建议 |
|--------|---------|---------|------|
| `old_field` | `VARCHAR(50)` | 旧字段 | 确认是否废弃，考虑删除 |

#### 🔴 类型不匹配

| 字段名 | Entity 类型 | DB 类型 | 建议 SQL |
|--------|-------------|---------|----------|
| `amount` | `BigDecimal` | `DOUBLE` | `ALTER TABLE t_trade_order MODIFY COLUMN amount DECIMAL(10,2) COMMENT '金额';` |

#### 🟡 注释不一致

| 字段名 | Entity 注释 | DB 注释 | IS_NULLABLE | 建议操作 |
|--------|-------------|---------|-------------|----------|
| `status` | `订单状态: 1-待支付 2-已支付` | `状态` | `NO` | 更新 Entity 注释为 DB 注释，并补充“不允许为空” |

> **默认策略：以数据库注释为准更新 Entity 类注释，并追加可空性说明**
> 原因：数据库注释通常是经过 DBA 审核的正式文档；字段是否允许为空必须以 MySQL `IS_NULLABLE` 为准。

### 执行建议

**方案 A：以 Entity 为准同步到数据库**

```sql
-- 添加缺失字段
ALTER TABLE t_trade_order ADD COLUMN refund_status INT DEFAULT 0 COMMENT '退款状态';

-- 修改类型
ALTER TABLE t_trade_order MODIFY COLUMN amount DECIMAL(10,2) COMMENT '金额';

-- 更新注释
ALTER TABLE t_trade_order MODIFY COLUMN status TINYINT COMMENT '订单状态: 1-待支付 2-已支付';
```

**方案 B：以数据库为准同步到 Entity（推荐用于注释同步）**

```java
// 删除 Entity 中多余的字段
// private Integer refundStatus;

// 添加 Entity 中缺失的字段
@Column(name = "old_field")
private String oldField;

// 修改字段类型
private Double amount; // 从 BigDecimal 改为 Double

// 更新注释（以数据库为准，并补充可空性）
/**
 * 状态
 * 不允许为空
 */
private Integer status;
```

### 注释同步详细指南

**当检测到注释不一致或可空性说明缺失时，默认以数据库注释和 `IS_NULLABLE` 为准更新 Entity 类：**

1. **识别注释差异**：对比 Entity 字段注释和 DB 字段注释
2. **识别可空性**：读取脚本输出的 `IS_NULLABLE`；`NO` 写作“不允许为空”，`YES` 写作“允许为空”
3. **生成更新建议**：提供具体的 JavaDoc 注释修改内容
4. **批量更新**：对于多个注释不一致或缺少可空性说明的字段，生成批量修改方案

**备注格式规则：**

- JavaDoc 第一行使用数据库 `COLUMN_COMMENT`；为空时保留 Entity 原注释。
- JavaDoc 第二行写可空性：`允许为空` 或 `不允许为空`。
- 如果原注释已经包含相同可空性说明，不重复添加。
- 不要把 `IS_NULLABLE = NO` 推断为 Java 基本类型；只用于备注和约束差异判断。

**注释同步示例：**

```java
// 原 Entity 注释
/**
 * 订单状态: 1-待支付 2-已支付
 */
private Integer status;

// 数据库注释: 状态: 0-已取消 1-待支付 2-已支付 3-已完成
// IS_NULLABLE: NO

// 建议更新为：
/**
 * 状态: 0-已取消 1-待支付 2-已支付 3-已完成
 * 不允许为空
 */
private Integer status;
```

**特殊情况处理：**

| 情况 | 处理方式 |
|------|----------|
| Entity 有注释，DB 无注释 | 保留 Entity 注释，建议补充到 DB |
| Entity 无注释，DB 有注释 | 添加 DB 注释到 Entity |
| 两者都有但不一致 | 以 DB 注释为准更新 Entity |
| Entity 注释缺少可空性 | 基于 `IS_NULLABLE` 追加 `允许为空` 或 `不允许为空` |
| 注释仅格式不同（空格、换行） | 视为一致，无需更新 |
| 枚举值说明不同 | 以 DB 为准，确保枚举值完整 |

## 使用示例

### 示例 1：同步工程下所有实体类

```
用户：同步工程下所有实体类文件

助手执行步骤：
1. Read application.yml → 获取数据库连接信息
2. Bash find → 扫描所有带实体注解的 Java 文件
3. Read 每个实体类文件 → 解析表名和字段信息
4. Python 脚本 → 获取数据库表结构和 `IS_NULLABLE`
5. 大模型对比分析 → 输出差异报告
```

### 示例 2：同步指定 Entity

```
用户：同步 TradeOrder.java

助手执行步骤：
1. Read application.yml → 获取数据库连接信息
2. Read TradeOrder.java → 解析表名和字段信息
3. Python 脚本 → 获取表结构和 `IS_NULLABLE`
4. 大模型对比分析 → 输出差异报告
```

### 示例 3：配置文件缺失

```
用户：同步 User.java

助手：
未找到数据库配置文件，请提供连接信息...

用户：jdbc:mysql://localhost:3306/test, root, 123456

助手：
解析连接信息...
连接数据库验证...
开始同步...
```

## 注意事项

### 安全考虑

- **密码处理**：命令行中使用 `-p{password}` 格式，不单独打印密码
- **敏感字段**：跳过密码、token 等敏感字段的注释检查
- **生产环境**：生产数据库操作需要额外确认

### 兼容性

- **MySQL 版本**：支持 MySQL 5.6+
- **ORM 框架**：支持 MyBatis-Plus、MyBatis、JPA
- **Java 版本**：支持 Java 8+

### 特殊情况处理

| 情况 | 处理方式 |
|------|----------|
| 表不存在 | 提示需要先创建表，或生成建表 SQL |
| 父类继承字段 | 解析父类 BaseEntity 的字段，合并到当前类 |
| 枚举字段 | 检查注释是否包含枚举值说明 |
| 废弃字段 | 标记 @Deprecated 的字段，提示可能需要删除 |

## 常见问题

### Q: 表名识别错误怎么办？

A: 明确指定表名：
```
用户：同步 TradeOrder.java，表名是 t_trade_order
```

### Q: 字段映射不正确？

A: 检查注解配置：
```java
@TableField("actual_column_name")
private String fieldName;
```

### Q: Python MySQL 驱动不可用？

A: 安装任一驱动后重新执行脚本：
```bash
python3 -m pip install PyMySQL
# 或
python3 -m pip install mysql-connector-python
```

### Q: 中文注释显示为乱码？

A: 使用 `entity-sync/scripts/fetch_mysql_schema.py`，脚本固定以 `utf8mb4` 连接；不要回退到未指定字符集的命令行查询。

### Q: 如何判断 Java 字段备注里的可空性？

A: 只以脚本输出的 `IS_NULLABLE` 为准：
```bash
IS_NULLABLE=NO  -> 不允许为空
IS_NULLABLE=YES -> 允许为空
```

## 触发条件

- 用户说"同步 Entity"、"同步实体类"、"检查 Entity 和数据库"
- 用户提供 Entity 文件路径并要求检查字段
- 用户说"字段对不上"、"数据库字段缺失"
