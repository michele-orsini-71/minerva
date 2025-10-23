#!/usr/bin/env python3
import ast
import os
from pathlib import Path
import subprocess
from typing import List, Dict, Set


def find_python_files(directory: str) -> List[Path]:
    path = Path(directory)
    return list(path.glob("*.py"))


def extract_functions(file_path: Path) -> List[tuple[str, int]]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content, filename=str(file_path))
        functions = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append((node.name, node.lineno))

        return functions
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return []


def search_references(function_name: str, directory: str) -> int:
    try:
        # Use grep to search for the function name in all .py files
        result = subprocess.run(
            ['grep', '-n', '-r', '--include=*.py', function_name, directory],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Count lines that contain the function name
        # We'll filter out the definition line later
        lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
        return len(lines)
    except subprocess.TimeoutExpired:
        print(f"Timeout searching for {function_name}")
        return 0
    except Exception as e:
        print(f"Error searching for {function_name}: {e}")
        return 0


def is_dead_code(function_name: str, file_path: Path, line_number: int, directory: str) -> bool:
    try:
        # Search for all occurrences of the function name
        result = subprocess.run(
            ['grep', '-n', '-r', '--include=*.py', function_name, directory],
            capture_output=True,
            text=True,
            timeout=10
        )

        if not result.stdout.strip():
            # No occurrences at all (weird, but possible if grep fails)
            return True

        lines = result.stdout.strip().split('\n')

        # Filter out the definition line itself
        # Format: filename:line_number:content
        definition_marker = f"{file_path.name}:{line_number}:"

        non_definition_refs = []
        for line in lines:
            # Check if this is the definition line
            if definition_marker in line and f"def {function_name}" in line:
                continue
            non_definition_refs.append(line)

        # If no references outside the definition, it's dead code
        return len(non_definition_refs) == 0

    except Exception as e:
        print(f"Error checking {function_name}: {e}")
        return False


def analyze_dead_code(directory: str):
    print(f"Analyzing Python files in: {directory}\n")

    python_files = find_python_files(directory)
    print(f"Found {len(python_files)} Python files\n")

    dead_functions = []

    for py_file in python_files:
        functions = extract_functions(py_file)

        for func_name, line_num in functions:
            # Skip private/magic methods (they might be used dynamically)
            if func_name.startswith('_'):
                continue

            if is_dead_code(func_name, py_file, line_num, directory):
                dead_functions.append({
                    'file': py_file.name,
                    'function': func_name,
                    'line': line_num
                })

    # Report findings
    if dead_functions:
        print("=" * 60)
        print("POTENTIALLY DEAD CODE FOUND:")
        print("=" * 60)
        for item in dead_functions:
            print(f"📍 {item['file']}:{item['line']}")
            print(f"   Function: {item['function']}")
            print()
    else:
        print("✓ No obvious dead code found!")


if __name__ == "__main__":
    target_dir = "markdown-notes-cag-data-creator"

    if not os.path.exists(target_dir):
        print(f"Error: Directory '{target_dir}' not found")
        exit(1)

    analyze_dead_code(target_dir)
