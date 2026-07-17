---
name: github-issues
description: Browse and search recent GitHub issues using the `gh` CLI. Use when investigating bugs that might be recent regressions, when searching by keywords fails to find relevant issues, or when you need to see what issues have been filed in the last N days. Especially useful when a bug "used to work" or appears related to recent upstream changes.
---

# GitHub Issues Browser

Browse and search GitHub issues chronologically using the `gh` CLI. This is essential when investigating potential regressions where keyword searches fail because the issue title/description uses different vocabulary than your symptoms.

## When to use this skill

- Investigating a bug that "used to work" or "works on old version"
- Keyword searches aren't finding relevant issues
- You suspect a recent upstream change caused the problem
- You want to see all issues filed in the last N days
- Looking for issues that might be duplicates of yours before filing

## Key Insight

**Symptom vs. Root Cause Mismatch:** When a bug manifests as symptom X (e.g., "duplicate JS functions") but the root cause is Y (e.g., "v0 symbol mangling change"), searching for X won't find issues filed about Y. Browsing chronologically catches these.

## Commands

### List recent issues (all states)

```bash
# Last 50 issues, all states (open + closed)
gh issue list --repo <owner>/<repo> --state all --limit 50

# JSON output for more details
gh issue list --repo <owner>/<repo> --state all --limit 50 --json number,title,state,createdAt,closedAt,labels
```

### Filter by date (issues created in last N days)

```bash
# Issues created in last 7 days
gh issue list --repo <owner>/<repo> --state all --search "created:>=$(date -v-7d +%Y-%m-%d)"

# Issues created in last 14 days
gh issue list --repo <owner>/<repo> --state all --search "created:>=$(date -v-14d +%Y-%m-%d)"

# Linux date syntax
gh issue list --repo <owner>/<repo> --state all --search "created:>=$(date -d '7 days ago' +%Y-%m-%d)"
```

### Search with keywords + date filter

```bash
# Combine keyword search with date filter
gh issue list --repo <owner>/<repo> --state all --search "nightly created:>=2025-11-01"
gh issue list --repo <owner>/<repo> --state all --search "duplicate created:>=2025-11-15"
gh issue list --repo <owner>/<repo> --state all --search "SyntaxError created:>=2025-11-20"
```

### View issue details

```bash
# View full issue with comments
gh issue view <number> --repo <owner>/<repo>

# View in browser
gh issue view <number> --repo <owner>/<repo> --web

# JSON for programmatic access
gh issue view <number> --repo <owner>/<repo> --json title,body,comments,labels,state
```

### Search closed issues (often have solutions)

```bash
# Recently closed issues often contain solutions/workarounds
gh issue list --repo <owner>/<repo> --state closed --limit 30
gh issue list --repo <owner>/<repo> --state closed --search "created:>=2025-11-15"
```

### List by label

```bash
# Find bug reports
gh issue list --repo <owner>/<repo> --label bug --state all

# Find regressions specifically
gh issue list --repo <owner>/<repo> --label regression --state all
```

## Investigation Workflow

When investigating a potential regression:

### 1. Browse recent issues chronologically (don't just search)

```bash
gh issue list --repo rust-lang/rust --state all --limit 30
gh issue list --repo rustwasm/wasm-bindgen --state all --limit 30
```

### 2. Check issues from the timeframe when the bug appeared

```bash
# If bug appeared around Nov 20, check issues from Nov 18+
gh issue list --repo rustwasm/wasm-bindgen --state all --search "created:>=2025-11-18"
```

### 3. Look at recently closed issues (they may have your fix)

```bash
gh issue list --repo rustwasm/wasm-bindgen --state closed --search "created:>=2025-11-18"
```

### 4. Search with multiple symptom keywords

```bash
gh issue list --repo rustwasm/wasm-bindgen --state all --search "duplicate OR SyntaxError OR nightly"
```

### 5. Read promising issues in full

```bash
gh issue view 4820 --repo rustwasm/wasm-bindgen
```

## Common Repositories for WASM/Rust Issues

```bash
# Rust compiler
gh issue list --repo rust-lang/rust --state all --search "wasm created:>=2025-11-15"

# wasm-bindgen
gh issue list --repo rustwasm/wasm-bindgen --state all --limit 30

# wasm-pack
gh issue list --repo rustwasm/wasm-pack --state all --limit 30

# wasm_thread
gh issue list --repo chemicstry/wasm_thread --state all --limit 20
```

## Pro Tips

1. **Always check closed issues** - The fix might already exist
2. **Browse chronologically first** - Don't rely only on keyword search
3. **Check related repos** - A wasm-bindgen bug might be discussed in rust-lang/rust
4. **Look at issue cross-references** - Issues often link to duplicates/related issues
5. **Date filter is your friend** - `created:>=YYYY-MM-DD` narrows to relevant timeframe
