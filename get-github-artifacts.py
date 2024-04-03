#!/usr/bin/env python3
import os
import requests

# Configuration
GITHUB_ORG = os.getenv('GITHUB_ORG') # GitHub organization
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')  # GitHub token

# The base URL for the GitHub API
GITHUB_API_URL = 'https://api.github.com'

# Headers to use in the API requests
headers = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json',
}

def get_repos(org_name):
    print(f"Retrieving repositories for organization: {org_name}")
    repos = []
    page = 1
    while True:
        repos_url = f"{GITHUB_API_URL}/orgs/{org_name}/repos?per_page=100&page={page}"
        resp = requests.get(repos_url, headers=headers)
        resp.raise_for_status()
        current_page_repos = resp.json()
        if not current_page_repos:
            break  # Exit the loop if there are no repositories on this page
        repos.extend([repo['name'] for repo in current_page_repos])
        
        # Check if 'Link' header is present and if it contains a 'next' relation
        if "next" not in resp.links:
            break  # Exit the loop if there's no 'next' page
        page += 1
    return repos

def get_artifacts(repo_name):
    """Retrieve all artifacts for the given repository."""
    print(f"Retrieving artifacts for repository: {repo_name}")
    artifacts = []
    url = f"{GITHUB_API_URL}/repos/{GITHUB_ORG}/{repo_name}/actions/artifacts"
    while url:
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            artifacts.extend(response.json().get('artifacts', []))
            print(f"Found {len(response.json().get('artifacts', []))} artifacts")
            url = response.links.get('next', {}).get('url')
        except requests.HTTPError as e:
            print(f"Failed to retrieve artifacts for {repo_name}: {e}")
            break
    return artifacts

def download_artifact(artifact, repo_name):
    """Download the given artifact."""
    url = artifact['archive_download_url']
    try:
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()

        # Extract filename from URL and create a directory for it
        filename = f"{repo_name}-{artifact['id']}.zip"
        download_dir = 'DownloadedGitArtifacts'
        os.makedirs(download_dir, exist_ok=True)
        filepath = os.path.join(download_dir, filename)

        # Save the artifact to a file
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Downloaded {filename}")
    except requests.HTTPError as e:
        print(f"Failed to download artifact {artifact['id']} from {repo_name}: {e}")

def main():
    repos = get_repos(GITHUB_ORG)
    if not repos:
        print("No repositories found.")
        return

    for repo in repos:
        artifacts = get_artifacts(repo)
        if not artifacts:
            print(f"No artifacts found for {repo}.")
            continue

        for artifact in artifacts:
            download_artifact(artifact, repo)

if __name__ == '__main__':
    main()