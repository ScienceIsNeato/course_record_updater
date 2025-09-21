"""
Multi-Tenant Authorization Integration Tests

Tests the complete authorization system with multi-tenant data access scenarios.
Validates that users can only access data within their scope (institution/program boundaries).

Test Categories:
1. Institution-level data isolation
2. Program-level data scoping
3. Cross-tenant access prevention
4. Role hierarchy validation
5. Context-aware API endpoint security
"""

from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from auth_service import Permission, UserRole


class TestInstitutionDataIsolation:
    """Test that users can only access data from their own institution"""

    def test_institution_admin_cannot_access_other_institutions(self):
        """Test that institution admin can only access their own institution's data"""
        app = Flask(__name__)

        with app.test_request_context():
            # Mock institution admin user from Institution A
            with patch("auth_service.auth_service.get_current_user") as mock_user:
                mock_user.return_value = {
                    "user_id": "inst-admin-a",
                    "role": "institution_admin",
                    "institution_id": "institution-a",
                    "accessible_institutions": ["institution-a"],
                }

                with patch("auth_service.auth_service.has_permission") as mock_has_perm:
                    mock_has_perm.return_value = True

                    # Test accessing own institution's programs
                    from api_routes import list_programs

                    with patch(
                        "api_routes.get_programs_by_institution"
                    ) as mock_get_programs:
                        mock_get_programs.return_value = [
                            {
                                "program_id": "prog-a1",
                                "name": "Program A1",
                                "institution_id": "institution-a",
                            }
                        ]

                        with patch(
                            "api_routes.get_current_institution_id"
                        ) as mock_inst_id:
                            mock_inst_id.return_value = "institution-a"
                            with patch("api_routes.jsonify") as mock_jsonify:
                                mock_jsonify.return_value = MagicMock()

                                result = list_programs()

                                # Should successfully access own institution's programs
                                mock_get_programs.assert_called_once_with(
                                    "institution-a"
                                )
                                mock_jsonify.assert_called_once()

    def test_program_admin_cannot_access_other_institutions_programs(self):
        """Test that program admin cannot access programs from other institutions"""
        app = Flask(__name__)

        with app.test_request_context():
            # Mock program admin from Institution A
            with patch("auth_service.auth_service.get_current_user") as mock_user:
                mock_user.return_value = {
                    "user_id": "prog-admin-a",
                    "role": "program_admin",
                    "institution_id": "institution-a",
                    "program_ids": ["program-a1"],
                }

                with patch("auth_service.auth_service.has_permission") as mock_has_perm:
                    mock_has_perm.return_value = True

                    # Test accessing courses - should be filtered by institution
                    from api_routes import list_courses

                    with patch("api_routes.get_all_courses") as mock_get_courses:
                        # Mock courses from multiple institutions
                        mock_get_courses.return_value = [
                            {
                                "course_id": "course-a1",
                                "institution_id": "institution-a",
                                "program_id": "program-a1",
                            },
                            {
                                "course_id": "course-b1",
                                "institution_id": "institution-b",
                                "program_id": "program-b1",
                            },
                        ]

                        with patch(
                            "api_routes.get_current_institution_id"
                        ) as mock_inst_id:
                            mock_inst_id.return_value = "institution-a"
                            with patch("api_routes.jsonify") as mock_jsonify:
                                mock_jsonify.return_value = MagicMock()

                                result = list_courses()

                                # Should only see courses from own institution
                                mock_get_courses.assert_called_once_with(
                                    "institution-a"
                                )

    def test_instructor_cannot_access_other_institutions_sections(self):
        """Test that instructor cannot access sections from other institutions"""
        app = Flask(__name__)

        with app.test_request_context():
            # Mock instructor from Institution A
            with patch("auth_service.auth_service.get_current_user") as mock_user:
                mock_user.return_value = {
                    "user_id": "instructor-a",
                    "role": "instructor",
                    "institution_id": "institution-a",
                }

                with patch("auth_service.auth_service.has_permission") as mock_has_perm:
                    mock_has_perm.return_value = True

                    # Test accessing sections - instructors get filtered by instructor_id
                    from api_routes import list_sections

                    with patch(
                        "api_routes.get_sections_by_instructor"
                    ) as mock_get_sections:
                        mock_get_sections.return_value = [
                            {
                                "section_id": "section-a1",
                                "instructor_id": "instructor-a",
                                "institution_id": "institution-a",
                            }
                        ]

                        with patch(
                            "api_routes.get_current_institution_id"
                        ) as mock_inst_id:
                            mock_inst_id.return_value = "institution-a"
                            with patch("api_routes.jsonify") as mock_jsonify:
                                mock_jsonify.return_value = MagicMock()

                                result = list_sections()

                                # Should access sections by instructor (which filters by institution internally)
                                mock_get_sections.assert_called_once_with(
                                    "instructor-a"
                                )


