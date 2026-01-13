"""
Load test for SQLite concurrency handling.

Tests that multiple concurrent database operations don't cause failures.
This reproduces the issue causing 20 test failures in the full suite.
"""

import threading
import time
from typing import List

from src.database.database_factory import get_database_service


class TestSQLiteConcurrency:
    """Test SQLite handles concurrent access properly."""

    def test_concurrent_reads_simple(self):
        """Test that multiple threads can read from database simultaneously."""
        db = get_database_service()
        results: List[bool] = []
        errors: List[Exception] = []

        def read_operation(thread_id: int):
            """Perform a simple read operation."""
            try:
                # Simple read operation - get all institutions
                institutions = db.get_all_institutions()
                results.append(True)
                print(
                    f"Thread {thread_id}: Read {len(institutions) if institutions else 0} institutions"
                )
            except Exception as e:
                errors.append(e)
                print(f"Thread {thread_id}: ERROR - {e}")

        # Create 10 concurrent readers
        threads = []
        for i in range(10):
            t = threading.Thread(target=read_operation, args=(i,))
            threads.append(t)

        # Start all threads at once
        for t in threads:
            t.start()

        # Wait for all to complete
        for t in threads:
            t.join(timeout=5.0)

        # Assert: all reads should succeed
        assert len(errors) == 0, f"Got {len(errors)} errors: {errors}"
        assert len(results) == 10, f"Only {len(results)}/10 threads completed"

    def test_concurrent_reads_heavy(self):
        """Test heavy concurrent read load."""
        db = get_database_service()
        results: List[bool] = []
        errors: List[Exception] = []

        def heavy_read_operation(thread_id: int):
            """Perform multiple read operations."""
            try:
                for _ in range(5):
                    db.get_all_institutions()
                    db.get_users_by_role("instructor")
                    # Small delay to simulate processing
                    time.sleep(0.001)
                results.append(True)
            except Exception as e:
                errors.append(e)
                print(f"Thread {thread_id}: ERROR - {e}")

        # Create 20 concurrent readers doing 5 operations each
        threads = []
        for i in range(20):
            t = threading.Thread(target=heavy_read_operation, args=(i,))
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=10.0)

        assert len(errors) == 0, f"Got {len(errors)} errors: {errors}"
        assert len(results) == 20, f"Only {len(results)}/20 threads completed"

    def test_concurrent_writes_simple(self):
        """Test that multiple threads can write to database with proper locking."""
        db = get_database_service()
        results: List[str] = []
        errors: List[Exception] = []

        def write_operation(thread_id: int):
            """Perform a simple write operation."""
            try:
                # Create a test user
                user_data = {
                    "email": f"concurrent_test_{thread_id}@example.com",
                    "first_name": "Test",
                    "last_name": f"User{thread_id}",
                    "role": "instructor",
                    "institution_id": "test-institution",
                    "account_status": "active",
                    "email_verified": True,
                }
                user_id = db.create_user(user_data)
                if user_id:
                    results.append(user_id)
                    print(f"Thread {thread_id}: Created user {user_id}")
                else:
                    errors.append(
                        Exception(f"Thread {thread_id}: Failed to create user")
                    )
            except Exception as e:
                errors.append(e)
                print(f"Thread {thread_id}: ERROR - {e}")

        # Create 10 concurrent writers
        threads = []
        for i in range(10):
            t = threading.Thread(target=write_operation, args=(i,))
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=5.0)

        # Assert: all writes should succeed
        assert len(errors) == 0, f"Got {len(errors)} errors: {errors}"
        assert len(results) == 10, f"Only {len(results)}/10 threads completed"

        # Verify all users were created
        for user_id in results:
            user = db.get_user_by_id(user_id)
            assert user is not None, f"User {user_id} not found after creation"

    def test_concurrent_mixed_operations(self):
        """Test mix of concurrent reads and writes."""
        db = get_database_service()
        read_results: List[bool] = []
        write_results: List[str] = []
        errors: List[Exception] = []

        def read_operation(thread_id: int):
            try:
                for _ in range(3):
                    db.get_all_institutions()
                    time.sleep(0.001)
                read_results.append(True)
            except Exception as e:
                errors.append(e)
                print(f"Reader {thread_id}: ERROR - {e}")

        def write_operation(thread_id: int):
            try:
                user_data = {
                    "email": f"mixed_test_{thread_id}@example.com",
                    "first_name": "Mixed",
                    "last_name": f"User{thread_id}",
                    "role": "instructor",
                    "institution_id": "test-institution",
                    "account_status": "active",
                    "email_verified": True,
                }
                user_id = db.create_user(user_data)
                if user_id:
                    write_results.append(user_id)
                else:
                    errors.append(
                        Exception(f"Writer {thread_id}: Failed to create user")
                    )
            except Exception as e:
                errors.append(e)
                print(f"Writer {thread_id}: ERROR - {e}")

        # Mix: 15 readers, 5 writers
        threads = []
        for i in range(15):
            t = threading.Thread(target=read_operation, args=(i,))
            threads.append(t)
        for i in range(5):
            t = threading.Thread(target=write_operation, args=(i,))
            threads.append(t)

        # Shuffle to mix reads/writes
        import random

        random.shuffle(threads)

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=10.0)

        assert len(errors) == 0, f"Got {len(errors)} errors: {errors}"
        assert len(read_results) == 15, f"Only {len(read_results)}/15 readers completed"
        assert len(write_results) == 5, f"Only {len(write_results)}/5 writers completed"
