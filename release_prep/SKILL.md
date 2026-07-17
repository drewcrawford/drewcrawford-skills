---
name: release_prep
description: Prepare a Rust crate for release.  Use this when the user asks to prepare for a release or to do "release prep".
allowed-tools: Skill(gitea), Skill(changelog), Skill(github), Read(~/.claude/skills/release_prep/**), Read(/tmp/**), WebFetch(domain:crates.io), Bash(~/.claude/skills/release_prep/scripts/line_count), Bash(~/.claude/skills/release_prep/scripts/compare_api.sh), Bash(~/.claude/skills/release_prep/scripts/compare_docs.sh), Bash(~/.claude/skills/release_prep/scripts/spdx), Bash(~/.claude/skills/release_prep/scripts/check_docs), Bash(~/.claude/skills/release_prep/scripts/11_ensure_agents_symlink), Bash(./scripts/check_all), Bash(./scripts/fmt), Bash(./scripts/check), Bash(./scripts/clippy), Bash(./scripts/tests), Bash(./scripts/docs), Bash(./scripts/native/tests), Bash(./scripts/wasm32/tests), Bash(cargo:*), Bash(grep:*), Bash(jq:*), Bash(find:*), Bash(test:*), Bash(echo:*), Bash(ln -s AGENTS.md CLAUDE.md), Bash(readlink CLAUDE.md), Bash(readlink ./CLAUDE.md), Bash(git status), Bash(git remote:*), Bash(git push origin), Bash(git push github), Bash(git tag:*), Bash(git stash:*), Bash(git checkout:*), Bash(git show-ref:*), Bash(git describe:*), Bash(git rev-parse:*), Bash(gh repo view:*), Bash(gh repo edit:*)
---

To prepare for a release, we follow a checklist in the checklist folder (i.e. release_prep/checklist/1.md, 2.md, etc.).  We want to focus on ONLY one step at a time, as the steps can be complex.

Do not ask to continue between steps.  If you are unable to complete a step, stop and await further instructions.

You may be asked "start with step N".  This means we have already completed the prior steps.

# Task

If you have a 'Task' or 'task mode' capability:

1. Run each checklist step in a separate Task, sequentially
2. Tell each task the path to its checklist file (use ~/.claude... syntax)
3. Require each task to record if it made any edits
4. If the task made edits, re-run the task again, to see if it will makes further edits, or if alternatively it reports no edits
5. When the subagent reports there are no edits, move on to the next checklist item.

# Reporting

At the end of your task report

* which step #s passed out of the box
* which ones passed after edits were made
* which ones failed
