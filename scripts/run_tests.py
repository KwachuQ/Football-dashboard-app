#!/usr/bin/env python
"""
Test runner script with better output formatting.
Run with: python scripts/run_tests.py
"""
import sys
import subprocess


def main():
    """Run pytest with custom configuration."""
    cmd = [
        "pytest",
        "-v",
        "--tb=short",
        "--color=yes",
        "-m", "not slow",  # Skip slow tests by default
        "tests/",
    ]
    
    print("Running Football Dashboard Tests...")
    print(f"Command: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()