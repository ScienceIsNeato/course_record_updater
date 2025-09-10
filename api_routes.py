"""
API Routes Module

This module defines the new REST API endpoints for the CEI Course Management System.
These routes provide a proper REST API structure while maintaining backward compatibility
with the existing single-page application.
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from typing import Dict, List, Optional, Any

# Import our services
from auth_service import login_required, permission_required, get_current_user, has_permission
from database_service_extended import (
    get_users_by_role, create_course, get_course_by_number, get_courses_by_department,
    create_term, get_term_by_name, get_active_terms,
    create_course_section, get_sections_by_instructor, get_sections_by_term
)
from import_service import import_excel, create_import_report

# Create API blueprint
api = Blueprint('api', __name__, url_prefix='/api')

# ========================================
# DASHBOARD ROUTES (Role-based views)
# ========================================

@api.route('/dashboard')
@login_required
def dashboard():
    """
    Role-based dashboard - returns different views based on user role
    """
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    role = user['role']
    
    if role == 'instructor':
        return render_template('dashboard/instructor.html', user=user)
    elif role == 'program_admin':
        return render_template('dashboard/program_admin.html', user=user)
    elif role == 'site_admin':
        return render_template('dashboard/site_admin.html', user=user)
    else:
        flash('Unknown user role. Please contact administrator.', 'danger')
        return redirect(url_for('index'))

# ========================================
# USER MANAGEMENT API
# ========================================

@api.route('/users', methods=['GET'])
@permission_required('manage_users')
def list_users():
    """
    Get list of users, optionally filtered by role
    
    Query parameters:
    - role: Filter by user role (optional)
    - department: Filter by department (optional)
    """
    try:
        role_filter = request.args.get('role')
        department_filter = request.args.get('department')
        
        if role_filter:
            users = get_users_by_role(role_filter)
        else:
            # TODO: Implement get_all_users function
            users = []
        
        # Filter by department if specified
        if department_filter and users:
            users = [u for u in users if u.get('department') == department_filter]
        
        return jsonify({
            'success': True,
            'users': users,
            'count': len(users)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/users', methods=['POST'])
@permission_required('manage_users')
def create_user():
    """
    Create a new user
    
    Request body should contain:
    - email: User's email address
    - first_name: User's first name
    - last_name: User's last name
    - role: User's role (instructor, program_admin, site_admin)
    - department: User's department (optional)
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validate required fields
        required_fields = ['email', 'first_name', 'last_name', 'role']
        missing_fields = [f for f in required_fields if not data.get(f)]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # TODO: Implement create_user in database_service_extended
        # user_id = create_user(data)
        user_id = "stub-user-id"  # Stub for now
        
        if user_id:
            return jsonify({
                'success': True,
                'user_id': user_id,
                'message': 'User created successfully'
            }), 201
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to create user'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/users/<user_id>', methods=['GET'])
@login_required
def get_user(user_id: str):
    """
    Get user details by ID
    
    Users can only view their own details unless they have manage_users permission
    """
    try:
        current_user = get_current_user()
        
        # Check permissions - users can view their own info, admins can view any
        if user_id != current_user['user_id'] and not has_permission('manage_users'):
            return jsonify({
                'success': False,
                'error': 'Permission denied'
            }), 403
        
        # TODO: Implement get_user_by_id function
        # user = get_user_by_id(user_id)
        user = None  # Stub for now
        
        if user:
            return jsonify({
                'success': True,
                'user': user
            })
        else:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========================================
# COURSE MANAGEMENT API
# ========================================

