---
name: wasm32_rustflags
description: Provides information about the latest rustflags.  Use this when unit tests fail on wasm32-unknown-unknown with DataCloneError: WebAssembly.Memory object could not be cloned.
---

Check your config.toml.  You may need these:

```toml
[unstable]
# Tell *Cargo* to rebuild these crates for non-host targets (needs nightly)
build-std = ["std", "panic_abort"]

[target.'cfg(target_arch="wasm32")']
runner = "wasm-server-runner"

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
]
```