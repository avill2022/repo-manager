

import requests

url = "https://avillsoftware.com/repo-manager/get_repos.php"

response = requests.get(url, timeout=10)

# Check if request was successful
if response.status_code == 200:
    data = response.json()  # Automatically parses JSON → Python dict/list
    print(data)
else:
    print(f"Error: {response.status_code}")
