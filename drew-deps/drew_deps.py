#!/usr/bin/env python3
"""
Analyzes external drewcrawford dependencies of a Rust workspace.

Produces a topologically-sorted list showing dependency ranks:
- Rank 0: No drewcrawford dependencies
- Rank 1: Depends only on rank 0 crates
- Rank N: Depends on at least one rank N-1 crate

Crates in dependency cycles are grouped together at their effective rank.

Usage:
    python3 drew_deps.py [workspace_path]
"""

import re
import sys
from collections import defaultdict
from pathlib import Path


# Known drewcrawford crates
DREWCRAWFORD_CRATES = {
    # Core crates
    "some_executor", "some_local_executor", "some_global_executor",
    "test_executors", "blocking_semaphore",
    # Async utilities
    "await_values", "continue", "portable_async_sleep",
    # Data structures
    "send_cells", "wasm_safe_mutex",
    # Threading
    "wasm_thread",
    # Logging
    "logwise", "logwise_proc", "exfiltrate",
    # Graphics/Window
    "images_and_words", "app_window", "nicholas", "tgar",
    # Other utilities
    "async_file", "investigator",
    "kiruna", "pcore", "objr", "blocksr", "foundationr", "coaborern",
    "dispatchr", "quartzcore", "uikitrs", "appkit", "metal_rs",
    # Game/engine specific
    "echos_hill", "petrucci", "missing_key",
    "speeds_n_feeds", "blitcurve", "noise", "path_finder",
    "design_system", "headline", "assets",
}


def normalize_name(name):
    """Normalize crate name (convert - to _)."""
    return name.replace('-', '_')


def is_drewcrawford_crate(name):
    """Check if a crate is authored by drewcrawford."""
    return normalize_name(name) in DREWCRAWFORD_CRATES


def parse_cargo_lock(lock_path):
    """Parse Cargo.lock and return package info, handling multiple versions."""
    packages = []  # list of (name, version, deps)
    current_pkg = None
    current_version = None
    current_deps = []
    in_deps = False

    with open(lock_path) as f:
        for line in f:
            line = line.strip()
            if line == "[[package]]":
                if current_pkg and current_version:
                    packages.append((current_pkg, current_version, current_deps))
                current_pkg = None
                current_version = None
                current_deps = []
                in_deps = False
            elif line.startswith("name = ") and '"' in line:
                current_pkg = line.split('"')[1]
            elif line.startswith("version = ") and '"' in line:
                current_version = line.split('"')[1]
            elif line == "dependencies = [":
                in_deps = True
            elif in_deps:
                if line == "]":
                    in_deps = False
                elif '"' in line:
                    dep = line.strip(' ",')
                    parts = dep.split()
                    dep_name = parts[0]
                    current_deps.append(dep_name)

        if current_pkg and current_version:
            packages.append((current_pkg, current_version, current_deps))

    return packages


def find_workspace_crates(workspace_root):
    """Find workspace crates."""
    workspace_crates = set()

    cargo_toml = workspace_root / "Cargo.toml"
    if not cargo_toml.exists():
        return workspace_crates

    with open(cargo_toml) as f:
        content = f.read()

    match = re.search(r'members\s*=\s*\[(.*?)\]', content, re.DOTALL)
    members = []
    if match:
        members_str = match.group(1)
        members = re.findall(r'"([^"]+)"', members_str)

    for toml_path in [cargo_toml] + [workspace_root / m / "Cargo.toml" for m in members]:
        if toml_path.exists():
            with open(toml_path) as f:
                content = f.read()
            match = re.search(r'\[package\].*?name\s*=\s*"([^"]+)"', content, re.DOTALL)
            if match:
                workspace_crates.add(normalize_name(match.group(1)))

    return workspace_crates


def find_sccs(nodes, edges):
    """Find strongly connected components using Tarjan's algorithm."""
    index_counter = [0]
    stack = []
    lowlinks = {}
    index = {}
    on_stack = {}
    sccs = []

    def strongconnect(node):
        index[node] = index_counter[0]
        lowlinks[node] = index_counter[0]
        index_counter[0] += 1
        stack.append(node)
        on_stack[node] = True

        for neighbor in edges.get(node, []):
            if neighbor not in index:
                strongconnect(neighbor)
                lowlinks[node] = min(lowlinks[node], lowlinks[neighbor])
            elif on_stack.get(neighbor, False):
                lowlinks[node] = min(lowlinks[node], index[neighbor])

        if lowlinks[node] == index[node]:
            scc = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                scc.append(w)
                if w == node:
                    break
            sccs.append(scc)

    for node in nodes:
        if node not in index:
            strongconnect(node)

    return sccs


