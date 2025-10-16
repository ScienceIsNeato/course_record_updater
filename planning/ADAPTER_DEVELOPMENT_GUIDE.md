# Adapter Development Guide

## Overview

This guide provides comprehensive instructions for developing custom import/export adapters for the Course Record Updater system. Each adapter is purpose-built for a specific institution's data formats and requirements.

## Adapter Development Process

### 1. Institution Request Workflow

#### Initial Request
1. **Institution Admin Contact**: Institution administrator contacts system developer
2. **Data Sample Provision**: Institution provides sample data files in their format
3. **Requirements Analysis**: Developer analyzes data structure, business rules, and use cases
4. **Scope Definition**: Define what data types the adapter will handle (courses, students, faculty, etc.)

#### Sample Data Analysis
```python
# Example analysis of institution data
sample_analysis = {
    "file_format": ".xlsx",
    "data_types_detected": ["courses", "faculty", "assessments"],
    "column_structure": {
        "course_identifier": "Course_Code",
        "course_title": "Course_Name", 
        "instructor": "Faculty_Name",
        "term": "Academic_Term",
        "enrollment": "Student_Count"
    },
    "business_rules": {
        "course_code_format": "^[A-Z]{2,4}[0-9]{3,4}$",
        "term_format": "FA2024, SP2025, SU2025",
        "required_fields": ["Course_Code", "Course_Name", "Academic_Term"]
    }
}
```

### 2. Adapter Architecture

#### Base Adapter Interface
All adapters must inherit from `BaseAdapter` and implement required methods:

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Tuple
from pathlib import Path

class BaseAdapter(ABC):
    """Base class for all import/export adapters"""
    
    @abstractmethod
    def validate_file_compatibility(self, file_path: str) -> Tuple[bool, str]:
        """
        Check if uploaded file is compatible with this adapter
        
        Returns:
            Tuple[bool, str]: (is_compatible, error_message_or_details)
        """
        pass
    
    @abstractmethod
    def detect_data_types(self, file_path: str) -> List[str]:
        """
        Analyze file and detect what types of data are present
        
        Returns:
            List[str]: List of data types found (e.g., ['courses', 'faculty'])
        """
        pass
    
    @abstractmethod
    def get_adapter_info(self) -> Dict[str, Any]:
        """
        Return metadata about this adapter for UI display
        
        Returns:
            Dict with adapter name, description, supported formats, etc.
        """
        pass
    
    @abstractmethod
    def parse_file(self, file_path: str, options: Dict[str, Any]) -> Dict[str, List[Dict]]:
        """
        Parse the file and return structured data
        
        Returns:
            Dict mapping data types to lists of records
        """
        pass
    
    @abstractmethod
    def format_export_data(self, data: Dict[str, List[Dict]], options: Dict[str, Any]) -> bytes:
        """
        Format database data for export in this adapter's format
        
        Returns:
            bytes: Formatted file content ready for download
        """
        pass
```

### 3. Implementation Example

#### Complete Custom Adapter
```python
import pandas as pd
from typing import Dict, List, Any, Tuple
from pathlib import Path
import re
from datetime import datetime

