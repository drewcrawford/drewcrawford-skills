---
name: debug-hanging-wasm-unit-tests
description: Debug hanging unit tests on wasm32-unknown-unknown target in browser. Use specifically when unit tests hang, timeout, or run indefinitely on WASM target. Use this when cargo +nightly test --target wasm32-unknown-unknown --examples --bin --libs reaches the browser runner (e.g., Safari shows ‘Loading page elements…’) but never prints test results—this almost always means a WASM test is blocking the main thread.  Use immediately for errors such as "Failed to detect test as having been run. It might have timed out."  Do not use for general test failures, compilation errors, or doctest issues.
---

# Debug Hanging WASM Unit Tests

Expert guidance for identifying and fixing unit tests that hang indefinitely in WebAssembly browser environments.

# Verification

You want to verify some key assumptions to decide if this skill applies.

1.  Is the hanging test a unit test, or a doctest?  For example, compare

```
cargo test --bin
cargo test --lib
cargo test --doc
```

If the problem is with the `--doc` command, you have a doctest problem.  Doctests have a completely different execution model and are NOT covered under this guide.

2.  Is the hanging test a startup issue?  For example if you encounter an explicit error, that isn't a timeout, it may be unrelated to problems in tests.

# Known issue

One confirmed cause of this issue is the lack of certain rustflags.

Ones to try are (.cargo/config.toml):

```toml
[unstable]
# Tell *Cargo* to rebuild these crates for non-host targets (needs nightly)
build-std = ["std", "panic_abort"]

[target.'cfg(target_arch="wasm32")']
runner = "wasm-bindgen-test-runner"
rustflags = ["-C", "target-feature=+atomics",
    # see https://github.com/wasm-bindgen/wasm-bindgen/issues/4727
    # and https://github.com/rust-lang/rust/pull/147225
    "-Clink-arg=--shared-memory",
    # 4GB
    "-Clink-arg=--max-memory=4294967296",
    "-Clink-arg=--import-memory",
    "-Clink-arg=--export=__wasm_init_tls",
    "-Clink-arg=--export=__tls_size",
    "-Clink-arg=--export=__tls_align",
    "-Clink-arg=--export=__tls_base",
    # Workaround for wasm-bindgen duplicate function declarations with v0 mangling
    # see https://github.com/rustwasm/wasm-bindgen/issues/4820
    "-Csymbol-mangling-version=legacy",
    "-Zunstable-options",
]
```

A second confirmed cause of this issue is the specific version of rust nightly.  These flags are up to date for  1.93.0-nightly (9fa462fe3 2025-11-21), but these seem to change every so often.

Consider using the github-issues skill to check recent issues in wasm-bindgen.  Keep in mind that an issue there may have different symptoms, but could be the same underlying problem.



## Critical WASM Threading Rule

**In browser WASM environments, the main test thread CANNOT block, spin-wait, or perform synchronous waiting operations.** The main thread must remain responsive to the browser's event loop. Blocking the main thread prevents worker threads from being scheduled, causing tests to hang indefinitely.

## Scope

This skill applies **only to unit tests** (`#[test]` or `#[test_executors::async_test]`) that hang on WASM targets.

