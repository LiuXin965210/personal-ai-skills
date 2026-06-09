---
name: git-commit-helper
description: Git 提交助手 - 自动识别代码仓管理方式、生成符合项目规范的提交消息、支持分批提交
version: 1.0.0
source: local-git-analysis
analyzed_commits: 100
---

# Git 提交助手

## 提交消息格式

本项目采用以下提交消息格式：

```
{需求号} {变更类型} {变更内容}
```

### 格式说明

- **需求号**: 格式为 `{用户名}-{需求ID}`，如 `yilihuo-51952`
- **变更类型**: 使用 conventional commits 类型
  - `feat` - 新功能
  - `fix` - Bug 修复
  - `chore` - 维护任务（配置、依赖等）
  - `docs` - 文档更新
  - `refactor` - 重构
  - `test` - 测试相关
  - `perf` - 性能优化
- **变更内容**: 简洁描述本次变更内容

### 示例

```
yilihuo-51952 feat 新增分销订单实体类
yilihuo-51952 fix 修复订单金额计算错误
yilihuo-51952 chore 更新 Kiro hooks 配置
yilihuo-51952 docs 新增迁移策略文档
```

## 代码仓管理方式识别

### 识别规则

通过以下方式识别代码仓管理方式：

1. **远程仓库 URL**: 检查 `git remote -v` 输出
   - 包含 `gerrit` 关键字 → Gerrit 管理
   - 包含 `gitlab` 或 `git.haier.net/jsh` → GitLab 管理

2. **项目名称前缀**:
   - `ylh-*` 开头 → Gerrit 管理
   - `jsh-*` 开头 → GitLab 管理

3. **分支命名模式**:
   - 直接在 `dev`/`master` 上提交 → Gerrit
   - 使用 `user/{用户名}-{需求号}` 分支 → GitLab

### 当前项目识别

本项目为 **GitLab 管理**：
- 远程仓库: `https://git.haier.net/jsh/backend/purchase/jsh-service-purchase-order-smb.git`
- 项目前缀: `jsh-service-purchase-order-smb`

## GitLab 工作流

### 分支策略

GitLab 需要创建 user 分支进行开发：

```
user/{用户名}-{需求号}
```

例如: `user/yilihuo-51592`

### 分支创建流程

1. **检查当前分支**: 使用 `git branch --show-current`
2. **如果已在 user 分支**: 无需重新创建，直接使用
3. **如果不在 user 分支**:
   - 询问用户需求号
   - 基于 `dev` 或 `master` 创建 user 分支
   - 切换到 user 分支

### 提交流程

1. **确保代码最新**: 执行 `git pull` 或 `git fetch + git merge`
2. **分析变更内容**: 使用 `git status` 和 `git diff`
3. **生成提交清单**: 按逻辑分组变更文件
4. **用户确认**: 展示分批提交计划
5. **分批提交**: 按确认的计划执行提交

## Gerrit 工作流

### 分支策略

Gerrit 支持直接在 `dev` 或 `master` 分支上提交。

### 提交流程

1. **切换到目标分支**: `dev` 或 `master`
2. **确保代码最新**: `git pull`
3. **提交变更**: 直接提交到当前分支

## 分批提交策略

### 核心原则

**优先保证一个需求的内容一起提交**，仅在有明确分离必要时才分批提交。

### 变更分组原则

#### 需要分批提交的场景

| 场景 | 说明 | 提交顺序 |
|-----|------|---------|
| **基础配置 + 业务代码** | 配置文件变更与业务逻辑变更分离 | 先提交配置，再提交业务代码 |
| **多需求并行开发** | 不同需求号的变更需分开提交 | 按需求号分组提交 |
| **独立修复/优化** | 与当前需求无关的独立变更 | 单独提交 |

#### 不需要分批提交的场景

- **同一需求的完整功能**: 实体类、Repository、Service、Controller 等一起提交
- **关联性强的变更**: 如 DTO 和使用它的 Service 应一起提交
- **小型功能开发**: 变更文件较少时，合并为一次提交

