# skills

Claude Code skills I actually use, extracted from a year of running agents
against a ~40-crate Rust ecosystem, cross-platform GUI work, and the general
business of shipping software. No demos, no aspirational stubs — every skill
here earns its place by getting invoked in real sessions.

## Install

As a plugin (Claude Code 2.x):

```
/plugin marketplace add drewcrawford/skills
/plugin install crawford-skills@crawford-skills
```

Or the old way, which also installs for OpenAI Codex:

```bash
git clone https://github.com/drewcrawford/skills && ./skills/install-skills.sh
```

The installer is idempotent and garbage-collects skills you've deleted from
the source tree, so re-running it after a `git pull` is the whole update story.

## What's in the box

**Metacognition** — the skills I'd keep if I could only keep three:

* **stuck** — teaches the agent to notice it's thrashing (compile-fix loops,
  repeated test hangs, "let me try a completely different approach" for the
  third time) and escalate with a diagnostic report instead of burning another
  hour. Includes a transcript analyzer that scores sessions for stuck patterns
  after the fact. Detects which agent runtime it's in (Claude Code, Codex,
  Antigravity) and adapts.
* **investigate** — a protocol for hard bugs: a running INVESTIGATION.md that
  separates what we've *verified* (with the evidence) from what we merely
  suspect, so a multi-day debugging session survives context loss and
  tomorrow-you doesn't repeat today's dead ends.
* **dev-manager** — an escalation rubric: when should an agent stop coding and
  flag an architectural decision for a human? Encodes the judgment call.

**Release engineering:**

* **release_prep** — a 25-step Rust release checklist (semver, MSRV, SPDX,
  API diffing against the last tag, doc coverage) that drives one subagent per
  step and composes the CI and changelog skills below.
* **changelog** — generates release notes from git history with a five-level
  voice dial, from just-the-facts to Slack-release-notes chipper.
* **github** / **gitea** — CI monitors for both forges: full Python API
  clients with change-detection polling, per-job log retrieval, and a 0/1/127
  exit-code contract so they compose into shell deploy gates.
* **drew-deps** — topological release ordering for crates depending on my
  ecosystem, via Tarjan's SCC over a hand-parsed Cargo.lock. Niche, but if
  you're using my crates, it's exactly the tool you want.

**Rust / WASM specifics** — the accumulated scar tissue:

* **rust-docs** — build and search docs for dependency crates locally, before
  guessing APIs or scraping the web.
* **wasm-time-best-practices**, **wasm32-browser**, **update_config_toml** —
  time handling on wasm32, browser selection for wasm-bindgen-test-runner,
  and the .cargo/config.toml flags that fix known upstream compiler issues
  (cited to the issues in question).

**Everything else:**

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
linked on demand rather than jammed into the context window. Tool-backed
skills declare `allowed-tools` so the agent gets exactly the commands it
needs and nothing else. There's a longer argument about progressive
disclosure in `write-skills/`.

## License

MIT.

## Author

Written by [Drew Crawford](https://sealedabstract.com) — I build SDKs, Rust
infrastructure, and agent tooling for hire. If you've shipped Rust to a
browser lately, you've already shipped my code; if these skills saved you an
afternoon, that's the product demo. drew@drewcrawfordapps.com
