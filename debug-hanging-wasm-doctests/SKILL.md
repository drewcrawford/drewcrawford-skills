---
name: debug-hanging-wasmt-doctests
description: Debug hanging doctests on wasm32-unknown-unknown target in browser. Use specifically when doc tests hang, timeout, or run indefinitely on WASM target. Use this when cargo +nightly test --target wasm32-unknown-unknown --doc reaches the browser runner (e.g., Safari shows ‘Loading page elements…’) but never prints test results.  Do not use for general test failures, compilation errors, or doctest issues. Do not use for unit tests.
---

# Overview

This guide is specific to doctests on wasm32.  It has information that is not related to unit tests, integration tests, or other types of tests.  It is completely unrelated to native, x86_64, AArch64 platforms.

## Critical WASM Threading Rule

**In browser WASM environments, the main doctest thread CANNOT block, spin-wait, or perform synchronous waiting operations.** 

Moreover, the main doctest thread CANNOT be an async method so it cannot `await` on those things either.

This means that

* While you can spawn threads in a doctest, you CANNOT wait on their results or use them to pass/fail the test
* The only workaround is a) to move to a unit test, which will involve the strategies in the debug-hanging-wasm-unit-tests skill.  Or b) compiling out the test on wasm32.

## Common Blocking Operations

These operations will hang if called from the main test thread on WASM:

- `mutex.lock()` - Blocks waiting for lock acquisition
- `condvar.wait(guard)` - Blocks waiting for notification
- `thread::park()` - Parks current thread
- `thread::sleep(duration)` - Sleeps current thread
- `std::hint::spin_loop()` in tight loop - Spins without yielding
- `channel.recv()` - Blocks waiting for message
- Any synchronous operation that waits for worker thread state changes

**Safe operations** (don't block event loop):
- `.await` on async operations
- Spawning threads with `thread::spawn()`
- Awaiting futures/continuations
- Non-blocking try operations (`mutex.try_lock()`, `channel.try_recv()`)

## Quick Diagnostic

If unit tests hang when running `cargo +nightly test --target=wasm32-unknown-unknown`:

1. **Verify disable method works**: Disable ALL tests first to confirm the method works
2. **Identify the hanging test**: Systematically re-enable tests one at a time with `#[cfg(not(target_arch = "wasm32"))]` to find which test(s) hang
3. **Check for main thread blocking**: Look for blocking operations in the main test function body
4. **Restructure the test**: Move ALL blocking operations into spawned worker threads

## Disabling doctests on wasm32

Use this pattern:

/// ```rust
/// #![cfg_attr(target_arch = "wasm32", doc = "ignore")]
/// //my doctest goes here
/// ```




