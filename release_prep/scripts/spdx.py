#!/usr/bin/env python3

import os
import sys

def find_spdx_line(lib_rs_path):
    with open(lib_rs_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip().startswith('// SPDX-License-Identifier:'):
                return line.rstrip('\n')
    return None

def main():
    root = os.getcwd()
    lib_rs_path = os.path.join(root, "lib.rs")
    src_lib_rs_path = os.path.join(root, "src", "lib.rs")
    src_main_rs_path = os.path.join(root, "src", "main.rs")
    
    # Check for lib.rs in root first, then src/lib.rs, then src/main.rs
    if os.path.exists(lib_rs_path):
        spdx_source = lib_rs_path
    elif os.path.exists(src_lib_rs_path):
        spdx_source = src_lib_rs_path
    elif os.path.exists(src_main_rs_path):
        spdx_source = src_main_rs_path
    else:
        print("Error: No lib.rs or main.rs found in root directory or src/ directory.")
        sys.exit(1)
    spdx_line = find_spdx_line(spdx_source)
    if not spdx_line:
        print(f"Error: No SPDX-License-Identifier found in {spdx_source}.")
        sys.exit(1)

    for dirpath, dirnames, filenames in os.walk(root):
        # Skip target directories
        if 'target' in dirnames:
            dirnames.remove('target')
        for filename in filenames:
            if filename.endswith('.rs'):
                file_path = os.path.join(dirpath, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                # Find the first non-empty, non-shebang line
                for idx, line in enumerate(lines):
                    line_strip = line.strip()
                    if line_strip == '' or line_strip.startswith('#!'):
                        continue
                    if line_strip.startswith('// SPDX-License-Identifier:'):
                        break
                    # If not present, insert SPDX line above this
                    print(f"Adding SPDX license to {file_path}")
                    lines.insert(idx, spdx_line + '\n')
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                    break

if __name__ == "__main__":
    main()

