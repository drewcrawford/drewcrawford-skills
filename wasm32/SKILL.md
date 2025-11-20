---
name: wasm32-workflows
description: Troubleshoot and debug issues specific to wasm32-unknown-unknown target, WebAssembly platform workflows, browser-based WASM testing, and WASM-specific problems. Use when working with wasm32 targets, encountering WASM platform issues, debugging WebAssembly tests, or when logs/output seem incomplete in browser environments.
---

# WASM32 Platform Workflows

## Important Context

This skill contains highly specific domain knowledge for the wasm32 platform. The WebAssembly target has unique characteristics and limitations that require specialized approaches different from native targets.

## Critical Information About Logging

**WARNING**: Logs collected on the wasm32-unknown-unknown target are frequently inaccurate or incomplete, especially when running tests in browser environments.

### Key Issues with WASM Logging

1. **Incomplete Log Output**: Standard logging mechanisms may not capture all output when running on wasm32 targets
2. **Browser Console Limitations**: Browser-based test runners may suppress or buffer output in ways that make debugging difficult
3. **Asynchronous Execution**: WASM's execution model can cause logs to appear out of order or be lost entirely

## Instructions

When working with wasm32 workflow issues:

1. **Assume logs are incomplete**: Any logs you collect from wasm32 targets should be considered potentially incomplete or misleading
2. **Ask for manual log collection**: Always ask the user how they prefer to collect correct logs, as they may have specific manual methods for accurate log collection on their WASM setup
3. **Consider platform-specific issues**: Be aware that standard debugging approaches may not work as expected on WASM targets

## Typical Questions to Ask

When encountering WASM-related issues, ask the user:
- "How would you prefer to collect accurate logs from your wasm32 target?"
- "Do you have a specific manual process for debugging WASM tests in your browser environment?"
- "Are there any platform-specific logging tools or techniques you use for WebAssembly debugging?"

## Note

We are currently preparing comprehensive documentation on accurate log collection methods for wasm32 targets. Until that documentation is available, rely on user guidance for their specific WASM debugging workflow.