# Personal AI Skills

个人 AI 助手技能仓库，用来沉淀可复用的工作流、领域知识、脚本和模板。

仓库根目录直接按技能名组织，不按 Codex、Claude Code 等工具来源分层。每个技能目录保留自身原始结构，例如 `SKILL.md`、`references/`、`scripts/`、`agents/`。

## 当前技能

- `code-migration`
- `entity-sync`
- `git-commit-helper`
- `prd-task-breakdown`
- `requirement-design-doc`
- `troubleshoot-jsh-issue`

## 目录约定

```text
.gitignore
README.md
<skill-name>/
  SKILL.md
  references/
  scripts/
  agents/
```

不是每个技能都需要 `references/`、`scripts/` 或 `agents/`，按实际需要保留。

## 安全约定

不要提交真实密钥、token、cookie、数据库密码、个人配置或本地缓存文件。需要示例配置时，只提交 `*.example.*`。

本仓库已排除常见敏感文件名，例如 `.env`、`*secret*`、`*token*`、`sls_config.json` 等。
