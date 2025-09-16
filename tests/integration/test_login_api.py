"""
Integration tests for login API endpoints

Tests the complete login/logout flow through the API endpoints.
"""

import pytest
import json
from flask import Flask
from unittest.mock import patch, MagicMock

from app import app


@pytest.fixture
def client():
    """Create test client"""
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"
    
    with app.test_client() as client:
        with app.app_context():
            yield client


@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "user_id": "user-123",
        "email": "test@example.com",
        "password_hash": "hashed-password",
        "role": "instructor",
        "account_status": "active",
        "institution_id": "inst-123",
        "display_name": "Test User",
        "login_count": 5
    }


class TestLoginAPI:
    """Test login API endpoint"""
    
    @patch("login_service.SessionService")
    @patch("login_service.PasswordService")
    @patch("login_service.db")
    def test_login_success(self, mock_db, mock_password_service, mock_session_service, client, sample_user_data):
        """Test successful login via API"""
        # Setup
        mock_password_service.check_account_lockout.return_value = None
        mock_db.get_user_by_email.return_value = sample_user_data
        mock_password_service.verify_password.return_value = True
        mock_password_service.clear_failed_attempts.return_value = None
        mock_db.update_user.return_value = True
        mock_session_service.create_user_session.return_value = None
        
        # Execute
        response = client.post('/api/auth/login', 
                             data=json.dumps({
                                 "email": "test@example.com",
                                 "password": "password123"
                             }),
                             content_type='application/json')
        
        # Verify
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["login_success"] is True
        assert data["email"] == "test@example.com"
        assert data["role"] == "instructor"
        assert data["message"] == "Login successful"
    
    @patch("login_service.PasswordService")
    @patch("login_service.db")
    def test_login_invalid_credentials(self, mock_db, mock_password_service, client):
        """Test login with invalid credentials"""
        # Setup
        mock_password_service.check_account_lockout.return_value = None
        mock_db.get_user_by_email.return_value = None
        mock_password_service.track_failed_login.return_value = None
        
        # Execute
        response = client.post('/api/auth/login',
                             data=json.dumps({
                                 "email": "invalid@example.com",
                                 "password": "wrongpassword"
                             }),
                             content_type='application/json')
        
        # Verify
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Invalid email or password" in data["error"]
    
    @patch("login_service.PasswordService")
    def test_login_account_locked(self, mock_password_service, client):
        """Test login when account is locked"""
        # Setup
        from password_service import AccountLockedError
        mock_password_service.check_account_lockout.side_effect = AccountLockedError("Account is locked")
        
        # Execute
        response = client.post('/api/auth/login',
                             data=json.dumps({
                                 "email": "test@example.com",
                                 "password": "password123"
                             }),
                             content_type='application/json')
        
        # Verify
        assert response.status_code == 423
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Account is locked" in data["error"]
    
    def test_login_missing_data(self, client):
        """Test login with missing required data"""
        # Execute - missing password
        response = client.post('/api/auth/login',
                             data=json.dumps({
                                 "email": "test@example.com"
                             }),
                             content_type='application/json')
        
        # Verify
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Missing required field: password" in data["error"]
    
    def test_login_no_json(self, client):
        """Test login with no JSON data"""
        # Execute
        response = client.post('/api/auth/login')
        
        # Verify
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "No JSON data provided" in data["error"]
    
    @patch("login_service.SessionService")
    @patch("login_service.PasswordService")
    @patch("login_service.db")
    def test_login_remember_me(self, mock_db, mock_password_service, mock_session_service, client, sample_user_data):
        """Test login with remember me option"""
        # Setup
        mock_password_service.check_account_lockout.return_value = None
        mock_db.get_user_by_email.return_value = sample_user_data
        mock_password_service.verify_password.return_value = True
        mock_password_service.clear_failed_attempts.return_value = None
        mock_db.update_user.return_value = True
        mock_session_service.create_user_session.return_value = None
        
        # Execute
        response = client.post('/api/auth/login',
                             data=json.dumps({
                                 "email": "test@example.com",
                                 "password": "password123",
                                 "remember_me": True
                             }),
                             content_type='application/json')
        
        # Verify
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["login_success"] is True
        
        # Verify remember_me was passed to session service
        mock_session_service.create_user_session.assert_called_once()
        session_call = mock_session_service.create_user_session.call_args
        assert session_call[0][1] is True  # remember_me parameter


