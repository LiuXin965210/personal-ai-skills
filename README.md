# Personal AI Skills

个人 AI 助手技能仓库，用来沉淀可复用的工作流、领域知识、脚本和模板。

这个仓库不绑定单一工具。当前可以放 Codex skills，后续也可以补充 Claude Code skills 或其他本地 AI 编程助手可复用的技能资产。

## 目录结构

```text
skills/
  <skill-name>/
    SKILL.md
    agents/openai.yaml
    references/
    scripts/
    assets/
claude/
  <skill-name>/
scripts/
  validate_skills.py
```

## 新建 skill

```bash
cp -R skills/.template "skills/<skill-name>"
```

然后编辑 `skills/<skill-name>/SKILL.md`：

- `name` 必须和目录语义一致，使用小写短横线命名。
- `description` 写清楚触发条件，让 AI 助手能判断什么时候使用。
- 正文只保留核心流程；详细资料放入 `references/`，确定性流程放入 `scripts/`。

## 校验

```bash
python3 scripts/validate_skills.py
```

## 本地安装

可以把成熟的 Codex skill 复制或软链接到本机 Codex skills 目录：

```bash
ln -s "$PWD/skills/<skill-name>" "$HOME/.codex/skills/<skill-name>"
```

如果已有同名目录，先确认不是重要内容后再处理。

Claude Code 相关技能后续放入 `claude/` 或按实际工具要求建立对应目录。
