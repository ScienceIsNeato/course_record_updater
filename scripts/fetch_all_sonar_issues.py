
import os
import requests
import json
import sys

# Configuration
SONAR_TOKEN = os.environ.get("SONAR_TOKEN")
ORG_KEY = "scienceisneato"
PROJECT_KEY = "ScienceIsNeato_course_record_updater"
API_BASE = "https://sonarcloud.io/api"

if not SONAR_TOKEN:
    print("❌ Error: SONAR_TOKEN environment variable not set")
    sys.exit(1)

def fetch_all_issues():
    print(f"🔍 Fetching issues for project: {PROJECT_KEY}")
    
    all_issues = []
    page = 1
    page_size = 500
    
    while True:
        print(f"  - Fetching page {page}...")
        try:
            # Fetch ALL open issues (confirmed + accumulated technical debt)
            # We filter by "open" status to see what's active
            # We can also filter by branch if needed, but let's see main first or the PR branch
            # To check PR branch specific issues, we need the pullRequest parameter or branch parameter
            # Let's check the branch 'fix/sonarcloud-cleanup-2025-11'
            
            params = {
                "componentKeys": PROJECT_KEY,
                "statuses": "OPEN,CONFIRMED,REOPENED",
                "ps": page_size,
                "p": page,
                "branch": "fix/sonarcloud-cleanup-2025-11"
            }
            
            response = requests.get(
                f"{API_BASE}/issues/search",
                auth=(SONAR_TOKEN, ""),
                params=params,
                timeout=30  # B113: Always set timeout on requests
            )
            
            if response.status_code != 200:
                print(f"❌ API Error: {response.status_code} - {response.text}")
                break
                
            data = response.json()
            issues = data.get("issues", [])
            
            if not issues:
                break
                
            all_issues.extend(issues)
            
            if len(issues) < page_size:
                break
                
            page += 1
            
        except Exception as e:
            print(f"❌ Exception: {e}")
            break
            
    print(f"✅ Fetched {len(all_issues)} total issues")
    
    # Save to file
    output_file = "logs/sonar_all_issues_branch.json"
    os.makedirs("logs", exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(all_issues, f, indent=2)
        
    print(f"📄 Saved to {output_file}")
    return all_issues

if __name__ == "__main__":
    fetch_all_issues()