class TestLogoutAPI:
    """Test logout API endpoint"""
    
    @patch("login_service.SessionService")
    def test_logout_success(self, mock_session_service, client):
        """Test successful logout via API"""
        # Setup
        mock_session_service.get_session_info.return_value = {"email": "test@example.com"}
        mock_session_service.destroy_session.return_value = None
        
        # Execute
        response = client.post('/api/auth/logout')
        
        # Verify
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["logout_success"] is True
        assert data["message"] == "Logout successful"
    
    @patch("login_service.SessionService")
    def test_logout_with_error(self, mock_session_service, client):
        """Test logout when error occurs"""
        # Setup
        mock_session_service.get_session_info.side_effect = Exception("Session error")
        mock_session_service.destroy_session.return_value = None
        
        # Execute
        response = client.post('/api/auth/logout')
        
        # Verify - should still succeed
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["logout_success"] is True


class TestLoginStatusAPI:
    """Test login status API endpoint"""
    
    @patch("login_service.SessionService")
    def test_status_logged_in(self, mock_session_service, client):
        """Test getting status when user is logged in"""
        # Setup
        mock_session_service.is_user_logged_in.return_value = True
        mock_session_service.validate_session.return_value = True
        mock_session_service.get_session_info.return_value = {
            "user_id": "user-123",
            "email": "test@example.com",
            "role": "instructor",
            "institution_id": "inst-123",
            "display_name": "Test User"
        }
        
        # Execute
        response = client.get('/api/auth/status')
        
        # Verify
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["logged_in"] is True
        assert data["email"] == "test@example.com"
        assert data["role"] == "instructor"
    
    @patch("login_service.SessionService")
    def test_status_not_logged_in(self, mock_session_service, client):
        """Test getting status when user is not logged in"""
        # Setup
        mock_session_service.is_user_logged_in.return_value = False
        
        # Execute
        response = client.get('/api/auth/status')
        
        # Verify
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["logged_in"] is False
        assert data["message"] == "Not logged in"


class TestSessionRefreshAPI:
    """Test session refresh API endpoint"""
    
    @patch("login_service.SessionService")
    def test_refresh_success(self, mock_session_service, client):
        """Test successful session refresh"""
        # Setup
        mock_session_service.is_user_logged_in.return_value = True
        mock_session_service.refresh_session.return_value = None
        
        # Execute
        response = client.post('/api/auth/refresh')
        
        # Verify
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["refresh_success"] is True
        assert data["message"] == "Session refreshed successfully"
    
    @patch("login_service.SessionService")
    def test_refresh_no_session(self, mock_session_service, client):
        """Test refresh when no active session"""
        # Setup
        mock_session_service.is_user_logged_in.return_value = False
        
        # Execute
        response = client.post('/api/auth/refresh')
        
        # Verify
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data["success"] is False
        assert "No active session" in data["error"]


class TestLockoutStatusAPI:
    """Test lockout status API endpoint"""
    
    @patch("login_service.PasswordService")
    def test_lockout_status_not_locked(self, mock_password_service, client):
        """Test checking lockout status when not locked"""
        # Setup
        mock_password_service.is_account_locked.return_value = (False, None)
        
        # Execute
        response = client.get('/api/auth/lockout-status/test@example.com')
        
        # Verify
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["is_locked"] is False
        assert data["message"] == "Account is not locked"
    
    @patch("login_service.PasswordService")
    def test_lockout_status_locked(self, mock_password_service, client):
        """Test checking lockout status when locked"""
        # Setup
        from datetime import datetime, timedelta
        unlock_time = datetime.now() + timedelta(minutes=30)
        mock_password_service.is_account_locked.return_value = (True, unlock_time)
        
        # Execute
        response = client.get('/api/auth/lockout-status/test@example.com')
        
        # Verify
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["is_locked"] is True
        assert data["unlock_time"] == unlock_time.isoformat()


