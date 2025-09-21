# UAT Test Cases for PR #6: Multi-Tenant Context Hardening

## PR Overview
**Title**: Start multi-tenant context hardening  
**Story**: 5.6 - Program Context Management  
**Key Changes**: Replace stubbed data with Firestore queries, add program filtering, implement default context fallbacks

---

## 🎯 Test Objective
Validate that the multi-tenant context hardening correctly:
1. **Eliminates stubbed data** - All institution/program access now queries the database
2. **Enforces proper data isolation** - Users only see data within their scope
3. **Provides default context fallbacks** - Auto-sets appropriate program context
4. **Maintains backward compatibility** - Existing functionality still works

---

## 📋 UAT Test Cases

### **TC-MT-001: Site Admin Database-Backed Institution Access**
**Prerequisites**: Database seeded, logged in as site admin (`siteadmin@system.local`)

**Test Steps**:
1. Navigate to Site Admin dashboard
2. Observe the institution statistics (should show 3 institutions: CEI, RCC, PTU)
3. Check institution list in any admin panels
4. Verify all institutions are visible

**Expected Results**:
- ✅ **Database Query**: Institution data comes from Firestore (not hardcoded `["inst-123", "inst-456"]`)
- ✅ **All Institutions Visible**: Site admin sees all 3 seeded institutions
- ✅ **Real Data**: Institution names and IDs match seeded data (CEI, RCC, PTU)

**Validation**:
- Institution count should be 3 (not mock data)
- Institution names should be realistic (not generic IDs)

---

### **TC-MT-002: Site Admin Database-Backed Program Access**
**Prerequisites**: Database seeded, logged in as site admin

**Test Steps**:
1. Navigate to dashboard and check program statistics
2. Look for program-related data across the interface
3. If program filtering is available, test switching between programs

**Expected Results**:
- ✅ **Database Query**: Program data comes from Firestore (not hardcoded `["prog-123", "prog-456"]`)
- ✅ **All Programs Visible**: Site admin sees programs from all institutions
- ✅ **Real Data**: Program names match seeded data (Computer Science, Electrical Engineering, Liberal Arts, etc.)

**Validation**:
- Program count should reflect actual seeded programs (6+ programs across institutions)
- Program names should be realistic academic programs

---

### **TC-MT-003: Institution Admin Scoped Access**
**Prerequisites**: Database seeded, logged in as CEI institution admin (`sarah.admin@cei.edu`)

**Test Steps**:
1. Navigate to Institution Admin dashboard
2. Check institution statistics (should show only CEI data)
3. Verify program list shows only CEI programs
4. Check that other institutions' data is not visible

**Expected Results**:
- ✅ **Institution Scoped**: Only CEI institution data visible
- ✅ **Program Scoped**: Only CEI programs visible (Computer Science, Electrical Engineering, Unclassified)
- ✅ **Data Isolation**: No RCC or PTU data visible

**Validation**:
- Institution count should be 1 (CEI only)
- Program names should only include CEI programs
- Statistics should be filtered to CEI scope

---

### **TC-MT-004: Program Admin Scoped Access**
**Prerequisites**: Database seeded, logged in as CEI program admin (`lisa.prog@cei.edu`)

**Test Steps**:
1. Navigate to Program Admin dashboard
2. Check course statistics and listings
3. Verify section data is filtered to accessible programs
4. Test any program switching functionality

**Expected Results**:
- ✅ **Program Scoped**: Only courses in assigned programs visible
- ✅ **Section Filtering**: Sections filtered by accessible courses in accessible programs
- ✅ **Data Isolation**: No courses/sections from other programs visible

**Validation**:
- Course count should reflect only assigned program courses
- Section data should be filtered accordingly
- No cross-program data leakage

---

### **TC-MT-005: Default Program Context Auto-Assignment**
**Prerequisites**: Database seeded, user without explicit program context

**Test Steps**:
1. Login as a user who should get auto-assigned program context
2. Navigate to dashboard
3. Check if program context is automatically set
4. Verify the auto-selected program is appropriate (default program if available)

**Expected Results**:
- ✅ **Auto-Assignment**: Program context automatically set for non-site-admin users
- ✅ **Default Priority**: Default program (is_default=true) selected first if available
- ✅ **Fallback Logic**: First accessible program used if no default exists
- ✅ **Context Persistence**: Auto-assigned context persists across requests

**Validation**:
- Check browser console/network tab for context setting API calls
- Verify subsequent API requests use the auto-assigned program context
- Confirm appropriate program data is displayed

---

### **TC-MT-006: Course List Program Filtering**
**Prerequisites**: Database seeded, logged in as program admin with limited program access

**Test Steps**:
1. Navigate to any course listing functionality
2. Verify only courses in accessible programs are shown
3. Test program_id parameter filtering if available
4. Attempt to access courses outside scope (should be denied)

**Expected Results**:
- ✅ **Program Filtering**: Course list filtered by accessible programs
- ✅ **Access Control**: Cannot view courses outside program scope
- ✅ **Parameter Validation**: program_id parameter validated against user access
- ✅ **Error Handling**: Appropriate error for unauthorized program access

**Validation**:
- Course count should match only accessible program courses
- Attempting to access unauthorized program should return 403 error
- API responses should be consistently filtered

---

