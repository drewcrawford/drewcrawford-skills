The fix is to ensure in .cargo/config.toml

```toml
# these flags must be present


[target.'cfg(target_arch="wasm32")']

rustflags = [
# these flags must be present
"-C", "target-feature=+atomics",
# see https://github.com/wasm-bindgen/wasm-bindgen/issues/4727
# and https://github.com/rust-lang/rust/pull/147225
"-Clink-arg=--shared-memory",
# 4GB
"-Clink-arg=--max-memory=4294967296",
"-Clink-arg=--import-memory",
"-Clink-arg=--export=__wasm_init_tls",
"-Clink-arg=--export=__tls_size",
"-Clink-arg=--export=__tls_align",
"-Clink-arg=--export=__tls_base"
]
```

