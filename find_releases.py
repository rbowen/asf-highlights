#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["httpx"]
# ///

import httpx
from datetime import datetime, timedelta
from collections import defaultdict

# Fetch latest data
releases_data = httpx.get("https://projects.apache.org/json/foundation/releases.json").json()

# Calculate last month's date range
today = datetime.now()
last_month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
last_month_end = today.replace(day=1) - timedelta(days=1)

# Track releases by project
project_releases = defaultdict(list)

for project_id, releases in releases_data.items():
    for release_name, release_date_str in releases.items():
        release_date = datetime.strptime(release_date_str, "%Y-%m-%d")
        
        if last_month_start <= release_date <= last_month_end:
            project_releases[project_id].append({
                "name": release_name,
                "date": release_date_str
            })

# Print results
if project_releases:
    total_releases = sum(len(releases) for releases in project_releases.values())
    print(f"In {last_month_start.strftime('%B, %Y')}, {len(project_releases)} projects made {total_releases} releases\n")
    for project in sorted(project_releases.keys()):
        print(f"{project.upper()}:")
        for release in project_releases[project]:
            print(f"  - {release['name']} on {release['date']}")
        print()
else:
    print(f"No releases made in {last_month_start.strftime('%B %Y')}")
