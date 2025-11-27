The fix is to add

```rust
#[cfg(target_arch = "wasm32")]
wasm_bindgen_test::wasm_bindgen_test_configure!(run_in_browser);
```

to a test module.  (I think we only need one statement per crate - try adding this only once at first.)

After this fix:

* you may see a new error.  That's expected, it means we fixed this one and we can move on to looking into that one.
* if you see the same error, the fix is not being correctly applied