#!/usr/bin/env python3

import requests
from datetime import datetime, timedelta, timezone

def main():
    url = "https://projects.apache.org/json/foundation/releases.json"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Error fetching data: {e}")
        return
    
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_releases = []
    
    for project, releases in data.items():
        if isinstance(releases, dict):
            for version, date_str in releases.items():
                if isinstance(date_str, str):
                    try:
                        if 'T' in date_str:
                            release_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        else:
                            release_date = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                        
                        if release_date >= seven_days_ago:
                            recent_releases.append({
                                'project': project,
                                'version': version,
                                'date': date_str
                            })
                    except Exception:
                        continue
    
    recent_releases.sort(key=lambda x: x['date'], reverse=True)
    
    print(f"Apache releases in the last 7 days ({len(recent_releases)} total):\n")
    
    if not recent_releases:
        print("No releases found in the last 7 days.")
        return
    
    for release in recent_releases:
        print(f"• {release['project']} {release['version']} - {release['date']}")

if __name__ == "__main__":
    main()
