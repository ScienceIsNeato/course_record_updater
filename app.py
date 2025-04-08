from flask import Flask, render_template, request, redirect, url_for
import os
import datetime
# from google.cloud import firestore # No longer needed here
import docx # Import python-docx library
from werkzeug.utils import secure_filename # For basic filename validation

# Import the database service (assuming it's in the root for now)
# If placed elsewhere, adjust the import path
import database_service
# Import Adapter components
from adapters.base_adapter import BaseAdapter, ValidationError

app = Flask(__name__)

# Allowed extension for upload
ALLOWED_EXTENSIONS = {'docx'}

# --- Firestore Client Initialization --- (REMOVED - Handled in database_service)
# try:
#     # Assumes GOOGLE_APPLICATION_CREDENTIALS environment variable is set.
#     # For local development, download a service account key and set the variable:
#     # export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/keyfile.json"
#     # Alternatively, initialize with explicit project ID if needed:
#     # db = firestore.Client(project='your-gcp-project-id')
#     db = firestore.Client()
#     print("Firestore client initialized successfully.")
# except Exception as e:
#     print(f"Error initializing Firestore client: {e}")
#     # Handle error appropriately - maybe exit or disable DB features
#     db = None # Ensure db is None if initialization fails

# Configuration ( Placeholder - Add Firestore setup later )
# app.config['SECRET_KEY'] = os.urandom(24)

# --- Data ( Firestore Functions ) --- (REMOVED - Handled in database_service)

# COURSES_COLLECTION = 'courses' # Define collection name

# def save_course_to_firestore(course_data):
#     """Saves course data dictionary to Firestore, adding a timestamp."""
#     if not db:
#         print("Firestore client not available. Cannot save data.")
#         return None # Indicate failure
#     try:
#         # Add a server timestamp for ordering/tracking
#         course_data['timestamp'] = firestore.SERVER_TIMESTAMP
#         # Add document to the collection. Firestore auto-generates the ID.
#         _, doc_ref = db.collection(COURSES_COLLECTION).add(course_data)
#         print(f"Course data saved with ID: {doc_ref.id}")
#         return doc_ref.id # Return the new document ID
#     except Exception as e:
#         print(f"Error saving course to Firestore: {e}")
#         return None

# def get_courses_from_firestore():
#     """Retrieves all courses from Firestore, ordered by timestamp descending."""
#     if not db:
#         print("Firestore client not available. Cannot retrieve data.")
#         return []
#     try:
#         courses_ref = db.collection(COURSES_COLLECTION)
#         # Order by timestamp, newest first
#         query = courses_ref.order_by('timestamp', direction=firestore.Query.DESCENDING)
#         docs = query.stream()

#         courses_list = []
#         for doc in docs:
#             course = doc.to_dict()
#             course['id'] = doc.id # Add the document ID to the dictionary
#             courses_list.append(course)
#         print(f"Retrieved {len(courses_list)} courses from Firestore.")
#         return courses_list
#     except Exception as e:
#         print(f"Error getting courses from Firestore: {e}")
#         return []

# --- Routes ---

@app.route('/')
def index():
    """Main page route, displays the form and the course data."""
    # Calls the service function (Verified: Already uses DB service)
    courses = database_service.get_all_courses()
    return render_template('index.html', courses=courses)

@app.route('/add_course_manual', methods=['POST'])
def add_course_manual():
    """Handles manual course addition via form submission."""
    adapter = BaseAdapter()
    try:
        # Validate form data using the adapter
        validated_data = adapter.parse_and_validate(request.form)

        # If validation succeeds, save to database via service
        if database_service.save_course(validated_data):
            print(f"Successfully added course: {validated_data.get('course_number', 'N/A')}")
            # TODO: Add flash success message
        else:
            print("Failed to save course to Firestore after validation.")
            # TODO: Add flash error message (DB error)

    except ValidationError as e:
        # Handle validation errors from the adapter
        print(f"Validation Error adding course: {e}")
        # TODO: Add flash error message(s) based on e
    except Exception as e:
        # Handle unexpected errors
        print(f"Unexpected Error adding course: {e}")
        # TODO: Add generic flash error message

    return redirect(url_for('index'))

def allowed_file(filename):
    """Checks if the filename has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handles file upload and basic text extraction."""
    selected_adapter = request.form.get('adapter_name', 'N/A')

    # Check if the post request has the file part
    if 'course_document' not in request.files:
        print("Error: No file part in request")
        # Flash message: "No file selected"
        return redirect(url_for('index'))

    file = request.files['course_document']

    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    if file.filename == '':
        print("Error: No selected file")
        # Flash message: "No file selected"
        return redirect(url_for('index'))

    if file and allowed_file(file.filename):
        try:
            # filename = secure_filename(file.filename) # Good practice, though not strictly needed here
            print(f"Processing uploaded file: {file.filename} with adapter: {selected_adapter}")

            # Read the file stream using python-docx
            document = docx.Document(file.stream)

            extracted_text = "\n".join([para.text for para in document.paragraphs])

            # --- Placeholder for actual parsing and saving ---            
            print("--- Extracted Text Start ---")
            print(extracted_text)
            print("--- Extracted Text End ---")
            # --------------------------------------------------

            # In a real scenario, you would now:
            # 1. Select the appropriate parsing function based on selected_adapter.
            # 2. Call the parsing function with the document or extracted_text.
            # 3. Validate the parsed data.
            # 4. Save the validated data using save_course_to_firestore().
            # 5. Provide feedback (flash message) to the user.

            print(f"Successfully processed basic text from {file.filename}")
            # Flash message: "File processed, basic text extracted (check logs)"

        except Exception as e:
            print(f"Error processing file {file.filename}: {e}")
            # Flash message: "Error processing file."
    else:
        print(f"Error: File type not allowed or file error. Filename: {file.filename}")
        # Flash message: "Invalid file type. Please upload a .docx file."

    return redirect(url_for('index'))

# @app.route('/edit/<int:course_id>', methods=['POST'])
# def edit_course(course_id):
#     """Handles editing an existing course."""
#     # Find course by id
#     # Update course data from request
#     # Save updated data (replace with Firestore update)
#     return redirect(url_for('index')) # Or return JSON status

# @app.route('/delete/<int:course_id>', methods=['POST'])
# def delete_course(course_id):
#     """Handles deleting a course."""
#     # Find course by id
#     # Perform delete confirmation (if needed on backend)
#     # Remove course (replace with Firestore delete)
#     return redirect(url_for('index')) # Or return JSON status


if __name__ == '__main__':
    # Use a default port or get from environment variable for deployment flexibility
    port = int(os.environ.get('PORT', 8080))
    # Set debug=True for development, False for production
    # Use host='0.0.0.0' to be accessible externally (e.g., in Docker/Cloud Run)
    app.run(debug=True, host='0.0.0.0', port=port) 