class PTUCSVAdapter(BaseAdapter):
    """Adapter for Pacific Technical University CSV enrollment data"""
    
    def __init__(self):
        self.required_columns = ['student_id', 'course_code', 'term', 'enrollment_status']
        self.optional_columns = ['grade', 'credits', 'instructor_email']
        
    def get_adapter_info(self) -> Dict[str, Any]:
        return {
            "id": "ptu_csv_enrollment_v1",
            "name": "PTU CSV Enrollment Format v1.0",
            "description": "Imports student enrollment data from PTU's CSV exports",
            "supported_formats": [".csv"],
            "institution_id": "ptu_institution_id",
            "data_types": ["students", "enrollments", "courses"],
            "version": "1.0.0",
            "created_by": "System Developer",
            "last_updated": "2024-09-25",
            "file_size_limit": "50MB",
            "max_records": 10000
        }
    
    def validate_file_compatibility(self, file_path: str) -> Tuple[bool, str]:
        """Check if CSV file matches PTU's enrollment format"""
        try:
            # Check file extension
            if not file_path.lower().endswith('.csv'):
                return False, "File must be in CSV format"
            
            # Read first few rows to check structure
            df = pd.read_csv(file_path, nrows=5)
            
            # Check required columns
            missing_columns = [col for col in self.required_columns if col not in df.columns]
            if missing_columns:
                return False, f"Missing required columns: {', '.join(missing_columns)}"
            
            # Check data format patterns
            if 'course_code' in df.columns:
                # PTU uses format like "MATH101", "ENGL201"
                sample_codes = df['course_code'].dropna().head(3)
                pattern = r'^[A-Z]{3,4}[0-9]{3}$'
                invalid_codes = [code for code in sample_codes if not re.match(pattern, str(code))]
                if invalid_codes:
                    return False, f"Course codes don't match PTU format (MATH101): {invalid_codes}"
            
            return True, f"File compatible. Detected {len(df)} sample records."
            
        except Exception as e:
            return False, f"Error reading file: {str(e)}"
    
    def detect_data_types(self, file_path: str) -> List[str]:
        """Analyze CSV and detect what data types are present"""
        try:
            df = pd.read_csv(file_path, nrows=100)  # Sample for analysis
            detected_types = []
            
            # Check for student data
            if 'student_id' in df.columns:
                detected_types.append('students')
            
            # Check for enrollment data  
            if 'enrollment_status' in df.columns:
                detected_types.append('enrollments')
                
            # Check for course data
            if 'course_code' in df.columns:
                detected_types.append('courses')
                
            # Check for instructor data
            if 'instructor_email' in df.columns:
                detected_types.append('faculty')
                
            return detected_types
            
        except Exception:
            return []
    
    def parse_file(self, file_path: str, options: Dict[str, Any]) -> Dict[str, List[Dict]]:
        """Parse PTU CSV file into normalized data structures"""
        df = pd.read_csv(file_path)
        
        # Get institution_id from options
        institution_id = options.get('institution_id')
        
        result = {
            'students': [],
            'courses': [],
            'enrollments': [],
            'faculty': []
        }
        
        # Process each row
        for _, row in df.iterrows():
            # Extract student data
            if pd.notna(row.get('student_id')):
                student = {
                    'student_id': str(row['student_id']),
                    'institution_id': institution_id,
                    'status': 'active',
                    'created_at': datetime.now().isoformat()
                }
                result['students'].append(student)
            
            # Extract course data
            if pd.notna(row.get('course_code')):
                course = {
                    'course_number': row['course_code'],
                    'title': row.get('course_title', 'Unknown Course'),
                    'credits': int(row.get('credits', 3)),
                    'institution_id': institution_id,
                    'created_at': datetime.now().isoformat()
                }
                result['courses'].append(course)
            
            # Extract enrollment data
            if pd.notna(row.get('enrollment_status')):
                enrollment = {
                    'student_id': str(row['student_id']),
                    'course_number': row['course_code'],
                    'term': self._normalize_term(row.get('term')),
                    'status': row['enrollment_status'],
                    'grade': row.get('grade'),
                    'institution_id': institution_id,
                    'created_at': datetime.now().isoformat()
                }
                result['enrollments'].append(enrollment)
            
            # Extract faculty data if present
            if pd.notna(row.get('instructor_email')):
                faculty = {
                    'email': row['instructor_email'],
                    'first_name': row.get('instructor_first_name', 'Unknown'),
                    'last_name': row.get('instructor_last_name', 'Faculty'),
                    'role': 'instructor',
                    'institution_id': institution_id,
                    'created_at': datetime.now().isoformat()
                }
                result['faculty'].append(faculty)
        
        # Remove duplicates
        for data_type in result:
            result[data_type] = self._deduplicate_records(result[data_type], data_type)
        
        return result
    
    def format_export_data(self, data: Dict[str, List[Dict]], options: Dict[str, Any]) -> bytes:
        """Format data for export in PTU CSV format"""
        # Combine related data into enrollment records
        export_records = []
        
        enrollments = data.get('enrollments', [])
        students = {s['student_id']: s for s in data.get('students', [])}
        courses = {c['course_number']: c for c in data.get('courses', [])}
        faculty = {f['email']: f for f in data.get('faculty', [])}
        
        for enrollment in enrollments:
            student = students.get(enrollment['student_id'], {})
            course = courses.get(enrollment['course_number'], {})
            
            record = {
                'student_id': enrollment['student_id'],
                'course_code': enrollment['course_number'],
                'course_title': course.get('title', ''),
                'term': enrollment.get('term', ''),
                'enrollment_status': enrollment.get('status', ''),
                'grade': enrollment.get('grade', ''),
                'credits': course.get('credits', ''),
                'instructor_email': course.get('instructor_email', '')
            }
            export_records.append(record)
        
        # Convert to CSV
        df = pd.DataFrame(export_records)
        csv_content = df.to_csv(index=False)
        
        return csv_content.encode('utf-8')
    
    def _normalize_term(self, term_str: str) -> str:
        """Convert PTU term format to standard format"""
        if not term_str:
            return 'Unknown'
        
        # PTU uses "Fall 2024", "Spring 2025" format
        # Convert to "FA2024", "SP2025" format
        term_mapping = {
            'fall': 'FA',
            'spring': 'SP', 
            'summer': 'SU',
            'winter': 'WI'
        }
        
        parts = term_str.lower().split()
        if len(parts) >= 2:
            season = term_mapping.get(parts[0], parts[0][:2].upper())
            year = parts[1]
            return f"{season}{year}"
        
        return term_str
    
    def _deduplicate_records(self, records: List[Dict], data_type: str) -> List[Dict]:
        """Remove duplicate records based on data type key fields"""
        if not records:
            return records
        
        key_fields = {
            'students': ['student_id'],
            'courses': ['course_number'],
            'enrollments': ['student_id', 'course_number', 'term'],
            'faculty': ['email']
        }
        
        keys = key_fields.get(data_type, ['id'])
        seen = set()
        unique_records = []
        
        for record in records:
            key = tuple(record.get(field) for field in keys)
            if key not in seen:
                seen.add(key)
                unique_records.append(record)
        
        return unique_records