@api.route('/courses', methods=['GET'])
@login_required
def list_courses():
    """
    Get list of courses, optionally filtered by department
    
    Query parameters:
    - department: Filter by department (optional)
    """
    try:
        department_filter = request.args.get('department')
        
        if department_filter:
            courses = get_courses_by_department(department_filter)
        else:
            # TODO: Implement get_all_courses_v2 function
            courses = []
        
        return jsonify({
            'success': True,
            'courses': courses,
            'count': len(courses)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/courses', methods=['POST'])
@permission_required('manage_courses')
def create_course():
    """
    Create a new course
    
    Request body should contain:
    - course_number: Course number (e.g., "ACC-201")
    - course_title: Course title
    - department: Department name
    - credit_hours: Number of credit hours (optional, default 3)
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validate required fields
        required_fields = ['course_number', 'course_title', 'department']
        missing_fields = [f for f in required_fields if not data.get(f)]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        course_id = create_course(data)
        
        if course_id:
            return jsonify({
                'success': True,
                'course_id': course_id,
                'message': 'Course created successfully'
            }), 201
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to create course'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/courses/<course_number>', methods=['GET'])
@login_required
def get_course(course_number: str):
    """Get course details by course number"""
    try:
        course = get_course_by_number(course_number)
        
        if course:
            return jsonify({
                'success': True,
                'course': course
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Course not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========================================
# TERM MANAGEMENT API
# ========================================

@api.route('/terms', methods=['GET'])
@login_required
def list_terms():
    """Get list of active terms"""
    try:
        terms = get_active_terms()
        
        return jsonify({
            'success': True,
            'terms': terms,
            'count': len(terms)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/terms', methods=['POST'])
@permission_required('manage_terms')
def create_term_api():
    """
    Create a new academic term
    
    Request body should contain:
    - name: Term name (e.g., "2024 Fall")
    - start_date: Start date (YYYY-MM-DD)
    - end_date: End date (YYYY-MM-DD)
    - assessment_due_date: Assessment due date (YYYY-MM-DD)
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validate required fields
        required_fields = ['name', 'start_date', 'end_date', 'assessment_due_date']
        missing_fields = [f for f in required_fields if not data.get(f)]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        term_id = create_term(data)
        
        if term_id:
            return jsonify({
                'success': True,
                'term_id': term_id,
                'message': 'Term created successfully'
            }), 201
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to create term'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========================================
# COURSE SECTION MANAGEMENT API
# ========================================

@api.route('/sections', methods=['GET'])
@login_required
def list_sections():
    """
    Get list of course sections
    
    Query parameters:
    - instructor_id: Filter by instructor (optional)
    - term_id: Filter by term (optional)
    """
    try:
        instructor_id = request.args.get('instructor_id')
        term_id = request.args.get('term_id')
        
        current_user = get_current_user()
        
        # If no filters specified, determine default based on role
        if not instructor_id and not term_id:
            if current_user['role'] == 'instructor':
                # Instructors see only their own sections
                instructor_id = current_user['user_id']
            # Program admins and site admins see all sections (no filter)
        
        # Apply filters
        if instructor_id:
            sections = get_sections_by_instructor(instructor_id)
        elif term_id:
            sections = get_sections_by_term(term_id)
        else:
            # TODO: Implement get_all_sections function
            sections = []
        
        # Filter based on permissions
        if current_user['role'] == 'instructor' and not has_permission('view_all_sections'):
            # Ensure instructors only see their own sections
            sections = [s for s in sections if s.get('instructor_id') == current_user['user_id']]
        
        return jsonify({
            'success': True,
            'sections': sections,
            'count': len(sections)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/sections', methods=['POST'])
@permission_required('manage_courses')
def create_section():
    """
    Create a new course section
    
    Request body should contain:
    - course_id: Course ID
    - term_id: Term ID
    - section_number: Section number (optional, default "001")
    - instructor_id: Instructor ID (optional)
    - enrollment: Number of enrolled students (optional)
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validate required fields
        required_fields = ['course_id', 'term_id']
        missing_fields = [f for f in required_fields if not data.get(f)]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        section_id = create_course_section(data)
        
        if section_id:
            return jsonify({
                'success': True,
                'section_id': section_id,
                'message': 'Course section created successfully'
            }), 201
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to create course section'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========================================
# IMPORT API (New Excel Import System)
# ========================================

@api.route('/import/excel', methods=['POST'])
@permission_required('import_data')
def import_excel_api():
    """
    Import data from Excel file with conflict resolution
    
    Form data:
    - file: Excel file upload
    - conflict_strategy: "use_mine", "use_theirs", "merge", or "manual_review"
    - dry_run: "true" or "false" (optional, default false)
    - adapter_name: Import adapter to use (optional, default "cei_excel_adapter")
    """
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file uploaded'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        # Get parameters
        conflict_strategy = request.form.get('conflict_strategy', 'use_theirs')
        dry_run = request.form.get('dry_run', 'false').lower() == 'true'
        adapter_name = request.form.get('adapter_name', 'cei_excel_adapter')
        delete_existing_db = request.form.get('delete_existing_db', 'false').lower() == 'true'
        verbose = request.form.get('verbose_output', 'false').lower() == 'true'
        
        # Validate file type
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({
                'success': False,
                'error': 'Invalid file type. Only Excel files (.xlsx, .xls) are supported.'
            }), 400
        
        # Save uploaded file temporarily
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
            file.save(temp_file.name)
            temp_file_path = temp_file.name
        
        try:
            # Perform the import
            result = import_excel(
                file_path=temp_file_path,
                conflict_strategy=conflict_strategy,
                dry_run=dry_run,
                adapter_name=adapter_name,
                delete_existing_db=delete_existing_db,
                verbose=verbose
            )
            
            # Create response
            response_data = {
                'success': result.success,
                'dry_run': result.dry_run,
                'statistics': {
                    'records_processed': result.records_processed,
                    'records_created': result.records_created,
                    'records_updated': result.records_updated,
                    'records_skipped': result.records_skipped,
                    'conflicts_detected': result.conflicts_detected,
                    'conflicts_resolved': result.conflicts_resolved,
                    'execution_time': result.execution_time
                },
                'errors': result.errors,
                'warnings': result.warnings,
                'conflicts': [
                    {
                        'entity_type': c.entity_type,
                        'entity_key': c.entity_key,
                        'field_name': c.field_name,
                        'existing_value': str(c.existing_value),
                        'import_value': str(c.import_value),
                        'resolution': c.resolution
                    }
                    for c in result.conflicts[:50]  # Limit to first 50 conflicts
                ]
            }
            
            if result.success:
                return jsonify(response_data), 200
            else:
                return jsonify(response_data), 400
                
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/import/validate', methods=['POST'])
@permission_required('import_data')
def validate_import_file():
    """
    Validate Excel file format without importing
    
    Form data:
    - file: Excel file upload
    - adapter_name: Import adapter to use (optional, default "cei_excel_adapter")
    """
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file uploaded'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        # Get parameters
        adapter_name = request.form.get('adapter_name', 'cei_excel_adapter')
        
        # Validate file type
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({
                'success': False,
                'error': 'Invalid file type. Only Excel files (.xlsx, .xls) are supported.'
            }), 400
        
        # Save uploaded file temporarily
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
            file.save(temp_file.name)
            temp_file_path = temp_file.name
        
        try:
            # Perform dry run validation
            result = import_excel(
                file_path=temp_file_path,
                conflict_strategy='use_theirs',
                dry_run=True,  # Always dry run for validation
                adapter_name=adapter_name
            )
            
            # Create validation response
            validation_result = {
                'valid': result.success and len(result.errors) == 0,
                'records_found': result.records_processed,
                'potential_conflicts': result.conflicts_detected,
                'errors': result.errors,
                'warnings': result.warnings,
                'file_info': {
                    'filename': file.filename,
                    'adapter': adapter_name
                }
            }
            
            return jsonify({
                'success': True,
                'validation': validation_result
            })
                
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ========================================
# HEALTH CHECK API
# ========================================

@api.route('/health', methods=['GET'])
def health_check():
    """API health check endpoint"""
    return jsonify({
        'success': True,
        'status': 'healthy',
        'message': 'CEI Course Management API is running',
        'version': '2.0.0'
    })

# ========================================
# ERROR HANDLERS
# ========================================

@api.errorhandler(404)
def api_not_found(error):
    """Handle 404 errors for API routes"""
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@api.errorhandler(500)
def api_internal_error(error):
    """Handle 500 errors for API routes"""
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500
