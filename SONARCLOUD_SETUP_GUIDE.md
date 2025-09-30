# SonarCloud Integration Setup Guide

## 🔍 Current Issues Identified

Based on the error logs, we have several configuration issues:

1. **"Project not found" error** - SonarCloud can't locate the project
2. **Missing test results** - No `test-results.xml` generated (now fixed)
3. **Coverage path mismatch** - Workflow vs properties file conflict (now fixed)
4. **Branch configuration conflict** - Workflow args vs properties file (now fixed)

## ✅ Fixes Applied

### 1. Workflow Configuration Fixed
- ✅ Added `--junitxml=test-results.xml` to pytest command
- ✅ Fixed coverage report path alignment
- ✅ Resolved branch configuration conflicts

### 2. Properties File Updated
- ✅ Commented out conflicting `sonar.branch.name=main`
- ✅ Let workflow args override branch configuration

## 🔧 SonarCloud Project Setup Verification

### Step 1: Verify Project Exists
1. Go to [SonarCloud.io](https://sonarcloud.io)
2. Sign in with your GitHub account
3. Check if project `ScienceIsNeato_course_record_updater` exists
4. If not, create it:
   - Organization: `scienceisneato`
   - Project Key: `ScienceIsNeato_course_record_updater`
   - Repository: Connect to `ScienceIsNeato/course_record_updater`

### Step 2: Verify Token Permissions
1. Go to SonarCloud → Account → Security
2. Generate a new token with:
   - Name: `GitHub Actions - course_record_updater`
   - Type: `Global Analysis Token`
   - Expiration: `No expiration` (or set appropriate date)

### Step 3: Update GitHub Secrets
1. Go to GitHub repository → Settings → Secrets and variables → Actions
2. Verify `SONAR_TOKEN` secret exists and is up-to-date
3. If missing, add the token from Step 2

### Step 4: Pull Request Analysis (Free Account Limitation)
**⚠️ IMPORTANT**: Free SonarCloud accounts have limitations:
- ✅ **Analysis runs**: SonarCloud will analyze your code
- ❌ **Real-time PR decoration**: Not available on free plan
- ✅ **Post-merge analysis**: Results appear after PR is merged to main
- ✅ **Quality gates**: Still enforced in CI/CD pipeline

**For real-time PR decoration**: Upgrade to paid plan required

## 🚨 Common Issues & Solutions

### Issue: "Project not found"
**Cause**: Project doesn't exist in SonarCloud or token lacks permissions
**Solution**: 
1. Create project in SonarCloud
2. Update SONAR_TOKEN with correct permissions
3. Verify organization name matches exactly

### Issue: PR not showing in SonarCloud UI
**Cause**: Free account limitation - PR decoration only available after merge
**Solution**: This is expected behavior for free accounts. Analysis still runs and enforces quality gates

### Issue: Missing coverage/test reports
**Cause**: Workflow not generating required XML files
**Solution**: ✅ Fixed - added `--junitxml=test-results.xml` to pytest

### Issue: Branch name conflicts
**Cause**: Properties file overriding workflow branch args
**Solution**: ✅ Fixed - commented out conflicting branch name in properties

## 🔄 Next Steps

1. **Verify SonarCloud Project**: Check if project exists and is accessible
2. **Update Token**: Ensure SONAR_TOKEN has correct permissions
3. **Test Integration**: Push changes and verify SonarCloud analysis runs
4. **Check PR Decoration**: Verify analysis results appear in PR comments

## 📊 Expected Results

After fixes, you should see:
- ✅ SonarCloud analysis completes successfully
- ✅ Coverage and test results properly imported
- ✅ Quality gates enforced in CI/CD pipeline
- ✅ Project appears in SonarCloud UI with analysis history
- ⚠️ PR decoration only available after merge (free account limitation)

## 🛠️ Troubleshooting Commands

If issues persist, check:
```bash
# Verify workflow runs locally (without SonarCloud)
python -m pytest tests/unit/ --cov=. --cov-report=xml --junitxml=test-results.xml

# Check if files are generated
ls -la coverage.xml test-results.xml
```

## 📝 Configuration Summary

**Workflow**: `.github/workflows/sonarcloud.yml`
- ✅ Generates `coverage.xml` and `test-results.xml`
- ✅ Passes correct branch name to SonarCloud
- ✅ Uses SonarCloud GitHub Action (not SonarQube)

**Properties**: `sonar-project.properties`
- ✅ Project key: `ScienceIsNeato_course_record_updater`
- ✅ Organization: `scienceisneato`
- ✅ Branch name: Overridden by workflow args
- ✅ Coverage/test paths: Aligned with workflow
