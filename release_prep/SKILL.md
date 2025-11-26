---
name: release_prep
description: Prepare a Rust crate for release.  Use this when the user asks to prepare for a release or to do "release prep".
---

To prepare for a release, we follow a checklist in the checklist folder (i.e. release_prep/checklist/1.md, 2.md, etc.).  We want to focus on ONLY one step at a time, as the steps can be complex.

Do not ask to continue between steps.  If you are unable to complete a step, stop and await further instructions.

You may be asked "start with step N".  This means we have already completed the prior steps.

# Task

If you have a 'Task' or 'task mode' capability:

1. Run each checklist step in a separate Task
2. Tell each task where the release_prep folder is located and where the path to its checklist file
2. Require each task to record if it made any edits
3. If the task made edits, re-run the task again, to see if it will makes further edits, or if alternatively it reports no edits
4. When the subagent reports there are no edits, move on to the next checklist item.

# Reporting

At the end of your task report

* which step #s passed out of the box
* which ones passed after edits were made
* which ones failed
