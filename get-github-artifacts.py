import os
import requests

# Configuration
ORGANIZATION_NAME = os.geten('ORGANIZATION_NAME') # GitHub organization
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')  # GitHub token
CIRCLECI_TOKEN = os.getenv('CIRCLECI_TOKEN')  # CircleCI token

# The base URL for the GitHub API
GITHUB_API_URL = 'https://api.github.com'

# Headers to use in the API requests
headers = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json',
}

def get_repos(org_name):
    """Retrieve all repositories for the given organization."""
    print(f"Retrieving repositories for organization: {org_name}")
    repos = []
    url = f"{GITHUB_API_URL}/orgs/{org_name}/repos"
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

def get_artifacts(repo_name):
    """Retrieve all artifacts for the given repository."""
    print(f"Retrieving artifacts for repository: {repo_name}")
    artifacts = []
    url = f"{GITHUB_API_URL}/repos/{ORGANIZATION_NAME}/{repo_name}/actions/artifacts"
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
    repos = get_repos(ORGANIZATION_NAME)
    if not repos:
        print("No repositories found.")
        return

    for repo in repos:
        artifacts = get_artifacts(repo['name'])
        if not artifacts:
            print(f"No artifacts found for {repo['name']}.")
            continue

        for artifact in artifacts:
            download_artifact(artifact, repo['name'])

if __name__ == '__main__':
    main()