#!/usr/bin/env python3
import os
import requests
import sys

def check_write_access_to_repo(repo_full_name, api_token):
    """
    Check if the given API token has write access to the specified repository.
    
    :param repo_full_name: Full name of the repository (e.g., 'username/repo').
    :param api_token: GitHub API token.
    :return: True if write access is present, False otherwise.
    """
    # GitHub API URL for the repository
    url = f"https://api.github.com/repos/{repo_full_name}"

    # Headers for authentication
    headers = {
        "Authorization": f"token {api_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Send a GET request to the API
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        # If response is not OK, return False
        return False

    # Parse the JSON response
    repo_info = response.json()
    
    # Permissions are included in the response
    permissions = repo_info.get('permissions', {})
    return permissions.get('push', False)

def main():
    repo_full_name = sys.argv[1]
    api_token = sys.argv[2]

    has_write_access = check_write_access_to_repo(repo_full_name, api_token)
    print("Has write access" if has_write_access else "No write access")

if __name__ == "__main__":
    main()