**Not applicable to:**
- Doctests (different execution model - mention they exist but this guidance doesn't apply)
- Compilation errors
- Test assertion failures
- Tests that complete but fail

## Quick Diagnostic

If unit tests hang when running `cargo +nightly test --target=wasm32-unknown-unknown`:

1. **Verify disable method works**: Disable ALL tests first to confirm the method works
2. **Identify the hanging test**: Systematically re-enable tests one at a time with `#[cfg(not(target_arch = "wasm32"))]` to find which test(s) hang
3. **Check for main thread blocking**: Look for blocking operations in the main test function body
4. **Restructure the test**: Move ALL blocking operations into spawned worker threads

## Unit Test Structure

### ✅ Correct Pattern: Worker Thread Blocking

```rust
use std::sync::{Arc, Mutex, Condvar};

#[test_executors::async_test]
async fn test_blocking_operation() {
    let pair = Arc::new((Mutex::new(false), Condvar::new()));
    let pair_clone = Arc::clone(&pair);

    // Thread 1: Setter (can block in worker)
    let (c1, r1) = continuation();
    thread::spawn(move || {
        thread::sleep(Duration::from_millis(10));  // ✅ OK: sleep in worker
        let (mutex, condvar) = &*pair_clone;
        let mut ready = mutex.lock().unwrap();     // ✅ OK: lock in worker
        *ready = true;
        drop(ready);
        condvar.notify_one();
        c1.send(());
    });

    // Thread 2: Waiter (MUST be in worker, not main thread)
    let (c2, r2) = continuation();
    thread::spawn(move || {
        let (mutex, condvar) = &*pair;
        let mut ready = mutex.lock().unwrap();     // ✅ OK: lock in worker
        while !*ready {
            ready = condvar.wait(ready).unwrap();  // ✅ OK: blocking wait in worker
        }
        assert!(*ready);
        c2.send(());
    });

    // Main thread: Only awaits continuations - NEVER blocks
    r1.await;
    r2.await;
}
```

### ❌ Anti-Pattern: Main Thread Blocking (HANGS!)

```rust
use std::sync::{Arc, Mutex, Condvar};

#[test_executors::async_test]
async fn test_blocking_operation() {
    let pair = Arc::new((Mutex::new(false), Condvar::new()));
    let pair_clone = Arc::clone(&pair);

    let (c, r) = continuation();
    thread::spawn(move || {
        thread::sleep(Duration::from_millis(10));
        let (mutex, condvar) = &*pair_clone;
        let mut ready = mutex.lock().unwrap();
        *ready = true;
        drop(ready);
        condvar.notify_one();
        c.send(());
    });

    // ❌ WRONG: Main thread blocking/spinning
    let (mutex, condvar) = &*pair;
    let mut ready = mutex.lock().unwrap();         // ❌ HANGS: blocking on main thread
    while !*ready {
        ready = condvar.wait(ready).unwrap();      // ❌ HANGS: blocking wait on main thread
    }
    assert!(*ready);

    r.await;
}
```

**Why it hangs**: `condvar.wait()` blocks the current thread using `thread::park()` which doesn't yield to the browser event loop. The worker thread never gets scheduled, so it never sets the value, creating a deadlock.

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

## Systematic Debugging Process

When tests hang on WASM target, follow this process:

### Step 1: Verify Disable Method Works

**CRITICAL**: Before trying to identify which tests hang, verify that disabling tests actually works.

1. Add `#[cfg(not(target_arch = "wasm32"))]` to ALL potentially problematic tests
2. Run tests: `cargo +nightly test --target=wasm32-unknown-unknown`
3. Tests should complete quickly (seconds, not minutes)
4. If still hangs, your disable method isn't working correctly

**Why this matters**: If disabling doesn't work, you'll waste time thinking specific tests hang when actually the disable syntax is wrong.

### Step 2: Identify Hanging Tests

Once you've confirmed disabling works:

1. **Run with timeout** to avoid infinite hangs:
   ```bash
   timeout 90 cargo +nightly test --target=wasm32-unknown-unknown
   ```

2. **Re-enable tests one at a time**:
   - Remove `#[cfg(not(target_arch = "wasm32"))]` from ONE test
   - Run with timeout
   - If it passes (< 90 seconds), the test is fine - move to next
   - If it times out, mark it: `#[cfg(not(target_arch = "wasm32"))] // HANGS on WASM`
   - Re-disable it and continue to next test

3. **Result**: List of all tests that hang on WASM

### Step 3: Fix Each Hanging Test

For each hanging test identified:

1. **Identify blocking operations** in main test function body (look for `mutex.lock()`, `condvar.wait()`, `thread::sleep()`, `thread::park()`, spin loops)
2. **Move ALL blocking operations** into `thread::spawn(move || { ... })` workers
3. **Coordinate with continuations**: `let (c, r) = continuation(); ... c.send(); ... r.await`
4. **Main thread only awaits** - never blocks or spins
5. **Verify fix**: Re-enable test and confirm it passes

## Test Attribute Requirements

For WASM tests with worker threads:

```rust
// At module level (in tests module)
#[cfg(all(test, target_arch = "wasm32"))]
wasm_bindgen_test::wasm_bindgen_test_configure!(run_in_browser);

// On async tests that spawn threads
#[test_executors::async_test]
async fn test_name() {
    // Test body
}
```

## Complete Example: Before and After

### Before (Hangs on WASM)
```rust
use std::sync::{Arc, Mutex, Condvar};
use std::collections::VecDeque;

#[test_executors::async_test]
async fn test_producer_consumer() {
    let queue = Arc::new((Mutex::new(VecDeque::new()), Condvar::new()));
    let producer = Arc::clone(&queue);

    let (c, r) = continuation();
    thread::spawn(move || {
        let (mutex, condvar) = &*producer;
        let mut q = mutex.lock().unwrap();
        q.push_back(42);
        drop(q);
        condvar.notify_one();
        c.send(());
    });

    // ❌ Main thread blocking
    let (mutex, condvar) = &*queue;
    let mut q = mutex.lock().unwrap();      // ❌ Blocking on main thread
    while q.is_empty() {
        q = condvar.wait(q).unwrap();       // ❌ HANGS HERE - blocking on main thread
    }
    assert_eq!(q[0], 42);

    r.await;
}
```

### After (Works on WASM)
```rust
use std::sync::{Arc, Mutex, Condvar};
use std::collections::VecDeque;

#[test_executors::async_test]
async fn test_producer_consumer() {
    let queue = Arc::new((Mutex::new(VecDeque::new()), Condvar::new()));
    let producer = Arc::clone(&queue);

    // Producer thread
    let (c1, r1) = continuation();
    thread::spawn(move || {
        let (mutex, condvar) = &*producer;
        let mut q = mutex.lock().unwrap();
        q.push_back(42);
        drop(q);
        condvar.notify_one();
        c1.send(());
    });

    // ✅ Consumer in worker thread (not main thread)
    let consumer = Arc::clone(&queue);
    let (c2, r2) = continuation();
    thread::spawn(move || {
        let (mutex, condvar) = &*consumer;
        let mut q = mutex.lock().unwrap();     // ✅ OK in worker thread
        while q.is_empty() {
            q = condvar.wait(q).unwrap();      // ✅ OK in worker thread
        }
        assert_eq!(q[0], 42);
        c2.send(());
    });

    // Main thread only awaits - never blocks
    r1.await;
    r2.await;
}
```

## Key Takeaways

1. **Main thread rule**: On WASM in browser, main unit test thread must NEVER block or spin-wait
2. **Worker threads**: ALL blocking operations must be in `thread::spawn()` workers
3. **Verify disable works FIRST**: Before identifying hanging tests, confirm disabling method works
4. **Systematic approach**: Disable all → verify → re-enable one at a time → identify → fix
5. **Generic APIs**: This applies to standard `std::sync` primitives, not just custom crates
6. **Unit tests only**: Doctests have different execution models

## Scope Reminder

This skill applies specifically to:
- ✅ Unit tests (`#[test]`) that hang on wasm32-unknown-unknown target
- ✅ Tests using `std::sync` primitives (Mutex, Condvar, channels, etc.)
- ✅ Browser WASM environment with worker threads

This skill does NOT apply to:
- ❌ Doctests (different execution model)
- ❌ Compilation errors
- ❌ Test assertion failures
- ❌ Native platform tests
- ❌ Tests that complete but fail assertions
