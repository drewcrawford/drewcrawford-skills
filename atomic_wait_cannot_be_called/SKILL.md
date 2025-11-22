---
name: atomic_wait_cannot_be_called
description: Provides information about diagnosing an error.  Use this skill IMMEDIATELY when you encounter an error like `Atomics.wait cannot be called in this context`
---

# Summary

You are likely dealing with a complex situation that may require escalation from the user unless the situation is obvious from this document.

# Threading model

## Terminology

On wasm, the "main thread" is:

* the initial top-level browsing context thread
* the one that runs your page's JS
* owns the DOM, canvas, Web APIs
* has a Window object
* And (critically!) does not support Atomics.wait() at all, for any reason

A "worker thread" is:

* aka a "web worker"
* Spawned in Rust via some ::spawn function
* can absolutely block with Atomics.wait, all day every day
* has no DOM access
* has no Window object, instead its global object is `DedicatedWorkerGlobalScope`
* Can not encounter the `Atomics.wait cannot be called in this context` error.

The error `Atomics.wait cannot be called in this context` is twofold: you are on a main thread, and you are doing something that is blocking.

## Application

There is a common fallacy that "you can't do blocking operations on wasm".  This is totally incorrect.  It is fine to do blocking operations on wasm, *from a worker thread*.  If you encounter this error, we know you are doing them *from the main thread*.  

So you can either:

1.  Find a way not to block
2.  Block, but on a different thread

And we must figure out which one to do.


## Identifying blocking functions

Blocking operations can be difficult to identify. They may have names like `block`, `sleep`, `park`, or `wait`.  


But they may not.  To specifically identify, produce a backtrace.

If that is difficult, consider using your rust-docs skill to try to identify blocking functions around the code in question.

### Test situations

The following are indicators you are on the main thread and will encounter this error for all your blocking calls:

* `#[wasm_bindgen_test]` will run tests on the main thread
* `#[test_executors::async_test]` complies to `#[wasm_bindgen_test]and runs on the main thread

### Solution pattern

```rust
use std::sync::{Arc, Mutex};
use r#continue::continuation;

#[cfg(target_arch = "wasm32")]
use wasm_thread as thread;

#[cfg(not(target_arch="wasm32"))
use std::thread as thread;

#[test_executors::async_test]
async fn test_blocking_operation() {
	let mtx = Mutex::new(0);
	// Spawn a worker thread for blocking operations
	//assumes using the continuation crate - use rust-docs for more detailsx
	let (sender, receiver) = r#continuation();

	thread::spawn(move || {
		// This blocking call is now safe - we're on a worker thread
		let mut guard = mtx.blocking_operation();
		// ... do work ...
		*guard += 1;

		let result = *guard;
		sender.send(result);
	});

	// Await the result on the main thread (non-blocking)
	let result = receiver.await;
	println!("Worker returned: {result}");
}
```

# Escalation steps

Before escalating to the user, use the `wasm_thread` skill for additional information.

Escalate to the user if:
96 +  * The blocking operation cannot easily be moved to a worker thread
97 +  * You need to block on the main thread for architectural reasons
98 +  * The fix requires significant restructuring of the test or application code






