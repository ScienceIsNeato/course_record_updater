# SonarCloud "Project not found" Error - Systematic Troubleshooting

## 🔍 Current Error Analysis

**Error**: `Project not found. Please check the 'sonar.projectKey' and 'sonar.organization' properties, the 'SONAR_TOKEN' environment variable, or contact the project administrator to check the permissions of the user the token belongs to`

**Current Configuration**:
- Project Key: `ScienceIsNeato_course_record_updater`
- Organization: `scienceisneat`
- Token: ✅ Confirmed correct

## 🚨 Most Likely Causes

### 1. **Project Doesn't Exist in SonarCloud** (Most Common)
Even with correct credentials, the project must be created in SonarCloud UI first.

**Check**: Go to [SonarCloud.io](https://sonarcloud.io) → Projects
- Look for `ScienceIsNeato_course_record_updater`
- If not found, the project needs to be created

### 2. **Token Type Issue**
The token must be a "Global Analysis Token", not a regular user token.

**Check**: SonarCloud → Account → Security → Tokens
- Token type should be "Global Analysis Token"
- Not "User Token" or "Project Token"

### 3. **Organization Name Case Sensitivity**
SonarCloud is case-sensitive for organization names.

**Check**: Verify exact organization name in SonarCloud UI
- Current: `scienceisneat`
- Must match exactly (lowercase)

## 🔧 Step-by-Step Troubleshooting

### Step 1: Verify Project Exists
1. Go to [SonarCloud.io](https://sonarcloud.io)
2. Sign in with GitHub account
3. Check if project `ScienceIsNeato_course_record_updater` exists
4. If not found, create it:
   - Click "Add Project" → "Import from GitHub"
   - Select `ScienceIsNeato/course_record_updater`
   - This will auto-generate the project key

### Step 2: Verify Token Type
1. Go to SonarCloud → Account → Security
2. Check existing tokens:
   - Type should be "Global Analysis Token"
   - If not, create a new one with correct type
3. Update GitHub secret `SONAR_TOKEN` with new token

### Step 3: Check Organization Name
1. In SonarCloud, check the exact organization name
2. Verify it matches `scienceisneat` (lowercase)
3. If different, update `sonar-project.properties`

### Step 4: Test Configuration Locally
```bash
# Test SonarCloud connection (requires SONAR_TOKEN)
cd /Users/pacey/Documents/SourceCode/course_record_updater
source venv/bin/activate
source .envrc

# Test with debug logging
sonar-scanner -Dsonar.projectKey=ScienceIsNeato_course_record_updater \
              -Dsonar.organization=scienceisneat \
              -Dsonar.host.url=https://sonarcloud.io \
              -X
```

## 🎯 Quick Fixes to Try

### Fix 1: Create Project in SonarCloud
If project doesn't exist:
1. Go to SonarCloud → Add Project
2. Import from GitHub → Select `ScienceIsNeato/course_record_updater`
3. This creates the project with correct key

### Fix 2: Regenerate Token
If token type is wrong:
1. SonarCloud → Account → Security → Tokens
2. Delete old token
3. Create new "Global Analysis Token"
4. Update GitHub secret `SONAR_TOKEN`

### Fix 3: Verify Organization
Check exact organization name in SonarCloud:
- Should be `scienceisneat` (lowercase)
- If different, update `sonar-project.properties`

## 🔍 Debug Commands

### Test SonarCloud Connection
```bash
# Test with debug logging
sonar-scanner -Dsonar.projectKey=ScienceIsNeato_course_record_updater \
              -Dsonar.organization=scienceisneat \
              -Dsonar.host.url=https://sonarcloud.io \
              -X
```

### Check Token Permissions
```bash
# Test token with SonarCloud API
curl -u "$SONAR_TOKEN:" "https://sonarcloud.io/api/authentication/validate"
```

## 📋 Expected Results

After fixes:
- ✅ SonarCloud project exists and is accessible
- ✅ Token has correct permissions
- ✅ Analysis runs successfully
- ✅ Quality gates are enforced

## 🚨 If Still Failing

If all steps are correct but still failing:
1. **Check GitHub Actions logs** for exact error details
2. **Verify token scope** - needs "Execute Analysis" permission
3. **Check organization membership** - user must be member of organization
4. **Try different project key format** - sometimes auto-generated keys work better

## 📞 Next Steps

1. **Verify project exists** in SonarCloud UI
2. **Check token type** is "Global Analysis Token"
3. **Test locally** with debug logging
4. **Update GitHub secret** if token was regenerated
5. **Re-run workflow** to test integration
