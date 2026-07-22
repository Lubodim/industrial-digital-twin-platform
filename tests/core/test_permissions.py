from __future__ import annotations

from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from django.test import TestCase

from core.constants import (
    ROLE_ADMIN,
    ROLE_ENGINEER,
    ROLE_VIEWER,
)
from core.permissions import (
    can_access_platform,
    can_approve_experiment,
    can_change_object,
    can_create_business_data,
    can_delete_object,
    can_manage_catalogs,
    can_run_external_research,
    can_run_internal_analysis,
    can_view_audit_log,
    can_view_business_data,
    can_view_object,
    get_user_role_names,
    is_authenticated_user,
    is_engineer,
    is_object_owner,
    is_platform_admin,
    is_viewer,
    normalize_role_name,
    resolve_object_owner,
    user_has_any_role,
    user_has_role,
)


User = get_user_model()


class CorePermissionTests(TestCase):
    def setUp(self):
        self.admin_group = Group.objects.create(
            name=ROLE_ADMIN,
        )

        self.engineer_group = Group.objects.create(
            name=ROLE_ENGINEER,
        )

        self.viewer_group = Group.objects.create(
            name=ROLE_VIEWER,
        )

        self.admin = User.objects.create_user(
            username="platform-admin",
            password="test-password",
        )
        self.admin.groups.add(self.admin_group)

        self.engineer = User.objects.create_user(
            username="engineer",
            password="test-password",
        )
        self.engineer.groups.add(self.engineer_group)

        self.other_engineer = User.objects.create_user(
            username="other-engineer",
            password="test-password",
        )
        self.other_engineer.groups.add(
            self.engineer_group
        )

        self.viewer = User.objects.create_user(
            username="viewer",
            password="test-password",
        )
        self.viewer.groups.add(self.viewer_group)

        self.unassigned_user = User.objects.create_user(
            username="unassigned-user",
            password="test-password",
        )

        self.superuser = User.objects.create_superuser(
            username="superuser",
            email="superuser@example.com",
            password="test-password",
        )

        self.inactive_user = User.objects.create_user(
            username="inactive-user",
            password="test-password",
            is_active=False,
        )

        self.owned_object = SimpleNamespace(
            created_by=self.engineer,
        )

        self.other_owned_object = SimpleNamespace(
            created_by=self.other_engineer,
        )

    def test_normalize_role_name(self):
        self.assertEqual(
            normalize_role_name("  Engineer  "),
            "engineer",
        )

    def test_normalize_role_rejects_empty_name(self):
        with self.assertRaises(ValueError):
            normalize_role_name("  ")

    def test_normalize_role_rejects_non_string(self):
        with self.assertRaises(TypeError):
            normalize_role_name(123)

    def test_authenticated_active_user_is_recognized(self):
        self.assertTrue(
            is_authenticated_user(self.engineer)
        )

    def test_anonymous_user_is_not_authenticated(self):
        self.assertFalse(
            is_authenticated_user(
                AnonymousUser()
            )
        )

    def test_none_is_not_authenticated(self):
        self.assertFalse(
            is_authenticated_user(None)
        )

    def test_inactive_user_is_not_authenticated(self):
        self.assertFalse(
            is_authenticated_user(
                self.inactive_user
            )
        )

    def test_returns_normalized_role_names(self):
        role_names = get_user_role_names(
            self.engineer
        )

        self.assertEqual(
            role_names,
            {"engineer"},
        )

    def test_anonymous_user_has_no_roles(self):
        self.assertEqual(
            get_user_role_names(
                AnonymousUser()
            ),
            set(),
        )

    def test_user_has_role_is_case_insensitive(self):
        self.assertTrue(
            user_has_role(
                self.engineer,
                "ENGINEER",
            )
        )

    def test_user_without_role_is_rejected(self):
        self.assertFalse(
            user_has_role(
                self.viewer,
                ROLE_ENGINEER,
            )
        )

    def test_superuser_is_considered_to_have_every_role(self):
        self.assertTrue(
            user_has_role(
                self.superuser,
                ROLE_ENGINEER,
            )
        )

        self.assertTrue(
            user_has_role(
                self.superuser,
                ROLE_ADMIN,
            )
        )

    def test_user_has_any_role(self):
        self.assertTrue(
            user_has_any_role(
                self.viewer,
                (
                    ROLE_ENGINEER,
                    ROLE_VIEWER,
                ),
            )
        )

    def test_user_has_any_role_returns_false_for_empty_roles(self):
        self.assertFalse(
            user_has_any_role(
                self.engineer,
                (),
            )
        )

    def test_admin_group_grants_platform_admin_access(self):
        self.assertTrue(
            is_platform_admin(self.admin)
        )

    def test_superuser_is_platform_admin(self):
        self.assertTrue(
            is_platform_admin(self.superuser)
        )

    def test_staff_flag_alone_does_not_grant_platform_admin(self):
        staff_user = User.objects.create_user(
            username="staff-only",
            password="test-password",
            is_staff=True,
        )

        self.assertFalse(
            is_platform_admin(staff_user)
        )

    def test_engineer_role_is_recognized(self):
        self.assertTrue(
            is_engineer(self.engineer)
        )

    def test_admin_also_has_engineering_access(self):
        self.assertTrue(
            is_engineer(self.admin)
        )

    def test_viewer_is_not_engineer(self):
        self.assertFalse(
            is_engineer(self.viewer)
        )

    def test_viewer_role_is_recognized(self):
        self.assertTrue(
            is_viewer(self.viewer)
        )

    def test_engineer_does_not_implicitly_have_viewer_role(self):
        self.assertFalse(
            is_viewer(self.engineer)
        )

    def test_all_active_authenticated_users_can_enter_platform(self):
        self.assertTrue(
            can_access_platform(
                self.unassigned_user
            )
        )

    def test_anonymous_user_cannot_enter_platform(self):
        self.assertFalse(
            can_access_platform(
                AnonymousUser()
            )
        )

    def test_admin_engineer_and_viewer_can_view_business_data(self):
        self.assertTrue(
            can_view_business_data(self.admin)
        )
        self.assertTrue(
            can_view_business_data(
                self.engineer
            )
        )
        self.assertTrue(
            can_view_business_data(self.viewer)
        )

    def test_unassigned_user_cannot_view_business_data(self):
        self.assertFalse(
            can_view_business_data(
                self.unassigned_user
            )
        )

    def test_only_engineers_and_admins_can_create_business_data(self):
        self.assertTrue(
            can_create_business_data(
                self.engineer
            )
        )

        self.assertTrue(
            can_create_business_data(self.admin)
        )

        self.assertFalse(
            can_create_business_data(self.viewer)
        )

    def test_resolve_object_owner_uses_created_by(self):
        owner = resolve_object_owner(
            self.owned_object
        )

        self.assertEqual(
            owner,
            self.engineer,
        )

    def test_resolve_object_owner_supports_requested_by(self):
        obj = SimpleNamespace(
            requested_by=self.engineer,
        )

        self.assertEqual(
            resolve_object_owner(obj),
            self.engineer,
        )

    def test_resolve_object_owner_returns_none_when_absent(self):
        obj = SimpleNamespace(name="No owner")

        self.assertIsNone(
            resolve_object_owner(obj)
        )

    def test_engineer_is_owner_of_owned_object(self):
        self.assertTrue(
            is_object_owner(
                self.engineer,
                self.owned_object,
            )
        )

    def test_other_engineer_is_not_owner(self):
        self.assertFalse(
            is_object_owner(
                self.other_engineer,
                self.owned_object,
            )
        )

    def test_authorized_roles_can_view_object(self):
        self.assertTrue(
            can_view_object(
                self.engineer,
                self.owned_object,
            )
        )

        self.assertTrue(
            can_view_object(
                self.viewer,
                self.owned_object,
            )
        )

    def test_unassigned_user_cannot_view_object(self):
        self.assertFalse(
            can_view_object(
                self.unassigned_user,
                self.owned_object,
            )
        )

    def test_object_cannot_be_viewed_when_it_is_none(self):
        self.assertFalse(
            can_view_object(
                self.engineer,
                None,
            )
        )

    def test_engineer_can_change_owned_object(self):
        self.assertTrue(
            can_change_object(
                self.engineer,
                self.owned_object,
            )
        )

    def test_engineer_cannot_change_other_users_object(self):
        self.assertFalse(
            can_change_object(
                self.engineer,
                self.other_owned_object,
            )
        )

    def test_admin_can_change_every_object(self):
        self.assertTrue(
            can_change_object(
                self.admin,
                self.other_owned_object,
            )
        )

    def test_viewer_cannot_change_object(self):
        self.assertFalse(
            can_change_object(
                self.viewer,
                self.owned_object,
            )
        )

    def test_delete_access_matches_change_access(self):
        self.assertTrue(
            can_delete_object(
                self.engineer,
                self.owned_object,
            )
        )

        self.assertFalse(
            can_delete_object(
                self.engineer,
                self.other_owned_object,
            )
        )

    def test_engineer_can_start_research_for_own_experiment(self):
        self.assertTrue(
            can_run_external_research(
                self.engineer,
                self.owned_object,
            )
        )

    def test_engineer_cannot_start_research_for_other_experiment(self):
        self.assertFalse(
            can_run_external_research(
                self.engineer,
                self.other_owned_object,
            )
        )

    def test_admin_can_start_research_for_every_experiment(self):
        self.assertTrue(
            can_run_external_research(
                self.admin,
                self.other_owned_object,
            )
        )

    def test_viewer_cannot_start_research(self):
        self.assertFalse(
            can_run_external_research(
                self.viewer,
                self.owned_object,
            )
        )

    def test_internal_analysis_uses_same_access_rules(self):
        self.assertTrue(
            can_run_internal_analysis(
                self.engineer,
                self.owned_object,
            )
        )

        self.assertFalse(
            can_run_internal_analysis(
                self.engineer,
                self.other_owned_object,
            )
        )

    def test_only_admin_can_approve_experiment(self):
        self.assertTrue(
            can_approve_experiment(
                self.admin,
                self.owned_object,
            )
        )

        self.assertFalse(
            can_approve_experiment(
                self.engineer,
                self.owned_object,
            )
        )

        self.assertFalse(
            can_approve_experiment(
                self.viewer,
                self.owned_object,
            )
        )

    def test_only_admin_can_manage_catalogs(self):
        self.assertTrue(
            can_manage_catalogs(self.admin)
        )

        self.assertFalse(
            can_manage_catalogs(
                self.engineer
            )
        )

    def test_only_admin_can_view_audit_log(self):
        self.assertTrue(
            can_view_audit_log(self.admin)
        )

        self.assertFalse(
            can_view_audit_log(
                self.engineer
            )
        )
