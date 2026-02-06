#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "requests>=2.31.0",
# ]
# ///
import os
import subprocess
import requests
import re
import time

def get_apache_repos():
    """Fetch all Apache repositories from GitHub API"""
    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/orgs/apache/repos?page={page}&per_page=100"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if not data or not isinstance(data, list):
            break
        repos.extend(data)
        print(f"Fetched page {page}, found {len(repos)} repositories so far...")
        page += 1
        time.sleep(2)  # Rate limiting
    return repos

def get_project_dir(repo_name):
    """Determine project directory based on repository name"""
    if repo_name.startswith('incubator-'):
        # Handle incubator projects
        project = repo_name.replace('incubator-', '').split('-')[0]
        return f"incubator/{project}"
    else:
        # Regular Apache projects
        project = repo_name.split('-')[0]
        return project

def clone_repo_metadata(repo_url, target_dir):
    """Clone repository with metadata only (no files)"""
    os.makedirs(target_dir, exist_ok=True)
    cmd = ["git", "clone", "--filter=blob:none", "--no-checkout", repo_url, target_dir]
    subprocess.run(cmd, check=True, capture_output=True)

def main():
    print("Fetching Apache repositories...")
    repos = get_apache_repos()
    total_repos = len(repos)
    print(f"Found {total_repos} repositories")
    
    # Save complete repository list
    with open("all-repositories.txt", "w") as f:
        for repo in repos:
            f.write(f"{repo['name']}\n")
    print(f"Saved repository list to all-repositories.txt")
    
    os.makedirs("REPOSITORIES", exist_ok=True)
    
    for i, repo in enumerate(repos, 1):
        repo_name = repo['name']
        clone_url = repo['clone_url']
        
        project_dir = get_project_dir(repo_name)
        target_path = os.path.join("REPOSITORIES", project_dir, repo_name)
        
        if os.path.exists(target_path):
            print(f"[{i}/{total_repos}] Skipping {repo_name} (already exists)")
            continue
            
        print(f"[{i}/{total_repos}] Cloning {repo_name} -> {project_dir}/ ({total_repos - i} remaining)")
        
        try:
            clone_repo_metadata(clone_url, target_path)
        except subprocess.CalledProcessError as e:
            print(f"Error cloning {repo_name}: {e}")
    
    print("Done!")

if __name__ == "__main__":
    main()
