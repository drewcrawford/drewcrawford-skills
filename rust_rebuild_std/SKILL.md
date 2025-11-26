---
name: rust_rebuild_std
description: Provides information about rebuilding rust standard library, use when encountering the rust-lld linker error: --shared-memory is disallowed by ... because it was not compiled with 'atomics' or 'bulk-memory' features
---

The fix is to add the following in .cargo/config.toml

```toml
[unstable]
# Tell *Cargo* to rebuild these crates for non-host targets (needs nightly)
build-std = ["std", "panic_abort"]
```