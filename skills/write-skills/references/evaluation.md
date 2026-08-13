# Evaluating skills

Read this reference when testing description triggering, output quality, regressions, or the value of an existing skill.

## Separate two questions

1. Triggering: does the client load the skill for relevant prompts and avoid it for near misses?
2. Quality: once loaded, does the skill improve correctness, usability, reliability, time, or token cost relative to a baseline?

Test them separately. A perfect workflow is useless if its description does not activate; perfect activation is harmful if the instructions degrade output.

## Trigger evaluation

Create roughly 20 realistic queries: 8–10 positives and 8–10 negatives. Vary phrasing, explicitness, detail, complexity, file paths, personal context, abbreviations, and occasional typos.

Use hard cases:

- Positive queries should include indirect intent where the domain keyword is absent or the relevant task is embedded in a larger request.
- Negative queries should be near misses sharing vocabulary with the skill but requiring a different capability.

Avoid obviously unrelated negatives; they do not measure precision.

Record each query and label:

```json
[
  {"query": "realistic user prompt", "should_trigger": true},
  {"query": "realistic adjacent request", "should_trigger": false}
]
```

Observe whether the client actually loaded `SKILL.md`; do not infer activation merely from a good answer. Because model behavior is nondeterministic, run each query several times (three is a useful starting point) and compute the trigger rate.

Split cases once optimization begins:

- train: about 60%, used to diagnose and revise;
- validation: about 40%, held back to choose the best revision.

Keep positive/negative proportions similar and the split fixed. Broaden or narrow by concept, not by copying keywords from failed prompts. Select the revision with the best held-out result, which may not be the final iteration. Finish with fresh unseen sanity cases.

## Output-quality evaluation

Start with 2–3 realistic tasks, including one boundary condition. Each case needs:

- a natural user prompt;
- a human-readable expected outcome;
- optional input files.

Run each case in a clean context twice:

- with the current skill;
- without the skill, or with a snapshot of the previous version when improving one.

Keep task text, inputs, environment, and output destination equivalent. Do not disclose which configuration is expected to win. Preserve raw outputs and execution traces.

After the first run, add assertions for objective, observable properties. Good assertions check validity, existence, counts, dimensions, required content, or externally verifiable behavior. Avoid “the output is good” and brittle exact phrasing. Leave taste, visual polish, and overall usefulness to human or blind holistic review.

Grade each assertion PASS or FAIL with concrete evidence. Use deterministic scripts for mechanical checks and an agent judge only where code cannot inspect the property reliably. A superficial heading is not evidence that the underlying requirement was met.

Record time and token use when the client exposes them. Compare what the skill buys against what it costs.

## Analyze results

- Always passes with and without the skill: the assertion may be too easy or the instruction adds no value.
- Always fails: the assertion, task, or capability may be broken.
- Passes only with the skill: identify the instruction or resource producing the gain.
- Flaky across runs: tighten ambiguous instructions or repair a nondeterministic eval.
- Large time/token outlier: inspect the trace for an unnecessary path.

Blindly compare outputs for organization, polish, usability, and correctness when assertions tie. Human review should record actionable feedback, including empty feedback when the result is satisfactory.

## Iteration loop

1. Combine failed assertions, human feedback, traces, and the current skill.
2. Propose a generalized, lean improvement.
3. Apply it and rerun the full suite in a clean iteration directory.
4. Grade, aggregate, and review again.
5. Stop when feedback is consistently empty, the desired threshold is met, or gains plateau.

If additions stop helping, remove constraints. More instructions can reduce quality by competing for attention or forcing irrelevant work.

Sources: [Optimizing skill descriptions](https://agentskills.io/skill-creation/optimizing-descriptions) and [Evaluating skill output quality](https://agentskills.io/skill-creation/evaluating-skills).
