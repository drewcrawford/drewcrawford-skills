---
name: drew-deps
description: Analyze drewcrawford crate dependencies in a Rust workspace. Shows external drewcrawford dependencies topologically sorted by rank (rank 0 = no drew deps, rank N = depends on rank N-1). Detects dependency cycles. Use when you need to understand the dependency hierarchy of drewcrawford crates, plan release order, or identify circular dependencies.
---

# Drew Dependencies Analyzer

Analyzes external drewcrawford crate dependencies in a Rust workspace, producing a topologically-sorted list showing dependency ranks.

## What It Does

- **Rank 0**: Crates with no drewcrawford dependencies
- **Rank 1**: Crates that depend only on rank 0 crates
- **Rank N**: Crates that depend on at least one rank N-1 crate

Crates in dependency cycles are detected and marked with `[CYCLE]`.

## Usage

Run the script from any Rust workspace with a `Cargo.lock`:

```bash
python3 ~/.claude/skills/drew-deps/drew_deps.py
```

Or from within a project:

```bash
python3 ~/.claude/skills/drew-deps/drew_deps.py /path/to/workspace
```

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
2. **Dependency Auditing**: See which drew crates your project pulls in
3. **Cycle Detection**: Identify problematic circular dependencies
4. **Understanding Architecture**: Visualize the dependency hierarchy

## How It Works

1. Parses `Cargo.lock` to get all packages and their dependencies
2. Filters to only drewcrawford crates (excludes workspace members)
3. Uses latest version of each crate for analysis
4. Finds strongly connected components (SCCs) using Tarjan's algorithm to handle cycles
5. Computes topological rank for each SCC
6. Reports results grouped by rank

## Known Drewcrawford Crates

The script recognizes these crate families:
- **Executors**: `some_executor`, `some_local_executor`, `some_global_executor`, `test_executors`, `blocking_semaphore`
- **Async**: `await_values`, `continue`, `portable_async_sleep`
- **Data structures**: `send_cells`, `wasm_safe_mutex`
- **Threading**: `wasm_thread`
- **Logging**: `logwise`, `logwise_proc`, `exfiltrate`
- **Graphics**: `images_and_words`, `app_window`, `nicholas`, `tgar`
- **Utilities**: `async_file`, `investigator`
- **Platform**: `kiruna`, `pcore`, `objr`, `blocksr`, `foundationr`, etc.

To add more crates, edit the `DREWCRAWFORD_CRATES` set in the script.
