---
name: atomic_wait_cannot_be_called
description: Provides a solution to the wasm32 error `Atomics.wait cannot be called in this context`
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

# Error explanation

The error `Atomics.wait cannot be called in this context` is twofold:
1.  You're on the main thread
2.  You're making a blocking call

You can be confident that when you see this error, BOTH things are true.  The question is whether to change #1 or #2, so that the error is resolved.  You can do the same thing on a different thread, or you can do a different thing on the main thread.

## Misconceptions

There is a common fallacy that "you can't do blocking operations on wasm".  This is totally incorrect.  It is fine to do blocking operations on wasm, *from a worker thread*.  If you encounter this error, we know you are doing it *from the main thread*.  

So you can either:

1.  Eliminate blocking, by removing calls to blocking functions
2.  Continue to block, continue to call the same functions, but on a different thread

You must carefully consider which way to go, considering the pros and cons.


## Identifying blocking functions

Blocking operations can be difficult to identify. They may have names like `block`, `sleep`, `park`, or `wait`.  

But they may not.  To specifically identify, produce a backtrace to identify the problematic function.

If that is difficult, consider using your rust-docs skill to try to identify blocking functions around the situation in question.

### Test situations

The following are indicators you are on the main thread and will encounter this error for all your blocking calls:


* `#[wasm_bindgen_test]` will run tests on the main thread
* `#[test_executors::async_test]` complies to `#[wasm_bindgen_test]and runs on the main thread

### Problem pattern

```rust
#[test]
fn test_blocking_operation() {
	let mtx = Mutex::new(0);

	//this blocking call may be dangerous on the main thread
	let mut guard = mtx.blocking_operation();
	// ... do work ...
	*guard += 1;
	
	let result = *guard;
	sender.send(result);
}
```


### Solution pattern - worker thread

This shows how to test a blocking function on WASM.  Since testing a blocking function is the purpose of this test, we will choose #2, continuing to block but on another thread.

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

### Solution pattern - nonblocking main thread

Instead of moving blocking onto a worker thread, we will eliminate blocking on the main thread:

```rust
#[cfg_attr(target_arch = "wasm32" wasm_bindgen_test::wasm_bindgen_test)]
#[test]
fn test_nonblocking_operation() {
	let mtx = Mutex::new(0);
	//we discovered this nonblocking call after using our rust-docs skill
	let mut guard = mtx.spin_lock(); 
	*guard += 1;
	drop(guard);
```


# Escalation steps

Before escalating to the user, use the `wasm_thread` skill for additional information.

Escalate to the user if:
* The blocking operation cannot easily be moved to a worker thread
* You need to block on the main thread for architectural reasons
* The fix requires significant restructuring of the test or application code






