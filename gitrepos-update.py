#!/usr/bin/env python3
import subprocess
import json
import sys
import os
import requests
from pathlib import Path
import shutil

def print_error(message):
    print(f"❌ Error: {message}", file=sys.stderr)

def print_success(message):
    print(f"✅ {message}")

def print_info(message):
    print(f"ℹ️ {message}")

def check_gh_installed():
    """Check if GitHub CLI is installed"""
    return shutil.which("gh") is not None

def show_installation_instructions():
    """Show installation instructions for gh CLI"""
    print("\n📦 GitHub CLI (gh) is not installed on your system.")
    print("\nPlease install it using the appropriate method for your operating system:\n")
    
    print("🔹 **macOS (Homebrew):**")
    print("   brew install gh")
    
    print("\n🔹 **Windows (Winget):**")
    print("   winget install --id GitHub.cli")
    
    print("\n🔹 **Windows (Scoop):**")
    print("   scoop install gh")
    
    print("\n🔹 **Linux (Ubuntu/Debian):**")
    print("   sudo apt install gh")
    
    print("\n🔹 **Linux (Fedora):**")
    print("   sudo dnf install gh")
    
    print("\n🔹 **Other Linux distributions:**")
    print("   Visit: https://github.com/cli/cli#installation")
    
    print("\n🔐 **After installation, authenticate with:**")
    print("   gh auth login")
    
    print("\n📚 For more details, visit: https://cli.github.com/")
    
