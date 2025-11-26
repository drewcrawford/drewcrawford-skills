---
name: wasm_thread_errors
description: An index of common wasm_thread errors and their solutions.  Use this BEFORE taking any other steps to ID a wasm_thread error.
---

Use the appropriate guide based on your situation:

# ReferenceError: self is not defined

(specifically in is_web_worker_thread or 
  during Builder::spawn). This typically manifests when native tests pass but WASM tests fail, and the stack trace shows js_sys::eval being called.
  
Read the use_browser.md file.

#  DataCloneError: WebAssembly.Memory object could not be cloned

Read the target_atomics.md file.