### 分组判断流程

```
1. 检查是否有多个需求号 → 按需求号分组
2. 检查是否有基础配置变更 → 配置单独提交
3. 检查是否有独立修复 → 单独提交
4. 其余变更 → 合并为一次提交
```

### 基础配置文件识别

以下文件类型视为基础配置：

- `pom.xml`, `build.gradle` - 依赖配置
- `application*.yml`, `application*.properties` - 应用配置
- `*.xml` (MyBatis 映射文件除外) - 配置文件
- `.gitignore`, `.editorconfig` - 项目配置
- `CLAUDE.md`, `README.md` - 项目文档
- `.claude/`, `.kiro/` - 工具配置

### 分批提交示例

#### 示例 1: 单一需求（推荐合并提交）

```
批次 1: 新增分销订单功能
文件:
  - src/main/java/.../model/TradeOrder.java
  - src/main/java/.../repository/TradeOrderRepository.java
  - src/main/java/.../service/TradeOrderService.java
  - src/main/java/.../controller/TradeOrderController.java
  - src/main/java/.../dto/TradeOrderDTO.java
消息: yilihuo-51592 feat 新增分销订单功能
```

#### 示例 2: 配置 + 业务代码（分批提交）

```
批次 1: 更新项目配置
文件:
  - pom.xml
  - application.yml
消息: yilihuo-51952 chore 更新依赖和配置

批次 2: 新增采购单功能
文件:
  - src/main/java/.../model/PurchaseOrder.java
  - src/main/java/.../service/PurchaseOrderService.java
  - src/main/java/.../controller/PurchaseOrderController.java
消息: yilihuo-51952 feat 新增采购单功能
```

#### 示例 3: 多需求并行（按需求号分组）

```
批次 1: 需求 A
文件: (需求 A 相关的所有文件)
消息: yilihuo-51592 feat 新增订单导出功能

批次 2: 需求 B
文件: (需求 B 相关的所有文件)
消息: yilihuo-51952 fix 修复金额计算问题
```

## 用户自定义分组

### 指定分组方式

用户可以明确指定哪些文件分在一组提交：

```
把 TradeOrder.java 和 TradeOrderService.java 放一起提交，消息为 yilihuo-51592 feat 新增订单功能
```

```
分两批提交：
第一批：pom.xml，消息为 yilihuo-51952 chore 更新依赖
第二批：其余所有文件，消息为 yilihuo-51952 feat 新增采购功能
```

### 交互式分组确认

当变更文件较多时，助手会：

1. 展示所有变更文件列表
2. 提供推荐的分组方案
3. 询问用户是否需要调整
4. 用户可指定自定义分组
5. 确认后执行提交

### 分组确认示例

```
检测到以下变更文件：

1. pom.xml
2. application.yml
3. src/.../model/Order.java
4. src/.../service/OrderService.java
5. src/.../controller/OrderController.java

推荐分组方案：
- 批次 1 (配置): pom.xml, application.yml
- 批次 2 (业务): 其余文件

是否按此方案提交？或请指定您的分组方式。
```

## 使用方式

### 自动模式

用户请求提交时，助手自动：

1. 识别代码仓类型
2. 检查当前分支状态
3. 分析变更内容，识别需求号
4. 判断是否需要分批（配置/业务分离、多需求并行）
5. 生成分组提交计划
6. 展示计划并询问用户确认或调整
7. 执行确认后的提交

### 指定分组模式

用户可明确指定文件分组：

```
把 Order.java 和 OrderService.java 放一起提交，消息为 yilihuo-51592 feat 新增订单功能
```

```
分三批提交：
1. pom.xml → yilihuo-51952 chore 更新依赖
2. application.yml → yilihuo-51952 chore 更新配置
3. 其余文件 → yilihuo-51952 feat 新增采购功能
```

