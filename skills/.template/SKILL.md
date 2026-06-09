---
name: example-skill
description: Replace this with a precise trigger description. Use when an AI assistant should follow this personal workflow for a specific task, domain, tool, or repository.
---

# Example Skill

## When To Use

Use this skill when the user asks for the specific workflow described in the frontmatter.

## Workflow

1. Identify the operating context and required inputs.
2. Load only the reference files needed for the current request.
3. Prefer bundled scripts for deterministic or repetitive operations.
4. Validate the result before reporting completion.

## References

- Put detailed domain notes in `references/`.
- Put reusable commands or deterministic helpers in `scripts/`.
- Put output templates, sample files, or static assets in `assets/`.