def get_repos_from_gh():
    """Get all repositories with name and description using gh CLI"""
    try:
        print_info("Fetching repositories from GitHub...")
        
        # Use gh api directly to get all repos with description in one call
        result = subprocess.run(
            ["gh", "api", "user/repos", "--paginate", "--jq", "[.[] | {name: .name, description: .description}]"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse the JSON output
        formatted_repos = json.loads(result.stdout)
        
        print_success(f"Found {len(formatted_repos)} repositories from GitHub")
        return formatted_repos
        
    except subprocess.CalledProcessError as e:
        print_error(f"GitHub CLI command failed: {e}")
        if e.stderr:
            print(f"Details: {e.stderr}")
        return None
    except json.JSONDecodeError as e:
        print_error(f"Failed to parse GitHub response: {e}")
        return None
    except FileNotFoundError:
        print_error("GitHub CLI command not found even after check")
        return None
def fetch_remote_json(url):
    """Fetch JSON from remote URL with error handling"""
    try:
        print_info(f"Fetching data from {url}...")
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"Error: {response.status_code}")
        #response.raise_for_status()
    except requests.exceptions.ConnectionError:
        print_error(f"Cannot connect to {url} - No internet connection or server is down")
        return None
    except requests.exceptions.Timeout:
        print_error(f"Timeout while connecting to {url}")
        return None
    except requests.exceptions.HTTPError as e:
        print_error(f"HTTP error {e.response.status_code} from {url}")
        return None
    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON response from {url}: {e}")
        return None
    except Exception as e:
        print_error(f"Unexpected error fetching from {url}: {e}")
        return None

def post_remote_json(url, data):
    """Post JSON to remote URL with error handling"""
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

def merge_repos(github_repos, remote_repos):
    """Merge github repos with remote repos - add new repos, remove deleted ones"""
    if not remote_repos:
        print_info("No remote data to merge")
        return {
            "languages": [
                {
                    "name": "new",
                    "repos": [{"name": repo["name"], "todo": ""} for repo in github_repos]
                }
            ]
        }
    
    # Get all repo names from github_repos
    github_repo_names = {repo.get("name") for repo in github_repos if repo.get("name")}
    
    # Get all repo names from remote_repos and build lookup
    remote_repo_names = set()
    remote_lookup = {}  # To preserve todo values
    
    # Extract languages array from remote_repos
    languages = remote_repos.get("languages", [])
    
    for lang_obj in languages:
        lang_name = lang_obj.get("name")
        for repo in lang_obj.get("repos", []):
            repo_name = repo.get("name")
            if repo_name:
                remote_repo_names.add(repo_name)
                remote_lookup[repo_name] = {
                    "todo": repo.get("todo", ""),
                    "language": lang_name
                }
    
    # Find repos to add (in github but not in remote)
    repos_to_add = github_repo_names - remote_repo_names
    
    # Find repos to remove (in remote but not in github)
    repos_to_remove = remote_repo_names - github_repo_names
    
    print_info(f"Repos to add: {len(repos_to_add)} - {repos_to_add if repos_to_add else 'none'}")
    print_info(f"Repos to remove: {len(repos_to_remove)} - {repos_to_remove if repos_to_remove else 'none'}")
    
    # Create new structure for remote_repos
    new_languages = []
    
    # First, process existing languages (excluding repos to remove)
    for lang_obj in languages:
        lang_name = lang_obj.get("name")
        filtered_repos = []
        
        for repo in lang_obj.get("repos", []):
            repo_name = repo.get("name")
            if repo_name not in repos_to_remove:
                # Keep this repo
                filtered_repos.append(repo)
        
        # Only add language if it has repos after filtering
        if filtered_repos:
            new_languages.append({
                "name": lang_name,
                "repos": filtered_repos
            })
    
    # Add new repos under "new" language
    if repos_to_add:
        new_repos_list = []
        for repo_name in repos_to_add:
            # Find description from github_repos if needed
            description = ""
            for repo in github_repos:
                if repo.get("name") == repo_name:
                    description = repo.get("description") or ""
                    break
            
            new_repos_list.append({
                "name": repo_name,
                "todo": ""
            })
            print_info(f"Added new repo: {repo_name}")
        
        new_languages.append({
            "name": "new",
            "repos": new_repos_list
        })
    
    # Log removals
    for repo_name in repos_to_remove:
        print_info(f"Removed deleted repo: {repo_name}")
    
    # Return the merged structure
    merged_repos = {"languages": new_languages}
    
    print_success(f"Merge complete: {len(repos_to_add)} added, {len(repos_to_remove)} removed")
    return merged_repos

def save_local_json(data, filename="gitrepos.json"):
    """Save JSON data to local file"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print_success(f"Saved merged data to {filename}")
        return True
    except Exception as e:
        print_error(f"Failed to save {filename}: {e}")
        return False

def update():
    """Main update function"""
    print("\n🚀 Starting repository manager update...\n")
    
    # Step 1: Check if gh is installed
    if not check_gh_installed():
        show_installation_instructions()
        sys.exit(1)
    
    print_success("GitHub CLI is installed")
    
    # Step 2: Get repositories from GitHub
    github_repos = get_repos_from_gh()
    if github_repos is None:
        print_error("Failed to fetch repositories from GitHub")
        sys.exit(1)
    
    # Step 3: Fetch remote JSON
    remote_url = "https://avillsoftware.com/repo-manager/get_repos.php"
    remote_repos = fetch_remote_json(remote_url)
    
    if remote_repos is None:
        print_info("Continuing with local GitHub data only (no remote data to merge)")
        merged_repos = github_repos
    else:
        # Step 4: Merge the two JSON structures
        merged_repos = merge_repos(github_repos, remote_repos)
    
    # Step 5: Post merged JSON to save endpoint
    save_url = "https://avillsoftware.com/repo-manager/save_repos.php"
    post_success = post_remote_json(save_url, merged_repos)
    
    if not post_success:
        print_info("Will still save local copy despite API failure")
    
    # Step 6: Save locally regardless of API success
    save_local_json(merged_repos, "gitrepos.json")
    
    print("\n✨ Repository manager update completed!\n")

def main():
    """Main entry point"""
    if len(sys.argv) != 2 or sys.argv[1] != "update":
        print("Usage: python repo-manager.py update")
        print("\nThis command will:")
        print("  1. Check if GitHub CLI (gh) is installed")
        print("  2. Fetch all your repositories from GitHub")
        print("  3. Merge with remote todo data")
        print("  4. Save the result to gitrepos.json")
        #sys.exit(1)
    
    try:
        update()
    except KeyboardInterrupt:
        print("\n\n⚠️ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()