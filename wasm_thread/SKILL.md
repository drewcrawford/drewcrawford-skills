---
name: wasm_thread
description: Provides information about correctly spawning threads on wasm.  Use this before writing code that spawns threads on wasm platforms.  Use this before diagnosing why spawning threads isn't working on a wasm platform.  Use this to diagnose why something is dropped, because it is passed to a spawn closure on a WASM platform that is not executing.

---
# wasm_thread

On wasm32-unknown-unknown, std::thread mostly does not work.  Instead you need to use wasm_thread crate to spawn threads.

## Exception

wasm_thread has no wasm_thread::park() function.  For this API specifically, it is acceptable to use `std::thread::park()`.


# Conditional compilation

You should either do

```rust
#[cfg(not(target_arch = "wasm32"))]
use std::thread;
#[cfg(target_arch = "wasm32")]
use wasm_thread as thread;
```

at the top of a file.

or, if this problem is common in the crate, create a sys module that exports a `thread` type that can be used from the entire crate.

# names

Always pass a name to provided threads with 

```rust
thread::Builder::new().name("My name".to_string())
.spawn(|| {
	//hello world
})
.unwrap();
```

# Use additional skill

Using wasm_thread requires the skill wasm_atomics.  Before proceeding you should use that skill first.

# Sleep

It is acceptable to use thread::sleep *when you are not on the main thread*.

For example,

```rust
thread::Builder::new().name("My name".to_string())
.spawn(|| {
	//not on main thread
	//completely acceptable
	thread:sleep(Duration::from_millis(100)); 
})
.unwrap();
//questionable, need to investigate the calling context
//to determine main vs non-main thread
// thread:sleep(Duration::from_millis(100))
```

If you determine you need to sleep on the main thread, you should escalate to a human for more information.

