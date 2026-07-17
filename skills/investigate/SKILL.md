---
name: investigate
description: Provides a structured approach to solving "hard" bugs.  Use this when debugging a problem where the cause is not obvious from preliminary debugging
---

The key idea is to keep a running log of what we've discovered so far, so that when we are finished working for today we can pick this up tomorrow.

Create a file called INVESTIGATION.md.  Required format:

```md
# Investigation

## Original problem

Describe briefly the original problem

## Changes made

We have not made any changes.

## Verified

We have not verified anything so far.

## Ideas

List ideas that might advance the investigation

## Steps taken

List each investigate step, and briefly summarize the output.

## Notes

List any notes that might be important to remember later.

```

## Changes made

Briefly describe changes we've made to the codebase,

```
* Disabled all wasm32 tests to isolate the problem
* Added log code to src/example.rs to trace
* Rewrote the foo test since it hung on windows
```

## Verified

Describe things we become certain about over the course of the investigation, along with the reason we are certain. 

```
* We know the tests fail because we ran `cargo test` and got a panic.
* We know the tests pass on another machine because the user tried it.
```

We must think hard before deciding we are certain.  Certainty comes from clear hard evidence, not guesswork.

## Ideas

This is the guesswork.  List different ways we might solve the problem or gather more information.

```
* I could use a relevant skill to look for more information about this topic.
* I could check recent commits to see what's been changed.
* I think there is a panic, but it isn't being printed.
* Alternatively, maybe there's no panic, and the code is just hanging?
```

## Steps taken

Document the steps we've taken in our investigation to avoid duplication of effort.

```
1.  Checked the recent github issues, found nothing relevant
2.  Did a search for the error message on the web, results seem mostly unrelated
3.  Did a search for the error message in the codebase, but it appears to come from a dependent crate.
```

## Notes

Any other facts relevant to the investigation.

```
This only reproduces on nightly.
```


## Subinvestigations

From time to time, you will encounter problems that form a tree.  For example,

1.  "Make the tests pass" may composed of multiple subproblems:
    1.  Make the tests *compile*
	2.  Find out which tests are failing
	3.  Make the first test pass
	
Each of these may be fairly complex tasks.  When this occurs, create a subinvestigation in INVESTIGATION_1.md to solve this subproblem.  If the subproblem is disconnected from the main problem, assign it to a task or subagent.


In some cases, it is not clear whether to work through a subproblem or stay on the main problem.  For example, if logging is broken, debugging may be difficult, but on the other hand we could also try to debug without logging.  In this situation, you can instruct a subagent to explore how complex the subproblem will be, or to try to solve it but give up if it seems hard.  In this way we can focus efficiently on the best path.
