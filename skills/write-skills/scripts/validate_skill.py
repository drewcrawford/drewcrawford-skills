#!/usr/bin/env python3
"""Validate the portable structure and metadata of one or more Agent Skills."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TOP_LEVEL_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):(?:[ \t]*(.*))?$")
KNOWN_FIELDS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}
RESOURCE_RE = re.compile(
    r"(?:\]\(|`)((?:scripts|references|assets|templates)/[^)`\s#]+)"
)


@dataclass
class Result:
    path: str
    valid: bool
    errors: list[str]
    warnings: list[str]


def scalar_value(raw: str, continuation: list[str]) -> str:
    raw = raw.strip()
    if raw in {"|", "|-", "|+"}:
        return "\n".join(line.strip() for line in continuation).strip()
    if raw in {">", ">-", ">+"}:
        return " ".join(line.strip() for line in continuation if line.strip()).strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {'"', "'"}:
        if raw[0] == '"':
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return raw[1:-1]
        return raw[1:-1].replace("''", "'")
    return re.split(r"\s+#", raw, maxsplit=1)[0].strip()


def parse_frontmatter(lines: list[str], errors: list[str]) -> tuple[dict[str, str], int]:
    if not lines or lines[0].strip() != "---":
        errors.append("SKILL.md must begin with a line containing exactly ---")
        return {}, 0

    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        errors.append("YAML frontmatter has no closing --- delimiter")
        return {}, 0

    fields: dict[str, str] = {}
    i = 1
    while i < end:
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if line.startswith((" ", "\t")):
            i += 1
            continue
        match = TOP_LEVEL_RE.match(line)
        if not match:
            errors.append(f"frontmatter line {i + 1} is not a top-level YAML field")
            i += 1
            continue
        key, raw = match.group(1), match.group(2) or ""
        if key in fields:
            errors.append(f"frontmatter field {key!r} appears more than once")
        continuation: list[str] = []
        cursor = i + 1
        while cursor < end and (
            not lines[cursor].strip() or lines[cursor].startswith((" ", "\t"))
        ):
            continuation.append(lines[cursor])
            cursor += 1
        fields[key] = scalar_value(raw, continuation)
        i = cursor
    return fields, end


def validate_skill(skill_path: Path) -> Result:
    errors: list[str] = []
    warnings: list[str] = []
    path = skill_path.resolve()
    skill_file = path / "SKILL.md"
    if not path.is_dir():
        return Result(str(path), False, ["path is not a directory"], [])
    if not skill_file.is_file():
        return Result(str(path), False, ["SKILL.md is missing"], [])

    try:
        text = skill_file.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return Result(str(path), False, ["SKILL.md is not valid UTF-8"], [])

    if "\t" in text.partition("---")[2].partition("---")[0]:
        errors.append("frontmatter contains a tab; use spaces for YAML indentation")
    lines = text.splitlines()
    fields, frontmatter_end = parse_frontmatter(lines, errors)

    name = fields.get("name", "")
    description = fields.get("description", "")
    if not name:
        errors.append("required field 'name' is missing or empty")
    else:
        if len(name) > 64:
            errors.append("name exceeds 64 characters")
        if not NAME_RE.fullmatch(name):
            errors.append("name must contain lowercase letters, digits, and single hyphens only")
        if name != path.name:
            errors.append(f"name {name!r} does not match parent directory {path.name!r}")

    if not description:
        errors.append("required field 'description' is missing or empty")
    elif len(description) > 1024:
        errors.append("description exceeds 1024 characters")

    compatibility = fields.get("compatibility", "")
    if compatibility and len(compatibility) > 500:
        errors.append("compatibility exceeds 500 characters")

    unknown = sorted(set(fields) - KNOWN_FIELDS)
    if unknown:
        warnings.append("unknown frontmatter field(s): " + ", ".join(unknown))
    if "allowed-tools" in fields:
        warnings.append("allowed-tools is experimental and may reduce portability")

    body = "\n".join(lines[frontmatter_end + 1 :]).strip() if frontmatter_end else ""
    if not body:
        errors.append("Markdown body is empty")
    if len(lines) > 500:
        warnings.append(f"SKILL.md has {len(lines)} lines; keep it below 500")

    for match in RESOURCE_RE.finditer(body):
        relative = match.group(1).rstrip(".,;:")
        if any(token in relative for token in ("[", "]", "<", ">", "*")):
            continue
        if not (path / relative).exists():
            errors.append(f"referenced resource does not exist: {relative}")

    return Result(str(path), not errors, errors, warnings)


def print_text(results: list[Result]) -> None:
    for result in results:
        status = "PASS" if result.valid else "FAIL"
        print(f"{status} {result.path}")
        for warning in result.warnings:
            print(f"  warning: {warning}")
        for error in result.errors:
            print(f"  error: {error}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Agent Skills metadata, body, and local resource links."
    )
    parser.add_argument("paths", nargs="+", type=Path, help="skill directories")
    parser.add_argument(
        "--format", choices=("text", "json"), default="text", help="output format"
    )
    args = parser.parse_args()

    results = [validate_skill(path) for path in args.paths]
    if args.format == "json":
        print(json.dumps([asdict(result) for result in results], indent=2))
    else:
        print_text(results)
    return 0 if all(result.valid for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
