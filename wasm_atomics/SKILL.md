---
name: atomic_wait_cannot_be_called
description: Provides information about diagnosing an error.  Use this skill when you encounter an error on WASM targets like `Atomics.wait cannot be called in this context`
---
# wasm_atomics

You are probably trying to build a multithreaded WASM program, which requires `-C target-feature=+atomics` on WASM.

# Procedure

Always begin with nightly rust for WASM platforms.  (It's fine to use stable Rust for native platforms, this document is specific to WASM platforms only.)

```bash
cargo +nightly [command] --target=wasm32-unknown-unknown
```

Try running without custom rustflags first.  The rustflags needed nightly frequently change, and your guess is out of date.

```bash
cargo +nightly test --target=wasm32-unknown-unknown
```

When you do this, it uses the rustflags from `.cargo/config.toml`.  If you need rustflags for your own purposes, those are more up to date than your own knowledge, but you should consider the possibility that 'nightly' is far more frequent still and these things change.

# Warning

When rustflags are not correct or too old, you will frequently encounter error messages at runtime that are misleading and incorrect.  Before you interpret them you should decide if the rustflags being out of date might be the cause of the error.






