#!/usr/bin/env python3
import os
import requests
import hashlib
import json

# Configuration
GITHUB_ORG = os.getenv('GITHUB_ORG')  # GitHub org
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')  # GitHub token
CIRCLECI_TOKEN = os.getenv('CIRCLECI_TOKEN')  # CircleCI token

if not GITHUB_TOKEN or not CIRCLECI_TOKEN:
    raise ValueError("GitHub or CircleCI token not found. Please set the GITHUB_TOKEN and CIRCLECI_TOKEN environment variables.")

GITHUB_API_URL = 'https://api.github.com'
CIRCLECI_API_URL = 'https://circleci.com/api/v2'
DOWNLOAD_DIR = 'CircleArtifacts'
PROGRESS_FILE = 'download_progress.json'

github_session = requests.Session()
github_session.headers.update({'Authorization': f'token {GITHUB_TOKEN}', 'Accept': 'application/vnd.github.v3+json'})

circleci_session = requests.Session()
circleci_session.auth = (CIRCLECI_TOKEN, '')
circleci_session.headers.update({'Accept': 'application/json'})

def hash_filename(filename):
    name, extension = os.path.splitext(filename)
    hasher = hashlib.md5()
    hasher.update(name.encode('utf-8'))
    return f"{hasher.hexdigest()}{extension}"

def read_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as file:
            return json.load(file)
    return {}

def write_progress(project_slug, pipeline_id, workflow_id, job_number):
    progress = read_progress()
    progress_key = f"{project_slug}-{pipeline_id}-{workflow_id}"
    progress[progress_key] = job_number
    with open(PROGRESS_FILE, 'w') as file:
        json.dump(progress, file)

def has_completed(project_slug, pipeline_id, workflow_id, job_number):
    progress = read_progress()
    progress_key = f"{project_slug}-{pipeline_id}-{workflow_id}"
    return progress.get(progress_key, -1) >= job_number

def get_github_repositories(org_name):
    repos_url = f"{GITHUB_API_URL}/orgs/{org_name}/repos"
    resp = github_session.get(repos_url)
    resp.raise_for_status()
    return [repo['name'] for repo in resp.json()]

def download_artifacts_for_project(project_slug):
    print(f"\nProcessing project: {project_slug}")
    
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
            jobs_url = f"{CIRCLECI_API_URL}/workflow/{workflow['id']}/job"
            jobs_resp = circleci_session.get(jobs_url)
            jobs = jobs_resp.json().get('items', [])

            for job in jobs:
                if 'job_number' in job:
                    if has_completed(project_slug, pipeline['id'], workflow['id'], job['job_number']):
                        print(f"Skipping already downloaded job {job['job_number']} in {project_slug}")
                        continue

                    artifacts_url = f"{CIRCLECI_API_URL}/project/gh/{project_slug}/{job['job_number']}/artifacts"
                    artifacts_resp = circleci_session.get(artifacts_url)
                    artifacts = artifacts_resp.json().get('items', [])
                    total_artifacts = len(artifacts)

                    for i, artifact in enumerate(artifacts, 1):
                        print(f"\nDownloading artifact {i} of {total_artifacts} for job {job['job_number']}: {artifact['path']}")
                        download_resp = circleci_session.get(artifact['url'], stream=True)

                        hashed_filename = hash_filename(f"{project_slug}-{job['job_number']}-{artifact['path']}")
                        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
                        file_path = os.path.join(DOWNLOAD_DIR, hashed_filename)

                        with open(file_path, 'wb') as f:
                            for chunk in download_resp.iter_content(chunk_size=8192):
                                f.write(chunk)

                        print(f"Saved to {file_path}")
                    
                    write_progress(project_slug, pipeline['id'], workflow['id'], job['job_number'])

def main():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    repositories = get_github_repositories(GITHUB_ORG)

    for repo in repositories:
        download_artifacts_for_project(f"{GITHUB_ORG}/{repo}")

if __name__ == '__main__':
    main()
