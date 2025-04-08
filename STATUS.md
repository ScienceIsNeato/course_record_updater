# Project Status: Course Record Updater

**Last Updated:** $(date +%Y-%m-%d\ %H:%M:%S)

## Overall Progress

*   **Current Phase:** Refactoring & Foundation (Manual Flow)
*   **Next Major Goal:** Implement the Database Service module.

## Milestones (Revised Plan)

*(Current focus marked with `->`)*

1.  **[X] Project Definition & Documentation Setup**
    *   [X] Create `PROJECT_OVERVIEW.md`
    *   [X] Create `STATUS.md`
    *   [X] Define initial milestones.
    *   [X] **Refine architecture:** Separate DB logic, define new endpoints, emphasize TDD.
2.  **[X] Basic Flask Application Setup**
    *   [X] Initialize Flask project structure.
    *   [X] Create `requirements.txt`.
    *   [X] Set up basic Flask routing for `/`.
    *   [X] Create basic `index.html` template.
3.  **[X] UI Mockup - Input Areas**
    *   [X] Implement HTML form for manual entry (pointing to `/add_course_manual`).
    *   [X] Implement HTML form for file upload (pointing to `/add_course_automatic`).
    *   [X] Basic CSS styling.
4.  **[X] UI Mockup - Display Area**
    *   [X] Implement HTML table structure.
    *   [X] Add placeholder Edit/Delete buttons.
    *   [X] Style table.

--- (Refactoring Point) ---

5.  **[->] Database Service Module**
    *   [ ] Create a new module (e.g., `database_service.py`).
    *   [ ] Move Firestore client initialization into this module.
    *   [ ] Implement `save_course(course_data)` function (adds timestamp, saves to Firestore).
    *   [ ] Implement `get_all_courses()` function (retrieves all, orders by timestamp).
    *   [ ] Add basic unit tests for these functions (requires mocking Firestore client).
6.  **[ ] Base Adapter Implementation**
    *   [ ] Create `adapters/base_adapter.py`.
    *   [ ] Define `BaseAdapter` class.
    *   [ ] Implement `parse_and_validate(form_data)` method:
        *   Takes form data (dictionary).
        *   Performs type checking/conversion (e.g., year/students to int).
        *   Validates required fields.
        *   Returns standardized, validated data dictionary on success, or raises/returns error indication on failure.
    *   [ ] Add unit tests for `parse_and_validate`.
7.  **[ ] Integrate Manual Flow (/add_course_manual)**
    *   [ ] Rename `/add` route in `app.py` to `/add_course_manual` (ensure method is POST).
    *   [ ] Update the route handler:
        *   Instantiate `BaseAdapter`.
        *   Call `adapter.parse_and_validate(request.form)`.
        *   If successful, call `database_service.save_course(validated_data)`.
        *   Handle errors from adapter or DB service (e.g., print, flash message later).
        *   Redirect to index.
    *   [ ] Update `/` route handler in `app.py` to use `database_service.get_all_courses()`.
    *   [ ] Update `index.html` form action to point to `/add_course_manual`.
    *   [ ] Add integration tests for the manual add workflow.

--- (Manual Flow Complete) ---

8.  **[ ] File Adapter Interface/Dispatcher**
    *   [ ] Create `adapters/file_adapter_interface.py` (or similar).
    *   [ ] Define class (e.g., `FileAdapterDispatcher`) maybe inheriting/using `BaseAdapter` for common validation.
    *   [ ] Implement logic to discover specific file adapters (e.g., in `adapters/` dir).
    *   [ ] Implement `process_file(document, adapter_name)` method:
        *   Dynamically load the specific adapter module based on `adapter_name`.
        *   Call the specific adapter's `parse(document)` function.
        *   Potentially call common validation from `BaseAdapter`.
        *   Return validated data or error.
    *   [ ] Add unit tests for discovery and dispatching (mocking specific adapters).
9.  **[ ] Dummy File Adapter (`dummy_adapter.py`)**
    *   [ ] Re-create/Verify `adapters/dummy_adapter.py`.
    *   [ ] Ensure it has the `parse(document)` function.
    *   [ ] Returns a dictionary matching expected fields.
    *   [ ] Add unit tests for the dummy parser.
10. **[ ] Integrate Automatic Flow (/add_course_automatic)**
    *   [ ] Rename `/upload` route to `/add_course_automatic` (ensure method is POST).
    *   [ ] Update the route handler:
        *   Perform file validation (presence, type).
        *   Instantiate `FileAdapterDispatcher`.
        *   Call `dispatcher.process_file(docx.Document(file.stream), adapter_name)`.
        *   If successful, call `database_service.save_course(validated_data)`.
        *   Handle errors.
        *   Redirect to index.
    *   [ ] Update `index.html` file upload form action.
    *   [ ] Add integration tests for the dummy file upload workflow.
11. **[ ] UI - Edit/Delete Functionality**
    *   [ ] Implement JavaScript for actions.
    *   [ ] Create Flask endpoints for Update/Delete.
    *   [ ] Implement corresponding functions in `database_service.py`.
    *   [ ] Integrate endpoints with DB service.
    *   [ ] Add tests.
12. **[ ] Adapter Implementation (Iterative)**
    *   [ ] Create `adapter_v1.py`.
    *   [ ] Implement parsing logic for the first real format.
    *   [ ] Add tests.
    *   [ ] Repeat...
13. **[ ] Deployment Setup (Google Cloud Run)**
    *   [ ] Create `Dockerfile`.
    *   [ ] Configure deployment.
    *   [ ] Deploy.

---

## Current Focus: Milestone 5 - Database Service Module

**Objective:** Create a dedicated module (`database_service.py`) to encapsulate all Firestore interactions, improving separation of concerns and testability.

**Tasks:**
*   Create `database_service.py`.
*   Move Firestore client initialization from `app.py` to `database_service.py`.
*   Implement `save_course(course_data)` function in the service.
*   Implement `get_all_courses()` function in the service.
*   Write initial unit tests for these service functions (mocking the Firestore client is essential here).
*   Remove Firestore-specific code from `app.py` (it will call the service later).

**Testing Note:** Rigorous testing (unit & integration) is critical. Confirm changes by running tests after each modification. 