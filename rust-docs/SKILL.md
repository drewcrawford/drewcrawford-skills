---
name: rust-docs
description: Build and search documentation for dependent Rust crates. Provides accurate API names, function 
 signatures, usage examples, and important information directly from crate documentation.  Use this before searching the web for information about an external crate, or searching on disk for its sourcecode.
allowed-tools: Bash, Glob, Grep, Read, WebFetch, TodoWrite, WebSearch, BashOutput, KillShell
---

# Dependent Crate Documentation Manual

This skill covers how to explore, build, and search documentation for dependent crates in a Rust project.

## 0. Finding a Dependent Crate by API Name

When you encounter an API and need to identify which crate provides it:

### Method 1: Search across all dependency source files
```bash
# Search for a specific API name (e.g., a function, struct, or trait)
grep -r "pub fn your_api_name" target/doc/src/
grep -r "pub struct YourTypeName" target/doc/src/
grep -r "pub trait YourTraitName" target/doc/src/
```

### Method 2: Use ripgrep for faster searching
```bash
# More efficient with ripgrep
rg "pub (fn|struct|trait|enum) YourApiName" target/doc/src/
```

### Method 3: Check Cargo.lock for crate names
```bash
# List all dependencies
cat Cargo.lock | grep "^name = " | sort -u

# Search for partial crate names
cat Cargo.lock | grep -i "partial_name"
```

## 1. Building Documentation for Dependent Crates

### Build docs for a specific crate
```bash
# For a regular dependency
cargo doc -p crate_name --no-deps

# For a path dependency (works the same way!)
cargo doc -p path_dependency_name --no-deps

# Build with dependencies included
cargo doc -p crate_name
```

### Build all documentation
```bash
# Build docs for all dependencies
cargo doc

# Build and open in browser
cargo doc --open

# Build only for specific features
cargo doc --features backend_wgpu
```

## 2. Searching Documentation Effectively

### HTML Documentation Search
Once documentation is built, it creates searchable HTML at `target/doc/`:

```bash
# Open the main documentation index
open target/doc/images_and_words/index.html

# Or for a specific crate
open target/doc/wgpu/index.html
```

### Source Code Search in Docs
Documentation includes source links. The source is stored at:
```bash
target/doc/src/crate_name/
```

Search examples:
```bash
# Find usage examples in documentation
rg "Example" target/doc/src/wgpu/
rg "```rust" target/doc/src/  # Find code examples

# Find specific patterns
rg "impl.*for.*Buffer" target/doc/src/wgpu/
rg "#\[derive" target/doc/src/logwise/  # Find derive macros
```

### Finding Related APIs
```bash
# Find all methods on a type
rg "impl.*YourType" target/doc/src/crate_name/

# Find all trait implementations
rg "impl.*TraitName.*for" target/doc/src/

# Find module structure
find target/doc/src/crate_name -name "*.html" | head -20
```

## 3. Identifying Repository URLs for Crates

### Method 1: Check Cargo.toml metadata
```bash
# Look in the built documentation
grep -r "repository" target/doc/src/*/Cargo.toml

# Check crate metadata
cargo metadata --format-version 1 | jq '.packages[] | select(.name=="crate_name") | .repository'
```

### Method 2: Check the HTML documentation
The generated docs often include repository links:
```bash
# Search for github/gitlab links in docs
grep -r "github.com" target/doc/crate_name/*.html
grep -r "Repository" target/doc/crate_name/*.html
```

### Method 3: Check Cargo.lock for git dependencies
```bash
# For git dependencies
grep -A 2 'name = "crate_name"' Cargo.lock
```

### Method 4: Use cargo tree with verbose output
```bash
cargo tree -p crate_name -v
```

## 4. Searching Source Code in Documentation Directory

### Understanding the documentation structure
```
target/doc/
├── src/                 # Source code for all crates
│   ├── wgpu/           # Source for wgpu crate
│   ├── logwise/        # Source for logwise crate
│   └── .../
├── wgpu/               # Generated HTML docs
├── logwise/            # Generated HTML docs
└── .../
```

### Effective source code searching

#### Find specific implementations
```bash
# Find where a function is defined
rg "fn function_name\(" target/doc/src/

# Find struct definitions with their fields
rg -A 10 "pub struct StructName" target/doc/src/

# Find trait definitions
rg -A 5 "pub trait TraitName" target/doc/src/
```

#### Find usage patterns
```bash
# Find how a type is used
rg "StructName::" target/doc/src/

# Find examples in tests
rg "#\[test\]" target/doc/src/crate_name/ -A 20

# Find macro usage
rg "macro_name!" target/doc/src/
```

#### Advanced searches
```bash
# Find all public APIs in a crate
rg "^pub " target/doc/src/crate_name/lib.rs

# Find unsafe code
rg "unsafe" target/doc/src/crate_name/

# Find specific attributes
rg "#\[cfg\(feature" target/doc/src/crate_name/

# Find TODO/FIXME comments
rg "(TODO|FIXME|HACK|NOTE):" target/doc/src/
```

## 5. Practical Workflow Example

Here's a complete workflow for exploring a crate:

```bash
# Step 1: Build the documentation
cargo doc -p wgpu

# Step 2: Find the main module file
ls target/doc/src/wgpu/

# Step 3: Search for specific APIs
rg "pub fn render" target/doc/src/wgpu/

# Step 4: Open documentation in browser
open target/doc/wgpu/index.html

# Step 5: Examine source structure
tree -L 2 target/doc/src/wgpu/

# Step 6: Find examples
rg "Example|example" target/doc/src/wgpu/ -A 5
```

## 6. Tips and Tricks

### Quick crate inspection
```bash
# See all public items in a crate's lib.rs
cat target/doc/src/crate_name/lib.rs | grep "^pub"

# Find the crate version
grep "^version = " target/doc/src/crate_name/Cargo.toml

# List all modules
find target/doc/src/crate_name -name "mod.rs" -o -name "lib.rs"
```

### Building docs faster
```bash
# Skip dependencies you don't need
cargo doc -p your_target_crate --no-deps

# Build specific workspace members only
cargo doc --workspace --no-deps
```

## Common Issues and Solutions

### Documentation not building
```bash
# Clean and rebuild
cargo clean
cargo doc

# Check for compilation errors first
cargo check
```

### Missing source in target/doc/src
```bash
# Ensure you're building with dependencies
cargo doc  # not cargo doc --no-deps
```

### Path dependencies not found
```bash
# Ensure path dependencies are specified correctly in Cargo.toml
# Then use the exact crate name (not path)
cargo doc -p exact_crate_name
```

---

This skill should help you effectively explore and understand the documentation of all dependent crates in your Rust project.