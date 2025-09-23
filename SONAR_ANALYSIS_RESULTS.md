# SonarCloud Analysis Results - Tue Sep 23 13:25:55 CDT 2025

## Quality Gate Status: FAILED

### Failed Conditions:
- **Security Rating on New Code**: 2 (required: 1) ❌
- **Coverage on New Code**: 47.83% (required: 80%) ❌

### Issues Summary:
- **Critical Issues**: 31
- **Major Issues**: 83  
- **Security Hotspots**: 5

### Security Hotspots (Priority for A Rating):
1. **app.py:21** - CSRF protection disabled (python:S4502)
2. **Dockerfile:19** - Recursive copy might add sensitive data (docker:S6470)
3. **Dockerfile:3** - Running as root user (docker:S6471)
4. **quality-gate.yml:152** - Missing full commit SHA (githubactions:S7637)
5. **index.html:304** - Missing resource integrity (Web:S5725)

### Key Critical Issues:
- Multiple Cognitive Complexity violations (28 functions > 15 complexity)
- datetime.utcnow() usage (12 instances in invitation_service.py)
- Duplicate literals and constants
- Missing error handling

### Next Actions:
1. **Fix Security Hotspots** → Get A security rating
2. **Address Critical Cognitive Complexity** → Reduce technical debt
3. **Fix datetime.utcnow()** → Use timezone-aware datetime
4. **Improve Coverage** → Get above 80% threshold

Generated: Tue Sep 23 13:25:55 CDT 2025

