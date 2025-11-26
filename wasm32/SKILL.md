---
name: wasm32-logging
description: Provides critical information that logs on wasm32 might be missing or present but incomplete.  Use this when doing log-based debugging on wasm32.  Use it when inferring any information from the presence or absence of a log message on wasm32.
---

# The problem

wasm32 is run via a complex series of runners between the console log in JS and the runners and wrappers redirecting the output, and many of these tools have interesting bugs.

In practice, you are likely to see no output or selective log output unless you carefully follow these instructions.

We are still collecting data on how to best solve the problem, leading theories are listed below.  Note that often there are multiple root causes that must all be addressed for logging

# Solution 0: 

println! and eprintln! are complete no ops on wasm.  You must either use  web_sys::console::log_1 or the logwise crate.

These tools do not fully solve the problem on their own but they might get you from "no logs" to "some logs".

Succeeded 0 out of 0 tries.

# Solution: `exfiltrate_cli`

The `exfiltrate_cli` tool provides an ability to remotely collect logwise logs, but it requires setup and orchestration.  Still it's a viable option and parts can be automated.

Succeeded 0 out of 0 tries.

# Solution 2: scripts/wasm-test-with-logs.sh and capture-logs.js

This is a custom orchestration layer that dumps logs via CDP.  See the usage for more information.

That said it is relatively new and you may encounter issues.

Succeeded 1 out of 1 tries.

# Solution: channels

It is thought that one of the main problems with logging is that, logs from only some threads are discarded.  If that is correct, it means an approach like this could work:

1.  Send logs into a channel
2.  Do actual logging from the main thread.

There are some details though.  The main thread cannot block, so you'd need an asynchronous channel, so there are many ways to introduce new bugs during this process.

Succeeded 0 out of 0 tries.

# Solution: don't panic

Another cause of logs not appearing are panics that don't get logged themselves (so you abort at some unreported moment).  It's also suspected somewhere in the wrapper layer it's possible for a panic to "time-travel" and delete some logs from before the panic, meaning logs are not reliable narrators on when the panic took place.  You may be able to spot potential sources of panic manually and rewrite them, even temporarily, to return or something.

Succeeded 0 out of 0 tries.

# Solution: do panic

Another approach is to try to use panic itself as a diagnostic tool.  Sometimes when you can't get good logs, you can still figure out if a panic occurred or not by some demonstratable change in behavior/output.  In this case you can use panics to smuggle 1 bit of information out by panicking conditionally.

Succeeded 0 out of 0 tries.

# Solution 5: console_error_panic_hook

Sometimes this can improve visibility of a panic, but this is not guaranteed.  If this surfaces a panic that's reliable, but if it doesn't – maybe the hook just doesn't work here.

Succeeded 0 out of 0 tries.

# Solution 6: nocapture

Sometimes this improves log output in tests:

[cargo test...]  -- --nocapture

Succeeded 0 out of 0 tries.












