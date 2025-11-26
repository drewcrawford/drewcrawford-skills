---
name: debug-failing-wasm-unit-tests
description: Debug FAILIING unit tests on wasm32-unknown-unknown target.  Use this when encountering errors like `DataCloneError: WebAssembly.Memory object could not be cloned`, or any other explicit errors in running wasm32 tests.
---

# Use nightly rust

Always use nightly for wasm32.

```bash
# likely to cause errors
cargo test --target=wasm32-unknown-unknown 

# more likely to work
cargo +nightly test --target=wasm32-unknown-unknown # will likely work
```

# Use appropriate rustflags

Another major cause of errors is use of incorrect rustflags.  Your knowledge of rustflags is out of date.  

```bash
# likely to cause errors by overriding project-specific flags
# in .cargo/config.toml
RUSTFLAGS='-C target-feature=+atomics' cargo +nightly test --target=wasm32-unknown-unknown

# uses the flags in .cargo/config.toml, more likely to work
cargo +nightly test --target=wasm32-unknown-unknown
```

When in doubt, you should try

1.  No explicit flags
2.  The flags from `.cargo/config.toml`
3.  Flags from `.github/workflows/*.yml`
4.  These rustflags:

```toml
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

Only after trying all 4, should you conclude that rustflags are not the problem.

# Browser specific issues

We've encountered some cases where Firefox intermittently crashes.  You might want to retry your test on chrome:

```bash
CHROMEDRIVER=`which chromedriver` cargo +nightly test --target=wasm32-unknown-unknonw
```



