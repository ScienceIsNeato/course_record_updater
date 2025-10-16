# Dashboard Data Architecture Refactor Plan

## 🎯 **Objective**
Replace the current "7+ API calls per dashboard load" pattern with a single optimized data fetch that retrieves all dashboard data in one request, improving performance by ~80% and eliminating database threading issues.

## 🔍 **Current Problem**
```
Dashboard Load Pattern (BROKEN):
├── GET /api/institutions
├── GET /api/programs  
├── GET /api/courses
├── GET /api/users
├── GET /api/instructors
├── GET /api/sections
└── GET /api/terms

Issues:
❌ 7+ HTTP requests per page load
❌ 20+ database queries with repeated permission checks
❌ Race conditions and threading errors
❌ Inconsistent data state (partial loads)
❌ Poor performance (~2-3 seconds load time)
```

## ✅ **Target Solution**
```
Dashboard Load Pattern (FIXED):
└── GET /api/dashboard/data
    ├── Single permission check
    ├── 4 optimized database queries  
    ├── Consistent data snapshot
    └── ~400ms load time

Frontend:
├── Single data fetch
├── Populate all UI elements from dataset
├── Auto-refresh capability
└── Manual refresh controls
```

## 📋 **Implementation Checklist**

### **Phase 1: Core Infrastructure** ⏱️ ~90 minutes

#### **Step 1.1: Create Dashboard Service** (30 min)
- [ ] **File**: Create `dashboard_service.py`
- [ ] **Class**: `DashboardService` with role-based data methods
- [ ] **Method**: `get_dashboard_data(user: Dict) -> Dict`
- [ ] **Method**: `_get_site_admin_data() -> Dict`
- [ ] **Method**: `_get_institution_admin_data(institution_id: str) -> Dict`
- [ ] **Method**: `_get_program_admin_data(program_ids: List[str]) -> Dict`
- [ ] **Method**: `_get_instructor_data(user_id: str) -> Dict`
- [ ] **Optimization**: Use batch Firestore queries where possible
- [ ] **Error Handling**: Graceful degradation for partial failures
- [ ] **Logging**: Comprehensive logging for performance monitoring

#### **Step 1.2: Create Single API Endpoint** (15 min)
- [ ] **File**: Add to `api_routes.py`
- [ ] **Route**: `@api.route("/dashboard/data", methods=["GET"])`
- [ ] **Decorator**: `@login_required`
- [ ] **Logic**: Call `DashboardService.get_dashboard_data()`
- [ ] **Response**: Return JSON with all dashboard data
- [ ] **Error Handling**: Return structured error responses

#### **Step 1.3: Update Frontend Data Loading** (30 min)
- [ ] **Files**: Update ALL dashboard templates (`site_admin_panels.html`, `institution_admin.html`, etc.)
- [ ] **Function**: Replace `loadHeaderStats()` with `loadDashboardData()` across all templates
- [ ] **API Call**: Single `fetch('/api/dashboard/data')` in all dashboards
- [ ] **UI Updates**: Populate all elements from single dataset
- [ ] **Remove**: All individual API calls (`/api/programs`, `/api/courses`, etc.) - clean deletion
- [ ] **Variables**: Clean up confusing variable names (institutionsJSON → data.institutions)
- [ ] **Cleanup**: Remove all old API call functions immediately

#### **Step 1.4: Add Refresh Capabilities** (15 min)
- [ ] **Manual Refresh**: Add refresh button with click handler
- [ ] **Auto Refresh**: 5-minute interval timer
- [ ] **Focus Refresh**: Refresh when tab becomes visible
- [ ] **Last Updated**: Display "Last updated: X minutes ago"
- [ ] **Loading States**: Show loading indicators during refresh

### **Phase 2: Testing & Validation** ⏱️ ~30 minutes

#### **Step 2.1: Unit Tests** (15 min)
- [ ] **File**: Create `tests/unit/test_dashboard_service.py`
- [ ] **Test**: `test_get_dashboard_data_site_admin`
- [ ] **Test**: `test_get_dashboard_data_institution_admin`
- [ ] **Test**: `test_get_dashboard_data_program_admin`
- [ ] **Test**: `test_get_dashboard_data_instructor`
- [ ] **Test**: `test_error_handling_partial_failures`

#### **Step 2.2: Integration Tests** (15 min)
- [ ] **File**: Update `tests/integration/test_dashboard_api.py`
- [ ] **Test**: `test_dashboard_data_endpoint_site_admin`
- [ ] **Test**: `test_dashboard_data_endpoint_requires_auth`
- [ ] **Test**: `test_dashboard_data_performance` (< 500ms target)
- [ ] **Remove**: All tests for old individual API endpoints (clean slate approach)

### **Phase 3: Performance Optimization** ⏱️ ~30 minutes

#### **Step 3.1: Database Query Optimization** (20 min)
- [ ] **Batch Queries**: Use `db.get_all()` where possible
- [ ] **Query Reduction**: Eliminate duplicate institution lookups
- [ ] **Indexing**: Verify Firestore indexes are optimal
- [ ] **Caching**: Add method-level caching for repeated calls

