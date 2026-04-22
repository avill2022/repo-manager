import argparse
import json
import os
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

# ================================================
# gitrepos JSON file (in the same folder)
# Simple structure:
# {
#   "languages": [
#     {
#       "name": "kotlin",
#       "repos": [
#         {"name": "MyKotlinApp", "todo": "Refactor the login flow"},
#         {"name": "CleanArchitectureSample", "todo": "Write unit tests"}
#       ]
#     },
#     {
#       "name": "python",
#       "repos": [
#         {"name": "WebScraper", "todo": "Add retries"},
#         {"name": "DataAnalyzer", "todo": "Improve charts"}
#       ]
#     }
#   ]
# }
# ================================================

DATA_FILE = "gitrepos.json"


def normalize_repo_entry(repo_entry: Any) -> Dict[str, str]:
    if isinstance(repo_entry, str):
        return {"name": repo_entry.strip(), "todo": ""}

    if isinstance(repo_entry, dict):
        name = str(repo_entry.get("name", "")).strip()
        if not name:
            raise ValueError("Each repository must have a non-empty 'name'.")

        return {
            "name": name,
            "todo": str(repo_entry.get("todo", "")).strip(),
        }

    raise ValueError("Each repository must be a string or an object.")


def normalize_languages(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    if "languages" not in data:
        print("Error: Invalid JSON format. 'languages' key is missing.")
        sys.exit(1)

    normalized_languages = []

    for language in data["languages"]:
        if not isinstance(language, dict):
            print("Error: Each language entry must be an object.")
            sys.exit(1)

        language_name = str(language.get("name", "")).strip()
        if not language_name:
            print("Error: Each language must have a non-empty 'name'.")
            sys.exit(1)

        repos = language.get("repos", [])
        if not isinstance(repos, list):
            print(f"Error: Language '{language_name}' has an invalid 'repos' value.")
            sys.exit(1)

        try:
            normalized_repos = [normalize_repo_entry(repo) for repo in repos]
        except ValueError as exc:
            print(f"Error in language '{language_name}': {exc}")
            sys.exit(1)

        normalized_languages.append({"name": language_name, "repos": normalized_repos})

    return normalized_languages


def load_repos() -> List[Dict[str, Any]]:
    if not os.path.exists(DATA_FILE):
        print("Error: File 'gitrepos' not found in the current folder.")
        print("Please create a 'gitrepos' file with the correct JSON structure.")
        sys.exit(1)

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file_handle:
            data = json.load(file_handle)
        return normalize_languages(data)
    except json.JSONDecodeError as exc:
        print(f"Error: Invalid JSON in 'gitrepos' file: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"Error reading 'gitrepos' file: {exc}")
        sys.exit(1)


def save_repos(languages: List[Dict[str, Any]]) -> None:
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as file_handle:
            json.dump({"languages": languages}, file_handle, indent=4, ensure_ascii=False)
            file_handle.write("\n")
    except Exception as exc:
        print(f"Error writing 'gitrepos' file: {exc}")
        sys.exit(1)


def get_all_repos(languages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    all_repos = []
    global_id = 1

    for language in languages:
        for repo in language.get("repos", []):
            all_repos.append(
                {
                    "id": global_id,
                    "name": repo.get("name", ""),
                    "todo": repo.get("todo", ""),
                    "language": language.get("name", "unknown"),
                }
            )
            global_id += 1

    return all_repos


def find_language(languages: List[Dict[str, Any]], language_name: str) -> Optional[Dict[str, Any]]:
    for language in languages:
        if language.get("name", "").lower() == language_name.lower():
            return language
    return None


def find_repo_with_language(
    languages: List[Dict[str, Any]], repo_name: str
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    for language in languages:
        for repo in language.get("repos", []):
            if repo.get("name", "").lower() == repo_name.lower():
                return language, repo
    return None, None


def build_url(username: str, repo_name: str, protocol: str) -> str:
    if protocol == "ssh":
        return f"git@github.com:{username}/{repo_name}.git"
    return f"https://github.com/{username}/{repo_name}.git"


def show_help() -> None:
    print("GitHub Repository Manager Help\n")
    print("Usage:")
    print("  python repo-manager.py list")
    print("  python repo-manager.py list <language>")
    print("  python repo-manager.py download <username> <repo_name> [http|ssh]")
    print("  python repo-manager.py add <language> <repo_name> <todo>")
    print("  python repo-manager.py edit <repo_name> [--name NEW_NAME] [--language NEW_LANGUAGE] [--todo NEW_TODO]")
    print("  python repo-manager.py remove <repo_name>")
    print("  python repo-manager.py delete <repo_name>\n")
    print("Examples:")
    print('  python repo-manager.py add python MyTool "Create the CLI version"')
    print('  python repo-manager.py edit MyTool --todo "Publish first release"')
    print("  python repo-manager.py remove MyTool")
    print("  python repo-manager.py delete MyTool\n")
    print("Repository fields:")
    print("  name   Repository name")
    print("  todo   Next steps or pending work\n")
    print("Note: Repositories are cloned into: <language>/projects/<repo_name>")


def list_repositories(language_filter: Optional[str] = None) -> None:
    languages = load_repos()
    all_repos = get_all_repos(languages)

    if not all_repos:
        print("No repositories found.")
        return

    print("GitHub Repositories:\n")

    if language_filter:
        repos_to_show = [repo for repo in all_repos if repo["language"].lower() == language_filter.lower()]
        if not repos_to_show:
            print(f"No repositories found for language: {language_filter}")
            return
        print(f"Filtered by language: {language_filter}\n")
    else:
        repos_to_show = all_repos

    for repo in repos_to_show:
        print(f"  {repo['id']:3d}. [{repo['language'].upper()}] {repo['name']}")
        print(f"       TODO: {repo['todo'] or '(empty)'}")

    print()


def add_repository(language_name: str, repo_name: str, todo: str) -> None:
    repo_name = repo_name.strip()
    todo = todo.strip()
    language_name = language_name.strip()

    if not language_name or not repo_name:
        print("Error: language and repository name cannot be empty.")
        return

    languages = load_repos()
    _, existing_repo = find_repo_with_language(languages, repo_name)
    if existing_repo is not None:
        print(f"Error: Repository '{repo_name}' already exists.")
        return

    language = find_language(languages, language_name)
    if language is None:
        language = {"name": language_name, "repos": []}
        languages.append(language)

    language["repos"].append({"name": repo_name, "todo": todo})
    save_repos(languages)

    print(f"Repository '{repo_name}' added to '{language['name']}'.")
    print(f"TODO: {todo or '(empty)'}")


def edit_repository(
    repo_name: str,
    new_name: Optional[str],
    new_language: Optional[str],
    new_todo: Optional[str],
) -> None:
    languages = load_repos()
    current_language, repo = find_repo_with_language(languages, repo_name)

    if current_language is None or repo is None:
        print(f"Error: Repository '{repo_name}' not found.")
        return

    target_name = new_name.strip() if new_name is not None else repo["name"]
    target_language_name = new_language.strip() if new_language is not None else current_language["name"]
    target_todo = new_todo.strip() if new_todo is not None else repo.get("todo", "")

    if not target_name or not target_language_name:
        print("Error: repository name and language cannot be empty.")
        return

    duplicated_language, duplicated_repo = find_repo_with_language(languages, target_name)
    if duplicated_repo is not None and duplicated_repo is not repo:
        print(f"Error: Another repository already uses the name '{target_name}'.")
        return

    repo["name"] = target_name
    repo["todo"] = target_todo

    if current_language["name"].lower() != target_language_name.lower():
        current_language["repos"] = [
            existing_repo for existing_repo in current_language["repos"] if existing_repo is not repo
        ]

        target_language = find_language(languages, target_language_name)
        if target_language is None:
            target_language = {"name": target_language_name, "repos": []}
            languages.append(target_language)

        target_language["repos"].append(repo)

    languages = [language for language in languages if language.get("repos")]
    save_repos(languages)

    print(f"Repository '{repo_name}' updated.")
    print(f"Name: {repo['name']}")
    print(f"Language: {target_language_name}")
    print(f"TODO: {repo['todo'] or '(empty)'}")


def remove_repository(repo_name: str) -> bool:
    languages = load_repos()
    current_language, repo = find_repo_with_language(languages, repo_name)

    if current_language is None or repo is None:
        print(f"Error: Repository '{repo_name}' not found.")
        return False

    current_language["repos"] = [existing_repo for existing_repo in current_language["repos"] if existing_repo is not repo]
    languages = [language for language in languages if language.get("repos")]
    save_repos(languages)

    print(f"Repository '{repo_name}' removed from 'gitrepos'.")
    return True


def delete_repository(repo_name: str) -> None:
    languages = load_repos()
    current_language, repo = find_repo_with_language(languages, repo_name)

    if current_language is None or repo is None:
        print(f"Error: Repository '{repo_name}' not found.")
        return

    target_dir = os.path.join(os.getcwd(), current_language["name"].lower(), "projects", repo["name"])
    if os.path.exists(target_dir):
        try:
            shutil.rmtree(target_dir)
            print(f"Local folder deleted: ./{current_language['name'].lower()}/projects/{repo['name']}")
        except Exception as exc:
            print(f"Error deleting local folder: {exc}")
            return
    else:
        print("Local folder not found, only removing from 'gitrepos'.")

    remove_repository(repo_name)


def download_repository(username: str, repo_name: str, protocol: str = "http") -> None:
    if protocol not in ["http", "ssh"]:
        print("Error: Protocol must be 'http' or 'ssh'.")
        return

    languages = load_repos()
    _, found = find_repo_with_language(languages, repo_name)

    if found is None:
        print(f"Error: Repository '{repo_name}' not found.")
        print("Use 'list' to see available repositories.")
        return

    clone_url = build_url(username, found["name"], protocol)
    all_repos = get_all_repos(languages)
    repo_info = next(repo for repo in all_repos if repo["name"].lower() == repo_name.lower())
    language = repo_info["language"].lower()

    language_dir = os.path.join(os.getcwd(), language)
    projects_dir = os.path.join(language_dir, "projects")
    target_dir = os.path.join(projects_dir, found["name"])

    os.makedirs(projects_dir, exist_ok=True)

    print(f"Cloning '{found['name']}' ({language})...")
    print(f"Username : {username}")
    print(f"Protocol : {'SSH' if protocol == 'ssh' else 'HTTPS'}")
    print(f"Target   : ./{language}/projects/{found['name']}")
    print(f"URL      : {clone_url}")
    print(f"TODO     : {found.get('todo', '') or '(empty)'}\n")

    if os.path.exists(target_dir):
        print(f"Removing existing folder: {found['name']}...")
        try:
            shutil.rmtree(target_dir)
            print("Old folder removed.")
        except Exception as exc:
            print(f"Error: Failed to remove existing folder: {exc}")
            return

    try:
        subprocess.run(
            ["git", "clone", clone_url, target_dir],
            check=True,
            capture_output=True,
            text=True,
        )
        print("Successfully cloned.")
        os.chdir(target_dir)
        print(f"Changed directory to: ./{language}/projects/{found['name']}")
        print(f"Current path: {os.getcwd()}")
    except FileNotFoundError:
        print("Error: 'git' command not found. Please install Git.")
    except subprocess.CalledProcessError as exc:
        print("Error: Git clone failed.")
        if exc.stderr:
            print(exc.stderr.strip())
    except Exception as exc:
        print(f"Error: Unexpected error: {exc}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="GitHub Repository Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )

    subparsers = parser.add_subparsers(dest="command", required=False)

    list_parser = subparsers.add_parser("list", help="List all repositories or by language")
    list_parser.add_argument("language", nargs="?", help="Optional: filter by language")

    download_parser = subparsers.add_parser("download", help="Download a repository")
    download_parser.add_argument("username", help="GitHub username")
    download_parser.add_argument("repo_name", help="Repository name")
    download_parser.add_argument(
        "protocol",
        choices=["http", "ssh"],
        nargs="?",
        default="http",
        help="Protocol: http or ssh",
    )

    add_parser = subparsers.add_parser("add", help="Add a repository to gitrepos")
    add_parser.add_argument("language", help="Language or category")
    add_parser.add_argument("repo_name", help="Repository name")
    add_parser.add_argument("todo", help="Next steps for the repository")

    edit_parser = subparsers.add_parser("edit", help="Edit an existing repository")
    edit_parser.add_argument("repo_name", help="Current repository name")
    edit_parser.add_argument("--name", dest="new_name", help="New repository name")
    edit_parser.add_argument("--language", dest="new_language", help="New language or category")
    edit_parser.add_argument("--todo", dest="new_todo", help="New TODO text")

    remove_parser = subparsers.add_parser("remove", help="Remove a repository from gitrepos")
    remove_parser.add_argument("repo_name", help="Repository name")

    delete_parser = subparsers.add_parser("delete", help="Delete a repository from gitrepos and local disk")
    delete_parser.add_argument("repo_name", help="Repository name")

    subparsers.add_parser("help", help="Show detailed help and instructions")

    return parser


def main() -> None:
    parser = build_parser()

    if len(sys.argv) == 1:
        show_help()
        return

    args = parser.parse_args()

    if args.command == "list":
        list_repositories(args.language)
    elif args.command == "download":
        download_repository(args.username, args.repo_name, args.protocol)
    elif args.command == "add":
        add_repository(args.language, args.repo_name, args.todo)
    elif args.command == "edit":
        if args.new_name is None and args.new_language is None and args.new_todo is None:
            print("Error: edit requires at least one of --name, --language, or --todo.")
            return
        edit_repository(args.repo_name, args.new_name, args.new_language, args.new_todo)
    elif args.command == "remove":
        remove_repository(args.repo_name)
    elif args.command == "delete":
        delete_repository(args.repo_name)
    elif args.command == "help":
        show_help()
    else:
        show_help()


if __name__ == "__main__":
    main()
