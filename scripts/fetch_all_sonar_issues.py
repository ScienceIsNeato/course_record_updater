import os
import requests
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()

SONAR_TOKEN = os.environ.get('SONAR_TOKEN')
PROJECT_KEY = 'ScienceIsNeato_course_record_updater'
ORG_KEY = 'scienceisneato'
API_URL = 'https://sonarcloud.io/api/issues/search'
OUTPUT_FILE = 'logs/all_sonar_issues.json'

def fetch_issues():
    if not SONAR_TOKEN:
        logger.error("Error: SONAR_TOKEN environment variable is missing.")
        return

    headers = {
        'Authorization': f'Bearer {SONAR_TOKEN}'
    }
    
    params = {
        'componentKeys': PROJECT_KEY,
        'organization': ORG_KEY,
        'statuses': 'OPEN,CONFIRMED,REOPENED',
        'ps': 500,  # Page size (max 500)
        'p': 1      # Page number
    }

    all_issues = []
    logger.info(f"Fetching issues for project: {PROJECT_KEY}...")

    while True:
        try:
            response = requests.get(API_URL, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            issues = data.get('issues', [])
            all_issues.extend(issues)
            
            logger.info(f"Fetched page {params['p']}: {len(issues)} issues")
            
            # Check if there are more pages
            paging = data.get('paging', {})
            total = paging.get('total', 0)
            page_index = paging.get('pageIndex', 1)
            page_size = paging.get('pageSize', 100)
            
            if page_index * page_size >= total:
                break
                
            params['p'] += 1
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API Request failed: {e}")
            if response:
                logger.error(f"Response: {response.text}")
            break

    logger.info(f"Total issues fetched: {len(all_issues)}")
    
    # Save to file
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(all_issues, f, indent=2)
    
    logger.info(f"Saved issues to {OUTPUT_FILE}")
    
    # Print Summary
    summary = {
        'BUG': 0,
        'VULNERABILITY': 0,
        'CODE_SMELL': 0
    }
    
    for issue in all_issues:
        issue_type = issue.get('type', 'UNKNOWN')
        summary[issue_type] = summary.get(issue_type, 0) + 1
        
    logger.info("\nIssue Summary:")
    logger.info(f"  Security (VULNERABILITY): {summary.get('VULNERABILITY', 0)}")
    logger.info(f"  Reliability (BUG): {summary.get('BUG', 0)}")
    logger.info(f"  Maintainability (CODE_SMELL): {summary.get('CODE_SMELL', 0)}")

if __name__ == "__main__":
    fetch_issues()

