---
name: release-prep
description: Prepare a Rust crate for release.  Use this when the user asks to prepare for a release or to do "release prep".
compatibility: Requires a Rust toolchain, git, standard Unix command-line tools, network access, and optional gh/Gitea credentials for forge operations.
---

To prepare for a release, follow the files in `checklist/` relative to this skill's directory (`checklist/1.md`, `checklist/2.md`, and so on). Focus on only one step at a time because individual steps can be complex.

Do not ask to continue between steps.  If you are unable to complete a step, stop and await further instructions.

You may be asked "start with step N".  This means we have already completed the prior steps.

# Task

If you have a 'Task' or 'task mode' capability:

1. Run each checklist step in a separate Task, sequentially
2. Tell each task the absolute path to its checklist file, resolved from this skill's directory
3. Require each task to record if it made any edits
4. If the task made edits, re-run the task again, to see if it will makes further edits, or if alternatively it reports no edits
5. When the subagent reports there are no edits, move on to the next checklist item.

# Reporting

At the end of your task report

* which step #s passed out of the box
* which ones passed after edits were made
* which ones failed
