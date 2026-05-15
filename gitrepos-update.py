#!/usr/bin/env python3
"""Wrapper script - delegates to main.py for repository update functionality."""
import sys
from main import update, print_error

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] != "update":
        print("Usage: python gitrepos-update.py update")
        print("\nThis command will:")
        print("  1. Check if GitHub CLI (gh) is installed")
        print("  2. Fetch all your repositories from GitHub")
        print("  3. Merge with remote todo data")
        print("  4. Save the result to gitrepos.json")
        sys.exit(1)
    try:
        update()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)
