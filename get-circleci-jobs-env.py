#!/usr/bin/env python
import argparse
import hashlib
import json
import os
import requests
from urllib.parse import urlparse, parse_qs

# Configuration
GITHUB_ORG = os.getenv('GITHUB_ORG')  # GitHub org
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')  # GitHub token
CIRCLECI_TOKEN = os.getenv('CIRCLECI_TOKEN')  # CircleCI token

if not GITHUB_TOKEN or not CIRCLECI_TOKEN:
    raise ValueError("GitHub or CircleCI token not found. Please set the GITHUB_TOKEN and CIRCLECI_TOKEN environment variables.")

GITHUB_API_URL = 'https://api.github.com'
CIRCLECI_API_URL = 'https://circleci.com/api/v2'
PROGRESS_FILE = 'saved_progress.json'

github_session = requests.Session()
github_session.headers.update({'Authorization': f'token {GITHUB_TOKEN}', 'Accept': 'application/vnd.github.v3+json'})

circleci_session = requests.Session()
circleci_session.auth = (CIRCLECI_TOKEN, '')
circleci_session.headers.update({'Accept': 'application/json'})

def authenticate_to_circleci(username, password):
    # Initialize a requests session
    session = requests.Session()

    # Send a GET request to the CircleCI login page and follow redirects to /u/login?state
    login_url = "https://circleci.com/auth/login"
    response = session.get(login_url, allow_redirects=True)
    login_url_with_state = response.url
    parsed_url = urlparse(login_url_with_state)
    query_params = parse_qs(parsed_url.query)
    state = query_params.get('state', [None])[0]  # Default to None if not found

    # Send a POST request with the provided credentials
    data = {'state': state, 'username': username, 'password': password, 'action': 'default'}
    response = session.post(login_url_with_state, data)

    # Return authenticated session
    return session

def get_github_repositories(org_name):
    repos = []
    page = 1
    while True:
        repos_url = f"{GITHUB_API_URL}/orgs/{org_name}/repos?per_page=100&page={page}"
        resp = github_session.get(repos_url)
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

def get_job_details(project_slug, job_id):
    job_details_url = f"{CIRCLECI_API_URL}/project/{project_slug}/job/{job_id}"
    job_details_resp = circleci_session.get(job_details_url)
    job_details = job_details_resp.json()
    return job_details

def get_workflow_job_vars(project_slug, circleci_app_session):
    print(f"\n\n\nProcessing project: {project_slug}")
    
    pipelines_url = f'{CIRCLECI_API_URL}/project/gh/{project_slug}/pipeline'
    pipelines_resp = circleci_session.get(pipelines_url)

    if not pipelines_resp.ok:
        print(f"No pipelines found or access denied for: {project_slug}")
        return

    pipelines = pipelines_resp.json().get('items', [])

    for pipeline in pipelines:
        workflows_url = f"{CIRCLECI_API_URL}/pipeline/{pipeline['id']}/workflow"
        workflows_resp = circleci_session.get(workflows_url)
        workflows = workflows_resp.json().get('items', [])

        for workflow in workflows:
            if seen_workflow(project_slug, workflow['name']):
                print(f"Skipping already processed workflow {workflow['name']} in {project_slug}")
                continue

            print(f"\nProject: {project_slug}")
            print(f"Workflow: {workflow['name']} ({workflow['id']})")
            print(f"Trigger: {pipeline['trigger']['type']}")
            jobs_url = f"{CIRCLECI_API_URL}/workflow/{workflow['id']}/job"
            jobs_resp = circleci_session.get(jobs_url)
            jobs = jobs_resp.json().get('items', [])

            latest_job = max(jobs, key=lambda j: j.get('job_number', 0))

            job_number = latest_job.get('job_number', 0)

            if has_completed(project_slug, workflow['name'], workflow['id'], job_number):
                print(f"Skipping already processed job {job_number} in {project_slug}")
                continue

            print(f"Job: {job_number}")
            job_env_url = f"https://circleci.com/api/private/output/raw/github/{project_slug}/{job_number}/output/0/99"
            job_env_resp = circleci_app_session.get(job_env_url)
            print(job_env_resp.text)
            write_progress(project_slug, workflow['name'], workflow['id'], job_number)
            

def has_completed(project_slug, workflow_name, workflow_id, job_number):
    progress = read_progress()
    progress_key = f"{project_slug}-{workflow_name}-{workflow_id}"
    return progress.get(progress_key, -1) >= job_number

def read_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as file:
            return json.load(file)
    return {}

def seen_workflow(project_slug, workflow_name):
    progress = read_progress()
    progress_key = f"{project_slug}-{workflow_name}"
    return any(key.startswith(progress_key) for key in progress)

def write_progress(project_slug, workflow_name, workflow_id, job_number):
    progress = read_progress()
    progress_key = f"{project_slug}-{workflow_name}-{workflow_id}"
    progress[progress_key] = job_number
    with open(PROGRESS_FILE, 'w') as file:
        json.dump(progress, file)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process CircleCI jobs for GitHub repositories')
    parser.add_argument('-p', help='Specify a CircleCI password')
    parser.add_argument('-r', help='Specify a single repository name to process')
    parser.add_argument('-u', help='Specify a CircleCI username')

    args = parser.parse_args()

    if args.r:
        repositories = [args.r]
    else:
        repositories = get_github_repositories(GITHUB_ORG)

    circleci_app_session = authenticate_to_circleci(args.u, args.p)

    for repo in repositories:
        get_workflow_job_vars(f"{GITHUB_ORG}/{repo}", circleci_app_session)