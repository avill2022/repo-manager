#!/usr/bin/env python3
"""Wrapper script - delegates to main.py for repository management functionality."""
import sys
from main import cmd_help, cmd_list, cmd_add, cmd_edit, cmd_remove, cmd_delete, cmd_download, build_parser

def main() -> None:
    parser = build_parser()
    if len(sys.argv) == 1:
        cmd_help()
        return
    args = parser.parse_args()
    if args.command == "list":
        cmd_list(args.language)
    elif args.command == "download":
        cmd_download(args.username, args.repo_name, args.protocol)
    elif args.command == "add":
        cmd_add(args.language, args.repo_name, args.todo)
    elif args.command == "edit":
        if args.new_name is None and args.new_language is None and args.new_todo is None:
            print("Error: edit requires at least one of --name, --language, or --todo.")
            return
        cmd_edit(args.repo_name, args.new_name, args.new_language, args.new_todo)
    elif args.command == "remove":
        cmd_remove(args.repo_name)
    elif args.command == "delete":
        cmd_delete(args.repo_name)
    elif args.command == "help":
        cmd_help()
    else:
        cmd_help()

if __name__ == "__main__":
    main()
