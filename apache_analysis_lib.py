#!/usr/bin/env python3
"""
Apache Analysis Library - Shared functions for Apache repository analysis

This library contains common functionality used by both the highlights
and badges scripts for analyzing Apache repositories.
"""

import subprocess
import logging
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ApacheAnalysisBase:
    """Base class with shared functionality for Apache repository analysis."""
    
    def __init__(self, base_dir=None):
        """Initialize with base directory containing REPOSITORIES subdirectory."""
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = Path(__file__).parent
        
        # All repositories are now in the REPOSITORIES subdirectory
        self.repositories_dir = self.base_dir / 'REPOSITORIES'
        
    def run_git_command(self, repo_path, command):
        """Run a git command in the specified repository."""
        try:
            result = subprocess.run(
                ['git'] + command,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.warning(f"Git command failed in {repo_path}: {result.stderr}")
                return None
        except subprocess.TimeoutExpired:
            logger.error(f"Git command timed out in {repo_path}")
            return None
        except Exception as e:
            logger.error(f"Error running git command in {repo_path}: {e}")
            return None
    
    def update_repository(self, repo_path):
        """Update a repository with metadata only."""
        logger.info(f"Updating repository: {repo_path}")
        
        # Fetch all remote refs without downloading objects
        fetch_result = self.run_git_command(repo_path, ['fetch', '--all'])
        if fetch_result is None:
            return False
            
        # Update remote tracking branches
        update_result = self.run_git_command(repo_path, ['remote', 'update'])
        if update_result is None:
            return False
            
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
                earliest_date = None
                earliest_email = None
                earliest_info = None
                all_emails = []
                all_commits = []
                most_recent_name = None
                
                # Find the earliest commit across all emails for this person
                for email_key, info in email_infos:
                    all_emails.append(info['email'])
                    if 'all_commits' in info:
                        all_commits.extend(info['all_commits'])
                    
                    # Track the most recent name (from the latest commit)
                    if most_recent_name is None or info['first_commit_date'] > earliest_info['first_commit_date']:
                        most_recent_name = info['name']
                    
                    if earliest_date is None or info['first_commit_date'] < earliest_date:
                        earliest_date = info['first_commit_date']
                        earliest_email = email_key
                        earliest_info = info.copy()
                
                # Remove duplicate commits (same hash)
                unique_commits = {}
                for commit in all_commits:
                    unique_commits[commit['hash']] = commit
                
                # Update the earliest info with merged data
                earliest_info['name'] = most_recent_name  # Use the most recent name
                earliest_info['all_emails'] = list(set(all_emails))  # All unique emails
                earliest_info['all_commits'] = list(unique_commits.values())
                earliest_info['total_commits'] = len(unique_commits)
                
                resolved_contributors[earliest_email] = earliest_info
                
                # Log the identity resolution
                earliest_date = earliest_info['first_commit_date']
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
        if '@users.noreply.github.com' in author_email:
            # Extract GitHub username from noreply email
            # Format: 12345678+username@users.noreply.github.com
            parts = author_email.split('@')[0]
            if '+' in parts:
                return parts.split('+')[1]
        
        # Check if author name looks like a GitHub username (no spaces, starts with letter/number)
        if ' ' not in author_name and re.match(r'^[a-zA-Z0-9]', author_name):
            return author_name
        
        # If we can't determine GitHub username, return the author name
        return author_name

    def find_all_repositories(self, target_project=None):
        """Find all git repositories in the REPOSITORIES directory."""
        repositories = []
        
        # Check if REPOSITORIES directory exists
        if not self.repositories_dir.exists():
            logger.error(f"REPOSITORIES directory not found: {self.repositories_dir}")
            return repositories
        
        if target_project:
            # Look for specific project in REPOSITORIES directory
            project_dir = self.repositories_dir / target_project
            if not project_dir.exists():
                # Check if it's an incubator project
                incubator_project_dir = self.repositories_dir / 'incubator' / target_project
                if incubator_project_dir.exists():
                    project_dir = incubator_project_dir
                else:
                    logger.error(f"Project directory not found: {project_dir}")
                    return repositories
                
            if (project_dir / '.git').exists():
                # Direct repository
                repositories.append(project_dir)
            else:
                # Directory containing multiple repositories - search recursively
                repositories.extend(self._find_git_repos_recursive(project_dir, max_depth=3))
        else:
            # Find all repositories in REPOSITORIES directory
            for project_dir in self.repositories_dir.iterdir():
                if not project_dir.is_dir() or project_dir.name.startswith('.') or project_dir.name == 'backups':
                    continue
                    
                if (project_dir / '.git').exists():
                    # Direct repository
                    repositories.append(project_dir)
                else:
                    # Directory containing multiple repositories - search recursively
                    repositories.extend(self._find_git_repos_recursive(project_dir, max_depth=3))
        
        return repositories
    
    def _find_git_repos_recursive(self, directory, max_depth=3, current_depth=0):
        """Recursively find git repositories up to max_depth levels."""
        repositories = []
        
        if current_depth >= max_depth:
            return repositories
            
        try:
            for item in directory.iterdir():
                if not item.is_dir():
                    continue
                    
                if (item / '.git').exists():
                    # Found a git repository
                    repositories.append(item)
                else:
                    # Recurse into subdirectory
                    repositories.extend(self._find_git_repos_recursive(item, max_depth, current_depth + 1))
        except (PermissionError, OSError):
            # Skip directories we can't read
            pass
            
        return repositories
