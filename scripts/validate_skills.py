#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
REQUIRED_KEYS = ("name", "description")


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("missing YAML frontmatter")

    try:
        _, yaml_block, _ = text.split("---", 2)
    except ValueError as exc:
        raise ValueError("unterminated YAML frontmatter") from exc

    data: dict[str, str] = {}
    for line in yaml_block.strip().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"invalid frontmatter line: {line}")
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def validate_skill(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    skill_file = skill_dir / "SKILL.md"

    if not skill_file.exists():
        return [f"{skill_dir.relative_to(ROOT)}: missing SKILL.md"]

    try:
        meta = parse_frontmatter(skill_file)
    except ValueError as exc:
        return [f"{skill_file.relative_to(ROOT)}: {exc}"]

    for key in REQUIRED_KEYS:
        if not meta.get(key):
            errors.append(f"{skill_file.relative_to(ROOT)}: missing `{key}`")

    name = meta.get("name", "")
    if name and not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
        errors.append(f"{skill_file.relative_to(ROOT)}: invalid skill name `{name}`")

    description = meta.get("description", "")
    if description and len(description.split()) < 8:
        errors.append(f"{skill_file.relative_to(ROOT)}: description is too short to be a useful trigger")

    return errors


def main() -> int:
    if not SKILLS_DIR.exists():
        print("skills directory does not exist", file=sys.stderr)
        return 1

    skill_dirs = sorted(path for path in SKILLS_DIR.iterdir() if path.is_dir() and not path.name.startswith("."))
    errors: list[str] = []
    for skill_dir in skill_dirs:
        errors.extend(validate_skill(skill_dir))

    if errors:
        print("Skill validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Validated {len(skill_dirs)} skill(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
