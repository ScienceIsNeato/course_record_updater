import json
import logging
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()

INPUT_FILE = 'logs/all_sonar_issues.json'

def analyze_issues():
    try:
        with open(INPUT_FILE, 'r') as f:
            issues = json.load(f)
    except FileNotFoundError:
        logger.error(f"File not found: {INPUT_FILE}")
        return

    # Group by Impact (Security, Reliability, Maintainability)
    security = []
    reliability = []
    maintainability = []

    for issue in issues:
        impacts = [i.get('softwareQuality') for i in issue.get('impacts', [])]
        
        if 'SECURITY' in impacts:
            security.append(issue)
        elif 'RELIABILITY' in impacts:
            reliability.append(issue)
        else:
            maintainability.append(issue)

    logger.info(f"Total Issues: {len(issues)}")
    logger.info(f"  Security: {len(security)}")
    logger.info(f"  Reliability: {len(reliability)}")
    logger.info(f"  Maintainability: {len(maintainability)}")
    logger.info("-" * 40)

    # Analyze Security Issues
    logger.info("\n🚨 SECURITY ISSUES (Priority 1):")
    print_issues(security)

    # Analyze Reliability Issues
    logger.info("\n⚠️  RELIABILITY ISSUES (Priority 2):")
    print_issues(reliability)

    # Analyze Maintainability Issues (Top 5 Rules)
    logger.info("\n🔧 MAINTAINABILITY ISSUES (Priority 3 - Top Rules):")
    print_rule_summary(maintainability)

def print_issues(issue_list):
    if not issue_list:
        logger.info("  None")
        return

    grouped = defaultdict(list)
    for issue in issue_list:
        rule = issue.get('rule')
        msg = issue.get('message')
        key = f"{rule}: {msg}"
        grouped[key].append(issue)

    for key, issues in grouped.items():
        rule, msg = key.split(': ', 1)
        count = len(issues)
        logger.info(f"  [{count}x] {msg} ({rule})")
        # List unique files
        files = sorted(list(set(i.get('component').split(':')[-1] for i in issues)))
        for f in files[:5]: # Show first 5 files
            logger.info(f"    - {f}")
        if len(files) > 5:
            logger.info(f"    - ... and {len(files)-5} more")

def print_rule_summary(issue_list):
    if not issue_list:
        logger.info("  None")
        return

    rule_counts = defaultdict(int)
    rule_msgs = {}
    
    for issue in issue_list:
        rule = issue.get('rule')
        rule_counts[rule] += 1
        rule_msgs[rule] = issue.get('message')

    sorted_rules = sorted(rule_counts.items(), key=lambda x: x[1], reverse=True)

    for rule, count in sorted_rules[:10]:
        msg = rule_msgs.get(rule, "Unknown")
        logger.info(f"  [{count}x] {msg} ({rule})")

if __name__ == "__main__":
    analyze_issues()

