#!/usr/bin/env python
"""Manual test script to demonstrate database schema validation.

This script intentionally creates a schema mismatch and shows that the
validator catches it with a clear error message.

Run this to verify that schema validation is working correctly.
"""

from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine
from sqlalchemy.orm import declarative_base

from database_validator import SchemaValidationError, validate_schema

print("🔬 Manual Schema Validation Test")
print("=" * 60)

# Create in-memory database with one schema
engine = create_engine("sqlite:///:memory:")
metadata = MetaData()
users_table = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String),
    Column("email_verified", String),  # Note: email_verified (correct)
)
metadata.create_all(engine)

print("\n📊 Database Schema Created:")
print("  Table: users")
print("  Columns: id, name, email_verified")

# Create SQLAlchemy model with DIFFERENT schema (intentional typo)
TestBase = declarative_base()


class User(TestBase):  # type: ignore[misc,valid-type]
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    is_email_verified = Column(
        String
    )  # TYPO: is_email_verified instead of email_verified


print("\n🏗️  SQLAlchemy Model Created:")
print("  Table: users")
print("  Columns: id, name, is_email_verified")  # Note the typo!


# Create mock db_service
class MockSQLite:
    def __init__(self):
        self.engine = engine


class MockDBService:
    def __init__(self):
        self.sqlite = MockSQLite()


# Temporarily replace Base to use our test models
import database_validator

original_base = database_validator.Base
database_validator.Base = TestBase

print("\n🔍 Running Schema Validation...")
print("-" * 60)

try:
    db_service = MockDBService()
    validate_schema(db_service, strict=True)
    print("❌ UNEXPECTED: Validation passed (should have failed!)")
except SchemaValidationError as e:
    print(f"✅ EXPECTED: Validation caught the schema mismatch!\n")
    print(f"Error message:\n{e}\n")
    print("This is exactly what we want - clear error at startup!")
finally:
    # Restore original Base
    database_validator.Base = original_base

print("\n" + "=" * 60)
print("✅ Manual test complete!")
print("\nWhat this means:")
print("  • If you misspell a column name in code, app won't start")
print("  • You get a clear error message with suggestions")
print("  • No more silent failures or cryptic runtime errors")
print("  • Database refactoring is now much safer")