### **TC-MT-007: Section List Program Filtering**
**Prerequisites**: Database seeded, logged in as program admin

**Test Steps**:
1. Navigate to section listing functionality
2. Verify sections are filtered by accessible courses in accessible programs
3. Test section filtering with program_id parameter
4. Verify instructor-scoped filtering still works

**Expected Results**:
- ✅ **Nested Filtering**: Sections filtered by courses in accessible programs
- ✅ **Program Parameter**: program_id parameter filtering works correctly
- ✅ **Instructor Scope**: Instructors still see only their assigned sections
- ✅ **Access Control**: Cannot view sections outside scope

**Validation**:
- Section count should reflect program-filtered courses
- Instructor users should see only their sections
- Program filtering should work in combination with other filters

---

### **TC-MT-008: Context Middleware Validation**
**Prerequisites**: Database seeded, any user role

**Test Steps**:
1. Make API requests that require institution context
2. Verify context validation runs before API operations
3. Test API requests without proper context (should be rejected)
4. Check that context is logged appropriately

**Expected Results**:
- ✅ **Context Required**: API requests validate institution context
- ✅ **Error Handling**: Requests without context return "Institution context required"
- ✅ **Middleware Function**: Context validation runs before all protected operations
- ✅ **Logging**: Context information logged for debugging

**Validation**:
- API requests without context should return 400 error
- Error message should be "Institution context required"
- Check browser network tab for consistent context validation

---

### **TC-MT-009: Cross-Tenant Data Isolation**
**Prerequisites**: Database seeded with multiple institutions, multiple user accounts

**Test Steps**:
1. Login as CEI institution admin
2. Note visible data (institutions, programs, courses)
3. Logout and login as RCC institution admin
4. Verify completely different data set is visible
5. Ensure no CEI data is accessible to RCC admin

**Expected Results**:
- ✅ **Complete Isolation**: No cross-institution data visibility
- ✅ **Context Switching**: Different users see completely different scoped data
- ✅ **API Filtering**: All API endpoints respect institution context
- ✅ **Security**: No unauthorized data access possible

**Validation**:
- Institution A admin should see 0 Institution B data
- API responses should be completely different between contexts
- No data leakage across institutional boundaries

---

### **TC-MT-010: Backward Compatibility**
**Prerequisites**: Existing functionality from before PR #6

**Test Steps**:
1. Test all existing dashboard functionality
2. Verify API response formats haven't changed
3. Check that session-based context still works
4. Confirm existing program switching still functions

**Expected Results**:
- ✅ **Same UX**: User experience unchanged from user perspective
- ✅ **API Compatibility**: Response formats maintained
- ✅ **Session Persistence**: Context persistence works as before
- ✅ **Feature Parity**: All existing features still functional

**Validation**:
- No broken functionality compared to pre-PR state
- API responses have same structure (just different data sources)
- User workflows remain identical

---

## 🔧 Technical Validation Points

### **Database Query Verification**
- [ ] `get_accessible_institutions()` queries Firestore instead of returning mock data
- [ ] `get_accessible_programs()` queries Firestore with proper role-based filtering
- [ ] All list endpoints apply proper program/institution filtering
- [ ] No hardcoded institution/program IDs remain in responses

### **Context Middleware Validation**
- [ ] `validate_context()` runs before all API requests
- [ ] Default program assignment logic works correctly
- [ ] Context validation errors return appropriate HTTP status codes
- [ ] Context information is properly logged

### **Security Validation**
- [ ] Cross-tenant data access is impossible
- [ ] Program access is validated against user permissions
- [ ] Institution context is required for all relevant operations
- [ ] API endpoints respect role-based access controls

---

## 🚨 Potential Issues to Watch For

1. **Performance Impact**: Database queries replacing mock data may be slower
2. **Context Conflicts**: Auto-assignment logic might conflict with existing context
3. **API Breaking Changes**: Filtering might change response data unexpectedly
4. **Default Program Logic**: Auto-assignment might select wrong program
5. **Session State**: Context changes might not persist properly

---

## 📊 Success Criteria

✅ **PASS**: All stubbed data replaced with database queries  
✅ **PASS**: Proper multi-tenant data isolation maintained  
✅ **PASS**: Default context assignment works correctly  
✅ **PASS**: No backward compatibility issues  
✅ **PASS**: Performance remains acceptable  
✅ **PASS**: Security controls are properly enforced  

---

## 📝 Test Execution Notes

**Recommended Test Order**:
1. Start with TC-MT-001 & TC-MT-002 (Site Admin - broadest access)
2. Progress to TC-MT-003 (Institution Admin - medium scope)
3. Test TC-MT-004 & TC-MT-005 (Program Admin - narrow scope)
4. Validate filtering with TC-MT-006 & TC-MT-007
5. Verify security with TC-MT-008 & TC-MT-009
6. Confirm compatibility with TC-MT-010

**Key Validation Commands**:
```bash
# Ensure database is seeded
python scripts/seed_db.py --clear

# Check application logs for context assignment
tail -f logs/app.log | grep "Auto-set default program context"

# Monitor API responses for proper filtering
# (Use browser dev tools Network tab)
```

This comprehensive UAT suite ensures that PR #6's multi-tenant context hardening works correctly while maintaining system security and user experience.
