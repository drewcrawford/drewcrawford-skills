---
name: wasm-bindgen-errors
description: An index of common wasm-bindgen errors and their solutions.  Use this BEFORE taking any other steps to ID a wasm-bindgen error.
---

# wasm-bindgen-test-runner

The error

```
thread 'main' (18595352) panicked at /Users/drew/Code/wasm-bindgen/crates/cli-support/src/decode.rs:92:18:
internal error: entered unreachable code
```

Is caused by running a test 

```bash
CARGO_TARGET_WASM32_UNKNOWN_UNKNOWN_RUNNER="wasm-test-runner" cargo...
```

(or its cargo.toml equivalent).  This may be expected in cases where examples and binaries are prominent usecases.

The solution is to override this inline with


CARGO_TARGET_WASM32_UNKNOWN_UNKNOWN_RUNNER="wasm-bindgen-test-runner" cargo...

#  SyntaxError: redeclaration of function wasm_bindgen_91101fae6e318954___convert__closures_____invoke______

This is caused by your .cargo/config.toml rustflags not containing:

```toml
rustflags = [
	# ...
	
	# Workaround for wasm-bindgen duplicate function declarations with v0 mangling
	# see https://github.com/rustwasm/wasm-bindgen/issues/4820
	"-Csymbol-mangling-version=legacy",
	"-Zunstable-options",
]
```
