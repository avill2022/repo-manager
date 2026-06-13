#!/usr/bin/env python3
"""
Repository Manager - Unified CLI tool for managing categorized GitHub repositories.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

load_dotenv()

DATA_FILE = "gitrepos.json"
REMOTE_GET_URL = os.getenv("REMOTE_GET_URL", "https://avillsoftware.com/repo-manager/get_repos.php")
REMOTE_SAVE_URL = os.getenv("REMOTE_SAVE_URL", "https://avillsoftware.com/repo-manager/save_repos.php")


def print_error(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)


def print_success(message: str) -> None:
    print(message)


def print_info(message: str) -> None:
    print(message)


def normalize_repo_entry(repo_entry: Any) -> Dict[str, str]:
    if isinstance(repo_entry, str):
        return {"name": repo_entry.strip(), "todo": ""}
    if isinstance(repo_entry, dict):
        name = str(repo_entry.get("name", "")).strip()
        if not name:
            raise ValueError("Each repository must have a non-empty 'name'.")
        return {"name": name, "todo": str(repo_entry.get("todo", "")).strip()}
    raise ValueError("Each repository must be a string or an object.")


def normalize_languages(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    if "languages" not in data:
        print_error("Invalid JSON format. 'languages' key is missing.")
        sys.exit(1)
    normalized = []
    for language in data["languages"]:
        if not isinstance(language, dict):
            print_error("Each language entry must be an object.")
            sys.exit(1)
        language_name = str(language.get("name", "")).strip()
        if not language_name:
            print_error("Each language must have a non-empty 'name'.")
            sys.exit(1)
        repos = language.get("repos", [])
        if not isinstance(repos, list):
            print_error(f"Language '{language_name}' has an invalid 'repos' value.")
            sys.exit(1)
        try:
            normalized_repos = [normalize_repo_entry(repo) for repo in repos]
        except ValueError as exc:
            print_error(f"Error in language '{language_name}': {exc}")
            sys.exit(1)
        normalized.append({"name": language_name, "repos": normalized_repos})
    return normalized


def load_repos() -> List[Dict[str, Any]]:
    if not os.path.exists(DATA_FILE):
        print_error(f"File '{DATA_FILE}' not found in the current folder.")
        print_info(f"Please create a '{DATA_FILE}' file with the correct JSON structure.")
        sys.exit(1)
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return normalize_languages(data)
    except json.JSONDecodeError as exc:
        print_error(f"Invalid JSON in '{DATA_FILE}': {exc}")
        sys.exit(1)
    except Exception as exc:
        print_error(f"Error reading '{DATA_FILE}': {exc}")
        sys.exit(1)


def save_repos(languages: List[Dict[str, Any]]) -> None:
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"languages": languages}, f, indent=4, ensure_ascii=False)
            f.write("\n")
    except Exception as exc:
        print_error(f"Error writing '{DATA_FILE}': {exc}")
        sys.exit(1)


def get_all_repos(languages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    all_repos = []
    global_id = 1
    for language in languages:
        for repo in language.get("repos", []):
            all_repos.append({
                "id": global_id,
                "name": repo.get("name", ""),
                "todo": repo.get("todo", ""),
                "language": language.get("name", "unknown"),
            })
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


def check_gh_installed() -> bool:
    return shutil.which("gh") is not None


def show_installation_instructions() -> None:
    print("\nGitHub CLI (gh) is not installed on your system.")
    print("\nPlease install it using the appropriate method for your operating system:\n")
    print("  macOS (Homebrew):   brew install gh")
    print("  Windows (Winget):   winget install --id GitHub.cli")
    print("  Windows (Scoop):    scoop install gh")
    print("  Linux (Ubuntu/Debian): sudo apt install gh")
    print("  Linux (Fedora):     sudo dnf install gh")
    print("\nAfter installation, authenticate with: gh auth login")
    print("For more details, visit: https://cli.github.com/")


def get_repos_from_gh() -> Optional[List[Dict[str, str]]]:
    try:
        print_info("Fetching repositories from GitHub...")
        result = subprocess.run(
            ["gh", "api", "user/repos", "--paginate", "--jq",
             "[.[] | {name: .name, description: .description}]"],
            capture_output=True, text=True, check=True
        )
        formatted_repos = json.loads(result.stdout)
        print_success(f"Found {len(formatted_repos)} repositories from GitHub")
        return formatted_repos
    except subprocess.CalledProcessError as e:
        print_error(f"GitHub CLI command failed: {e}")
        if e.stderr:
            print(f"Details: {e.stderr}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print_error(f"Failed to parse GitHub response: {e}")
        return None
    except FileNotFoundError:
        print_error("GitHub CLI command not found even after check")
        return None


def fetch_remote_json(url: str) -> Optional[Dict[str, Any]]:
    try:
        print_info(f"Fetching data from {url}...")
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        print_error(f"HTTP {response.status_code} from {url}")
        return None
    except requests.exceptions.ConnectionError:
        print_error(f"Cannot connect to {url} - No internet connection or server is down")
        return None
    except requests.exceptions.Timeout:
        print_error(f"Timeout while connecting to {url}")
        return None
    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON response from {url}: {e}")
        return None
    except Exception as e:
        print_error(f"Unexpected error fetching from {url}: {e}")
        return None


def post_remote_json(url: str, data: Dict[str, Any]) -> bool:
    try:
        print_info(f"Sending data to {url}...")
        response = requests.post(url, json=data, timeout=10)
        response.raise_for_status()
        print_success(f"Data sent successfully to {url}")
        return True
    except requests.exceptions.ConnectionError:
        print_error(f"Cannot connect to {url} - No internet connection or server is down")
        return False
    except requests.exceptions.Timeout:
        print_error(f"Timeout while connecting to {url}")
        return False
    except requests.exceptions.HTTPError as e:
        print_error(f"HTTP error {e.response.status_code} from {url}")
        return False
    except Exception as e:
        print_error(f"Unexpected error posting to {url}: {e}")
        return False


def merge_repos(github_repos: List[Dict[str, str]], remote_repos: Dict[str, Any]) -> Dict[str, Any]:
    if not remote_repos:
        print_info("No remote data to merge")
        return {
            "languages": [
                {"name": "new", "repos": [{"name": repo["name"], "todo": ""} for repo in github_repos]}
            ]
        }
    github_repo_names = {repo.get("name") for repo in github_repos if repo.get("name")}
    remote_repo_names = set()

    languages = remote_repos.get("languages", [])
    for lang_obj in languages:
        for repo in lang_obj.get("repos", []):
            repo_name = repo.get("name")
            if repo_name:
                remote_repo_names.add(repo_name)

    repos_to_add = github_repo_names - remote_repo_names
    repos_to_remove = remote_repo_names - github_repo_names

    print_info(f"Repos to add: {len(repos_to_add)} - {repos_to_add if repos_to_add else 'none'}")
    print_info(f"Repos to remove: {len(repos_to_remove)} - {repos_to_remove if repos_to_remove else 'none'}")

    new_languages = []
    for lang_obj in languages:
        lang_name = lang_obj.get("name")
        filtered_repos = []
        for repo in lang_obj.get("repos", []):
            repo_name = repo.get("name")
            if repo_name not in repos_to_remove:
                filtered_repos.append(repo)
        if filtered_repos:
            new_languages.append({"name": lang_name, "repos": filtered_repos})

    if repos_to_add:
        new_repos_list = [{"name": repo_name, "todo": ""} for repo_name in repos_to_add]
        new_languages.append({"name": "new", "repos": new_repos_list})
        for repo_name in repos_to_add:
            print_info(f"Added new repo: {repo_name}")

    for repo_name in repos_to_remove:
        print_info(f"Removed deleted repo: {repo_name}")

    merged = {"languages": new_languages}
    print_success(f"Merge complete: {len(repos_to_add)} added, {len(repos_to_remove)} removed")
    return merged


def save_local_json(data: Dict[str, Any], filename: str = DATA_FILE) -> bool:
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print_success(f"Saved merged data to {filename}")
        return True
    except Exception as e:
        print_error(f"Failed to save {filename}: {e}")
        return False


def update() -> None:
    print("\nStarting repository manager update...\n")
    if not check_gh_installed():
        show_installation_instructions()
        sys.exit(1)
    print_success("GitHub CLI is installed")
    github_repos = get_repos_from_gh()
    if github_repos is None:
        print_error("Failed to fetch repositories from GitHub")
        sys.exit(1)
    remote_repos = fetch_remote_json(REMOTE_GET_URL)
    if remote_repos is None:
        print_info("Continuing with local GitHub data only (no remote data to merge)")
        merged_repos = {
            "languages": [{"name": "new", "repos": [{"name": r["name"], "todo": ""} for r in github_repos]}]
        }
    else:
        merged_repos = merge_repos(github_repos, remote_repos)
    post_success = post_remote_json(REMOTE_SAVE_URL, merged_repos)
    if not post_success:
        print_info("Will still save local copy despite API failure")
    save_local_json(merged_repos, DATA_FILE)
    print("\nRepository manager update completed!\n")


def cmd_list(language_filter: Optional[str] = None) -> None:
    languages = load_repos()
    all_repos = get_all_repos(languages)
    if not all_repos:
        print("No repositories found.")
        return
    if language_filter:
        repos_to_show = [r for r in all_repos if r["language"].lower() == language_filter.lower()]
        if not repos_to_show:
            print(f"No repositories found for language: {language_filter}")
            return
        print(f"Filtered by language: {language_filter}\n")
    else:
        repos_to_show = all_repos
    repos_to_show.sort(key=lambda r: (0 if r["todo"] else 1, r["todo"].lower(), r["name"].lower()))
    for repo in repos_to_show:
        print(f"  {repo['id']:3d}. [{repo['language'].upper()}] {repo['name']}")
        print(f"       TODO: {repo['todo'] or '(empty)'}")
    print()


def cmd_add(language_name: str, repo_name: str, todo: str) -> None:
    repo_name = repo_name.strip()
    todo = todo.strip()
    language_name = language_name.strip()
    if not language_name or not repo_name:
        print_error("Language and repository name cannot be empty.")
        return
    languages = load_repos()
    _, existing_repo = find_repo_with_language(languages, repo_name)
    if existing_repo is not None:
        print_error(f"Repository '{repo_name}' already exists.")
        return
    language = find_language(languages, language_name)
    if language is None:
        language = {"name": language_name, "repos": []}
        languages.append(language)
    language["repos"].append({"name": repo_name, "todo": todo})
    save_repos(languages)
    print_success(f"Repository '{repo_name}' added to '{language['name']}'.")
    print_info(f"TODO: {todo or '(empty)'}")


def cmd_edit(
    repo_name: str,
    new_name: Optional[str],
    new_language: Optional[str],
    new_todo: Optional[str],
) -> None:
    languages = load_repos()
    current_language, repo = find_repo_with_language(languages, repo_name)
    if current_language is None or repo is None:
        print_error(f"Repository '{repo_name}' not found.")
        return
    target_name = new_name.strip() if new_name is not None else repo["name"]
    target_language_name = new_language.strip() if new_language is not None else current_language["name"]
    target_todo = new_todo.strip() if new_todo is not None else repo.get("todo", "")
    if not target_name or not target_language_name:
        print_error("Repository name and language cannot be empty.")
        return
    duplicated_language, duplicated_repo = find_repo_with_language(languages, target_name)
    if duplicated_repo is not None and duplicated_repo is not repo:
        print_error(f"Another repository already uses the name '{target_name}'.")
        return
    repo["name"] = target_name
    repo["todo"] = target_todo
    if current_language["name"].lower() != target_language_name.lower():
        current_language["repos"] = [r for r in current_language["repos"] if r is not repo]
        target_language = find_language(languages, target_language_name)
        if target_language is None:
            target_language = {"name": target_language_name, "repos": []}
            languages.append(target_language)
        target_language["repos"].append(repo)
    languages = [lang for lang in languages if lang.get("repos")]
    save_repos(languages)
    print_success(f"Repository '{repo_name}' updated.")
    print_info(f"Name: {repo['name']}")
    print_info(f"Language: {target_language_name}")
    print_info(f"TODO: {repo['todo'] or '(empty)'}")


def cmd_remove(repo_name: str) -> bool:
    languages = load_repos()
    current_language, repo = find_repo_with_language(languages, repo_name)
    if current_language is None or repo is None:
        print_error(f"Repository '{repo_name}' not found.")
        return False
    current_language["repos"] = [r for r in current_language["repos"] if r is not repo]
    languages = [lang for lang in languages if lang.get("repos")]
    save_repos(languages)
    print_success(f"Repository '{repo_name}' removed from '{DATA_FILE}'.")
    return True


def cmd_delete(repo_name: str) -> None:
    languages = load_repos()
    current_language, repo = find_repo_with_language(languages, repo_name)
    if current_language is None or repo is None:
        print_error(f"Repository '{repo_name}' not found.")
        return
    target_dir = os.path.join(os.getcwd(), current_language["name"].lower(), "projects", repo["name"])
    if os.path.exists(target_dir):
        try:
            shutil.rmtree(target_dir)
            print_success(f"Local folder deleted: ./{current_language['name'].lower()}/projects/{repo['name']}")
        except Exception as exc:
            print_error(f"Error deleting local folder: {exc}")
            return
    else:
        print_info(f"Local folder not found, only removing from '{DATA_FILE}'.")
    cmd_remove(repo_name)


def cmd_download(username: str, repo_name: str, protocol: str = "http") -> None:
    if protocol not in ["http", "ssh"]:
        print_error("Protocol must be 'http' or 'ssh'.")
        return
    languages = load_repos()
    _, found = find_repo_with_language(languages, repo_name)
    if found is None:
        print_error(f"Repository '{repo_name}' not found.")
        print_info("Use 'list' to see available repositories.")
        return
    clone_url = build_url(username, found["name"], protocol)
    all_repos = get_all_repos(languages)
    repo_info = next(r for r in all_repos if r["name"].lower() == repo_name.lower())
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
            print_success("Old folder removed.")
        except Exception as exc:
            print_error(f"Failed to remove existing folder: {exc}")
            return
    try:
        subprocess.run(
            ["git", "clone", clone_url, target_dir],
            check=True, capture_output=True, text=True,
        )
        print_success("Successfully cloned.")
        os.chdir(target_dir)
        print_info(f"Changed directory to: ./{language}/projects/{found['name']}")
        print_info(f"Current path: {os.getcwd()}")
    except FileNotFoundError:
        print_error("'git' command not found. Please install Git.")
    except subprocess.CalledProcessError as exc:
        print_error("Git clone failed.")
        if exc.stderr:
            print(exc.stderr.strip())
    except Exception as exc:
        print_error(f"Unexpected error: {exc}")


def cmd_help() -> None:
    print("GitHub Repository Manager Help\n")
    print("Usage:")
    print("  python main.py list [language]")
    print("  python main.py add <language> <repo_name> <todo>")
    print("  python main.py edit <repo_name> [--name NEW_NAME] [--language NEW_LANGUAGE] [--todo NEW_TODO]")
    print("  python main.py remove <repo_name>")
    print("  python main.py delete <repo_name>")
    print("  python main.py download <username> <repo_name> [http|ssh]")
    print("  python main.py update")
    print("  python main.py help\n")
    print("Commands:")
    print("  list         List repositories (optionally filtered by language)")
    print("  add          Add a repository to the local data file")
    print("  edit         Edit repository name, language, or TODO")
    print("  remove       Remove a repository from the local data file")
    print("  delete       Remove repository from data file and delete local folder")
    print("  download     Clone a repository to <language>/projects/<repo_name>")
    print("  update       Sync repositories from GitHub and remote API")
    print("  help         Show this help message\n")
    print("Repository fields:")
    print("  name   Repository name")
    print("  todo   Next steps or pending work\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="GitHub Repository Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )
    subparsers = parser.add_subparsers(dest="command", required=False)

    p_list = subparsers.add_parser("list", help="List all repositories or by language")
    p_list.add_argument("language", nargs="?", help="Optional: filter by language")

    p_dl = subparsers.add_parser("download", help="Download a repository")
    p_dl.add_argument("username", help="GitHub username")
    p_dl.add_argument("repo_name", help="Repository name")
    p_dl.add_argument("protocol", choices=["http", "ssh"], nargs="?", default="http",
                      help="Protocol: http or ssh")

    p_add = subparsers.add_parser("add", help="Add a repository")
    p_add.add_argument("language", help="Language or category")
    p_add.add_argument("repo_name", help="Repository name")
    p_add.add_argument("todo", help="Next steps for the repository")

    p_edit = subparsers.add_parser("edit", help="Edit an existing repository")
    p_edit.add_argument("repo_name", help="Current repository name")
    p_edit.add_argument("--name", dest="new_name", help="New repository name")
    p_edit.add_argument("--language", dest="new_language", help="New language or category")
    p_edit.add_argument("--todo", dest="new_todo", help="New TODO text")

    p_rm = subparsers.add_parser("remove", help="Remove a repository from data file")
    p_rm.add_argument("repo_name", help="Repository name")

    p_del = subparsers.add_parser("delete", help="Delete repo from data file and local disk")
    p_del.add_argument("repo_name", help="Repository name")

    subparsers.add_parser("update", help="Sync repositories from GitHub and remote API")
    subparsers.add_parser("help", help="Show detailed help and instructions")

    return parser


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
            print_error("Edit requires at least one of --name, --language, or --todo.")
            return
        cmd_edit(args.repo_name, args.new_name, args.new_language, args.new_todo)
    elif args.command == "remove":
        cmd_remove(args.repo_name)
    elif args.command == "delete":
        cmd_delete(args.repo_name)
    elif args.command == "update":
        try:
            update()
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
            sys.exit(1)
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            sys.exit(1)
    elif args.command == "help":
        cmd_help()
    else:
        cmd_help()


if __name__ == "__main__":
    main()
