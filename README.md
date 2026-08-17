# Agent Skills

Agent Skills I actually use, extracted from a year of running agents
against a ~40-crate Rust ecosystem, cross-platform GUI work, and the general
business of shipping software. No demos, no aspirational stubs — every skill
here earns its place by getting invoked in real sessions.

Each directory under `skills/` follows the open
[Agent Skills specification](https://agentskills.io/specification).

## Install

As a plugin (Claude Code 2.x):

```
/plugin marketplace add drewcrawford/drewcrawford-skills
/plugin install drewcrawford-skills@drewcrawford-skills
```

For local use with any client that scans the cross-client Agent Skills
directory, clone the repository and run the installer:

```bash
git clone https://github.com/drewcrawford/drewcrawford-skills
./drewcrawford-skills/install-skills.sh
```

The installer copies each skill once to `~/.agents/skills/`, the shared
cross-client location used by Codex and other compatible clients. It creates
symlinks in `~/.claude/skills/` for Claude Code. The installer is idempotent
and keeps an ownership manifest, so it removes retired skills from this
repository without touching skills installed by anything else. Re-run it
after `git pull` to update.

## What's in the box

**Metacognition** — two skills for investigations and architectural judgment:

* **investigate** — a protocol for hard bugs: a running INVESTIGATION.md that
  separates what we've *verified* (with the evidence) from what we merely
  suspect, so a multi-day debugging session survives context loss and
  tomorrow-you doesn't repeat today's dead ends.
* **dev-manager** — an escalation rubric: when should an agent stop coding and
  flag an architectural decision for a human? Encodes the judgment call.

**Release engineering:**

* **release-prep** — a Rust release gate. `release_prep` decides the mechanical
  checks itself (SPDX, MSRV, editions, publishability, doc coverage, README/crate-doc
  drift, crates.io name ownership) in seconds, and hands back a named prompt for
  the few that need judgment. Composes the CI and changelog skills below.
* **changelog** — generates release notes from git history with a five-level
  voice dial, from just-the-facts to Slack-release-notes chipper.
* **github** / **gitea** — CI monitors for both forges: full Python API
  clients with change-detection polling, per-job log retrieval, and a 0/1/124
  exit-code contract so they compose into shell deploy gates.
* **ecosystem-deps** — topological release ordering for any family of crates
  a workspace depends on, via Tarjan's SCC over a hand-parsed Cargo.lock.
  Point it at any crates.io author (`--author you`), an explicit list, or a
  checked-in manifest; with no flags it analyzes my ~40-crate ecosystem,
  which is what I use it for.

**Rust / WASM specifics** — the accumulated scar tissue:

* **rust-docs** — build and search docs for dependency crates locally, before
  guessing APIs or scraping the web.
* **wasm-time-best-practices**, **wasm32-browser**, **update-config-toml** —
  time handling on wasm32, browser selection for wasm-bindgen-test-runner,
  and the .cargo/config.toml flags that fix known upstream compiler issues
  (cited to the issues in question).

**Everything else:**

* **quiet-machine** — provisions exclusive, self-reaping Hetzner Cloud VMs for
  trusted tests, reuses idle machines through their paid billing window, ships
  dirty local worktrees over SSH, and turns live setup fixes into reusable
  Packer images.
* **dev-browser** — browser automation with persistent page state: a
  Playwright/CDP server with an ARIA snapshot engine and a WebSocket relay
  into your real Chrome. (Extended from an upstream project — see its README
  for attribution.)
* **github-issues** — chronological issue triage for "this used to work"
  bugs: search by recency, not just keywords.
* **linear** — an operator manual for
  [linearis](https://github.com/linearis-oss/linearis) (`npm i -g linearis`):
  Linear.app issue and project workflow with JSON output for every operation.
* **write-skills** — the meta-skill: how I write these, as a skill, with
  templates. If you disagree with my skills, use this one to write yours.

## Design notes

Every skill is a directory with a `SKILL.md` — YAML frontmatter for
activation, lean instructions, and depth (reference.md, examples.md, scripts)
linked on demand rather than jammed into the context window. This repository
intentionally omits the experimental `allowed-tools` field and leaves tool
risk classification, permissions, and approval decisions to the client.
There's a longer argument about progressive disclosure in `write-skills/`.

Pull requests validate every skill with the Agent Skills reference validator.

## License

MIT.

## Author

Written by [Drew Crawford](https://sealedabstract.com) — I build SDKs, Rust
infrastructure, and agent tooling for hire. If you've shipped Rust to a
browser lately, you've already shipped my code; if these skills saved you an
afternoon, that's the product demo. drew@drewcrawfordapps.com