```

### 4. Testing Framework

#### Adapter Test Template
```python
import pytest
import tempfile
import pandas as pd
from pathlib import Path

class TestPTUCSVAdapter:
    """Test suite for PTU CSV Adapter"""
    
    @pytest.fixture
    def adapter(self):
        return PTUCSVAdapter()
    
    @pytest.fixture
    def sample_csv_file(self):
        """Create a sample CSV file for testing"""
        data = {
            'student_id': ['12345', '12346', '12347'],
            'course_code': ['MATH101', 'ENGL201', 'PHYS301'],
            'course_title': ['Calculus I', 'English Composition', 'Physics III'],
            'term': ['Fall 2024', 'Fall 2024', 'Spring 2025'],
            'enrollment_status': ['enrolled', 'enrolled', 'completed'],
            'grade': ['', '', 'A'],
            'credits': [4, 3, 4],
            'instructor_email': ['prof.smith@ptu.edu', 'prof.jones@ptu.edu', 'prof.wilson@ptu.edu']
        }
        
        df = pd.DataFrame(data)
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        df.to_csv(temp_file.name, index=False)
        temp_file.close()
        
        yield temp_file.name
        
        # Cleanup
        Path(temp_file.name).unlink()
    
    def test_adapter_info(self, adapter):
        """Test adapter metadata"""
        info = adapter.get_adapter_info()
        
        assert info['id'] == 'ptu_csv_enrollment_v1'
        assert info['name'] == 'PTU CSV Enrollment Format v1.0'
        assert '.csv' in info['supported_formats']
        assert 'students' in info['data_types']
    
    def test_file_compatibility_valid(self, adapter, sample_csv_file):
        """Test compatibility check with valid file"""
        is_compatible, message = adapter.validate_file_compatibility(sample_csv_file)
        
        assert is_compatible is True
        assert 'compatible' in message.lower()
    
    def test_file_compatibility_invalid_format(self, adapter):
        """Test compatibility check with invalid file format"""
        temp_file = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        temp_file.close()
        
        is_compatible, message = adapter.validate_file_compatibility(temp_file.name)
        
        assert is_compatible is False
        assert 'CSV format' in message
        
        Path(temp_file.name).unlink()
    
    def test_data_type_detection(self, adapter, sample_csv_file):
        """Test automatic data type detection"""
        detected_types = adapter.detect_data_types(sample_csv_file)
        
        assert 'students' in detected_types
        assert 'courses' in detected_types
        assert 'enrollments' in detected_types
        assert 'faculty' in detected_types
    
    def test_file_parsing(self, adapter, sample_csv_file):
        """Test file parsing functionality"""
        options = {'institution_id': 'ptu_test_institution'}
        result = adapter.parse_file(sample_csv_file, options)
        
        # Check data structure
        assert 'students' in result
        assert 'courses' in result
        assert 'enrollments' in result
        assert 'faculty' in result
        
        # Check data content
        assert len(result['students']) == 3
        assert len(result['courses']) == 3
        assert len(result['enrollments']) == 3
        
        # Check data quality
        first_student = result['students'][0]
        assert 'student_id' in first_student
        assert first_student['institution_id'] == 'ptu_test_institution'
    
    def test_export_formatting(self, adapter):
        """Test export data formatting"""
        sample_data = {
            'students': [
                {'student_id': '12345', 'institution_id': 'ptu_test'}
            ],
            'courses': [
                {'course_number': 'MATH101', 'title': 'Calculus I', 'credits': 4}
            ],
            'enrollments': [
                {
                    'student_id': '12345',
                    'course_number': 'MATH101', 
                    'term': 'FA2024',
                    'status': 'enrolled'
                }
            ]
        }
        
        result = adapter.format_export_data(sample_data, {})
        
        assert isinstance(result, bytes)
        csv_content = result.decode('utf-8')
        assert 'student_id,course_code' in csv_content
        assert '12345,MATH101' in csv_content
