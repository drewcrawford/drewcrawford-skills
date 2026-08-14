---
name: release-prep
description: Prepare a Rust crate for release.  Use this when the user asks to prepare for a release or to do "release prep".
compatibility: Requires a Rust toolchain, git, curl, standard Unix command-line tools, network access, and optional gh/Gitea credentials for forge operations.
---

# Release prep

Most of this checklist is decided by a grep, an exit code, or a path that does
or does not exist. `scripts/release_prep` runs all of that in seconds. What it
cannot decide, it hands back as a named prompt.

Run it from the repository being released:

```bash
scripts/release_prep                 # fast checks
scripts/release_prep --slow          # also builds, bisects, and runs the gate
```

Every check reports one of four verdicts:

| verdict | meaning | what to do |
|---|---|---|
| `ok` | decided, nothing to do | nothing |
| `FAIL` | decided, and it is wrong | apply the `fix:` command if there is one, otherwise follow the `prompt:` |
| `ask` | the script cannot decide | do the work the `prompt:` describes |
| `skip` | not applicable, or needs `--slow` | nothing, unless you meant to run it |

A check that raises reports `FAIL`, not `skip`. It confirmed nothing about the
repository, and `skip` does not block the gate — so a crashing check would
otherwise leave its subject unexamined under a run that says nothing is
outstanding.

Exit status is 0 only when nothing is outstanding, so the script doubles as the
gate: **work until it exits 0.**

Every `ask` fires on evidence and stops when the evidence changes — a changelog
missing a section for the version being released, a public API that moved since
the last tag, a commit no remote has seen. None of them is a standing reminder,
so `ask` on a re-run means something is genuinely still outstanding rather than
that the check has no opinion.

## How to work through it

1. Run `scripts/release_prep`. Read the whole report before starting — later
   items often explain earlier ones.
2. Handle every `FAIL` and `ask`. Each carries a `prompt:` written to be handed
   to an agent as-is, or followed yourself.
3. Re-run the script. It is cheap and idempotent, so **re-running is how you
   confirm convergence** — never re-run an agent to find out whether its own
   edit worked.
4. When the fast checks are clean, run `--slow` for the ones that build,
   bisect, or drive a browser.
5. Stop when it exits 0.

Do not ask the user for permission between checks. Do stop and ask if a check
tells you to escalate, or if fixing one would mean a decision the user has not
delegated — renaming a published crate, or going 1.0.

## Things the script deliberately leaves to you

- **Committing.** Several checks edit files, and the `ci` check needs a clean
  tree. Commit in logical units as you go; the script never commits.
- **Ordering.** The check order is the recommended order. In particular the
  `gate` runs last, *after* the checks that edit files — a gate that runs
  before the edits does not cover them.
- **Tagging and publishing.** Neither is part of this skill.

## Running one check

```bash
scripts/release_prep --list                    # every check name
scripts/release_prep --only readme-sync        # just one
scripts/release_prep --skip gate --slow        # everything slow except the gate
scripts/release_prep --format json             # machine-readable findings
```

`--only` is how you resume: if you already handled the documentation, re-run
the rest rather than starting over.

## The bundled tools

The checks call these, and they are useful directly when you are fixing
something:

| script | what it does |
|---|---|
| `scripts/line_count` | report oversized source files |
| `scripts/spdx` | check, or with `--apply` insert, SPDX headers |
| `scripts/check_docs` | rustdoc with `-D missing_docs` and the doc-correctness lints denied |
| `scripts/compare_api.sh` | public API at a baseline vs the working tree |
| `scripts/compare_docs.sh` | documented items at a baseline vs the working tree |
| `scripts/11_ensure_agents_symlink` | ensure `CLAUDE.md` points at `AGENTS.md` |
| `templates/ci.yml` | the shared CI matrix, versioned by the marker on line 1 |

Both comparison scripts fall back to an empty baseline when the repository has
no tags, so they work for a first release.

## The CI template is a generation, not a file

`ci-template` does not compare bytes. A project is expected to add steps and
matrix entries of its own — installing a sibling tool, widening the matrix,
raising `timeout-minutes` where the template says to. What it may not do is
silently fall behind or quietly drop a step.

So the check asks three narrower questions: does the `# matrix vN` marker match
the template's, is every template step and job-level key still present, and
what has the project added? The marker is the whole contract — **bumping it is
how you record that you merged this generation forward**, and nothing else in
the file can carry that claim. Merge the template in, keep everything the
project added, bump the marker; the check then reads ok and lists the extra
steps rather than asking about them again.

## Documentation, in two directions

`docs-assets` and `readme-sync` encode a convention worth knowing, because
getting it wrong renders correctly on your machine and breaks in public:

- A **crate doc** reaches its assets by absolute URL
  (`https://github.com/<owner>/<repo>/raw/main/art/logo.png`). A relative path
  resolves against `target/doc` locally and against nothing on docs.rs.
- A **README** reaches the same asset by repo-relative path (`art/logo.png`).
- Video is `<video src=… controls>` in the crate doc and the `.gif` of the same
  name in the README, because GitHub will not play an `.mp4` through image
  syntax.

`readme-sync` normalizes away link syntax, logo URLs, wrap width, path
qualifiers, and `#[attr]` spelling before comparing, so anything it reports is
real drift. It also reads git history to say which side was edited more
recently — if the README is the newer one, the edit landed on the wrong side
and belongs in the crate doc, which is the source.

## Reporting

When you finish, tell the user which checks passed outright, which needed work
and what you changed, and which are still outstanding and why.
