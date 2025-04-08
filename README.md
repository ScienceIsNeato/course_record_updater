# Course Record Updater

A simple Flask web application to manage course records, intended to replace manual entry from Word documents.

## Features

*   Manual entry of course details via a web form.
*   Upload of `.docx` files for automatic data extraction (using format-specific adapters).
*   Display of course records in a table.
*   Inline editing and deletion of records.
*   Persistence using Google Cloud Firestore.

## Project Structure

```
.
├── adapters/             # Modules for parsing different input formats
│   ├── __init__.py
│   ├── base_adapter.py     # Base validation/parsing logic
│   ├── dummy_adapter.py    # Example file adapter
│   └── file_adapter_dispatcher.py # Handles loading specific file adapters
├── static/               # Static files (CSS, JavaScript)
│   └── script.js
├── templates/            # Flask HTML templates
│   └── index.html
├── tests/                # Unit and integration tests
│   ├── __init__.py
│   ├── test_base_adapter.py
│   ├── test_database_service.py
│   ├── test_dummy_adapter.py
│   └── test_file_adapter_dispatcher.py
├── .gitignore            # Git ignore file
├── app.py                # Main Flask application
├── database_service.py   # Handles Firestore interactions
├── PROJECT_OVERVIEW.md   # High-level project goals and architecture
├── README.md             # This file
├── requirements.txt      # Python dependencies
├── STATUS.md             # Current development status and milestones
└── venv/                 # Python virtual environment (if created)
```

## Setup and Running

1.  **Prerequisites:**
    *   Python 3 (tested with 3.13, adjust as needed)
    *   Google Cloud SDK (`gcloud`) installed and configured (for Firestore access)
    *   Credentials for Google Cloud Firestore (set up via `GOOGLE_APPLICATION_CREDENTIALS` environment variable or service account/default login).

2.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd course_record_updater
    ```

3.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate 
    # On Windows use `venv\Scripts\activate`
    ```

4.  **Install dependencies:**
    ```bash
    python -m pip install -r requirements.txt
    ```

5.  **Set Google Application Credentials:**
    Make sure the `GOOGLE_APPLICATION_CREDENTIALS` environment variable points to your service account key file, or that you are logged in via `gcloud auth application-default login`.
    ```bash
    # Example for service account key:
    export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/keyfile.json"
    ```

6.  **Run the application:**
    ```bash
    python app.py
    ```
    The application should be accessible at `http://localhost:8080` (or the port specified by the `PORT` environment variable).

## Running Tests

1.  Ensure the virtual environment is activated and dependencies are installed.
2.  **Unit Tests:** Run tests that mock external services:
    ```bash
    python -m pytest
    ```
3.  **Integration Tests (Requires Firestore Emulator):**

    **--> IMPORTANT: The Firestore emulator MUST be running in a separate terminal before executing these tests. <--**

    *   **Install Emulator:** If you haven't already, install the emulator component:
        ```bash
        gcloud components install cloud-firestore-emulator
        ```
    *   **Run Emulator:** In a **separate terminal window**, navigate to your project directory (optional but good practice) and start the emulator. Note the host and port it outputs (usually `localhost:8086` or similar).
        ```bash
        # In Terminal 1 (Leave this running):
        gcloud beta emulators firestore start --host-port=localhost:8086 
        ```
    *   **Set Environment Variable & Run Tests:** In the **original terminal** (where your venv is active), set the `FIRESTORE_EMULATOR_HOST` variable and run pytest. The tests should automatically connect to the running emulator.
        ```bash
        # In Terminal 2 (Your testing terminal):
        export FIRESTORE_EMULATOR_HOST="localhost:8086"
        python -m pytest 
        # Or, combining the export and run:
        # FIRESTORE_EMULATOR_HOST="localhost:8086" python -m pytest
        
        # Optionally run only integration tests if tagged:
        # FIRESTORE_EMULATOR_HOST="localhost:8086" python -m pytest -m integration
        ```
    *   **Stopping the Emulator:** When finished, go back to Terminal 1 and press `Ctrl+C` to stop the emulator process.

## Development Notes

*   This project uses Flask, Firestore, and python-docx.
*   Follow TDD principles where possible.
*   Run tests after any code changes.
*   See `PROJECT_OVERVIEW.md` for architecture details.
*   See `STATUS.md` for current development progress. 