### 指定文件模式

用户可指定具体文件和提交消息：

```
提交 TradeOrder.java 文件，消息为 yilihuo-51592 feat 新增分销订单实体类
```

助手将：
1. 验证文件存在
2. 确保代码最新
3. 执行指定提交

### 指定代码仓模式

```
提交到 gerrit TradeOrder.java 文件，消息为 yilihuo-51592 feat 新增分销订单实体类
```

助手将：
1. 切换到 Gerrit 工作流
2. 执行指定提交

## 代码冲突处理（CRITICAL）

### 核心原则

**遇到合并冲突时，必须交由用户手动解决，模型不得自行合并（merge）或使用任何策略选项自动解决冲突。**

### 为什么禁止模型自动合并

- 模型不了解冲突文件的业务上下文，自动选择 `ours`/`theirs` 可能丢弃用户或他人的有效代码
- 冲突往往涉及多人并行开发的代码，需要人工判断取舍
- 自动合并后的代码可能编译通过但逻辑错误，难以排查

### 冲突处理流程

当 `git merge` 或 `git pull` 出现冲突时，严格遵守以下流程：

1. **立即停止**：不要再执行任何 git 命令（包括 `git merge --abort`、`git checkout --theirs`、`git add` 等）
2. **列出冲突文件**：明确告知用户哪些文件存在冲突
3. **说明冲突原因**：简要说明是 add/add 冲突还是 content 冲突
4. **等待用户处理**：由用户手动编辑冲突文件完成合并
5. **用户确认后继续**：用户解决完毕并告知后，再执行 `git add` + `git commit` + `git push`

### 禁止的操作

以下操作一律禁止，不得执行：

- `git merge -X theirs`
- `git merge -X ours`
- `git merge --strategy-option theirs`
- `git checkout --theirs <file>`
- `git checkout --ours <file>`
- `git merge --abort`（除非用户明确要求）
- 任何通过 `git add` + `git commit` 跳过冲突检查的变通方式

### 示例

```
# 正确做法：列出冲突，等待用户

检测到合并冲突，涉及以下 3 个文件：
1. src/.../BaseFeign.java (content 冲突)
2. src/.../StockFeign.java (content 冲突)
3. src/.../UpdateDto.java (add/add 冲突)

请手动解决上述冲突后告知我，我将继续执行 git add + git commit。
```

### 唯一例外

仅当用户**明确打字要求**使用某个策略选项时（如"用 theirs 解决"、"全部用远程版本覆盖"），才可执行对应的合并策略。模型不得主动建议或推断用户意图。

## 提交前检查

每次提交前必须执行：

1. **拉取最新代码**:
   ```bash
   git fetch origin
   git merge origin/{目标分支}
   ```

2. **检查冲突**: 如遇冲突，严格按照上方"代码冲突处理"流程执行，不得自行合并

3. **验证变更**: 确认变更内容符合预期

## 工作流检查清单

### GitLab 工作流

- [ ] 确认需求号
- [ ] 检查/创建 user 分支
- [ ] 拉取最新代码
- [ ] 分析变更内容
- [ ] 生成分批提交计划
- [ ] 用户确认计划
- [ ] 执行分批提交
- [ ] 提示用户手动合并到 dev

### Gerrit 工作流

- [ ] 切换到 dev/master 分支
- [ ] 拉取最新代码
- [ ] 分析变更内容
- [ ] 生成分批提交计划
- [ ] 用户确认计划
- [ ] 执行分批提交

## 常用命令参考

```bash
# 查看当前分支
git branch --show-current

# 查看远程仓库
git remote -v

# 查看变更状态
git status

# 查看变更详情
git diff

# 拉取最新代码
git fetch origin
git merge origin/dev

# 创建 user 分支
git checkout -b user/yilihuo-51592 origin/dev

# 提交变更
git add {files}
git commit -m "{需求号} {类型} {内容}"

# 推送到远程
git push origin {分支名}
```