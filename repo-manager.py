import sys
import json
import subprocess
import argparse
import os
import shutil
from typing import List, Dict, Any

# ================================================
# gitrepos JSON file (in the same folder)
# Simple structure:
# {
#   "languages": [
#     {
#       "name": "kotlin",
#       "repos": ["MyKotlinApp", "CleanArchitectureSample"]
#     },
#     {
#       "name": "python",
#       "repos": ["WebScraper", "DataAnalyzer"]
#     }
#   ]
# }
# ================================================

def load_repos() -> List[Dict[str, Any]]:
    file_path = "gitrepos"
    
    if not os.path.exists(file_path):
        print("❌ Error: File 'gitrepos' not found in the current folder.")
        print("   Please create a 'gitrepos' file with the correct JSON structure.")
        sys.exit(1)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if "languages" not in data:
            print("❌ Error: Invalid JSON format. 'languages' key is missing.")
            sys.exit(1)
            
        return data["languages"]
    
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in 'gitrepos' file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading 'gitrepos' file: {e}")
        sys.exit(1)


def get_all_repos(languages: List[Dict]) -> List[Dict]:
    all_repos = []
    global_id = 1
    
    for lang in languages:
        for repo_name in lang.get("repos", []):
            all_repos.append({
                "id": global_id,
                "name": repo_name,
                "language": lang.get("name", "unknown").lower()
            })
            global_id += 1
    
    return all_repos


def build_url(username: str, repo_name: str, protocol: str) -> str:
    if protocol == "ssh":
        return f"git@github.com:{username}/{repo_name}.git"
    else:
        return f"https://github.com/{username}/{repo_name}.git"


def show_help():
    print("🚀 GitHub Repository Manager Help\n")
    print("Usage:")
    print("  python repo-manager.py list                    # List all repositories")
    print("  python repo-manager.py list <language>         # List by language")
    print("  python repo-manager.py download <username> <repo_name>")
    print("  python repo-manager.py download <username> <repo_name> ssh\n")
    
    print("Examples:")
    print("  python repo-manager.py list")
    print("  python repo-manager.py list kotlin")
    print("  python repo-manager.py download octocat Hello-World")
    print("  python repo-manager.py download octocat Hello-World ssh\n")
    
    print("SSH Setup Instructions:")
    print("  1. ssh-keygen -t ed25519 -C 'your_email@example.com'")
    print("  2. cat ~/.ssh/id_ed25519.pub")
    print("  3. Add key to GitHub → Settings → SSH and GPG keys")
    print("  4. Test: ssh -T git@github.com\n")
    
    print("Useful Git Commands:")
    print("  git remote -v                    # Check remotes")
    print("  git remote set-url origin <url>  # Change remote")
    print("  git push -u origin main          # First push")
    print("  git pull                         # Update\n")
    
    print("Note: Repositories are cloned into: <language>/<repo_name>")


def list_repositories(language_filter: str = None):
    languages = load_repos()
    all_repos = get_all_repos(languages)
    
    if not all_repos:
        print("No repositories found.")
        return
    
    print("📋 GitHub Repositories:\n")
    
    if language_filter:
        filtered = [r for r in all_repos if r["language"] == language_filter.lower()]
        if not filtered:
            print(f"No repositories found for language: {language_filter}")
            return
        repos_to_show = filtered
        print(f"Filtered by language: {language_filter.capitalize()}\n")
    else:
        repos_to_show = all_repos
    
    for repo in repos_to_show:
        print(f"   {repo['id']:3d}. [{repo['language'].upper()}] {repo['name']}")
    
    print()
    print("Download examples:")
    print("   python repo-manager.py download <username> <repo_name>")
    print("   python repo-manager.py download <username> <repo_name> ssh")

def download_repository(username: str, repo_name: str, protocol: str = "http"):
    if protocol not in ["http", "ssh"]:
        print("❌ Error: Protocol must be 'http' or 'ssh'")
        return

    languages = load_repos()
    all_repos = get_all_repos(languages)

    # Find repository
    found = next(
        (repo for repo in all_repos if repo["name"].lower() == repo_name.lower()),
        None
    )

    if not found:
        print(f"❌ Error: Repository '{repo_name}' not found.")
        print("   Use 'list' to see available repositories.")
        return

    clone_url = build_url(username, found["name"], protocol)
    language = found["language"]

    # Define paths
    language_dir = os.path.join(os.getcwd(), language)
    projects_dir = os.path.join(language_dir, "projects")
    target_dir = os.path.join(projects_dir, found["name"])

    # Create base directories
    os.makedirs(projects_dir, exist_ok=True)

    print(f"🚀 Cloning '{found['name']}' ({language})...")
    print(f"   Username : {username}")
    print(f"   Protocol : {'SSH' if protocol == 'ssh' else 'HTTPS'}")
    print(f"   Target   : ./{language}/projects/{found['name']}")
    print(f"   URL      : {clone_url}\n")

    # === Remove existing folder if it exists ===
    if os.path.exists(target_dir):
        print(f"   Removing existing folder: {found['name']}...")
        try:
            shutil.rmtree(target_dir)
            print("   ✅ Old folder removed.")
        except Exception as e:
            print(f"❌ Failed to remove existing folder: {e}")
            return

    try:
        # Clone the repository
        subprocess.run(
            ["git", "clone", clone_url, target_dir],
            check=True,
            capture_output=True,
            text=True
        )

        print("✅ Successfully cloned!")

        # Change directory into the cloned project
        os.chdir(target_dir)
        print(f"📂 Changed directory to: ./{language}/projects/{found['name']}")

        # Optional: Show current working directory for confirmation
        print(f"   Current path: {os.getcwd()}")

    except FileNotFoundError:
        print("❌ Error: 'git' command not found. Please install Git.")
    except subprocess.CalledProcessError as e:
        print("❌ Git clone failed:")
        if e.stderr:
            print(e.stderr.strip())
        # If clone failed, you might want to remove the partial folder:
        # if os.path.exists(target_dir):
        #     shutil.rmtree(target_dir, ignore_errors=True)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="GitHub Repository Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False
    )
    
    subparsers = parser.add_subparsers(dest="command", required=False)
    
    # list command
    list_parser = subparsers.add_parser("list", help="List all repositories or by language")
    list_parser.add_argument("language", nargs="?", help="Optional: filter by language (e.g. kotlin)")
    
    # download command
    download_parser = subparsers.add_parser("download", help="Download a repository")
    download_parser.add_argument("username", help="GitHub username")
    download_parser.add_argument("repo_name", help="Repository name")
    download_parser.add_argument("protocol", choices=["http", "ssh"], nargs="?", 
                                default="http", help="Protocol: http or ssh")
    
    # help command
    subparsers.add_parser("help", help="Show detailed help and instructions")
    
    if len(sys.argv) == 1:
        show_help()
        return
    
    args = parser.parse_args()
    
    if args.command == "list":
        list_repositories(args.language)
    elif args.command == "download":
        download_repository(args.username, args.repo_name, args.protocol)
    elif args.command == "help":
        show_help()
    else:
        show_help()


if __name__ == "__main__":
    main()