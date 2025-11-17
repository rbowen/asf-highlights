#!/usr/bin/env python3
"""
ASF Highlights - Weekly New Contributor Report

This script analyzes ASF repositories to identify new contributors
who made their first commit in the past 7 days.
"""

import os
import sys
import subprocess
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import defaultdict
import argparse
import logging
import re
import markdown
from apache_analysis_lib import ApacheAnalysisBase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('highlights.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ApacheHighlights(ApacheAnalysisBase):
    def __init__(self, base_dir=None):
        super().__init__(base_dir)
        self.report_data = defaultdict(list)
        # Use timezone-aware datetime for comparison
        self.cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
        
    def update_repository(self, repo_path):
        """Update a repository with metadata only."""
        logger.info(f"Updating repository: {repo_path}")
        
        # Fetch latest changes (metadata only)
        result = self.run_git_command(repo_path, ['fetch', '--all'])
        if result is None:
            return False
            
        # Update all remote tracking branches
        self.run_git_command(repo_path, ['remote', 'update'])
        return True
    
    def parse_git_date(self, date_str):
        """Parse git date string and return timezone-aware datetime."""
        try:
            # Git ISO format: 2025-01-27 10:30:45 -0800
            # Remove any extra whitespace and normalize
            date_str = re.sub(r'\s+', ' ', date_str.strip())
            
            # Try to parse with timezone
            if '+' in date_str or date_str.count('-') > 2:
                # Has timezone info
                try:
                    return datetime.fromisoformat(date_str.replace(' ', 'T'))
                except ValueError:
                    # Try alternative parsing
                    parts = date_str.rsplit(' ', 1)
                    if len(parts) == 2:
                        date_part, tz_part = parts
                        # Convert to ISO format
                        dt = datetime.fromisoformat(date_part.replace(' ', 'T'))
                        # For now, just make it UTC (we could parse timezone properly)
                        return dt.replace(tzinfo=timezone.utc)
            
            # No timezone info, assume UTC
            dt = datetime.fromisoformat(date_str.replace(' ', 'T'))
            return dt.replace(tzinfo=timezone.utc)
            
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to parse date '{date_str}': {e}")
            # Return a very old date so it won't be considered new
            return datetime(1970, 1, 1, tzinfo=timezone.utc)
    
    def is_bot_or_ci(self, author_name, author_email):
        """Check if a contributor appears to be a bot or CI system."""
        # Convert to lowercase for case-insensitive matching
        name_lower = author_name.lower()
        email_lower = author_email.lower()
        
        # Common bot indicators in names
        bot_name_patterns = [
            '[bot]',
            'jenkins',
            'ci',
            'continuous integration',
            'github-actions',
            'dependabot',
            'renovate',
            'codecov',
            'travis',
            'circleci',
            'appveyor',
            'buildbot',
            'automation',
            'auto-commit'
        ]
        
        # Common bot indicators in emails
        bot_email_patterns = [
            'jenkins',
            'ci@',
            'automation@',
            'github-actions',
            'dependabot',
            'renovate',
            'codecov',
            'travis',
            'circleci',
            'appveyor',
            'buildbot'
        ]
        
        # Check name patterns first
        for pattern in bot_name_patterns:
            if pattern in name_lower:
                return True
        
        # Check email patterns
        for pattern in bot_email_patterns:
            if pattern in email_lower:
                return True
        
        # Check for specific bot email domains
        bot_domains = [
            'dependabot.com',
            'renovatebot.com',
            'codecov.io'
        ]
        
        # Handle GitHub noreply addresses carefully
        if 'users.noreply.github.com' in email_lower:
            # Check if it's a known bot using this domain by looking for bot indicators in the email
            if any(bot_indicator in email_lower for bot_indicator in ['dependabot', 'renovate', 'github-actions', 'bot']):
                return True
            # Otherwise, it's typically a real user using GitHub's privacy feature
            return False
        elif 'noreply.github.com' in email_lower:
            # This is typically a bot or automated system
            return True
        
        # Check other bot domains
        for domain in bot_domains:
            if email_lower.endswith(domain):
                return True
        
        # Additional checks for common bot/CI patterns
        if any(pattern in name_lower for pattern in ['noreply', 'donotreply', 'no-reply']) or \
           any(pattern in email_lower for pattern in ['noreply', 'no-reply', 'donotreply']):
            return True
        
        return False
    
    def normalize_contributor_identity(self, contributors):
        """
        Attempt to resolve contributor identities across different email addresses.
        This handles cases where the same person uses different email addresses over time.
        """
        # Group contributors by normalized name
        name_groups = defaultdict(list)
        
        for email_key, info in contributors.items():
            # Normalize the name (lowercase, remove extra spaces)
            normalized_name = ' '.join(info['name'].lower().split())
            name_groups[normalized_name].append((email_key, info))
        
        # For each name group, find the earliest commit across all email addresses
        resolved_contributors = {}
        
        for normalized_name, email_infos in name_groups.items():
            if len(email_infos) == 1:
                # Single email for this name, use as-is
                email_key, info = email_infos[0]
                resolved_contributors[email_key] = info
            else:
                # Multiple emails for the same name - merge all commit data
                earliest_info = None
                earliest_email = None
                earliest_date = None
                all_commits_merged = []
                total_commits = 0
                
                for email_key, info in email_infos:
                    # Merge all commits from all email addresses
                    if 'all_commits' in info:
                        all_commits_merged.extend(info['all_commits'])
                    if 'total_commits' in info:
                        total_commits += info['total_commits']
                    
                    # Track the earliest commit across all emails
                    if earliest_date is None or info['first_commit_date'] < earliest_date:
                        earliest_date = info['first_commit_date']
                        earliest_info = info.copy()  # Make a copy to avoid modifying original
                        earliest_email = email_key
                
                # Sort merged commits by date and remove duplicates by hash
                seen_hashes = set()
                unique_commits = []
                for commit in sorted(all_commits_merged, key=lambda x: x['date']):
                    if commit['hash'] not in seen_hashes:
                        unique_commits.append(commit)
                        seen_hashes.add(commit['hash'])
                
                # Use the email with the earliest commit, but keep the most recent name
                most_recent_name = max(email_infos, key=lambda x: x[1]['first_commit_date'])[1]['name']
                earliest_info['name'] = most_recent_name
                earliest_info['all_commits'] = unique_commits
                earliest_info['total_commits'] = len(unique_commits)
                
                resolved_contributors[earliest_email] = earliest_info
                
                # Log the identity resolution
                all_emails = [email for email, _ in email_infos]
                logger.info(f"Resolved identity for '{most_recent_name}': {len(all_emails)} email addresses, {len(unique_commits)} total commits, earliest commit: {earliest_date.strftime('%Y-%m-%d')}")
        
        return resolved_contributors

    def get_all_contributors(self, repo_path):
        """Get all contributors and their first commit dates.
        
        This method finds the very first commit ever made by each contributor
        in the entire history of the repository across all branches, with
        identity resolution to handle email address changes.
        """
        # Get all commits with author info and dates across ALL branches and ALL time
        log_output = self.run_git_command(repo_path, [
            'log', '--all', '--pretty=format:%an|%ae|%ad|%H', '--date=iso'
        ])
        
        if not log_output:
            return {}
            
        contributors = {}
        commit_counts = {}  # Track total commits per contributor
        
        for line in log_output.split('\n'):
            if not line.strip():
                continue
                
            try:
                parts = line.split('|')
                if len(parts) != 4:
                    continue
                    
                author_name, author_email, commit_date, commit_hash = parts
                commit_datetime = self.parse_git_date(commit_date)
                
                # Filter out bots and CI systems
                if self.is_bot_or_ci(author_name, author_email):
                    continue
                
                # Use author email as key to avoid duplicates (same person, different names)
                key = author_email.lower()
                
                # Count commits for this contributor
                if key not in commit_counts:
                    commit_counts[key] = []
                commit_counts[key].append({
                    'date': commit_datetime,
                    'hash': commit_hash
                })
                
                if key not in contributors:
                    contributors[key] = {
                        'name': author_name,
                        'email': author_email,
                        'first_commit_date': commit_datetime,
                        'first_commit_hash': commit_hash
                    }
                else:
                    # Update if this is an earlier commit (finding the VERY FIRST commit ever)
                    if commit_datetime < contributors[key]['first_commit_date']:
                        contributors[key]['first_commit_date'] = commit_datetime
                        contributors[key]['first_commit_hash'] = commit_hash
                        # Keep the name from the earliest commit
                        contributors[key]['name'] = author_name
                        
            except (ValueError, IndexError) as e:
                logger.warning(f"Failed to parse commit line: {line} - {e}")
                continue
        
        # Add commit counts and sort commits by date for each contributor
        for key in contributors:
            if key in commit_counts:
                # Sort commits by date (oldest first)
                commit_counts[key].sort(key=lambda x: x['date'])
                contributors[key]['total_commits'] = len(commit_counts[key])
                contributors[key]['all_commits'] = commit_counts[key]
            else:
                contributors[key]['total_commits'] = 0
                contributors[key]['all_commits'] = []
        
        # Apply identity resolution to handle email address changes
        resolved_contributors = self.normalize_contributor_identity(contributors)
        
        return resolved_contributors
    
    def get_github_username(self, repo_path, author_name, author_email):
        """Try to get GitHub username from commit info."""
        # First try to get GitHub username from recent commits
        log_output = self.run_git_command(repo_path, [
            'log', '--all', '--author=' + author_email, 
            '--pretty=format:%an <%ae>', '-n', '1'
        ])
        
        if log_output:
            # Check if the name looks like a GitHub username (no spaces, starts with @, etc.)
            name_part = log_output.split('<')[0].strip()
            if name_part and not ' ' in name_part and len(name_part) > 1:
                return name_part
        
        # If email is from GitHub, extract username
        if '@users.noreply.github.com' in author_email:
            # Format: username@users.noreply.github.com or ID+username@users.noreply.github.com
            username = author_email.split('@')[0]
            if '+' in username:
                username = username.split('+')[1]
            return username
        
        # Return the author name as fallback
        return author_name
    
    def analyze_milestones(self, repo_path):
        """Analyze contributors who hit milestone commits (10th, 25th, 50th, 100th, 500th, 1000th) within the time window."""
        repo_name = repo_path.name
        logger.info(f"Analyzing milestones for repository: {repo_name}")
        
        contributors = self.get_all_contributors(repo_path)
        milestones = {10: [], 25: [], 50: [], 100: [], 500: [], 1000: []}
        
        for email_key, info in contributors.items():
            if 'all_commits' not in info or not info['all_commits']:
                continue
                
            # Check each commit to see if it represents a milestone within our time window
            for i, commit in enumerate(info['all_commits']):
                commit_number = i + 1  # 1-based counting
                commit_date = commit['date']
                
                # Check if this commit falls within our time window and is a milestone
                if (commit_date >= self.cutoff_date and 
                    commit_number in milestones and 
                    commit_number <= info['total_commits']):
                    
                    github_username = self.get_github_username(
                        repo_path, info['name'], info['email']
                    )
                    
                    milestone_info = {
                        'name': info['name'],
                        'github_username': github_username,
                        'email': info['email'],
                        'milestone_commit_number': commit_number,
                        'milestone_commit_date': commit_date.isoformat(),
                        'milestone_commit_hash': commit['hash'],
                        'total_commits': info['total_commits']
                    }
                    
                    milestones[commit_number].append(milestone_info)
        
        return milestones

    def analyze_repository(self, repo_path):
        """Analyze a repository for new contributors.
        
        This identifies contributors whose FIRST EVER commit in the repository
        was made within the specified time window.
        """
        repo_name = repo_path.name
        logger.info(f"Analyzing repository: {repo_name}")
        
        contributors = self.get_all_contributors(repo_path)
        new_contributors = []
        
        for email_key, info in contributors.items():
            # Check if this contributor's FIRST EVER commit was within our time window
            if info['first_commit_date'] >= self.cutoff_date:
                github_username = self.get_github_username(
                    repo_path, info['name'], info['email']
                )
                
                new_contributors.append({
                    'name': info['name'],
                    'github_username': github_username,
                    'email': info['email'],
                    'first_commit_date': info['first_commit_date'].isoformat(),
                    'first_commit_hash': info['first_commit_hash']
                })
        
        return new_contributors
    
    def update_project_repositories(self, target_project):
        """Update repositories for a specific project."""
        import time
        
        project_dir = self.repositories_dir / target_project
        if not project_dir.exists():
            logger.error(f"Project directory '{target_project}' not found")
            return
            
        if not project_dir.is_dir():
            logger.error(f"'{target_project}' is not a directory")
            return
        
        # First, count repositories in this project
        total_repos = 0
        if (project_dir / '.git').exists():
            # Direct repository
            total_repos = 1
        else:
            # Project directory containing multiple repos
            for repo_dir in project_dir.iterdir():
                if repo_dir.is_dir() and (repo_dir / '.git').exists():
                    total_repos += 1
        
        logger.info(f"Starting repository updates for project: {target_project} ({total_repos} repositories)")
        updated_count = 0
        failed_count = 0
        start_time = time.time()
        
        # Handle both direct repos and project subdirectories
        if (project_dir / '.git').exists():
            # Direct repository
            if self.update_repository(project_dir):
                updated_count += 1
            else:
                failed_count += 1
        else:
            # Project directory containing multiple repos
            for repo_dir in project_dir.iterdir():
                if repo_dir.is_dir() and (repo_dir / '.git').exists():
                    if self.update_repository(repo_dir):
                        updated_count += 1
                    else:
                        failed_count += 1
                    
                    # Progress update with time estimate
                    completed = updated_count + failed_count
                    remaining = total_repos - completed
                    elapsed_time = time.time() - start_time
                    
                    if completed > 0 and remaining > 0:
                        avg_time_per_repo = elapsed_time / completed
                        estimated_remaining_time = avg_time_per_repo * remaining
                        
                        if estimated_remaining_time > 60:
                            time_str = f"{estimated_remaining_time/60:.1f} minutes"
                        else:
                            time_str = f"{estimated_remaining_time:.0f} seconds"
                        
                        logger.info(f"Progress: {completed}/{total_repos} repositories updated, {remaining} remaining (est. {time_str})")
        
        total_time = time.time() - start_time
        if total_time > 60:
            time_str = f"{total_time/60:.1f} minutes"
        else:
            time_str = f"{total_time:.0f} seconds"
        
        logger.info(f"Project '{target_project}' updates complete: {updated_count} updated, {failed_count} failed in {time_str}")
    
    def update_all_repositories(self):
        """Update all repositories in the base directory using improved discovery."""
        import time
        
        # Use the improved repository discovery from base class
        repositories = self.find_all_repositories()
        total_repos = len(repositories)
        
        logger.info(f"Starting repository updates for {total_repos} repositories...")
        updated_count = 0
        failed_count = 0
        start_time = time.time()
        
        for repo_path in repositories:
            if self.update_repository(repo_path):
                updated_count += 1
            else:
                failed_count += 1
            
            # Progress update with time estimate - show progress more frequently
            completed = updated_count + failed_count
            remaining = total_repos - completed
            elapsed_time = time.time() - start_time
            
            # Show progress every 10 repositories or every 30 seconds, whichever comes first
            if completed > 0 and (completed % 10 == 0 or elapsed_time - getattr(self, '_last_progress_time', 0) >= 30):
                avg_time_per_repo = elapsed_time / completed
                estimated_remaining_time = avg_time_per_repo * remaining
                
                if estimated_remaining_time > 60:
                    time_str = f"{estimated_remaining_time/60:.1f} minutes"
                else:
                    time_str = f"{estimated_remaining_time:.0f} seconds"
                
                logger.info(f"Progress: {completed}/{total_repos} repositories processed "
                           f"({updated_count} updated, {failed_count} failed) - "
                           f"{remaining} remaining (ETA: {time_str})")
                
                # Track last progress time
                self._last_progress_time = elapsed_time
        
        total_time = time.time() - start_time
        if total_time > 60:
            time_str = f"{total_time/60:.1f} minutes"
        else:
            time_str = f"{total_time:.0f} seconds"
        
        logger.info(f"Repository updates complete: {updated_count} updated, {failed_count} failed in {time_str}")
    
    def analyze_all_repositories(self, target_project=None):
        """Analyze all repositories for new contributors and milestones using improved discovery."""
        if target_project:
            logger.info(f"Starting repository analysis for project: {target_project}")
            repositories = self.find_all_repositories(target_project)
        else:
            logger.info("Starting repository analysis...")
            repositories = self.find_all_repositories()
        
        # Group repositories by project for reporting
        project_repos = {}
        for repo_path in repositories:
            # Extract project name from repository path
            repo_str = str(repo_path)
            repositories_str = str(self.repositories_dir)
            
            if repo_str.startswith(repositories_str):
                rel_path = repo_str[len(repositories_str):].lstrip('/')
                path_parts = rel_path.split('/')
                
                # Special handling for incubator projects
                if path_parts[0] == 'incubator' and len(path_parts) > 1:
                    project_name = path_parts[1]  # Use the incubator project name
                else:
                    project_name = path_parts[0]
                
                if project_name not in project_repos:
                    project_repos[project_name] = []
                project_repos[project_name].append(repo_path)
        
        # Analyze each project's repositories
        for project_name, repo_paths in project_repos.items():
            # Skip if we're targeting a specific project and this isn't it
            if target_project and project_name != target_project:
                continue
                
            project_contributors = []
            project_milestones = {10: [], 25: [], 50: [], 100: [], 500: [], 1000: []}
            
            # Analyze all repositories for this project
            for repo_path in repo_paths:
                contributors = self.analyze_repository(repo_path)
                project_contributors.extend(contributors)
                
                # Analyze milestones for this repository
                milestones = self.analyze_milestones(repo_path)
                for milestone_num in project_milestones:
                    project_milestones[milestone_num].extend(milestones[milestone_num])
            
            # Process new contributors
            if project_contributors:
                # Remove duplicates based on email
                unique_contributors = {}
                for contrib in project_contributors:
                    email = contrib['email']
                    if email not in unique_contributors:
                        unique_contributors[email] = contrib
                    else:
                        # Keep the earlier first commit
                        try:
                            existing_date = datetime.fromisoformat(unique_contributors[email]['first_commit_date'])
                            new_date = datetime.fromisoformat(contrib['first_commit_date'])
                            # Ensure both dates are timezone-aware for comparison
                            if existing_date.tzinfo is None:
                                existing_date = existing_date.replace(tzinfo=timezone.utc)
                            if new_date.tzinfo is None:
                                new_date = new_date.replace(tzinfo=timezone.utc)
                            if new_date < existing_date:
                                unique_contributors[email] = contrib
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Date comparison failed for {email}: {e}")
                            # Keep the existing one if we can't compare
                
                # Store both new contributors and milestones
                self.report_data[project_name] = {
                    'new_contributors': list(unique_contributors.values()),
                    'milestones': project_milestones
                }
            elif any(project_milestones[m] for m in project_milestones):
                # No new contributors but has milestones
                self.report_data[project_name] = {
                    'new_contributors': [],
                    'milestones': project_milestones
                }
        
        if target_project and target_project not in self.report_data:
            logger.warning(f"Project '{target_project}' not found or has no new contributors or milestones")
        
        logger.info("Repository analysis complete")
    
    def generate_report(self, target_project=None):
        """Generate the weekly highlights report."""
        report_date = datetime.now().strftime('%Y-%m-%d')
        
        # Create reports directory structure
        reports_dir = Path('reports') / report_date
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        if target_project:
            report_file = reports_dir / f"apache_highlights_{target_project}_{report_date}.md"
        else:
            report_file = reports_dir / f"apache_highlights_{report_date}.md"
        
        with open(report_file, 'w') as f:
            f.write(f"# ASF Weekly Highlights - {report_date}\n\n")
            if target_project:
                f.write(f"Project: **{target_project}**\n\n")
            
            days_back = (datetime.now(timezone.utc) - self.cutoff_date).days
            f.write(f"Analysis period: past {days_back} days\n\n")
            
            if not self.report_data:
                f.write("No new contributors or milestones found in the specified time period.\n")
                return report_file
            
            # Calculate totals
            total_new_contributors = sum(len(data.get('new_contributors', [])) for data in self.report_data.values())
            total_milestones = sum(
                sum(len(milestones.get(m, [])) for m in [10, 25, 50, 100, 500, 1000])
                for data in self.report_data.values()
                for milestones in [data.get('milestones', {})]
            )
            
            # New Contributors Section
            f.write(f"## New Contributors\n\n")
            f.write(f"Contributors who made their **first commit ever** in the past {days_back} days:\n\n")
            
            if total_new_contributors == 0:
                f.write("No new contributors found in the specified time period.\n\n")
            else:
                f.write(f"**Total new contributors: {total_new_contributors}**\n\n")
                
                # Sort projects by number of new contributors (descending)
                sorted_projects = sorted(
                    [(name, data) for name, data in self.report_data.items() if data.get('new_contributors')],
                    key=lambda x: len(x[1]['new_contributors']), 
                    reverse=True
                )
                
                for project_name, project_data in sorted_projects:
                    contributors = project_data['new_contributors']
                    f.write(f"### {project_name} ({len(contributors)} new contributor{'s' if len(contributors) != 1 else ''})\n\n")
                    
                    # Sort contributors by first commit date
                    contributors.sort(key=lambda x: x['first_commit_date'])
                    
                    for contrib in contributors:
                        commit_date = datetime.fromisoformat(contrib['first_commit_date']).strftime('%Y-%m-%d')
                        github_user = contrib['github_username']
                        name = contrib['name']
                        
                        # Format the contributor info
                        if github_user != name and github_user:
                            f.write(f"- **{github_user}** ({name}) - First commit: {commit_date}\n")
                        else:
                            f.write(f"- **{name}** - First commit: {commit_date}\n")
                    
                    f.write("\n")
            
            # Milestones Section
            f.write(f"## Contributor Milestones\n\n")
            f.write(f"Contributors who reached milestone commits (10th, 25th, 50th, 100th, 500th, 1000th) in the past {days_back} days:\n\n")
            
            if total_milestones == 0:
                f.write("No milestone commits found in the specified time period.\n\n")
            else:
                f.write(f"**Total milestone commits: {total_milestones}**\n\n")
                
                # Process milestones by milestone number
                for milestone_num in [1000, 500, 100, 50, 25, 10]:  # Show higher milestones first
                    milestone_contributors = []
                    
                    for project_name, project_data in self.report_data.items():
                        milestones = project_data.get('milestones', {})
                        if milestone_num in milestones and milestones[milestone_num]:
                            for contrib in milestones[milestone_num]:
                                milestone_contributors.append((project_name, contrib))
                    
                    if milestone_contributors:
                        f.write(f"### {milestone_num}th Commit Milestone ({len(milestone_contributors)} contributor{'s' if len(milestone_contributors) != 1 else ''})\n\n")
                        
                        # Sort by project name, then by date
                        milestone_contributors.sort(key=lambda x: (x[0], x[1]['milestone_commit_date']))
                        
                        current_project = None
                        for project_name, contrib in milestone_contributors:
                            if project_name != current_project:
                                if current_project is not None:
                                    f.write("\n")
                                f.write(f"**{project_name}:**\n")
                                current_project = project_name
                            
                            commit_date = datetime.fromisoformat(contrib['milestone_commit_date']).strftime('%Y-%m-%d')
                            github_user = contrib['github_username']
                            name = contrib['name']
                            total_commits = contrib['total_commits']
                            
                            # Format the contributor info
                            if github_user != name and github_user:
                                f.write(f"- **{github_user}** ({name}) - {milestone_num}th commit on {commit_date} (total: {total_commits})\n")
                            else:
                                f.write(f"- **{name}** - {milestone_num}th commit on {commit_date} (total: {total_commits})\n")
                        
                        f.write("\n")
            
            # Add summary graph of top 10 projects with most new contributors
            f.write("## Summary\n\n")
            f.write("Top 10 projects by new contributors:\n\n")
            
            # Get projects with new contributors, sorted by count
            projects_with_contributors = []
            for project_name, project_data in self.report_data.items():
                new_contributors = project_data.get('new_contributors', [])
                if new_contributors:
                    projects_with_contributors.append((project_name, len(new_contributors)))
            
            # Sort by contributor count (descending) and take top 10
            top_projects = sorted(projects_with_contributors, key=lambda x: x[1], reverse=True)[:10]
            
            if top_projects:
                # Find the maximum count for scaling the graph
                max_count = max(count for _, count in top_projects)
                
                f.write("```\n")
                for project_name, count in top_projects:
                    # Create a simple bar chart using characters
                    bar_length = max(1, int((count / max_count) * 40))  # Scale to max 40 characters
                    bar = "█" * bar_length
                    f.write(f"{project_name:20} │{bar} {count}\n")
                f.write("```\n\n")
            else:
                f.write("No projects with new contributors found.\n\n")
        
        logger.info(f"Report generated: {report_file}")
        return report_file
    
    def generate_json_report(self, target_project=None):
        """Generate a JSON version of the report for programmatic use."""
        report_date = datetime.now().strftime('%Y-%m-%d')
        
        # Create reports directory structure
        reports_dir = Path('reports') / report_date
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        if target_project:
            json_file = reports_dir / f"apache_highlights_{target_project}_{report_date}.json"
        else:
            json_file = reports_dir / f"apache_highlights_{report_date}.json"
        
        # Calculate totals
        total_new_contributors = sum(len(data.get('new_contributors', [])) for data in self.report_data.values())
        total_milestones = sum(
            sum(len(milestones.get(m, [])) for m in [10, 25, 50, 100, 500, 1000])
            for data in self.report_data.values()
            for milestones in [data.get('milestones', {})]
        )
        
        report_json = {
            'report_date': report_date,
            'cutoff_date': self.cutoff_date.isoformat(),
            'analysis_period_days': (datetime.now(timezone.utc) - self.cutoff_date).days,
            'total_new_contributors': total_new_contributors,
            'total_milestone_commits': total_milestones,
            'projects': dict(self.report_data)
        }
        
        if target_project:
            report_json['target_project'] = target_project
        
        with open(json_file, 'w') as f:
            json.dump(report_json, f, indent=2, default=str)
        
        logger.info(f"JSON report generated: {json_file}")
        return json_file
    
    def convert_to_html(self, markdown_file):
        """Convert markdown report to HTML."""
        html_file = markdown_file.with_suffix('.html')
        
        try:
            with open(markdown_file, 'r') as f:
                markdown_content = f.read()
            
            # Convert markdown to HTML
            html_content = markdown.markdown(markdown_content, extensions=['tables'])
            
            # Add basic HTML structure
            full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>ASF Weekly Highlights</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1, h2, h3 {{ color: #333; }}
        pre {{ background: #f5f5f5; padding: 10px; border-radius: 5px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""
            
            with open(html_file, 'w') as f:
                f.write(full_html)
            
            logger.info(f"HTML report generated: {html_file}")
            return html_file
            
        except Exception as e:
            logger.error(f"Failed to convert to HTML: {e}")
            return None
    
    def upload_to_server(self, html_file):
        """Upload HTML file to server via SCP."""
        try:
            # SCP command to upload to fagin server
            scp_command = [
                'scp', 
                str(html_file), 
                'rbowen@fagin:/var/www/vhosts/boxofclue.com/apache-highlights/'
            ]
            
            result = subprocess.run(scp_command, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Successfully uploaded {html_file.name} to server")
                
                # Post to Mastodon after successful upload
                self.post_to_mastodon(html_file.name)
                
            else:
                logger.error(f"Failed to upload to server: {result.stderr}")
                
        except Exception as e:
            logger.error(f"Error uploading to server: {e}")
    
    def post_to_mastodon(self, html_filename):
        """Post announcement to Mastodon."""
        try:
            url = f"https://boxofclue.com/apache-highlights/{html_filename}"
            message = f"This week's ASF community highlights: {url}\n\nCode is at https://github.com/rbowen/asf-highlights"
            
            # Run mastodon_post.py using its virtual environment
            mastodon_command = [
                'bash', '-c',
                f'cd {Path(__file__).parent} && source mastodon_venv/bin/activate && python3 mastodon_post.py "{message}"'
            ]
            
            result = subprocess.run(mastodon_command, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("Successfully posted to Mastodon")
            else:
                logger.error(f"Failed to post to Mastodon: {result.stderr}")
                
        except Exception as e:
            logger.error(f"Error posting to Mastodon: {e}")
    
    def run(self, update_repos=True, analyze=True, target_project=None):
        """Run the complete highlights analysis."""
        if target_project:
            logger.info(f"Starting ASF Highlights analysis for project: {target_project}")
        else:
            logger.info("Starting ASF Highlights analysis")
        
        if update_repos:
            if target_project:
                # Only update repositories for the target project
                self.update_project_repositories(target_project)
            else:
                self.update_all_repositories()
        
        if analyze:
            self.analyze_all_repositories(target_project)
            markdown_report = self.generate_report(target_project)
            json_report = self.generate_json_report(target_project)
            
            # Convert markdown to HTML and upload
            if markdown_report:
                html_report = self.convert_to_html(markdown_report)
                if html_report:
                    self.upload_to_server(html_report)
            
            logger.info("Analysis complete!")
            logger.info(f"Reports generated: {markdown_report}, {json_report}")
            
            return markdown_report, json_report
        
        return None, None

def main():
    parser = argparse.ArgumentParser(description='ASF Weekly Highlights Generator')
    parser.add_argument('--no-update', action='store_true', 
                       help='Skip repository updates')
    parser.add_argument('--base-dir', type=str, 
                       help='Base directory containing ASF repositories')
    parser.add_argument('--days', type=int, default=7,
                       help='Number of days to look back for new contributors')
    parser.add_argument('--project', type=str,
                       help='Analyze only a specific project (e.g., spark, flink)')
    
    args = parser.parse_args()
    
    highlights = ApacheHighlights(args.base_dir)
    
    # Override cutoff date if specified
    if args.days != 7:
        highlights.cutoff_date = datetime.now(timezone.utc) - timedelta(days=args.days)
    
    try:
        highlights.run(update_repos=not args.no_update, target_project=args.project)
    except KeyboardInterrupt:
        logger.info("Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
