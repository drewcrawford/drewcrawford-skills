---
name: skill-name
description: Use this skill when the user needs [outcome] in [specific contexts], including [implicit or adjacent phrasing that should trigger it]. It [key capabilities]. Do not use it for [important near-miss boundary, only if needed].
---

# [Skill title]

[One sentence stating the operational goal and the non-obvious value this skill adds.]

## Load supporting material

- Read `[references/relevant.md]` when [specific condition].
- Run `[scripts/tool.py]` when [specific condition].

Delete this section if the skill has no resources. Do not use a generic “see references” instruction.

## Workflow

1. [Inspect the concrete input or source of truth.]
2. [Apply the preferred procedure and its decision rule.]
3. [Validate the result with a script, command, or observable criteria.]
4. [Repair failures and repeat validation before delivery.]

## Gotchas

- [Concrete fact the agent would reasonably get wrong without being told.]
- [Safety constraint or boundary that changes the procedure.]

Delete generic reminders and unused sections. Add a compact output template only when the output shape matters.

## Completion checks

- [ ] [Objective result condition]
- [ ] [Validation or safety condition]
