---
name: wasm-time-best-practices
description: Best practices for time handling in Rust projects supporting WebAssembly (WASM). Use when implementing timeouts, waiting, sleeping, or using Instant/Duration in code that targets WASM.
---
# WASM Time Best Practices
## The Problem
`std::time::Instant` often panics or behaves inconsistently on `wasm32-unknown-unknown` targets (e.g., in browsers). However, you generally want to avoid adding the `web_time` dependency for non-WASM builds to keep them standard.
## The Solution: Conditional Compilation
Use conditional compilation to switch between `std::time` (for native) and `web_time` (for WASM).
1.  **Add Dependency**: Add `web-time` as a target-specific dependency in `Cargo.toml`.
2.  **Alias Types**: Create a module or use imports to alias `Instant` and `Duration` to the correct crate based on the architecture.
## Implementation Example
### Cargo.toml
```toml
[target.'cfg(target_arch = "wasm32")'.dependencies]
web-time = "1.1"
```
### Rust Code
```rust
#[cfg(not(target_arch = "wasm32"))]
use std::time::{Duration, Instant};
#[cfg(target_arch = "wasm32")]
use web_time::{Duration, Instant};
fn do_something_with_timeout(deadline: Instant) {
	// ...
}
```
Or, centralize it in a `sys` or `time` module:
```rust
// src/time_utils.rs
#[cfg(not(target_arch = "wasm32"))]
pub use std::time::*;
#[cfg(target_arch = "wasm32")]
pub use web_time::*;
```