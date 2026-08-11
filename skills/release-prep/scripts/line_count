#!/usr/bin/env python3

import os
import sys
from pathlib import Path

def count_lines_in_file(file_path):
	"""Count non-empty lines in a file."""
	try:
		with open(file_path, 'r', encoding='utf-8') as f:
			lines = [line.strip() for line in f.readlines()]
			return len([line for line in lines if line])
	except (UnicodeDecodeError, PermissionError):
		return 0

def analyze_rust_files(search_dir=".", warn_threshold=900, severe_threshold=1500):
	"""Analyze Rust files and report line counts with warnings."""
	search_path = Path(search_dir)
	
	if not search_path.exists():
		print(f"Error: Directory '{search_dir}' does not exist")
		return
	
	rust_files = [f for f in search_path.rglob("*.rs") 
				   if 'target' not in f.parts]
	
	if not rust_files:
		print(f"No .rs files found in '{search_dir}' (excluding target/)")
		return
	
	total_lines = 0
	warnings = []
	severe_warnings = []
	
	print(f"Analyzing {len(rust_files)} Rust files in '{search_dir}' (excluding target/)...\n")
	
	for file_path in sorted(rust_files):
		line_count = count_lines_in_file(file_path)
		total_lines += line_count
		
		relative_path = file_path.relative_to(search_path)
		
		if line_count >= severe_threshold:
			severe_warnings.append((relative_path, line_count))
			print(f"🚨 SEVERE: {relative_path} - {line_count} lines")
		elif line_count >= warn_threshold:
			warnings.append((relative_path, line_count))
			print(f"⚠️  WARNING: {relative_path} - {line_count} lines")
	
	print(f"\n📊 Summary:")
	print(f"Total files: {len(rust_files)}")
	print(f"Total lines: {total_lines}")
	print(f"Warnings ({warn_threshold}+ lines): {len(warnings)}")
	print(f"Severe warnings ({severe_threshold}+ lines): {len(severe_warnings)}")
	
	if severe_warnings:
		print(f"\n🚨 Files requiring immediate attention:")
		for file_path, line_count in severe_warnings:
			print(f"  {file_path}: {line_count} lines")
	
	if warnings:
		print(f"\n⚠️  Files to consider refactoring:")
		for file_path, line_count in warnings:
			print(f"  {file_path}: {line_count} lines")

if __name__ == "__main__":
	search_directory = sys.argv[1] if len(sys.argv) > 1 else "."
	analyze_rust_files(search_directory)