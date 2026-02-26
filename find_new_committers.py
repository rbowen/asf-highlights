#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["httpx"]
# ///

import httpx
from datetime import datetime, timedelta
from collections import defaultdict

# Fetch latest data
people_data = httpx.get("https://projects.apache.org/json/foundation/people.json").json()
ldap_data = httpx.get("https://whimsy.apache.org/public/public_ldap_people.json").json()

# Calculate last month's date range
today = datetime.now()
last_month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
last_month_end = today.replace(day=1) - timedelta(days=1)

# Track new committers by project
new_committers = defaultdict(list)

for person_id, person_info in people_data.items():
    if person_id not in ldap_data["people"]:
        continue
    
    created_str = ldap_data["people"][person_id]["createTimestamp"]
    created = datetime.strptime(created_str, "%Y%m%d%H%M%SZ")
    
    if last_month_start <= created <= last_month_end:
        for group in person_info.get("groups", []):
            if not group.endswith("-pmc") and group not in ["apldap", "incubator"]:
                new_committers[group].append({
                    "name": person_info.get("name", person_id),
                    "id": person_id,
                    "date": created.strftime("%Y-%m-%d")
                })

# Print results
if new_committers:
    total_committers = sum(len(committers) for committers in new_committers.values())
    print(f"In {last_month_start.strftime('%B, %Y')}, {len(new_committers)} projects added a total of {total_committers} new committers\n")
    for project in sorted(new_committers.keys()):
        print(f"{project.upper()}:")
        for committer in new_committers[project]:
            print(f"  - {committer['name']} ({committer['id']}) on {committer['date']}")
        print()
else:
    print(f"No new committers added in {last_month_start.strftime('%B %Y')}")