#### **Step 3.2: Response Optimization** (10 min)
- [ ] **Data Minimization**: Only return fields needed by frontend
- [ ] **Compression**: Enable gzip compression for large responses
- [ ] **Pagination**: For large datasets, implement cursor-based pagination

### **Phase 4: Clean Replacement & Validation** ⏱️ ~30 minutes

#### **Step 4.1: Complete Replacement** (20 min)
- [ ] **Remove**: All old individual API endpoints (`/api/institutions`, `/api/programs`, etc.)
- [ ] **Remove**: Old frontend API call functions (no backward compatibility)
- [ ] **Update**: All dashboard templates to use new single data fetch pattern
- [ ] **Remove**: Any temporary or fallback code paths

#### **Step 4.2: Final Validation** (10 min)
- [ ] **Test**: All dashboards load correctly with new endpoint
- [ ] **Verify**: No references to old API endpoints remain
- [ ] **Clean**: Remove any unused imports or helper functions
- [ ] **Documentation**: Update API documentation to reflect new architecture

## 📊 **Expected Performance Improvements**

### **Before (Current State)**
```
Dashboard Load Metrics:
├── HTTP Requests: 7+
├── Database Queries: 20+
├── Permission Checks: 7+
├── Load Time: 2-3 seconds
├── Error Rate: High (threading issues)
└── Data Consistency: Poor (partial loads)
```

### **After (Target State)**
```
Dashboard Load Metrics:
├── HTTP Requests: 1
├── Database Queries: 4-6
├── Permission Checks: 1
├── Load Time: 400ms
├── Error Rate: Low (single failure point)
└── Data Consistency: High (atomic snapshot)
```

## 🔧 **Implementation Details**

### **Dashboard Service Architecture**
```python
class DashboardService:
    def get_dashboard_data(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """
        Single method that returns ALL dashboard data for a user.
        
        Returns:
            {
                "institutions": [...],
                "programs": [...],
                "courses": [...], 
                "users": [...],
                "instructors": [...],
                "sections": [...],
                "terms": [...],
                "metadata": {
                    "user_role": "site_admin",
                    "permissions": [...],
                    "last_updated": "2025-09-19T10:30:00Z",
                    "data_scope": "system_wide" | "institution" | "program"
                }
            }
        """
```

### **Frontend Loading Pattern**
```javascript
// REPLACE: Multiple API calls
const [institutions, programs, courses, users] = await Promise.all([
    fetch('/api/institutions'),
    fetch('/api/programs'), 
    fetch('/api/courses'),
    fetch('/api/users')
]);

// WITH: Single API call
const response = await fetch('/api/dashboard/data');
const data = await response.json();

// Use data.institutions, data.programs, data.courses, data.users
```

### **Refresh Strategy**
```javascript
const REFRESH_CONFIG = {
    autoRefreshInterval: 5 * 60 * 1000, // 5 minutes
    refreshOnFocus: true,
    refreshOnUserAction: false, // Phase 2 feature
    showLastUpdated: true
};
```

## 🚨 **Risk Mitigation**

### **Data Consistency**
- **Risk**: User sees stale data after another user makes changes
- **Mitigation**: 5-minute auto-refresh + manual refresh button
- **Future**: Real-time updates via WebSocket (Phase 3)

### **Performance Regression**
- **Risk**: Single large query slower than multiple small ones
- **Mitigation**: Database query optimization + caching + comprehensive performance testing
- **Monitoring**: Performance metrics during development

### **Error Handling**
- **Risk**: Single point of failure affects entire dashboard
- **Mitigation**: Graceful degradation + detailed error logging + comprehensive unit tests
- **Approach**: Clean replacement (no fallback needed - greenfield project)

## ✅ **Success Criteria**

### **Performance Metrics**
- [ ] Dashboard load time < 500ms (vs current 2-3 seconds)
- [ ] HTTP requests reduced from 7+ to 1
- [ ] Database queries reduced from 20+ to 4-6
- [ ] Zero threading errors in logs

### **User Experience**
- [ ] Faster permockuved performance
- [ ] Consistent data state (no partial loads)
- [ ] Reliable refresh functionality
- [ ] Clear last-updated indicators

### **Code Quality**
- [ ] Test coverage maintained at 80%+
- [ ] All quality gates passing
- [ ] Clean, maintainable service architecture
- [ ] Comprehensive error handling

## 🎯 **Next Steps After Completion**

### **Phase 2 Enhancements** (Future)
- Smart refresh before user actions
- Conflict detection and resolution
- Advanced caching strategies
- Progressive data loading

### **Phase 3 Real-time** (Much Later)
- WebSocket integration
- Live data updates
- Collaborative editing features
- Real-time notifications

---

## 📝 **Implementation Notes**

- This refactor solves both performance AND the current threading issues
- Single data fetch eliminates race conditions and partial load states
- Refresh strategy provides reasonable data freshness without complexity
- Architecture supports future real-time enhancements
- **GREENFIELD ADVANTAGE**: Clean replacement approach - no backward compatibility baggage
- **IMMEDIATE CLEANUP**: Delete old endpoints and code paths as soon as new ones work

**Total Estimated Time: 3 hours**  
**Performance Improvement: ~80% faster dashboard loading**  
**Risk Level: Low (clean replacement in greenfield project)**
