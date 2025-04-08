from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import os
import docx # Import python-docx library

# Import functions directly from database_service
from database_service import (
    save_course,
    get_all_courses,
    update_course,
    delete_course as delete_course_db,
    db as database_client # Import the client as well
)
# Import Adapter components
from adapters.base_adapter import BaseAdapter, ValidationError, ALLOWED_TERMS
# Import file adapter dispatcher components
from adapters.file_adapter_dispatcher import FileAdapterDispatcher, DispatcherError

app = Flask(__name__)

# Allowed extension for upload
ALLOWED_EXTENSIONS = {'docx'}

# --- Secret Key Configuration ---
# IMPORTANT: In a production environment, use a strong, environment-variable-based secret key.
# For local development, a simple key is acceptable, but avoid hardcoding sensitive keys.
# You can generate a good key using: python -c 'import os; print(os.urandom(24))'
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key') # Use environment variable or fallback

# --- Firestore Configuration --- (REMOVED - Handled by database_service.py)
# The database_service module now initializes the client.
# We can check if it succeeded by checking the imported `database_client`.
if database_client is None:
    print("ERROR: database_service failed to initialize Firestore client. Database operations will fail.")
    # Application might need to decide how to handle this (e.g., show error page, disable features)

# --- Service Initialization --- (REMOVED - No class to instantiate)

# Initialize the form adapter (still needed)
form_adapter = BaseAdapter()

# --- Routes ---

@app.route('/')
def index():
    """Render the main page with the course list and entry form."""
    courses = [] # Default to empty list
    if database_client is None:
        flash("Error: Database service is not available. Check Firestore connection.", "error")
    else:
        try:
            # Call the imported function directly
            courses = get_all_courses()
        except Exception as e:
            flash(f"Error fetching courses: {e}", "error")
            # courses remains empty
    # Pass ALLOWED_TERMS to the template context
    # Also pass an empty form_data dict for initial load
    return render_template('index.html', courses=courses, allowed_terms=ALLOWED_TERMS, form_data={})

@app.route('/add', methods=['POST'])
def add_course():
    """Handle the submission of the new course form."""
    if database_client is None:
        flash("Error: Cannot add course, database service is unavailable.", "error")
        return redirect(url_for('index'))

    form_data = request.form.to_dict()
    try:
        validated_data = form_adapter.parse_and_validate(form_data)

        # Clean up optional None fields before saving
        if 'num_students' in validated_data and validated_data['num_students'] is None:
            del validated_data['num_students']
        for grade_field in BaseAdapter.GRADE_FIELDS:
            if grade_field in validated_data and validated_data[grade_field] is None:
                del validated_data[grade_field]

        # Call the imported function directly
        course_id = save_course(validated_data)
        if course_id:
            flash(f"Course '{validated_data['course_title']}' added successfully with ID: {course_id}", "success")
        else:
            flash("Error: Failed to save course to the database.", "error")

    except ValidationError as e:
        # Format the error message for better display
        error_list = str(e).split('; ') # Split the combined error string
        formatted_message = "Please fix the following issues:<br><ul>"
        for error in error_list:
            formatted_message += f"<li>{error}</li>"
        formatted_message += "</ul>"
        # Flash with 'danger' category for red alert
        flash(formatted_message, "danger")
        # Re-render the form with existing data and errors
        try:
            # Fetch courses again for the template
            courses = get_all_courses()
        except Exception as fetch_e:
            flash(f"Error fetching courses while handling validation error: {fetch_e}", "error")
            courses = []
        # Pass the original form_data back to the template
        return render_template('index.html', courses=courses, allowed_terms=ALLOWED_TERMS, form_data=form_data)
    except Exception as e:
        flash(f"An error occurred while adding the course: {e}", "error")
        return redirect(url_for('index'))

    return redirect(url_for('index'))

@app.route('/edit_course/<string:course_id>', methods=['PUT', 'POST']) # Allow POST for form/JS compatibility
def edit_course(course_id):
    """Handles updating an existing course via JSON data."""
    if database_client is None:
        return jsonify({"error": "Database service unavailable"}), 503 # Service Unavailable

    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    update_data = request.get_json()
    if not update_data:
         return jsonify({"error": "No data provided"}), 400

    # Optional: Add partial validation logic here if needed

    # Call the imported function directly
    if update_course(course_id, update_data):
        return jsonify({"success": True, "message": "Course updated successfully"}), 200
    else:
        # Consider more specific error codes if database_service provided them
        return jsonify({"error": "Failed to update course"}), 500

@app.route('/delete_course/<string:course_id>', methods=['DELETE', 'POST']) # Allow POST for form/JS compatibility
def delete_course(course_id):
    """Handles deleting a course."""
    if database_client is None:
        return jsonify({"error": "Database service unavailable"}), 503

    # Optional: Add confirmation logic here

    # Call the imported function directly
    if delete_course_db(course_id):
        return jsonify({"success": True, "message": "Course deleted successfully"}), 200
    else:
        # Consider 404 if ID not found vs 500 for other errors
        return jsonify({"error": "Failed to delete course"}), 500