class TestUnlockAccountAPI:
    """Test account unlock API endpoint"""
    
    @patch("login_service.PasswordService")
    @patch("auth_service.get_current_user")
    def test_unlock_account_success(self, mock_get_current_user, mock_password_service, client):
        """Test successful account unlock"""
        # Setup
        mock_get_current_user.return_value = {"id": "admin-123"}
        mock_password_service.clear_failed_attempts.return_value = None
        
        # Execute
        response = client.post('/api/auth/unlock-account',
                             data=json.dumps({
                                 "email": "test@example.com"
                             }),
                             content_type='application/json')
        
        # Verify
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["unlock_success"] is True
        assert "has been unlocked" in data["message"]
    
    @patch("auth_service.get_current_user")
    def test_unlock_account_no_auth(self, mock_get_current_user, client):
        """Test unlock account when not authenticated"""
        # Setup
        mock_get_current_user.return_value = None
        
        # Execute
        response = client.post('/api/auth/unlock-account',
                             data=json.dumps({
                                 "email": "test@example.com"
                             }),
                             content_type='application/json')
        
        # Verify
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Authentication required" in data["error"]
    
    def test_unlock_account_missing_email(self, client):
        """Test unlock account with missing email"""
        # Execute
        response = client.post('/api/auth/unlock-account',
                             data=json.dumps({}),
                             content_type='application/json')
        
        # Verify
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Missing required field: email" in data["error"]


class TestLoginFlowIntegration:
    """Integration tests for complete login flow"""
    
    @patch("login_service.SessionService")
    @patch("login_service.PasswordService") 
    @patch("login_service.db")
    def test_complete_login_logout_flow(self, mock_db, mock_password_service, mock_session_service, client, sample_user_data):
        """Test complete login -> status check -> logout flow"""
        
        # Step 1: Login
        mock_password_service.check_account_lockout.return_value = None
        mock_db.get_user_by_email.return_value = sample_user_data
        mock_password_service.verify_password.return_value = True
        mock_password_service.clear_failed_attempts.return_value = None
        mock_db.update_user.return_value = True
        mock_session_service.create_user_session.return_value = None
        
        login_response = client.post('/api/auth/login',
                                   data=json.dumps({
                                       "email": "test@example.com",
                                       "password": "password123"
                                   }),
                                   content_type='application/json')
        
        assert login_response.status_code == 200
        login_data = json.loads(login_response.data)
        assert login_data["login_success"] is True
        
        # Step 2: Check status
        mock_session_service.is_user_logged_in.return_value = True
        mock_session_service.validate_session.return_value = True
        mock_session_service.get_session_info.return_value = {
            "user_id": "user-123",
            "email": "test@example.com",
            "role": "instructor"
        }
        
        status_response = client.get('/api/auth/status')
        assert status_response.status_code == 200
        status_data = json.loads(status_response.data)
        assert status_data["logged_in"] is True
        
        # Step 3: Logout
        mock_session_service.get_session_info.return_value = {"email": "test@example.com"}
        mock_session_service.destroy_session.return_value = None
        
        logout_response = client.post('/api/auth/logout')
        assert logout_response.status_code == 200
        logout_data = json.loads(logout_response.data)
        assert logout_data["logout_success"] is True
        
        # Verify all services were called appropriately
        mock_session_service.create_user_session.assert_called_once()
        mock_session_service.destroy_session.assert_called_once()
    
    @patch("login_service.PasswordService")
    @patch("login_service.db")
    def test_failed_login_attempts_tracking(self, mock_db, mock_password_service, client):
        """Test that failed login attempts are properly tracked"""
        
        # Setup for failed attempts
        mock_password_service.check_account_lockout.return_value = None
        mock_db.get_user_by_email.return_value = None  # User doesn't exist
        mock_password_service.track_failed_login.return_value = None
        
        # Make multiple failed login attempts
        for i in range(3):
            response = client.post('/api/auth/login',
                                 data=json.dumps({
                                     "email": "nonexistent@example.com",
                                     "password": "wrongpassword"
                                 }),
                                 content_type='application/json')
            
            assert response.status_code == 401
            data = json.loads(response.data)
            assert data["success"] is False
        
        # Verify tracking was called for each attempt
        assert mock_password_service.track_failed_login.call_count == 3
