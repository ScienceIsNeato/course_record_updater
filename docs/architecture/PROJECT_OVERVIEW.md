# Project Overview: Course Record Updater

**Version:** 0.1 (Initial Draft)

## 1. Goal

To replace the manual, error-prone process of transferring course information from various Word documents into a central Excel spreadsheet with a streamlined web application.

## 2. Problem Statement

Instructors submit course details in Word documents with inconsistent formatting each semester. A manual process is required to extract this data and update a central record (Excel), which is time-consuming and susceptible to errors.

## 3. Proposed Solution

A web application built with Python (Flask) that allows:
*   **Manual Entry:** Direct input of course details via a web form.
*   **Automated Extraction:** Uploading Word documents (`.docx`) and selecting a corresponding format "adapter" to automatically parse and extract the course information.
*   **Centralized Viewing/Editing:** Displaying all course records in a searchable/sortable ledger format, with options to edit or delete entries.

## 4. Key Components

*   **Frontend (Web UI):**
    *   Built using Flask templates (HTML, CSS, JavaScript).
    *   Provides interface for:
        *   File Upload (`/add_course_automatic` endpoint): Word document + Adapter selection dropdown.
        *   Manual Data Entry Form (`/add_course_manual` endpoint).
        *   Tabular Display of Course Records (Ledger style, reverse chronological).
        *   Inline Edit / Delete functionality per record (Future Milestone).
*   **Backend (API - Flask):**
    *   Flask application serving the UI and handling data operations.
    *   Endpoints for:
        *   `/` (GET): Display main page with forms and data.
        *   `/add_course_manual` (POST): Handle manual form submission.
        *   `/add_course_automatic` (POST): Handle Word document upload and trigger parsing.
        *   CRUD endpoints for Edit/Delete (Future Milestone).
*   **Adapters (`adapters/` package):**
    *   Responsible for **parsing and validating** input data into a standardized dictionary format.
    *   `BaseAdapter`: Handles parsing/validation for data common to all sources (e.g., field types, required checks), primarily used by the manual flow.
    *   `FileAdapterInterface` (or similar dispatcher): Handles file-specific initial processing and dispatches to specific file format adapters.
    *   Specific File Adapters (e.g., `adapter_v1.py`): Contain logic to parse unique `.docx` layouts.
    *   Adapters **do not** directly interact with the database.
*   **Database Service/Handler:**
    *   Separate component/module responsible for all interactions with SQLite via SQLAlchemy.
    *   Provides functions like `save_course`, `get_all_courses`, `update_course`, `delete_course`.
    *   Called by the Flask endpoint handlers *after* remockuving validated data from an adapter.
*   **Database:**
    *   SQLite (SQLAlchemy ORM).
    *   Flexible schema, free tier, GCP integration.

## 5. Technical Stack

*   **Language:** Python 3
*   **Web Framework:** Flask
*   **Database:** SQLite (SQLAlchemy ORM)
*   **DB Interaction:** `google-cloud-firestore` library (via Database Service)
*   **Word Document Parsing:** `python-docx` library (within Adapters)
*   **Frontend:** HTML, CSS, JavaScript (via Flask Templates)
*   **Testing Framework:** `pytest` (Recommended)
*   **Hosting:** Google Cloud Run

## 6. Core Workflow (Revised)

1.  User accesses the web application URL.
2.  **Input:**
    *   **Manual:** User fills the manual entry form and submits (POST to `/add_course_manual`).
    *   **Automatic:** User uploads a `.docx` file, selects the matching adapter, and submits (POST to `/add_course_automatic`).
3.  **Processing (Handler + Adapter):**
    *   The corresponding Flask route handler receives the request.
    *   The handler calls the appropriate adapter (`BaseAdapter` for manual, `FileAdapterInterface` -> specific file adapter for automatic).
    *   The adapter attempts to parse and validate the input (form data or file content) into a standard dictionary.
    *   The adapter returns the validated dictionary or an error indication to the handler.
4.  **Storage (Handler + DB Service):**
    *   If the adapter returned valid data, the handler calls the Database Service (e.g., `save_course(validated_data)`).
    *   The Database Service interacts with SQLite to persist the data.
5.  **Display:** The user is redirected back to the main page (`/`). The index route fetches the latest data via the Database Service and renders the updated table.
6.  **Management:** Future milestones for Edit/Delete will follow a similar pattern (fetch -> display -> user action -> handler -> adapter (maybe for validation) -> DB service -> redirect/update).

## 7. Development Philosophy & Testing

*   **Test-Driven Development (TDD):** Development should follow TDD principles where feasible. Write tests *before* writing implementation code (Red-Green-Refactor cycle).
*   **Mandatory Testing:** All code modifications (source code, test code, configuration) **must** be followed by running relevant tests (unit, integration) to ensure correctness and prevent regressions.
*   **Separation of Concerns:** The architecture emphasizes separating parsing/validation (Adapters) from persistence (Database Service) to enhance testability and maintainability.
*   **Incremental Development:** Focus on delivering functionality in small, well-tested milestones, starting with the core manual entry flow.

## 8. Assumptions & Scope (v0.2)

*   **No Authentication:** The initial version will be publicly accessible without login.
*   **Single Data Store:** All data resides in a single SQLite database file.
*   **Adapter Focus:** Build the framework first, then specific adapters iteratively.
*   **Deployment:** Target platform is Google Cloud Run.
