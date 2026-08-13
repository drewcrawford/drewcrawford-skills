---
name: write-skills
description: Create, revise, and evaluate portable Agent Skills. Use this skill whenever the user wants to author or improve a skill, SKILL.md, skill metadata or triggering, bundled scripts/references/assets, progressive disclosure, validation, or skill evals—even if they only ask to capture a repeatable workflow or turn recent work into reusable agent guidance.
---

# Write Agent Skills

Create lean, portable skills grounded in real expertise and verified by execution. A skill is valuable when it gives an agent knowledge, procedures, or reusable resources it would otherwise lack.

## Start by loading the right guidance

- Read [references/specification.md](references/specification.md) for exact format rules, optional fields, portability, installation, or validation questions.
- Read [references/authoring.md](references/authoring.md) when choosing scope, organizing a large skill, or turning source material and corrections into instructions.
- Read [references/evaluation.md](references/evaluation.md) when creating trigger tests, comparing a skill with a baseline, grading outputs, or iterating on an existing skill.
- Read [references/scripts.md](references/scripts.md) before adding or reviewing a bundled script.
- Use [templates/basic-skill.md](templates/basic-skill.md) as a starting scaffold, then replace every placeholder and remove every section the skill does not need.

Do not read every reference by default. Load only what the task requires.

## Authoring workflow

### 1. Ground the skill in evidence

Inspect the current skill and all relevant bundled files before editing it. Gather concrete examples from one or more of these sources:

- a real task completed with the user;
- user corrections, preferences, and failure reports;
- project runbooks, schemas, API specifications, code, issues, and review comments;
- execution traces and outputs from earlier uses of the skill.

Extract the reusable procedure, non-obvious facts, input/output contracts, and recurring failure modes. Do not manufacture a generic “best practices” skill from model knowledge alone when real source material is available.

### 2. Define a coherent boundary

Write down representative requests that should trigger the skill and adjacent requests that should not. Scope the skill like a well-designed function: broad enough to complete one coherent unit of work, but narrow enough to activate precisely and compose with other skills.

Ask only for missing information that would materially change the result. For an existing skill, preserve working behavior unless the user asks to change it.

### 3. Plan reusable contents

For each representative request, imagine performing it from scratch. Bundle only resources that remove repeated work or supply information the agent would not otherwise know:

- `scripts/` for deterministic, fragile, or repeatedly re-created logic;
- `references/` for detailed knowledge loaded only in relevant situations;
- `assets/` for templates, images, data, or boilerplate used in produced output;
- another clearly named directory when it better describes the content.

Keep the skill directory self-contained. Do not add process diaries, changelogs, installation guides, or user documentation that the executing agent does not need.

### 4. Write specification-compliant metadata

Create a directory whose name exactly matches the `name` field. Use a 1–64 character name made only of lowercase ASCII letters, digits, and single hyphens; do not start or end with a hyphen.

Treat `description` as the skill's trigger classifier:

- use imperative phrasing such as “Use this skill when…”;
- describe the user's intent and the outcomes the skill supports, not its internal implementation;
- include implicit phrasings and important file types, systems, or task contexts;
- state a narrow exclusion when a nearby skill or ordinary capability is an easy false positive;
- keep it concise and under 1024 characters.

Put all activation guidance in `description`; the body is unavailable until after activation. Use only specification-defined optional frontmatter fields when they add value. Omit experimental `allowed-tools` in portable skills because syntax and permission semantics vary by client.

### 5. Write only high-value instructions

Assume the agent is capable. Include project- or domain-specific procedures, decisive defaults, concrete gotchas, and validation criteria; omit textbook background and vague reminders.

- Use imperative steps and favor procedures that generalize over answers to one example.
- Give a default approach and a brief escape hatch instead of an equal-weight menu.
- Explain why when the agent should adapt its judgment.
- Be exact when ordering, safety, or consistency is fragile.
- Put high-frequency, non-obvious gotchas in `SKILL.md` so they are always seen.
- Provide a short output template when format matters.
- Use checklists for dependent multi-step work.
- For destructive or batch operations, require plan → validate against a source of truth → execute.
- Require work → validate → repair loops when a mechanical or reference-based check exists.

Keep `SKILL.md` below 500 lines and, preferably, 5,000 tokens. Move conditional detail into focused reference files. Link each resource directly from `SKILL.md` and say exactly when to load or run it. Avoid reference chains more than one level deep.

### 6. Make bundled scripts agent-friendly

Test every added or changed script. Prefer a pinned one-off command when it is genuinely simple; bundle a script when the command is complex or logic recurs.

Require non-interactive input, concise `--help`, actionable errors, meaningful exit codes, safe/idempotent defaults, and structured stdout with diagnostics on stderr. Add `--dry-run` or an explicit confirmation flag for destructive/stateful behavior, and bound or paginate large output. See [references/scripts.md](references/scripts.md) for the complete checklist.

### 7. Validate structure and links

From this skill's directory, run:

```bash
python3 scripts/validate_skill.py /path/to/skill
```

Fix every error. Review warnings rather than blindly suppressing them. When the official reference validator is available, also run:

```bash
skills-ref validate /path/to/skill
```

Exercise each bundled script with representative valid and invalid input. Confirm referenced files exist and paths are relative to the skill root.

### 8. Evaluate behavior when the skill is consequential

For a small skill, manually try a few realistic positive and near-miss negative prompts. For an important or complex skill, use the workflow in [references/evaluation.md](references/evaluation.md):

1. Measure trigger accuracy separately from output quality.
2. Run realistic tasks in clean contexts with the skill and against a no-skill or previous-version baseline.
3. Add objective assertions after inspecting first-run outputs.
4. Grade with concrete evidence and blind holistic comparison where useful.
5. Inspect traces, time, and token costs—not only final answers.
6. Generalize fixes, rerun the complete set, and stop when gains plateau.

Do not leak the intended answer, diagnosis, or previous run state into clean-context evaluations.

## Completion checklist

- [ ] The skill encodes real, non-obvious expertise.
- [ ] The folder and `name` match and satisfy the specification.
- [ ] The description says what the skill enables and when to use it.
- [ ] The scope has realistic positive and near-miss negative examples.
- [ ] `SKILL.md` is lean; conditional detail is explicitly routed to resources.
- [ ] Instructions provide defaults, gotchas, safety gates, and validation where needed.
- [ ] Bundled scripts are non-interactive, safe, documented, and tested.
- [ ] Local validation passes; the official validator passes when available.
- [ ] Behavioral testing shows an improvement over the relevant baseline.

Report what changed, what was validated, and any behavior that still needs a real-world or client-specific test.
