# Firestore to SQLite Replacement Plan

## Executive Summary

**Objective:** Replace Google Cloud Firestore with SQLite for simplified local development and production deployment. This is a complete replacement, not a data migration.

**Timeline:** 2-3 days of focused development

**Benefits:**
- ✅ Eliminate Firestore emulator complexity
- ✅ Visible database file (`course_records.db`)
- ✅ Standard SQL queries and tooling
- ✅ Simple backup and deployment
- ✅ No vendor lock-in or API quotas

**Greenfield Advantage:** No data migration needed - we can start fresh with a clean SQLite database and use existing seed scripts.

---

## Current State Analysis

### Database Collections (Firestore)
Based on codebase analysis, current collections:
- `institutions` - Institution/organization data
- `users` - User accounts and authentication
- `programs` - Academic programs within institutions  
- `courses` - Course catalog
- `terms` - Academic terms/semesters
- `course_offerings` - Course instances in specific terms
- `course_sections` - Instructor assignments and enrollments
- `course_outcomes` - Course Learning Outcomes (CLOs)
- `user_invitations` - Pending user invitations

### Service Layer Architecture
Current services that need database migration:
- `AuthService` - User authentication and authorization
- `DatabaseService` - Core database operations (main migration target)
- `DashboardService` - Data aggregation and metrics
- `ImportService` - Data import with adapter pattern
- `ExportService` - Data export functionality
- `InvitationService` - User invitation management
- `RegistrationService` - User registration workflow
- `LoginService` - Login/logout operations
- `PasswordService` - Password management
- `PasswordResetService` - Password reset workflow
- `EmailService` - Email notifications
- `SessionService` - Session management

---

## Replacement Strategy

### Phase 1: Database Schema Creation (Day 1)
**Goal:** Create SQLite schema equivalent to current Firestore structure

#### 1.1 Install SQLAlchemy Dependencies
```bash
pip install sqlalchemy
```

#### 1.2 Create SQLAlchemy Models
**File:** `models_sql.py`
```python
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

Base = declarative_base()

class Institution(Base):
    __tablename__ = 'institutions'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    short_name = Column(String)
    website_url = Column(String)
    primary_accreditor = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="institution")
    programs = relationship("Program", back_populates="institution")

class User(Base):
    __tablename__ = 'users'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)  # site_admin, institution_admin, program_admin, instructor
    institution_id = Column(String, ForeignKey('institutions.id'))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime)
    
    # Relationships
    institution = relationship("Institution", back_populates="users")
    course_sections = relationship("CourseSection", back_populates="instructor")

# Additional models for Program, Course, Term, etc...
```

#### 1.3 Create Database Connection Service
**File:** `database_sql.py`
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from models_sql import Base
import os

class SQLiteService:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.getenv('DATABASE_URL', 'sqlite:///course_records.db')
        
        self.engine = create_engine(db_path, echo=False)
        self.Session = scoped_session(sessionmaker(bind=self.engine))
        
    def create_tables(self):
        Base.metadata.create_all(self.engine)
        
    def get_session(self):
        return self.Session()
        
    def close_session(self):
        self.Session.remove()
```

### Phase 2: Database Abstraction Layer (Day 1)
**Goal:** Create database interface that abstracts all database operations for easy backend switching

**Note:** Since this is a greenfield replacement, we'll create the abstraction layer immediately and implement both Firestore (temporary) and SQLite (permanent) backends.

#### 2.1 Create Database Interface (Abstract Base Class)
**File:** `database_interface.py`
```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