```

### 5. Deployment Process

#### Integration Steps
1. **Code Review**: Developer reviews adapter implementation
2. **Testing**: Run comprehensive test suite with institution's data
3. **Validation**: Institution validates import/export results
4. **Deployment**: Deploy adapter to production environment
5. **Documentation**: Update system documentation with new adapter

#### Configuration Management
```python
# adapters/registry.py
AVAILABLE_ADAPTERS = {
    'mocku_excel_v1': {
        'class': 'MockUExcelAdapter',
        'module': 'adapters.cei_excel_adapter',
        'institution_id': 'mocku_institution_id',
        'active': True
    },
    'ptu_csv_enrollment_v1': {
        'class': 'PTUCSVAdapter', 
        'module': 'adapters.ptu_csv_adapter',
        'institution_id': 'ptu_institution_id',
        'active': True
    }
}

def get_adapters_for_institution(institution_id: str) -> List[Dict]:
    """Return all active adapters for an institution"""
    return [
        adapter_info for adapter_info in AVAILABLE_ADAPTERS.values()
        if adapter_info['institution_id'] == institution_id and adapter_info['active']
    ]
```

### 6. Best Practices

#### Development Guidelines
- **Start Simple**: Begin with core functionality, add features iteratively
- **Validate Early**: Implement compatibility checking before parsing logic
- **Handle Errors Gracefully**: Provide clear error messages for users
- **Test Thoroughly**: Use real institution data for testing (sanitized)
- **Document Assumptions**: Clearly document data format assumptions

#### Performance Considerations
- **Stream Large Files**: Use chunked processing for large datasets
- **Memory Management**: Be conscious of memory usage with large files
- **Progress Reporting**: Provide progress updates for long-running operations
- **Timeout Handling**: Implement reasonable timeouts for file processing

#### Security Requirements
- **Input Validation**: Validate all input data thoroughly
- **File Type Verification**: Verify file types beyond extension checking
- **Size Limits**: Implement appropriate file size limits
- **Sanitization**: Sanitize all user input before processing

---

This adapter development framework ensures consistent, reliable, and secure handling of diverse institutional data formats while providing clear guidance for creating new adapters as institutions are onboarded.