def compute_ranks(packages, workspace_crates):
    """
    Compute dependency rank for each drewcrawford crate.
    """
    # Group by crate name, keeping latest version
    by_name = {}
    for name, version, deps in packages:
        if is_drewcrawford_crate(name):
            normalized = normalize_name(name)
            if normalized not in workspace_crates:
                if name not in by_name or version > by_name[name][0]:
                    by_name[name] = (version, deps)

    # Build dependency graph (only drewcrawford -> drewcrawford edges)
    drew_deps = {}
    for name, (version, deps) in by_name.items():
        drew_deps[name] = set()
        for dep in deps:
            if dep in by_name:
                drew_deps[name].add(dep)

    # Find SCCs to handle cycles
    sccs = find_sccs(set(by_name.keys()), drew_deps)

    # Map each node to its SCC
    node_to_scc = {}
    for i, scc in enumerate(sccs):
        for node in scc:
            node_to_scc[node] = i

    # Build SCC graph
    scc_deps = defaultdict(set)
    for node, deps in drew_deps.items():
        scc_id = node_to_scc[node]
        for dep in deps:
            dep_scc = node_to_scc[dep]
            if dep_scc != scc_id:
                scc_deps[scc_id].add(dep_scc)

    # Compute ranks for SCCs
    scc_ranks = {}
    remaining = set(range(len(sccs)))

    while remaining:
        ready = []
        for scc_id in remaining:
            unranked_deps = [d for d in scc_deps[scc_id] if d in remaining]
            if not unranked_deps:
                ready.append(scc_id)

        if not ready:
            # Should not happen after SCC decomposition
            for scc_id in remaining:
                scc_ranks[scc_id] = 0
            break

        for scc_id in ready:
            deps = scc_deps[scc_id]
            if not deps:
                scc_ranks[scc_id] = 0
            else:
                scc_ranks[scc_id] = max(scc_ranks[d] for d in deps) + 1
            remaining.remove(scc_id)

    # Map back to individual crates
    ranks = {}
    for node in by_name:
        ranks[node] = scc_ranks[node_to_scc[node]]

    # Track which crates are in cycles (SCC size > 1)
    in_cycle = set()
    for scc in sccs:
        if len(scc) > 1:
            in_cycle.update(scc)

    return ranks, by_name, drew_deps, in_cycle


def main():
    # Determine workspace root
    if len(sys.argv) > 1:
        workspace_root = Path(sys.argv[1])
    else:
        workspace_root = Path.cwd()

    lock_path = workspace_root / "Cargo.lock"
    if not lock_path.exists():
        print(f"Error: No Cargo.lock found in {workspace_root}", file=sys.stderr)
        sys.exit(1)

    packages = parse_cargo_lock(lock_path)
    workspace_crates = find_workspace_crates(workspace_root)

    ranks, drew_crates, drew_deps, in_cycle = compute_ranks(packages, workspace_crates)

    if not drew_crates:
        print("No external drewcrawford dependencies found.")
        return

    # Group by rank
    by_rank = defaultdict(list)
    for crate, rank in ranks.items():
        by_rank[rank].append(crate)

    print("External drewcrawford Dependencies (topologically sorted by rank)")
    print("=" * 70)
    print()

    max_rank = max(by_rank.keys()) if by_rank else 0

    for rank in range(max_rank + 1):
        crates = sorted(by_rank[rank])
        if not crates:
            continue

        print(f"# Rank {rank}: ", end="")
        if rank == 0:
            print("no drewcrawford dependencies")
        else:
            print(f"depends on rank {rank-1} or lower")
        print()

        for crate in crates:
            version, _ = drew_crates[crate]
            deps = drew_deps[crate]
            cycle_marker = " [CYCLE]" if crate in in_cycle else ""
            if deps:
                deps_str = ", ".join(sorted(deps))
                print(f"  {crate} {version}{cycle_marker}")
                print(f"    <- {deps_str}")
            else:
                print(f"  {crate} {version}{cycle_marker}")
        print()

    print(f"Total: {len(drew_crates)} external drewcrawford dependencies")

    if in_cycle:
        print(f"\nCrates in dependency cycles: {', '.join(sorted(in_cycle))}")


if __name__ == "__main__":
    main()
