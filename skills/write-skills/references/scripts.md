# Bundled scripts for agentic use

Read this reference before adding or reviewing a script in a skill.

## Choose the lightest reliable mechanism

Reference an existing tool directly for a short, readable command. Pin its version when runtime resolution can change over time (`uvx`, `pipx`, `npx`, `bunx`, `deno run`, or `go run`). State prerequisites in `compatibility` when they apply to the whole skill.

Bundle a script when logic is complex, fragile, repeated across runs, or needs a stable interface. Prefer self-contained dependencies where the ecosystem supports them, such as PEP 723 metadata with `uv run` or versioned Deno imports.

## Interface contract

Design scripts for a non-interactive agent shell:

- accept every input through flags, environment variables, or stdin;
- never wait for a menu, password prompt, or TTY confirmation;
- implement concise `--help` with usage, flags, defaults, and examples;
- reject ambiguous or invalid input instead of guessing;
- state what failed, what was expected, what was received, and a corrective action;
- use meaningful documented exit codes;
- use exit `2` for invalid CLI usage and `124` for timeouts unless an established external convention requires otherwise;
- emit structured data such as JSON, CSV, or TSV on stdout;
- send progress, warnings, and diagnostics to stderr;
- default to idempotent, safe behavior because agents may retry;
- provide `--dry-run` for stateful/destructive operations and require explicit confirmation for irreversible execution;
- cap, summarize, paginate, or write large results to an output file so tool truncation does not hide critical data.
- avoid implicit output files; accept `--output` or `--output-dir` when an operation produces artifacts.

Resolve bundled resources relative to the skill root. In `SKILL.md`, list the script, say when to use it, and show the exact invocation.

## Testing checklist

- [ ] `--help` succeeds and is concise.
- [ ] A representative valid invocation produces the documented output.
- [ ] Missing required input fails quickly with an actionable message.
- [ ] Invalid enum, path, or format input is rejected.
- [ ] Structured stdout parses successfully and stderr contains only diagnostics.
- [ ] Repeating the operation is safe or explicitly guarded.
- [ ] Dry-run and confirmation gates work for state changes.
- [ ] Output remains useful below likely tool-output limits.
- [ ] Dependency versions and runtime requirements are explicit.

Source: [Using scripts in skills](https://agentskills.io/skill-creation/using-scripts).
