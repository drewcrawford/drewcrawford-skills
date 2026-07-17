---
name: ecosystem-deps
description: Analyze one crate ecosystem's dependencies inside a Rust workspace — any crates.io author's crates, an explicit list, or the built-in drewcrawford set. Shows the ecosystem's crates topologically sorted by rank (rank 0 = no ecosystem deps, rank N = depends on rank N-1) and detects dependency cycles. Use when you need release order for a family of crates, want to see which of an author's crates a project pulls in, or need to find circular dependencies.
---

# Ecosystem Dependencies Analyzer

Ranks a Rust workspace's external dependencies from a chosen "ecosystem" — any
set of crates you care about as a group: one author's published crates, your
company's internal set, or an explicit list. Rank order is release order.

## What It Does

- **Rank 0**: Crates with no dependencies on other ecosystem crates
- **Rank 1**: Crates that depend only on rank 0 crates
- **Rank N**: Crates that depend on at least one rank N-1 crate

Crates in dependency cycles are detected and marked with `[CYCLE]`.

## Usage

Run from any Rust workspace with a `Cargo.lock` (script lives at
`~/.claude/skills/ecosystem-deps/ecosystem_deps.py` for raw installs, or
`${CLAUDE_PLUGIN_ROOT}/skills/ecosystem-deps/ecosystem_deps.py` as a plugin):

```bash
# Default ecosystem: the drewcrawford crate set baked into the script
python3 ecosystem_deps.py [workspace_path]

# Any crates.io author's published crates (fetched from the crates.io API)
python3 ecosystem_deps.py --author someuser [workspace_path]

# Explicit crate list
python3 ecosystem_deps.py --crates tokio,hyper,tower [workspace_path]

# A checked-in ecosystem manifest, one crate name per line (# comments ok)
python3 ecosystem_deps.py --crates-file our-crates.txt [workspace_path]
```

`--author`, `--crates`, and `--crates-file` are mutually exclusive. Crate
names are `-`/`_` normalized, so either spelling works.

## Example Output

```
External drewcrawford Dependencies (topologically sorted by rank)
======================================================================

# Rank 0: no drewcrawford dependencies

  logwise_proc 0.4.0
  speeds_n_feeds 0.1.0
  wasm_thread 0.3.3

# Rank 1: depends on rank 0 or lower

  continue 0.1.1 [CYCLE]
    <- logwise
  logwise 0.4.0 [CYCLE]
    <- logwise_proc, wasm_safe_mutex, wasm_thread
  wasm_safe_mutex 0.1.1 [CYCLE]
    <- continue, wasm_thread

# Rank 2: depends on rank 1 or lower

  some_executor 0.6.2
    <- continue, wasm_thread
  ...

Total: 21 external drewcrawford dependencies

Crates in dependency cycles: continue, logwise, wasm_safe_mutex
```

## Use Cases

1. **Release Planning**: Know which crates to release first (start at rank 0, work up)
2. **Dependency Auditing**: See which of an author's crates your project pulls in
3. **Cycle Detection**: Identify problematic circular dependencies
4. **Understanding Architecture**: Visualize a crate family's dependency hierarchy

## How It Works

1. Resolves the ecosystem crate set (`--author` via the crates.io API with
   pagination; `--crates`/`--crates-file` verbatim; otherwise the built-in
   default set)
2. Parses `Cargo.lock` to get all packages and their dependencies
3. Filters to ecosystem crates, excluding workspace members
4. Uses the latest version of each crate for analysis
5. Finds strongly connected components (Tarjan's algorithm) to handle cycles
6. Computes topological rank per SCC and reports grouped by rank

## Default Ecosystem

With no selection flag, the script uses its built-in `DEFAULT_CRATES` set —
the author's own ~40 published crates (executors, async utilities, logging,
graphics/windowing, Apple-platform bindings). Edit that set in the script or
use the flags above to point it at your own ecosystem.

## Notes

- `--author` requires network access to crates.io; the other modes are offline.
- Only crates present in the workspace's `Cargo.lock` appear — this ranks what
  the workspace actually depends on, not the author's whole catalog.
