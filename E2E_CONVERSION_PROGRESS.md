# E2E Test Conversion Progress

**Goal:** Convert all 28 E2E tests from API-based to UI-based interactions

## ✅ Converted Tests (2/28)

### Institution Admin (2/10 done)
- ✅ **test_001**: Create program - Opens modal, fills name/short_name, submits
- ✅ **test_007**: Create term - Opens modal, fills name/dates, submits

## 📋 Pattern That Works

```python
# 1. Navigate to dashboard (fixture handles login)
authenticated_page.goto(f"{BASE_URL}/dashboard")
authenticated_page.wait_for_load_state("networkidle")

# 2. Click button to open modal
authenticated_page.click('button:has-text("Add X")')
authenticated_page.wait_for_selector("#createXModal", state="visible")

# 3. Fill form fields
authenticated_page.fill("#fieldId", "value")
authenticated_page.check("#checkboxId")  # if needed

# 4. Handle alert dialog (success message)
authenticated_page.once("dialog", lambda dialog: dialog.accept())

# 5. Submit and verify
authenticated_page.click('#createXForm button[type="submit"]')
authenticated_page.wait_for_selector("#createXModal", state="hidden", timeout=5000)
```

## 🚧 Remaining Tests (26/28)

### Institution Admin (8 more)
- test_002: Update course ⚠️ Needs course list UI
- test_003: Delete program ⚠️ Needs program list UI  
- test_004: Cannot delete program with courses ⚠️ Needs program list UI
- test_005: Invite instructor ⚠️ Needs invite UI
- test_006: Manage institution users ⚠️ Needs user list UI
- test_008: Create course offerings ⚠️ Needs dropdown population
- test_009: Assign instructors to sections ⚠️ Needs section list UI
- test_010: Cannot access other institutions ⚠️ Needs multi-inst test

### Instructor (4 tests)
- test_001-004: TBD (need to review)

### Program Admin (6 tests)
- test_001-006: TBD (need to review)

### Site Admin (8 tests)
- test_001-008: TBD (need to review)

### Others (6 tests)
- test_import_export.py
- test_csv_roundtrip.py

## 🔧 UI Gaps Identified

1. **List/Management UIs needed:**
   - Program list (view, edit, delete)
   - Course list (view, edit, delete)
   - User list (view, edit, delete)
   - Section list (view, edit, assign instructor)

2. **Dropdown population needed:**
   - Offering modal: course dropdown, term dropdown
   - Section modal: offering dropdown, instructor dropdown

3. **DOMContentLoaded race condition:**
   - Fixed in: programManagement.js
   - Needs fix in: offeringManagement.js, sectionManagement.js, others

## 🎯 Next Steps

1. **Quick wins**: Convert tests that use existing CREATE modals
   - Course creation (if modal exists)
   - Section creation (if modal exists)
   - Outcome creation (if modal exists)

2. **Implement dropdown population**: Add modal listeners to fetch and populate dropdowns when modals open

3. **Implement list UIs**: Build simple tables with edit/delete buttons for entities that need them

4. **Apply DOMContentLoaded fix**: Update all management JS files to avoid race condition

## 💡 Key Learnings

- Console error monitoring = debug superpower
- Zero-tolerance policy catches issues immediately  
- DOMContentLoaded race condition was blocking form submission
- Fix race condition: Check `document.readyState` before adding listener
- Pattern is repeatable and works beautifully!