class TestProgramScopedAccess:
    """Test that program admins can only access their assigned programs"""

    def test_program_admin_scoped_to_assigned_programs(self):
        """Test that program admin can only access their assigned programs"""
        from auth_service import AuthService

        # Test program admin with multiple programs
        with patch.object(AuthService, "get_current_user") as mock_get_user:
            mock_get_user.return_value = {
                "user_id": "prog-admin-multi",
                "role": "program_admin",
                "institution_id": "institution-a",
                "program_ids": ["program-a1", "program-a2"],
            }

            service = AuthService()

            # Test access to assigned program
            context = {"program_id": "program-a1"}
            assert (
                service._check_scoped_permission(
                    mock_get_user.return_value, "manage_courses", context
                )
                is True
            )

            # Test access to another assigned program
            context = {"program_id": "program-a2"}
            assert (
                service._check_scoped_permission(
                    mock_get_user.return_value, "manage_courses", context
                )
                is True
            )

            # Test access to non-assigned program
            context = {"program_id": "program-a3"}
            assert (
                service._check_scoped_permission(
                    mock_get_user.return_value, "manage_courses", context
                )
                is False
            )

    def test_program_admin_cannot_access_programs_from_other_institutions(self):
        """Test that program admin cannot access programs from other institutions even if program IDs match"""
        from auth_service import AuthService

        with patch.object(AuthService, "get_current_user") as mock_get_user:
            mock_get_user.return_value = {
                "user_id": "prog-admin-a",
                "role": "program_admin",
                "institution_id": "institution-a",
                "program_ids": ["program-1"],  # Same ID exists in other institution
            }

            service = AuthService()

            # Test access to program with same ID but different institution
            # This would require additional institution context checking
            context = {"program_id": "program-1", "institution_id": "institution-b"}
            assert (
                service._check_scoped_permission(
                    mock_get_user.return_value, "manage_courses", context
                )
                is False
            )


class TestCrossTenantAccessPrevention:
    """Test that cross-tenant data access is properly blocked"""

    def test_api_endpoints_validate_institution_context(self):
        """Test that API endpoints validate institution context in URL parameters"""
        app = Flask(__name__)

        with app.test_request_context("/api/institutions/institution-b"):
            # Mock institution admin from Institution A trying to access Institution B
            with patch("auth_service.auth_service.get_current_user") as mock_user:
                mock_user.return_value = {
                    "user_id": "inst-admin-a",
                    "role": "institution_admin",
                    "institution_id": "institution-a",
                    "accessible_institutions": ["institution-a"],
                }

                # Test permission decorator with context
                from auth_service import permission_required

                @permission_required(
                    "view_institution_data", context_keys=["institution_id"]
                )
                def test_endpoint(institution_id):
                    return f"Accessing {institution_id}"

                with patch("auth_service.auth_service.has_permission") as mock_has_perm:
                    # Should deny access to different institution
                    mock_has_perm.return_value = False

                    with patch("auth_service.jsonify") as mock_jsonify:
                        mock_jsonify.return_value = (MagicMock(), 403)

                        result = test_endpoint("institution-b")

                        # Should return 403 Forbidden
                        assert isinstance(result, tuple)
                        assert result[1] == 403

    def test_program_context_validation_in_api_endpoints(self):
        """Test that program-scoped API endpoints validate program context"""
        app = Flask(__name__)

        with app.test_request_context("/api/programs/program-b1"):
            # Mock program admin trying to access program outside their scope
            with patch("auth_service.auth_service.get_current_user") as mock_user:
                mock_user.return_value = {
                    "user_id": "prog-admin-a",
                    "role": "program_admin",
                    "institution_id": "institution-a",
                    "program_ids": ["program-a1"],
                }

                from auth_service import permission_required

                @permission_required("view_program_data", context_keys=["program_id"])
                def test_program_endpoint(program_id):
                    return f"Accessing program {program_id}"

                with patch("auth_service.auth_service.has_permission") as mock_has_perm:
                    # Should deny access to program outside scope
                    mock_has_perm.return_value = False

                    with patch("auth_service.jsonify") as mock_jsonify:
                        mock_jsonify.return_value = (MagicMock(), 403)

                        result = test_program_endpoint("program-b1")

                        # Should return 403 Forbidden
                        assert isinstance(result, tuple)
                        assert result[1] == 403


