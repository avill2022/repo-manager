# Repository Manager

A CLI tool for managing categorized GitHub repositories — list, add, edit, remove, clone, and sync repos with optional remote backup.

## Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd repo-manager
```

### 2. Environment variables (optional)

Edit the `.env` file in the project root and adjust as needed:

```bash
# .env is already present — edit it to your needs
```

The tool works without a `.env` file — defaults are hardcoded. Use `.env` to override remote API URLs or set a default GitHub username.

### 3. Install dependencies

**Standard Python:**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**NixOS (with flakes):**

```bash
nix develop
```

This drops you into a shell with Python, the GitHub CLI (`gh`), and all Python dependencies (requests, python-dotenv).

### 4. Data file

Create a `gitrepos.json` file in the project root with the following structure:

```json
{
  "languages": [
    {
      "name": "python",
      "repos": [
        { "name": "my-repo", "todo": "add tests" }
      ]
    }
  ]
}
```

## Usage

```bash
python main.py help
```

### Commands

| Command    | Description                                                |
|------------|------------------------------------------------------------|
| `list`     | List all repositories (optionally filter by language)      |
| `add`      | Add a repository to the local data file                    |
| `edit`     | Edit repository name, language, or TODO                    |
| `remove`   | Remove a repository from the local data file               |
| `delete`   | Remove repository from data file and delete local folder   |
| `download` | Clone a repository to `<language>/projects/<repo_name>`    |
| `update`   | Sync repositories from GitHub and remote API (requires `gh`) |
| `help`     | Show detailed help and instructions                        |

## Dependencies

### Python (pip)
- [requests](https://pypi.org/project/requests/) — HTTP requests for remote API sync
- [python-dotenv](https://pypi.org/project/python-dotenv/) — optional `.env` file support

### System
- [GitHub CLI (gh)](https://cli.github.com/) — required for the `update` command. Install via your package manager: `sudo apt install gh`, `brew install gh`, or `nix shell nixpkgs#gh`.

## Files

| File               | Purpose                                      |
|--------------------|----------------------------------------------|
| `main.py`          | Main CLI entry point with all commands       |
| `repo-manager.py`  | Wrapper script (delegates to main.py)        |
| `gitrepos-update.py` | Wrapper for the update command               |
| `gitrepos.json`    | Local repository data file                   |
| `.env`             | Optional environment configuration           |
| `flake.nix`        | Nix development shell                        |
| `requirements.txt` | Python dependencies                          |
