#!/usr/bin/env python3
"""
Analyzes external dependencies from a chosen crate ecosystem in a Rust workspace.

An "ecosystem" is any set of crates you care about as a group — one author's
published crates, your company's internal set, or an explicit list. The tool
finds which ecosystem crates the workspace depends on and produces a
topologically-sorted list showing dependency ranks:
- Rank 0: No dependencies on other ecosystem crates
- Rank 1: Depends only on rank 0 crates
- Rank N: Depends on at least one rank N-1 crate

Crates in dependency cycles are grouped together at their effective rank.
Rank order is release order: publish rank 0 first.

Usage:
    python3 ecosystem_deps.py [workspace_path]                 # default: drewcrawford set
    python3 ecosystem_deps.py --author someuser [path]         # any crates.io author
    python3 ecosystem_deps.py --crates foo,bar,baz [path]      # explicit list
    python3 ecosystem_deps.py --crates-file crates.txt [path]  # one name per line
"""

import argparse
import json
import re
import ssl
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path


# Default ecosystem: known drewcrawford crates (the author's own).
# Override with --author, --crates, or --crates-file.
DEFAULT_CRATES = {
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
DEFAULT_LABEL = "drewcrawford"

CRATES_IO_UA = "ecosystem-deps (github.com/drewcrawford/drewcrawford-skills)"


def normalize_name(name):
    """Normalize crate name (convert - to _)."""
    return name.replace('-', '_')


def _ssl_context():
    # macOS system Python often lacks a usable CA bundle; prefer certifi's.
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def crates_io_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": CRATES_IO_UA})
    with urllib.request.urlopen(req, timeout=30, context=_ssl_context()) as resp:
        return json.load(resp)


def fetch_author_crates(login):
    """Fetch the set of crate names published by a crates.io user."""
    try:
        user = crates_io_get(f"https://crates.io/api/v1/users/{login}")
        user_id = user["user"]["id"]
    except Exception as exc:
        print(f"Error: could not resolve crates.io user {login!r}: {exc}",
              file=sys.stderr)
        sys.exit(1)

    names = set()
    page = 1
    while True:
        data = crates_io_get(
            "https://crates.io/api/v1/crates"
            f"?user_id={user_id}&per_page=100&page={page}"
        )
        batch = [c["name"] for c in data.get("crates", [])]
        names.update(batch)
        total = data.get("meta", {}).get("total", 0)
        if not batch or len(names) >= total:
            break
        page += 1

    if not names:
        print(f"Error: crates.io user {login!r} has no published crates.",
              file=sys.stderr)
        sys.exit(1)
    return names


def resolve_ecosystem(args):
    """Return (crate_name_set_normalized, label) from CLI args."""
    if args.crates:
        names = {c.strip() for c in args.crates.split(",") if c.strip()}
        label = "listed"
    elif args.crates_file:
        path = Path(args.crates_file)
        if not path.exists():
            print(f"Error: crates file not found: {path}", file=sys.stderr)
            sys.exit(1)
        names = {
            line.strip() for line in path.read_text().splitlines()
            if line.strip() and not line.strip().startswith("#")
        }
        label = path.stem
    elif args.author:
        names = fetch_author_crates(args.author)
        label = args.author
    else:
        names = DEFAULT_CRATES
        label = DEFAULT_LABEL

    if not names:
        print("Error: ecosystem crate set is empty.", file=sys.stderr)
        sys.exit(1)
    return {normalize_name(n) for n in names}, label


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


def compute_ranks(packages, workspace_crates, ecosystem):
    """Compute dependency rank for each ecosystem crate."""
    # Group by crate name, keeping latest version
    by_name = {}
    for name, version, deps in packages:
        if normalize_name(name) in ecosystem:
            normalized = normalize_name(name)
            if normalized not in workspace_crates:
                if name not in by_name or version > by_name[name][0]:
                    by_name[name] = (version, deps)

    # Build dependency graph (only ecosystem -> ecosystem edges)
    eco_deps = {}
    for name, (version, deps) in by_name.items():
        eco_deps[name] = set()
        for dep in deps:
            if dep in by_name:
                eco_deps[name].add(dep)

    # Find SCCs to handle cycles
    sccs = find_sccs(set(by_name.keys()), eco_deps)

    # Map each node to its SCC
    node_to_scc = {}
    for i, scc in enumerate(sccs):
        for node in scc:
            node_to_scc[node] = i

    # Build SCC graph
    scc_deps = defaultdict(set)
    for node, deps in eco_deps.items():
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

    return ranks, by_name, eco_deps, in_cycle


def main():
    parser = argparse.ArgumentParser(
        description="Rank a workspace's external dependencies from a chosen crate ecosystem."
    )
    parser.add_argument("workspace_path", nargs="?", default=None,
                        help="workspace root (default: cwd)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--author", help="crates.io username; ecosystem = their published crates")
    group.add_argument("--crates", help="comma-separated crate names")
    group.add_argument("--crates-file", help="file of crate names, one per line (# comments ok)")
    args = parser.parse_args()

    ecosystem, label = resolve_ecosystem(args)

    workspace_root = Path(args.workspace_path) if args.workspace_path else Path.cwd()

    lock_path = workspace_root / "Cargo.lock"
    if not lock_path.exists():
        print(f"Error: No Cargo.lock found in {workspace_root}", file=sys.stderr)
        sys.exit(1)

    packages = parse_cargo_lock(lock_path)
    workspace_crates = find_workspace_crates(workspace_root)

    ranks, eco_crates, eco_deps, in_cycle = compute_ranks(
        packages, workspace_crates, ecosystem
    )

    if not eco_crates:
        print(f"No external {label} dependencies found.")
        return

    # Group by rank
    by_rank = defaultdict(list)
    for crate, rank in ranks.items():
        by_rank[rank].append(crate)

    print(f"External {label} Dependencies (topologically sorted by rank)")
    print("=" * 70)
    print()

    max_rank = max(by_rank.keys()) if by_rank else 0

    for rank in range(max_rank + 1):
        crates = sorted(by_rank[rank])
        if not crates:
            continue

        print(f"# Rank {rank}: ", end="")
        if rank == 0:
            print(f"no {label} dependencies")
        else:
            print(f"depends on rank {rank-1} or lower")
        print()

        for crate in crates:
            version, _ = eco_crates[crate]
            deps = eco_deps[crate]
            cycle_marker = " [CYCLE]" if crate in in_cycle else ""
            if deps:
                deps_str = ", ".join(sorted(deps))
                print(f"  {crate} {version}{cycle_marker}")
                print(f"    <- {deps_str}")
            else:
                print(f"  {crate} {version}{cycle_marker}")
        print()

    print(f"Total: {len(eco_crates)} external {label} dependencies")

    if in_cycle:
        print(f"\nCrates in dependency cycles: {', '.join(sorted(in_cycle))}")


if __name__ == "__main__":
    main()
