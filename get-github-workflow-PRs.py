#!/usr/bin/env python3
import requests
import traceback
import yaml

org = os.getenv('GITHUB_ORG')
specific_repo = "" # for testing
token = os.getenv('GITHUB_TOKEN')

def get_default_branch(repo_name, org, headers):
    repo_url = f"https://api.github.com/repos/{org}/{repo_name}"
    response = requests.get(repo_url, headers=headers)
    return response.json().get("default_branch", "master") if response.status_code == 200 else "master"

def get_raw_workflow_url(repo_name, workflow_path, org, default_branch):
    return f"https://raw.githubusercontent.com/{org}/{repo_name}/{default_branch}/{workflow_path}"

def get_workflow_file(url, headers):
    response = requests.get(url, headers=headers)
    return response.text if response.status_code == 200 else None

def is_pr_triggered_workflow(workflow_content):
    try:
        workflow_yaml = yaml.safe_load(workflow_content)
        # The 'True' key is used because the 'on' YAML key translates to a Python True boolean
        on_content = workflow_yaml.get(True, {})
        
        # Check if 'pull_request' key exists, regardless of its value
        if 'pull_request' in on_content:
            return True
        return False
    except yaml.YAMLError as exc:
        print(f"Error parsing YAML: {exc}")
        return False

def get_fork_pr_urls(org, token, specific_repo=None):
    headers = {'Authorization': f'token {token}'}
    page = 1
    while True:
        repos_url = f"https://api.github.com/orgs/{org}/repos?type=public&per_page=100&page={page}&sort=full_name"
        repos_response = requests.get(repos_url, headers=headers)
        if repos_response.status_code != 200:
            raise Exception(f"Failed to fetch repos: {repos_response.status_code}")
        repos = repos_response.json()
        if not repos:
            break
        for repo in sorted(repos, key=lambda r: r['name'].lower()):
            if specific_repo and repo['name'].lower() != specific_repo.lower():
                continue
            print(f"  Checking workflows for repository: {repo['name']}")
            default_branch = get_default_branch(repo['name'], org, headers)
            workflows_url = f"https://api.github.com/repos/{org}/{repo['name']}/actions/workflows"
            workflows_response = requests.get(workflows_url, headers=headers)
            if workflows_response.status_code != 200:
                print(f"  Failed to fetch workflows for repo {repo['name']}")
                continue
            for workflow in workflows_response.json().get('workflows', []):
                raw_workflow_url = get_raw_workflow_url(repo['name'], workflow['path'], org, default_branch)
                print(f"    Fetching workflow file from: {raw_workflow_url}")
                workflow_file_content = get_workflow_file(raw_workflow_url, headers)
                if workflow_file_content and is_pr_triggered_workflow(workflow_file_content):
                    print(f"        Workflow {workflow['name']} in {repo['name']} is triggered by pull requests.")
                    prs_url = f"https://api.github.com/repos/{org}/{repo['name']}/pulls"
                    print(f"        Fetching PRs in forks of repository: {repo['name']}")
                    prs_response = requests.get(prs_url, headers=headers)
                    if prs_response.status_code != 200:
                        print(f"            Failed to fetch PRs for repo {repo['name']}")
                        continue
                    for pr in prs_response.json():
                        # Check if the head repository of the PR exists before accessing its full name
                        if pr['head']['repo'] is not None and pr['head']['repo']['full_name'] != f"{org}/{repo['name']}":
                            print(f"            PR: {pr['html_url']}")
                        else:
                            print(f"            Skipping PR with missing head repo: {pr['html_url']}")
                else:
                    print(f"        Workflow is not triggered by PR")
        page += 1

try:
    get_fork_pr_urls(org, token, specific_repo)
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()  # This will print the stack trace
