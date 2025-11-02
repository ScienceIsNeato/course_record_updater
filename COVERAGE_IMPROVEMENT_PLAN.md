# Coverage Improvement Plan - Browser-Guided Testing 🔍

## Discovery Method
Used Cursor 2.0 Browser Integration to explore live application and understand uncovered code paths.

## Current Status
- **Total Uncovered Lines**: 211 across 11 files
- **Top Priority**: `static/institution_dashboard.js` (88 lines)

## Files Requiring Coverage (Ranked by Impact)

### 1. static/institution_dashboard.js (88 lines) 🟦 JS

**Browser Exploration Findings**:
- Refresh button triggers loading states and API fetches for all panels
- Multiple sortable tables with dynamic data rendering
- Error handling for failed API calls
- Loading indicators during data fetch

**Uncovered Lines**: 52-65, 67-77, 302, 456-458, 461, 472, 475, 477, 494-495, 502-503, 507, 510-514, 518-522, 526, 536-539, 541, 557-558, 565-567, 570, 579, 592-593, 600-602, 606, 618, 701-704, 709-712, 717-718, 721-723, 725, 737, 739-740, 744, 747-748

**Test Strategy**:
```javascript
// Lines 52-77: Refresh functionality
test('should show loading states when refresh button is clicked', async () => {
  // Test loading indicators appear
  // Test API calls are made
  // Test data updates after fetch
});

// Lines 456-477: Import/Export error handling
test('should handle import errors gracefully', () => {
  // Test error state rendering
  // Test error message display
});

// Lines 494-579: Table sorting and rendering
test('should sort table columns when headers are clicked', () => {
  // Test ascending/descending sort
  // Test sort indicators
});

// Lines 592-618: Data validation and transformation
test('should validate and transform dashboard data', () => {
  // Test data normalization
  // Test missing data handling
});

// Lines 701-748: Panel collapse/expand and state management
test('should toggle panel visibility', () => {
  // Test collapse/expand animations
  // Test state persistence
});
```

### 2. import_service.py (36 lines) 🐍 PY

**Uncovered Lines**: 461-462, 736-737, 755-756, 759-762, 764, 893-901, 940, 943, 958-959, 999, 1002, 1010-1013, 1015, 1057, 1068-1070, 1090

**Test Strategy**:
```python
# Error handling paths
def test_import_with_invalid_file_format():
    # Test validation errors
    pass

# Edge cases
def test_import_with_empty_data():
    # Test empty row handling
    pass

# Rollback scenarios
def test_import_rollback_on_failure():
    # Test transaction rollback
    pass
```

### 3. static/panels.js (20 lines) 🟦 JS

**Uncovered Lines**: 19, 29, 34, 128, 136, 145, 154, 165, 181, 476-477, 498-499, 509-510, 522-523, 535-536, 672

**Test Strategy**:
```javascript
// Panel interactions
test('should handle panel toggle events', () => {
  // Test panel collapse/expand
});

// Dynamic content loading
test('should load panel content on demand', () => {
  // Test lazy loading
});
```

### 4. dashboard_service.py (16 lines) 🐍 PY

**Uncovered Lines**: 184-187, 196-199, 1012, 1014-1015, 1017, 1020, 1272-1274

**Test Strategy**:
```python
# Error scenarios
def test_dashboard_data_aggregation_with_missing_programs():
    # Test partial data handling
    pass

# Edge cases
def test_dashboard_with_no_active_term():
    # Test fallback behavior
    pass
```

### 5. database_sqlite.py (14 lines) 🐍 PY

**Uncovered Lines**: 329, 513, 699, 1141, 1143-1144, 1146, 1153-1154, 1157, 1162-1164, 1167

**Test Strategy**:
```python
# Database error handling
def test_connection_failure_handling():
    # Test connection errors
    pass

# Transaction rollback
def test_transaction_rollback_on_constraint_violation():
    # Test constraint errors
    pass
```

### 6-11. Remaining Files

Files with < 15 uncovered lines each:
- `api/routes/clo_workflow.py` (12 lines)
- `clo_workflow_service.py` (12 lines)
- `adapters/cei_excel_adapter.py` (7 lines)
- `static/bulk_reminders.js` (4 lines)
- `api_routes.py` (1 line)
- `static/program_dashboard.js` (1 line)

**Strategy**: Quick wins - target error paths and edge cases.

## Execution Plan

### Phase 1: JavaScript Coverage (Quick Win)
1. ✅ Browser exploration complete (institution_dashboard.js)
2. Add tests for `institution_dashboard.js` refresh functionality (lines 52-77)
3. Add tests for table sorting (lines 494-579)
4. Add tests for error handling (lines 456-477)

### Phase 2: Python Service Coverage
1. Add tests for `import_service.py` error paths
2. Add tests for `dashboard_service.py` edge cases
3. Add tests for `database_sqlite.py` failure scenarios

### Phase 3: Remaining Files
1. Quick tests for CLO workflow files
2. Final coverage verification
3. Re-run SonarCloud analysis

## Success Criteria
- Coverage drops from 211 to < 50 uncovered lines
- SonarCloud quality gate passes
- All tests meaningful (not just coverage-chasing)

## Browser Integration Learnings
- **Powerful for Discovery**: Immediately understood dashboard functionality
- **Live Debugging**: Saw loading states, API calls, and data flow in real-time
- **Test Design**: Observations directly informed test strategy
- **Future Use**: Can explore any UI feature to understand testing needs

## Next Steps
1. Start with `institution_dashboard.js` tests (biggest impact)
2. Run coverage after each batch of tests
3. Use browser integration to verify new features work as expected
4. Document any discovered bugs or issues