class DatabaseInterface(ABC):
    """
    Abstract interface for database operations.
    All database implementations must implement these methods.
    This enables seamless switching between Firestore → SQLite → PostgreSQL.
    """
    
    # User Management
    @abstractmethod
    def create_user(self, user_data: Dict[str, Any]) -> str:
        """Create a new user and return user ID"""
        pass
    
    @abstractmethod
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email address"""
        pass
    
    @abstractmethod
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        pass
    
    @abstractmethod
    def update_user(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """Update user data"""
        pass
    
    @abstractmethod
    def list_users(self, institution_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List users, optionally filtered by institution"""
        pass
    
    # Institution Management
    @abstractmethod
    def create_institution(self, institution_data: Dict[str, Any]) -> str:
        """Create a new institution and return institution ID"""
        pass
    
    @abstractmethod
    def get_institution_by_id(self, institution_id: str) -> Optional[Dict[str, Any]]:
        """Get institution by ID"""
        pass
    
    @abstractmethod
    def list_institutions(self) -> List[Dict[str, Any]]:
        """List all institutions"""
        pass
    
    # Course Management
    @abstractmethod
    def create_course(self, course_data: Dict[str, Any]) -> str:
        """Create a new course and return course ID"""
        pass
    
    @abstractmethod
    def get_course_by_id(self, course_id: str) -> Optional[Dict[str, Any]]:
        """Get course by ID"""
        pass
    
    @abstractmethod
    def list_courses(self, institution_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List courses, optionally filtered by institution"""
        pass
    
    # Term Management
    @abstractmethod
    def create_term(self, term_data: Dict[str, Any]) -> str:
        """Create a new term and return term ID"""
        pass
    
    @abstractmethod
    def get_current_term(self, institution_id: str) -> Optional[Dict[str, Any]]:
        """Get current active term for institution"""
        pass
    
    # Course Section Management
    @abstractmethod
    def create_course_section(self, section_data: Dict[str, Any]) -> str:
        """Create a new course section and return section ID"""
        pass
    
    @abstractmethod
    def get_sections_by_instructor(self, instructor_id: str) -> List[Dict[str, Any]]:
        """Get all sections assigned to an instructor"""
        pass
    
    # Course Outcome Management
    @abstractmethod
    def create_course_outcome(self, outcome_data: Dict[str, Any]) -> str:
        """Create a new course outcome and return outcome ID"""
        pass
    
    @abstractmethod
    def get_outcomes_by_section(self, section_id: str) -> List[Dict[str, Any]]:
        """Get all outcomes for a course section"""
        pass
    
    # Invitation Management
    @abstractmethod
    def create_invitation(self, invitation_data: Dict[str, Any]) -> str:
        """Create a new invitation and return invitation ID"""
        pass
    
    @abstractmethod
    def get_invitation_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Get invitation by token"""
        pass
    
    # Utility Methods
    @abstractmethod
    def health_check(self) -> bool:
        """Check if database connection is healthy"""
        pass
    
    @abstractmethod
    def begin_transaction(self):
        """Begin a database transaction"""
        pass
    
    @abstractmethod
    def commit_transaction(self):
        """Commit current transaction"""
        pass
    
    @abstractmethod
    def rollback_transaction(self):
        """Rollback current transaction"""
        pass
```

#### 2.2 Create Firestore Implementation (Wrapper)
**File:** `database_firestore.py`
```python
from database_interface import DatabaseInterface
from database_service import *  # Import existing Firestore functions
from typing import List, Dict, Any, Optional

class FirestoreDatabase(DatabaseInterface):
    """
    Firestore implementation of DatabaseInterface.
    Wraps existing database_service.py functions.
    """
    
    def __init__(self):
        # Use existing Firestore connection
        pass
    
    def create_user(self, user_data: Dict[str, Any]) -> str:
        # Delegate to existing function
        return create_user(user_data)
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        # Delegate to existing function
        return get_user_by_email(email)
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        return get_user_by_id(user_id)
    
    # ... implement all interface methods by delegating to existing functions
```

#### 2.3 Create SQLite Implementation
**File:** `database_sqlite.py`
```python
from database_interface import DatabaseInterface
from sqlalchemy.exc import IntegrityError
from database_sql import SQLiteService
from models_sql import User, Institution, Program, Course, Term
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class SQLiteDatabase(DatabaseInterface):
    """
    SQLite implementation of DatabaseInterface.
    Provides same functionality as Firestore but with SQLite backend.
    """
    
    def __init__(self):
        self.db = SQLiteService()
        self.db.create_tables()
        self._transaction_session = None
    
    def create_user(self, user_data: Dict[str, Any]) -> str:
        """Create a new user and return user ID"""
        session = self._get_session()
        try:
            user = User(**user_data)
            session.add(user)
            if not self._transaction_session:
                session.commit()
            return user.id
        except IntegrityError as e:
            if not self._transaction_session:
                session.rollback()
            raise Exception(f"User creation failed: {e}")
        finally:
            if not self._transaction_session:
                session.close()
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email address"""
        session = self._get_session()
        try:
            user = session.query(User).filter(User.email == email).first()
            return self._user_to_dict(user) if user else None
        finally:
            if not self._transaction_session:
                session.close()
    
    def _user_to_dict(self, user: User) -> Dict[str, Any]:
        """Convert SQLAlchemy User to dictionary"""
        return {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'role': user.role,
            'institution_id': user.institution_id,
            'is_active': user.is_active,
            'created_at': user.created_at,
            'updated_at': user.updated_at,
            'last_login_at': user.last_login_at
        }
    
    def _get_session(self):
        """Get database session (transaction-aware)"""
        if self._transaction_session:
            return self._transaction_session
        return self.db.get_session()
    
    def begin_transaction(self):
        """Begin a database transaction"""
        self._transaction_session = self.db.get_session()
    
    def commit_transaction(self):
        """Commit current transaction"""
        if self._transaction_session:
            self._transaction_session.commit()
            self._transaction_session.close()
            self._transaction_session = None
    
    def rollback_transaction(self):
        """Rollback current transaction"""
        if self._transaction_session:
            self._transaction_session.rollback()
            self._transaction_session.close()
            self._transaction_session = None
    
    # ... implement all other interface methods
```

#### 2.4 Create PostgreSQL Implementation (Future)
**File:** `database_postgresql.py`
```python
from database_interface import DatabaseInterface
from database_sqlite import SQLiteDatabase  # Inherit most functionality

class PostgreSQLDatabase(SQLiteDatabase):
    """
    PostgreSQL implementation of DatabaseInterface.
    Inherits from SQLiteDatabase since both use SQLAlchemy.
    Only connection string differs.
    """
    
    def __init__(self):
        # Override connection for PostgreSQL
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker, scoped_session
        import os
        
        db_url = os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost/course_records')
        self.engine = create_engine(db_url)
        self.Session = scoped_session(sessionmaker(bind=self.engine))
        self._transaction_session = None
        
        # Create tables if they don't exist
        from models_sql import Base
        Base.metadata.create_all(self.engine)
    
    # All methods inherited from SQLiteDatabase work unchanged!
```

### Phase 3: Service Integration (Day 2)
**Goal:** Update all service classes to use database abstraction layer

#### 3.1 Create Database Service Factory
**File:** `database_factory.py`
```python
import os
from database_firestore import FirestoreDatabase
from database_sqlite import SQLiteDatabase
from database_postgresql import PostgreSQLDatabase

def get_database_service():
    """Factory function to return appropriate database service"""
    db_type = os.getenv('DATABASE_TYPE', 'sqlite')  # Default to SQLite
    
    if db_type == 'firestore':
        return FirestoreDatabase()
    elif db_type == 'sqlite':
        return SQLiteDatabase()
    elif db_type == 'postgresql':
        return PostgreSQLDatabase()
    else:
        raise ValueError(f"Unknown database type: {db_type}")

# Global instance
db_service = get_database_service()
```

#### 3.2 Update Service Imports
Update all service files to use the factory:
```python
# OLD (in auth_service.py, dashboard_service.py, etc.)
from database_service import create_user, get_user_by_email  # Direct function imports

# NEW  
from database_factory import db_service

# Usage changes from:
user = get_user_by_email(email)

# To:
user = db_service.get_user_by_email(email)
```

#### 3.3 Environment Configuration
**File:** `.envrc` (add)
```bash
export DATABASE_TYPE=sqlite
export DATABASE_URL=sqlite:///course_records.db
```

#### 3.4 Update Seed Scripts
Modify existing `scripts/seed_db.py` to work with new database abstraction:
```python
# OLD
from database_service import create_user, create_institution

# NEW
from database_factory import db_service

# Usage
user_id = db_service.create_user(user_data)
institution_id = db_service.create_institution(institution_data)
```

### Phase 4: Testing and Validation (Day 3)
**Goal:** Ensure all functionality works with SQLite

#### 4.1 Update Test Configuration
**File:** `tests/conftest.py`
```python
import pytest
import os
import tempfile
from database_factory import get_database_service

@pytest.fixture(scope="function")
def test_db():
    """Create temporary SQLite database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = f"sqlite:///{tmp.name}"
        
    os.environ['DATABASE_TYPE'] = 'sqlite'
    os.environ['DATABASE_URL'] = db_path
    
    db_service = get_database_service()
    
    yield db_service
    
    # Cleanup
    os.unlink(tmp.name.replace('sqlite:///', ''))
```

#### 4.2 Run Test Suite
```bash
# Test with SQLite
export DATABASE_TYPE=sqlite
python -m pytest tests/ -v

# Verify all tests pass
python scripts/ship_it.py --validation-type commit
```

#### 4.3 Manual Testing Checklist
- [ ] User registration and login
- [ ] Data import functionality  
- [ ] Dashboard data display
- [ ] Export functionality
- [ ] Institution management
- [ ] Course management
- [ ] All API endpoints

#### 4.4 Fresh Database Setup
Since this is a greenfield replacement, simply:
```bash
# Remove any existing database
rm -f course_records.db

# Set SQLite as default
export DATABASE_TYPE=sqlite

# Start application - database will be created automatically
./restart_server.sh

# Seed with fresh data
python scripts/seed_db.py --blank  # Just site admin
# OR
python scripts/seed_db.py  # Full test dataset
```

---

## Deployment Strategy

### Local Development
```bash
# Set environment
export DATABASE_TYPE=sqlite
export DATABASE_URL=sqlite:///course_records.db

# Run application
./restart_server.sh
```

### Production Deployment
**Option 1: Single SQLite File**
- Deploy `course_records.db` file with application
- Use file-based backups
- Scale vertically as needed

**Option 2: Upgrade Path to PostgreSQL**
- Start with SQLite for simplicity
- Migrate to PostgreSQL when scaling needs require it
- SQLAlchemy makes this migration straightforward

---

## Risk Mitigation

### Backup Strategy
```bash
# Simple SQLite backup
cp course_records.db course_records_backup_$(date +%Y%m%d).db

# Automated backup script
#!/bin/bash
BACKUP_DIR="backups"
mkdir -p $BACKUP_DIR
cp course_records.db "$BACKUP_DIR/course_records_$(date +%Y%m%d_%H%M%S).db"
```

### Rollback Plan
1. Keep Firestore emulator running during initial testing
2. Maintain parallel data export/import scripts
3. Environment variable toggle for quick rollback:
   ```bash
   export DATABASE_TYPE=firestore  # Rollback to Firestore
   export DATABASE_TYPE=sqlite     # Use SQLite
   ```

### Concurrent Write Handling
```python
# Add to SQLite service for write conflict handling
from sqlalchemy.exc import OperationalError
import time
import random

def retry_on_locked(func, max_retries=3):
    """Retry database operations on lock conflicts"""
    for attempt in range(max_retries):
        try:
            return func()
        except OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                time.sleep(random.uniform(0.1, 0.5))  # Random backoff
                continue
            raise
```

---

## Success Criteria

### Technical Validation
- [ ] All existing tests pass with SQLite
- [ ] Data migration completes without loss
- [ ] Performance equals or exceeds Firestore emulator
- [ ] Database file is visible and browsable
- [ ] Backup and restore procedures work

### User Experience Validation  
- [ ] All UI functionality works unchanged
- [ ] Import/export operations complete successfully
- [ ] Dashboard loads with correct data
- [ ] Multi-user scenarios work without conflicts

### Operational Benefits
- [ ] No more emulator configuration complexity
- [ ] Simple database file backup/restore
- [ ] Clear visibility into database contents
- [ ] Reduced development environment setup time

---

## Timeline Summary

| Day | Phase | Deliverable |
|-----|-------|-------------|
| 1 | Schema + Abstraction | SQLite schema + database interface created |
| 2 | Service Integration | All services updated to use abstraction layer |  
| 3 | Testing + Validation | Full test suite passes, manual validation complete |

**Total Effort:** 2-3 focused development days

**Greenfield Advantage:** No data migration complexity - just implement, test, and switch!

**Result:** Simplified, maintainable database solution that eliminates Firestore complexity while preserving all functionality.