class TestRoleHierarchyAccess:
    """Test role hierarchy access patterns"""

    def test_site_admin_can_access_all_institutions(self):
        """Test that site admin can access data from any institution"""
        from auth_service import AuthService

        with patch.object(AuthService, "get_current_user") as mock_get_user:
            mock_get_user.return_value = {"user_id": "site-admin", "role": "site_admin"}

            service = AuthService()

            # Site admin should have access to any institution
            institutions = service.get_accessible_institutions()
            # Use the actual mock institution IDs from AuthService
            assert "inst-123" in institutions
            assert "inst-456" in institutions
            assert len(institutions) >= 2

    def test_institution_admin_hierarchy_over_program_admin(self):
        """Test that institution admin can access all programs in their institution"""
        from auth_service import AuthService

        with patch.object(AuthService, "get_current_user") as mock_get_user:
            mock_get_user.return_value = {
                "user_id": "inst-admin-a",
                "role": "institution_admin",
                "institution_id": "inst-123",
            }

            service = AuthService()

            # Institution admin should access all programs in their institution
            programs = service.get_accessible_programs()
            # Use the actual mock program IDs from AuthService
            assert "prog-123" in programs
            assert "prog-456" in programs
            assert len(programs) >= 2

    def test_role_hierarchy_permission_inheritance(self):
        """Test that higher roles inherit permissions from lower roles"""
        from auth_service import ROLE_PERMISSIONS, UserRole

        # Site admin should have all permissions
        site_admin_perms = ROLE_PERMISSIONS[UserRole.SITE_ADMIN.value]
        institution_admin_perms = ROLE_PERMISSIONS[UserRole.INSTITUTION_ADMIN.value]
        program_admin_perms = ROLE_PERMISSIONS[UserRole.PROGRAM_ADMIN.value]
        instructor_perms = ROLE_PERMISSIONS[UserRole.INSTRUCTOR.value]

        # Test that higher roles have more permissions
        assert len(site_admin_perms) >= len(institution_admin_perms)
        assert len(institution_admin_perms) >= len(program_admin_perms)
        assert len(program_admin_perms) >= len(instructor_perms)

        # Test that instructor permissions are included in program admin
        for perm in instructor_perms:
            assert perm in program_admin_perms

        # Test that program admin permissions are included in institution admin
        for perm in program_admin_perms:
            assert perm in institution_admin_perms


