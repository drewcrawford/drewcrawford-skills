---
name: wasm32-browser
description: Configure browser for wasm-bindgen-test-runner. Use when wasm32 tests need to run in a specific browser (Chrome, Safari) instead of the default Firefox, or when Firefox doesn't support required features like WebGPU.
---

Ultimately what you need to do is set the right environment variable.

```bash
CHROMEDRIVER=`which chromedriver`
GECKODRIVER=`which geckodriver`
SAFARIDRIVER=`which safaridriver`
```

The main way to do this would be edit the scripts/wasm32/tests script to include this setting and document why it is needed (i.e. the specific error)

Our CI supports firefox and chrome, whereas macOS local environments also support Safari.