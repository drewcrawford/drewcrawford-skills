# Authoring effective skills

Read this reference when choosing scope, synthesizing source material, organizing a large skill, or diagnosing instructions that are vague, bloated, or brittle.

## Begin with real expertise

The strongest skills are extracted from work that has already happened. Mine:

- the successful sequence of steps;
- corrections and preferences the user supplied;
- inputs, outputs, and intermediate formats;
- environment facts and project conventions;
- real failure modes and their resolutions;
- repeated code or commands;
- issue history and review feedback that reveal recurring expectations.

When source material exists, synthesize it before drafting. Generic advice such as “handle errors” or “follow security best practices” consumes context without changing behavior. Replace it with the exact failure, check, command, or rule the agent needs.

## Spend context deliberately

Ask of every paragraph: would a capable agent likely get this wrong without it? Cut material when the answer is no. Prefer one working example and moderate stepwise detail over exhaustive prose.

Treat the skill as a coherent unit of work. Overly narrow skills force several instruction sets into context for one task. Overly broad skills trigger imprecisely and burden every run with irrelevant branches.

Put core procedure and high-frequency gotchas in `SKILL.md`. Move conditional material into focused references and give explicit routing conditions:

```markdown
Read `references/oauth.md` only when the service requires an OAuth flow.
```

Do not say only “see references for more information.”

## Calibrate control

Set specificity independently for each part of the workflow:

- High freedom: multiple approaches are valid and context should drive the choice. State the goal and the reason behind important constraints.
- Medium freedom: a preferred pattern exists but parameters vary. Give pseudocode, a template, or a script with options.
- Low freedom: ordering is fragile, errors are costly, or consistency is mandatory. Supply the exact command or sequence and a validation gate.

Choose a default. Mention an alternative only with the condition that justifies it.

Favor reusable procedures over a solution to one captured task. Preserve specific domain facts, but express the method so it transfers to the next instance.

## High-value instruction patterns

Use only the patterns the task needs.

### Gotchas

Record concrete facts that contradict reasonable assumptions. Keep frequently relevant gotchas in `SKILL.md`; otherwise state the condition for opening a gotchas reference.

### Output templates

Show a compact concrete shape when formatting matters. Store long or conditional templates as assets. Tell the agent which parts may be adapted.

### Checklists

Use checklists for workflows with dependent stages or easy-to-miss gates. Avoid checklists for obvious one-step tasks.

### Validation loops

Tell the agent to create the artifact, run a mechanical validator or compare against a source of truth, repair failures, and repeat until it passes. A validator should return enough information for the next correction.

### Plan–validate–execute

For destructive, batch, or stateful operations:

1. materialize the intended changes in a reviewable format;
2. validate the plan against the actual source of truth;
3. correct discrepancies;
4. execute only the validated plan.

## Improve through use

Read traces as well as final outputs. Common signals:

- wandering among approaches → add a default or clarify a decision rule;
- following irrelevant branches → move them to conditional references or cut them;
- repeating the same helper code → bundle and test a script;
- ignoring an instruction → make it concrete, reposition it, or explain why it matters;
- consistent success without the instruction → remove it;
- inconsistent behavior → reduce ambiguity or add one representative example.

Generalize corrections. Do not patch a skill with the exact nouns from one failed test when the underlying category can be expressed instead.

Source: [Best practices for skill creators](https://agentskills.io/skill-creation/best-practices).