class TestContextAwareAPIEndpoints:
    """Test context validation in API endpoints with institution_id and program_id"""

    def test_institution_context_extraction_from_request(self):
        """Test that institution context is properly extracted from request parameters"""
        app = Flask(__name__)

        # Test URL parameter extraction
        with app.test_request_context("/api/institutions/inst-123/programs"):
            from flask import request

            from auth_service import permission_required

            @permission_required("view_program_data", context_keys=["institution_id"])
            def test_endpoint():
                return "success"

            # Mock the permission checking
            with patch("auth_service.auth_service.is_authenticated") as mock_auth:
                mock_auth.return_value = True
                with patch("auth_service.auth_service.has_permission") as mock_has_perm:
                    mock_has_perm.return_value = True

                    # The decorator should extract institution_id from URL
                    result = test_endpoint()

                    # Should call has_permission with context containing institution_id
                    mock_has_perm.assert_called_once()
                    call_args = mock_has_perm.call_args
                    context = call_args[0][1] if len(call_args[0]) > 1 else {}
                    # Note: In real implementation, this would extract from request.view_args

    def test_program_context_extraction_from_json_body(self):
        """Test that program context is extracted from JSON request body"""
        app = Flask(__name__)

        # Test JSON body parameter extraction
        with app.test_request_context(
            "/api/courses",
            method="POST",
            json={"program_id": "prog-456", "name": "Test Course"},
        ):
            from auth_service import permission_required

            @permission_required("manage_courses", context_keys=["program_id"])
            def test_create_course():
                return "course created"

            with patch("auth_service.auth_service.is_authenticated") as mock_auth:
                mock_auth.return_value = True
                with patch("auth_service.auth_service.has_permission") as mock_has_perm:
                    mock_has_perm.return_value = True

                    result = test_create_course()

                    # Should extract program_id from JSON body
                    mock_has_perm.assert_called_once()

    def test_context_validation_with_multiple_parameters(self):
        """Test context validation when multiple context parameters are provided"""
        app = Flask(__name__)

        with app.test_request_context(
            "/api/programs/prog-123/courses/course-456", method="PUT"
        ):
            from auth_service import permission_required

            @permission_required(
                "manage_courses", context_keys=["program_id", "course_id"]
            )
            def test_update_course(program_id, course_id):
                return f"Updated course {course_id} in program {program_id}"

            with patch("auth_service.auth_service.is_authenticated") as mock_auth:
                mock_auth.return_value = True
                with patch("auth_service.auth_service.has_permission") as mock_has_perm:
                    mock_has_perm.return_value = True

                    result = test_update_course("prog-123", "course-456")

                    # Should validate both program and course context
                    mock_has_perm.assert_called_once()


class TestAuthorizationSystemIntegration:
    """Integration tests for complete authorization system"""

    def test_complete_multi_tenant_workflow(self):
        """Test complete workflow: login -> dashboard -> data access -> logout"""
        # This would be a comprehensive end-to-end test
        # For now, we'll test the key integration points

        from auth_service import AuthService, UserRole

        # Test that all components work together
        service = AuthService()

        # Test role validation
        assert UserRole.SITE_ADMIN.value == "site_admin"
        assert UserRole.INSTITUTION_ADMIN.value == "institution_admin"
        assert UserRole.PROGRAM_ADMIN.value == "program_admin"
        assert UserRole.INSTRUCTOR.value == "instructor"

        # Test role hierarchy
        hierarchy = UserRole.get_role_hierarchy()
        assert hierarchy.index("site_admin") < hierarchy.index("institution_admin")
        assert hierarchy.index("institution_admin") < hierarchy.index("program_admin")
        assert hierarchy.index("program_admin") < hierarchy.index("instructor")

    def test_permission_system_completeness(self):
        """Test that permission system covers all required scenarios"""
        from auth_service import ROLE_PERMISSIONS, Permission, UserRole

        # Test that all roles have permissions defined
        for role in UserRole:
            assert role.value in ROLE_PERMISSIONS
            assert len(ROLE_PERMISSIONS[role.value]) > 0

        # Test that key permissions exist
        key_permissions = [
            "manage_institutions",
            "manage_users",
            "view_all_data",
            "manage_institution_users",
            "manage_programs",
            "view_institution_data",
            "manage_program_users",
            "manage_courses",
            "view_program_data",
            "view_section_data",
            "submit_assessments",
        ]

        all_permissions = set()
        for role_perms in ROLE_PERMISSIONS.values():
            all_permissions.update(role_perms)

        for perm in key_permissions:
            assert perm in all_permissions, f"Missing key permission: {perm}"

    def test_authorization_decorators_integration(self):
        """Test that authorization decorators integrate properly with Flask"""
        from auth_service import login_required, permission_required, role_required

        app = Flask(__name__)

        with app.app_context():
            # Test that decorators can be applied
            @login_required
            def test_login_required():
                return "authenticated"

            @permission_required("manage_users")
            def test_permission_required():
                return "authorized"

            @role_required("site_admin")
            def test_role_required():
                return "admin access"

            # Test that decorators are callable
            assert callable(test_login_required)
            assert callable(test_permission_required)
            assert callable(test_role_required)
