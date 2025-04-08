# Project Status: Course Record Updater

**Last Updated:** $(date +%Y-%m-%d\ %H:%M:%S)

## Overall Progress

*   **Current Phase:** UI/UX Enhancements (Edit/Delete)
*   **Next Major Goal:** Implement inline editing and deletion of records.

## Milestones (Revised Plan)

*(Current focus marked with `->`)*

1.  **[X] Project Definition & Documentation Setup**
    *   [X] Create `PROJECT_OVERVIEW.md`
    *   [X] Create `STATUS.md`
    *   [X] Define initial milestones.
    *   [X] Refine architecture: Separate DB logic, define new endpoints, emphasize TDD.
2.  **[X] Basic Flask Application Setup**
    *   [X] Initialize Flask project structure.
    *   [X] Create `requirements.txt` (incl. testing deps).
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

5.  **[X] Database Service Module**
    *   [X] Create `database_service.py`.
    *   [X] Move Firestore client initialization into this module.
    *   [X] Implement `save_course(course_data)` function.
    *   [X] Implement `get_all_courses()` function.
    *   [X] Add basic unit tests for these functions (mocking Firestore).
    *   [X] Remove old Firestore code from `app.py`.
6.  **[X] Base Adapter Implementation**
    *   [X] Create `adapters/base_adapter.py`.
    *   [X] Define `BaseAdapter` class.
    *   [X] Implement `parse_and_validate(form_data)` method.
    *   [X] Add unit tests for `parse_and_validate`.
7.  **[X] Integrate Manual Flow (/add_course_manual)**
    *   [X] Rename `/add` route in `app.py` to `/add_course_manual`.
    *   [X] Update the route handler to use `BaseAdapter` and `database_service`.
    *   [X] Update `/` route handler to use `database_service`.
    *   [X] Update `index.html` form action.
    *   [ ] Add integration tests for the manual add workflow (Skipped for now).

--- (Manual Flow Complete) ---

8.  **[X] File Adapter Interface/Dispatcher**
    *   [X] Create `adapters/file_adapter_dispatcher.py`.
    *   [X] Define `FileAdapterDispatcher` class.
    *   [X] Implement adapter discovery logic.
    *   [X] Implement `process_file(document, adapter_name)` method with dynamic loading.
    *   [X] Add unit tests for discovery and dispatching.
9.  **[X] Dummy File Adapter (`dummy_adapter.py`)**
    *   [X] Re-create/Verify `adapters/dummy_adapter.py`.
    *   [X] Ensure it has the `parse(document)` function.
    *   [X] Returns a dictionary matching expected fields (strings for validation).
    *   [X] Add unit tests for the dummy parser.
10. **[X] Integrate Automatic Flow (/add_course_automatic)**
    *   [X] Rename `/upload` route to `/add_course_automatic`.
    *   [X] Update the route handler to use `FileAdapterDispatcher` and `database_service`.
    *   [X] Update `index.html` file upload form action.
    *   [ ] Add integration tests for the dummy file upload workflow (Skipped for now).
11. **[->] UI - Edit/Delete Functionality**
    *   [ ] Implement JavaScript for inline editing.
    *   [ ] Implement JavaScript for delete confirmation prompt.
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

## Current Focus: Milestone 11 - UI - Edit/Delete Functionality

**Objective:** Implement the client-side (JavaScript) and backend (Flask routes, DB service functions) logic needed to allow users to edit course records inline and delete them with confirmation.

**Tasks:**
*   **Database Service:**
    *   Implement `update_course(course_id: str, updated_data: dict)` in `database_service.py`.
    *   Implement `delete_course(course_id: str)` in `database_service.py`.
    *   Add unit tests for these new DB service functions (mocking Firestore).
*   **Flask Backend:**
    *   Create a new route `/edit_course/<string:course_id>` (e.g., method PUT or POST) in `app.py`.
    *   Handler should receive updated data (likely JSON from JS), validate it (perhaps using `BaseAdapter`), and call `database_service.update_course()`.
    *   Create a new route `/delete_course/<string:course_id>` (e.g., method DELETE or POST) in `app.py`.
    *   Handler should call `database_service.delete_course()`.
    *   Return appropriate JSON responses (success/error) from these endpoints.
    *   Add tests for these routes (likely integration tests mocking the DB service).
*   **Frontend JavaScript:**
    *   Create a `static/script.js` file and link it in `index.html`.
    *   Add event listeners to the "Edit" buttons:
        *   On click, make the table row's cells editable (e.g., replace `<td>` content with `<input>`).
        *   Add a "Save" and "Cancel" button to the row.
        *   On "Save", collect data from inputs, send an asynchronous request (e.g., `fetch` API) to the `/edit_course/...` endpoint.
        *   Handle success/error response (update UI, revert inputs on error).
        *   On "Cancel", revert changes.
    *   Add event listeners to the "Delete" buttons:
        *   On click, show a confirmation dialog (e.g., `window.confirm` or custom modal) maybe asking to type the course number (as originally requested).
        *   If confirmed, send an asynchronous request to the `/delete_course/...` endpoint.
        *   Handle success/error (remove row from table on success).

**Testing Note:** Unit test DB functions. Integration test Flask routes. Manually test the UI interactions thoroughly. 