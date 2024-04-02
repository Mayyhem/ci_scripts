#!/usr/bin/env python3
import os
import requests

# Constants
GITHUB_API = "https://api.github.com"
ORGANIZATION = os.getenv('GITHUB_ORG')
TOKEN = os.getenv('GITHUB_TOKEN')

# Set up the headers for authentication
headers = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def get_repositories(org_name):
    """Retrieve all repositories for the given organization."""
    print(f"Retrieving repositories for organization: {org_name}")
    repos = []
    url = f"{GITHUB_API}/orgs/{org_name}/repos"
    while url:
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            repos.extend(response.json())
            print(f"Found {len(response.json())} repositories")
            url = response.links.get('next', {}).get('url')
        except requests.HTTPError as e:
            print(f"Failed to retrieve repositories: {e}")
            break
    return repos

# Main execution
repositories = get_repositories(ORGANIZATION)
for repo in repositories:
    repo_name = repo["name"]
    permissions = repo["permissions"]
    print(f"Repository: {repo_name}")
    if permissions["admin"]:
        print("  - Access level: Admin")
    elif permissions["push"]:
        print("  - Access level: Write")
    elif permissions["pull"]:
        print("  - Access level: Read")
    else:
        print("  - Access level: None")