def allowed_file(filename):
    """Checks if the filename has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/add_course_automatic', methods=['POST'])
def add_course_automatic():
    """Handles file upload, dispatches, validates, checks duplicates, and saves data."""
    selected_adapter_name = request.form.get('adapter_name')
    courses = []
    upload_results = {"success": [], "duplicate": [], "failed": []} # Store results
    
    if database_client is None:
        flash("Error: Database service unavailable, cannot process upload.", "error")
        return redirect(url_for('index'))

    try:
        courses = get_all_courses()
    except Exception as fetch_e:
        flash(f"Error fetching courses: {fetch_e}", "error")

    file = request.files.get('course_document')

    # Basic checks - re-render template on error
    error_message = None
    if not file or file.filename == '':
        error_message = "No file selected."
    elif not selected_adapter_name:
        error_message = "No document format/adapter selected."
    elif not allowed_file(file.filename):
        error_message = f"File type not allowed ('{file.filename}'). Only .docx is permitted."

    if error_message:
        flash(f"Please fix the following issues:<br><ul><li>{error_message}</li></ul>", "danger")
        return render_template('index.html', courses=courses, allowed_terms=ALLOWED_TERMS, form_data={}, selected_adapter_name=selected_adapter_name, upload_results=None)

    # --- Processing Logic ---
    try:
        print(f"Processing uploaded file: {file.filename} with adapter: {selected_adapter_name}")
        document = docx.Document(file.stream)

        dispatcher = FileAdapterDispatcher(use_base_validation=True)
        validated_data_list = dispatcher.process_file(document, selected_adapter_name)
        
        if not validated_data_list:
             flash(f"Warning: Adapter '{selected_adapter_name}' parsed 0 records from {file.filename}.", "warning")
             # Render with empty results instead of redirecting
             return render_template('index.html', courses=courses, allowed_terms=ALLOWED_TERMS, form_data={}, selected_adapter_name=selected_adapter_name, upload_results=upload_results)
             
        # --- Save multiple courses --- 
        for course_data in validated_data_list:
            course_identifier = f"{course_data.get('course_number', 'N/A')} ({course_data.get('term', 'N/A')})"
            save_result = save_course(course_data)
            
            if isinstance(save_result, str) and save_result.startswith("DUPLICATE:"):
                existing_id = save_result.split(":", 1)[1]
                upload_results["duplicate"].append(f"{course_identifier} (Already exists: ID {existing_id})")
            elif save_result: # Successfully saved, got new ID
                upload_results["success"].append(f"{course_identifier} (New ID: {save_result})")
            else: # Failed to save for other reasons
                upload_results["failed"].append(f"{course_identifier}")
        
        # Flash summary messages (optional, as detailed results are passed)
        # if upload_results["success"]: flash(f"Successfully saved {len(upload_results['success'])} new course(s).", "success")
        # if upload_results["duplicate"]: flash(f"Skipped {len(upload_results['duplicate'])} duplicate course(s).", "warning")
        # if upload_results["failed"]: flash(f"Failed to save {len(upload_results['failed'])} course(s).", "danger")
        
        # Re-fetch courses to show updated list
        courses = get_all_courses() 
        # Render template with results
        return render_template('index.html', courses=courses, allowed_terms=ALLOWED_TERMS, form_data={}, selected_adapter_name=selected_adapter_name, upload_results=upload_results)

    # --- Error Handling (Re-render with results/errors) ---
    except (DispatcherError, ValidationError) as e:
        error_list = str(e).split('; ')
        formatted_message = "Processing Error:<br><ul>"
        for error in error_list:
            formatted_message += f"<li>{error}</li>"
        formatted_message += "</ul>"
        flash(formatted_message, "danger")
        return render_template('index.html', courses=courses, allowed_terms=ALLOWED_TERMS, form_data={}, selected_adapter_name=selected_adapter_name, upload_results=None)
    
    except Exception as e:
        flash(f"Unexpected Error processing file {file.filename}:<br><ul><li>{e}</li></ul>", "danger")
        print(f"Unexpected Error details: {e}")
        return render_template('index.html', courses=courses, allowed_terms=ALLOWED_TERMS, form_data={}, selected_adapter_name=selected_adapter_name, upload_results=None)

if __name__ == '__main__':
    # Use PORT environment variable if available (common in deployment), otherwise default to 8080
    port = int(os.environ.get('PORT', 8080))
    # Debug mode should be controlled by FLASK_DEBUG environment variable
    # Setting debug=True directly is suitable for local development but not recommended for production
    use_debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    print(f"INFO: Starting Flask server on port {port} with debug mode: {use_debug}")
    app.run(host='0.0.0.0', port=port, debug=use_debug) 