# Agent Skills specification reference

Use this reference for exact format, metadata, directory, portability, installation, or validation questions. It summarizes the Agent Skills specification and client-integration guidance at [agentskills.io](https://agentskills.io/home).

## Skill directory

A skill is a directory containing `SKILL.md`. Optional files and directories may use any layout; these names are conventional:

```text
skill-name/
├── SKILL.md
├── scripts/       # executable code
├── references/    # documentation loaded on demand
└── assets/        # templates and static resources used in output
```

Only `SKILL.md` is required. Do not create empty resource directories.

## `SKILL.md`

The file must begin with YAML frontmatter delimited by lines containing exactly `---`, followed by a Markdown body.

| Field | Required | Constraint |
| --- | --- | --- |
| `name` | yes | 1–64 characters; lowercase ASCII letters, digits, and hyphens; no leading, trailing, or consecutive hyphens; must match the parent directory |
| `description` | yes | 1–1024 characters; says what the skill does and when to use it |
| `license` | no | short license name or reference to a bundled license file |
| `compatibility` | no | 1–500 characters; include only for concrete environment requirements |
| `metadata` | no | mapping from string keys to string values; use collision-resistant keys |
| `allowed-tools` | no | experimental space-separated pre-approval syntax; support varies by client |

Use this portable minimum:

```yaml
---
name: skill-name
description: Use this skill when the user needs [outcome] in [contexts]. It [key capabilities].
---
```

Omit `allowed-tools` for cross-client skills. State dependencies and operating requirements in `compatibility` or the body and let each client apply its own permissions and user-confirmation policy.

The Markdown body has no prescribed schema. The full body enters context after activation, so every line has a recurring token cost. Keep it below 500 lines and preferably below 5,000 tokens.

## Progressive disclosure

Compatible clients generally load skills in three tiers:

1. Catalog: `name` and `description`, roughly 50–100 tokens per installed skill.
2. Instructions: the complete `SKILL.md` when the model or user activates it.
3. Resources: individual scripts, references, and assets only when needed.

Design for those tiers. Put activation conditions in `description`, instructions needed on every run in `SKILL.md`, and conditional detail in resources. A reference is useful only when `SKILL.md` tells the agent when to load it.

Reference bundled files with paths relative to the skill root:

```markdown
Read [references/api-errors.md](references/api-errors.md) when an API call returns a non-2xx status.

Run `scripts/validate.py --input plan.json` before applying the plan.
```

Keep references one hop from `SKILL.md`; do not require an agent to discover resources through chains of documents.

## Portability and locations

The specification defines the contents of a skill, not its installation path or conflict policy. The cross-client convention is:

- project: `.agents/skills/<skill-name>/`
- personal: `~/.agents/skills/<skill-name>/`

Clients may also scan native, administrator-provided, plugin, or configured locations. Project skills commonly override user skills with the same name, but precedence within one scope is client-defined. Do not encode a particular client's discovery commands, tool names, or permission syntax unless the skill intentionally targets that client and says so in `compatibility`.

Treat project skills as executable instructions from the repository. Clients may require the repository to be trusted before activation. Skill authors should still use safe defaults, validate inputs, and avoid hidden side effects.

## Validation

Run the bundled structural validator first:

```bash
python3 scripts/validate_skill.py /path/to/skill
```

Then use the official reference implementation when available:

```bash
skills-ref validate /path/to/skill
```

Structural validation cannot prove that a description triggers correctly or that the instructions improve output. Test those separately.

## Canonical sources

- [Overview](https://agentskills.io/home)
- [Specification](https://agentskills.io/specification)
- [Quickstart](https://agentskills.io/skill-creation/quickstart)
- [Client implementation guide](https://agentskills.io/client-implementation/adding-skills-support)
