#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["httpx"]
# ///

import httpx
from datetime import datetime, timedelta
from collections import defaultdict

# Fetch latest data
committee_data = httpx.get("https://whimsy.apache.org/public/committee-info.json").json()

# Calculate last month's date range
today = datetime.now()
last_month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
last_month_end = today.replace(day=1) - timedelta(days=1)

# Track new PMC members by project
new_pmc_members = defaultdict(list)

for project_id, project_info in committee_data.get("committees", {}).items():
    if not project_info.get("pmc"):
        continue
    
    for member_id, member_info in project_info.get("roster", {}).items():
        date_str = member_info.get("date")
        if not date_str:
            continue
        
        added = datetime.strptime(date_str, "%Y-%m-%d")
        
        if last_month_start <= added <= last_month_end:
            new_pmc_members[project_id].append({
                "name": member_info.get("name", member_id),
                "id": member_id,
                "date": date_str
            })

# Print results
if new_pmc_members:
    total_members = sum(len(members) for members in new_pmc_members.values())
    print(f"In {last_month_start.strftime('%B, %Y')}, {len(new_pmc_members)} projects added a total of {total_members} new PMC members\n")
    for project in sorted(new_pmc_members.keys()):
        print(f"{project.upper()}:")
        for member in new_pmc_members[project]:
            print(f"  - {member['name']} ({member['id']}) on {member['date']}")
        print()
else:
    print(f"No new PMC members added in {last_month_start.strftime('%B %Y')}")
