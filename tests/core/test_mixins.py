from __future__ import annotations

from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.views import View

from core.constants import (
    ROLE_ADMIN,
    ROLE_ENGINEER,
    ROLE_VIEWER,
)
from core.mixins import (
    AnyRoleRequiredMixin,
    AuditLogAccessRequiredMixin,
    BusinessDataCreateRequiredMixin,
    BusinessDataViewRequiredMixin,
    CatalogManagementRequiredMixin,
    ExperimentApprovalRequiredMixin,
    ExternalResearchRequiredMixin,
    InternalAnalysisRequiredMixin,
    ObjectChangeRequiredMixin,
    ObjectDeleteRequiredMixin,
    ObjectViewRequiredMixin,
    PlatformAccessRequiredMixin,
    PlatformPermissionMixin,
    RoleRequiredMixin,
)


User = get_user_model()


class SuccessView(View):
    """
    Minimal view used by the mixin tests.
    """

    def get(self, request, *args, **kwargs):
        return HttpResponse("success")


class PlatformAccessTestView(
    PlatformAccessRequiredMixin,
    SuccessView,
):
    pass


class BusinessViewTestView(
    BusinessDataViewRequiredMixin,
    SuccessView,
):
    pass


class BusinessCreateTestView(
    BusinessDataCreateRequiredMixin,
    SuccessView,
):
    pass


class EngineerRoleTestView(
    RoleRequiredMixin,
    SuccessView,
):
    required_role = ROLE_ENGINEER


class EngineerOrViewerTestView(
    AnyRoleRequiredMixin,
    SuccessView,
):
    required_roles = (
        ROLE_ENGINEER,
        ROLE_VIEWER,
    )


class ObjectViewTestView(
    ObjectViewRequiredMixin,
    SuccessView,
):
    test_object = None

    def get_object(self, queryset=None):
        return self.test_object


class ObjectChangeTestView(
    ObjectChangeRequiredMixin,
    SuccessView,
):
    test_object = None

    def get_object(self, queryset=None):
        return self.test_object


class ObjectDeleteTestView(
    ObjectDeleteRequiredMixin,
    SuccessView,
):
    test_object = None

    def get_object(self, queryset=None):
        return self.test_object


class CustomOwnerFieldChangeView(
    ObjectChangeRequiredMixin,
    SuccessView,
):
    owner_fields = (
        "requested_by",
    )

    test_object = None

    def get_object(self, queryset=None):
        return self.test_object


class ExternalResearchTestView(
    ExternalResearchRequiredMixin,
    SuccessView,
):
    test_experiment = None

    def get_experiment(self):
        return self.test_experiment


class InternalAnalysisTestView(
    InternalAnalysisRequiredMixin,
    SuccessView,
):
    test_experiment = None

    def get_experiment(self):
        return self.test_experiment


class ApprovalTestView(
    ExperimentApprovalRequiredMixin,
    SuccessView,
):
    test_experiment = None

    def get_experiment(self):
        return self.test_experiment


class CatalogManagementTestView(
    CatalogManagementRequiredMixin,
    SuccessView,
):
    pass


class AuditLogTestView(
    AuditLogAccessRequiredMixin,
    SuccessView,
):
    pass


class MissingPermissionCheckView(
    PlatformPermissionMixin,
    SuccessView,
):
    pass


class MissingRoleView(
    RoleRequiredMixin,
    SuccessView,
):
    pass


class EmptyAnyRoleView(
    AnyRoleRequiredMixin,
    SuccessView,
):
    required_roles = ()


class MissingObjectView(
    ObjectChangeRequiredMixin,
    SuccessView,
):
    pass


class CoreMixinTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

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
            username="mixin-admin",
            password="test-password",
        )
        self.admin.groups.add(
            self.admin_group
        )

        self.engineer = User.objects.create_user(
            username="mixin-engineer",
            password="test-password",
        )
        self.engineer.groups.add(
            self.engineer_group
        )

        self.other_engineer = User.objects.create_user(
            username="mixin-other-engineer",
            password="test-password",
        )
        self.other_engineer.groups.add(
            self.engineer_group
        )

        self.viewer = User.objects.create_user(
            username="mixin-viewer",
            password="test-password",
        )
        self.viewer.groups.add(
            self.viewer_group
        )

        self.unassigned_user = User.objects.create_user(
            username="mixin-unassigned",
            password="test-password",
        )

        self.owned_object = SimpleNamespace(
            created_by=self.engineer,
        )

        self.other_object = SimpleNamespace(
            created_by=self.other_engineer,
        )

        self.requested_object = SimpleNamespace(
            requested_by=self.engineer,
        )

    def build_request(self, user):
        request = self.factory.get(
            "/protected/"
        )
        request.user = user
        return request

    def dispatch_view(
        self,
        view_class,
        user,
        **view_attributes,
    ):
        view = view_class()

        for name, value in view_attributes.items():
            setattr(view, name, value)

        return view.dispatch(
            self.build_request(user)
        )

    def test_platform_access_allows_active_user(self):
        response = self.dispatch_view(
            PlatformAccessTestView,
            self.unassigned_user,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_platform_access_redirects_anonymous_user(self):
        response = self.dispatch_view(
            PlatformAccessTestView,
            AnonymousUser(),
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertIn(
            reverse("accounts:login"),
            response.url,
        )

    def test_business_view_allows_engineer(self):
        response = self.dispatch_view(
            BusinessViewTestView,
            self.engineer,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_business_view_allows_viewer(self):
        response = self.dispatch_view(
            BusinessViewTestView,
            self.viewer,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_business_view_rejects_unassigned_user(self):
        with self.assertRaisesMessage(
            Exception,
            "Нямате необходимите права",
        ):
            self.dispatch_view(
                BusinessViewTestView,
                self.unassigned_user,
            )

    def test_business_create_allows_engineer(self):
        response = self.dispatch_view(
            BusinessCreateTestView,
            self.engineer,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_business_create_rejects_viewer(self):
        with self.assertRaisesMessage(PermissionDenied,"Нямате необходимите права",):
            self.dispatch_view(BusinessCreateTestView,self.viewer,)

    def test_role_mixin_allows_matching_role(self):
        response = self.dispatch_view(
            EngineerRoleTestView,
            self.engineer,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_role_mixin_rejects_non_matching_role(self):
        with self.assertRaisesMessage(PermissionDenied,"Нямате необходимите права",):            
            self.dispatch_view(EngineerRoleTestView,self.viewer,)

    def test_any_role_mixin_allows_engineer(self):
        response = self.dispatch_view(
            EngineerOrViewerTestView,
            self.engineer,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_any_role_mixin_allows_viewer(self):
        response = self.dispatch_view(
            EngineerOrViewerTestView,
            self.viewer,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_object_view_allows_authorized_viewer(self):
        response = self.dispatch_view(
            ObjectViewTestView,
            self.viewer,
            test_object=self.owned_object,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_object_change_allows_owner(self):
        response = self.dispatch_view(
            ObjectChangeTestView,
            self.engineer,
            test_object=self.owned_object,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        def test_object_change_rejects_other_engineer(self,):
            with self.assertRaisesMessage(PermissionDenied,"Нямате право да редактирате този обект.",):
                self.dispatch_view(ObjectChangeTestView,self.other_engineer,test_object=self.owned_object,)

    def test_object_change_allows_admin(self):
        response = self.dispatch_view(
            ObjectChangeTestView,
            self.admin,
            test_object=self.owned_object,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_object_delete_allows_owner(self):
        response = self.dispatch_view(
            ObjectDeleteTestView,
            self.engineer,
            test_object=self.owned_object,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        def test_object_delete_rejects_viewer(
        self,
    ):
            with self.assertRaisesMessage(
                PermissionDenied,
                "Нямате право да изтривате този обект.",
            ):
                self.dispatch_view(
                    ObjectDeleteTestView,
                    self.viewer,
                    test_object=self.owned_object,
                )

    def test_custom_owner_fields_are_supported(self):
        response = self.dispatch_view(
            CustomOwnerFieldChangeView,
            self.engineer,
            test_object=self.requested_object,
        )

        self.assertEqual(
            response.status_code,
            200,
        )
    def test_permission_object_is_cached(self):
        class CountingObjectSourceView(SuccessView):
            calls = 0

            def get_object(self,queryset=None,):
                self.calls += 1
                return self.test_object

        class CountingObjectView(ObjectChangeRequiredMixin,CountingObjectSourceView,):
            pass

        view = CountingObjectView()

        view.test_object = self.owned_object

        response = view.dispatch(self.build_request(self.engineer))

        self.assertEqual(response.status_code,200,)

        self.assertEqual(view.calls,1,)

        self.assertEqual(view.get_object(),self.owned_object,)

        self.assertEqual(view.calls,1,)
        
    def test_external_research_allows_experiment_owner(self):
        response = self.dispatch_view(
            ExternalResearchTestView,
            self.engineer,
            test_experiment=self.owned_object,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        def test_external_research_rejects_other_engineer(
        self,
    ):
            with self.assertRaisesMessage(
                PermissionDenied,
                (
                    "Нямате право да стартирате външно "
                    "AI проучване за този експеримент."
                ),
            ):
                self.dispatch_view(
                    ExternalResearchTestView,
                    self.other_engineer,
                    test_experiment=self.owned_object,
                )

    def test_internal_analysis_allows_owner(self):
        response = self.dispatch_view(
            InternalAnalysisTestView,
            self.engineer,
            test_experiment=self.owned_object,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_approval_allows_admin(self):
        response = self.dispatch_view(
            ApprovalTestView,
            self.admin,
            test_experiment=self.owned_object,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        def test_approval_rejects_engineer(
        self,
    ):
            with self.assertRaisesMessage(
                PermissionDenied,
                (
                    "Само администратор може да одобрява "
                    "или отхвърля експерименти."
                ),
            ):
                self.dispatch_view(
                    ApprovalTestView,
                    self.engineer,
                    test_experiment=self.owned_object,
                )
                
                
    def test_catalog_management_allows_admin(self):
        response = self.dispatch_view(
            CatalogManagementTestView,
            self.admin,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        def test_catalog_management_rejects_engineer(self,):
            with self.assertRaisesMessage(PermissionDenied,"Нямате право да управлявате каталозите.",):
                self.dispatch_view(CatalogManagementTestView,self.engineer,)

    def test_audit_log_access_allows_admin(self):
        response = self.dispatch_view(AuditLogTestView,self.admin,)

        self.assertEqual(response.status_code,200,)

        def test_audit_log_access_rejects_engineer(self,):
            with self.assertRaisesMessage(PermissionDenied,(
                    "Нямате право да разглеждате "
                    "одитния журнал."),):
                
                self.dispatch_view(AuditLogTestView,self.engineer,)

    def test_missing_permission_check_is_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.dispatch_view(MissingPermissionCheckView,self.engineer,)

    def test_missing_required_role_is_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.dispatch_view(MissingRoleView,self.engineer,)

    def test_empty_required_roles_are_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
           
            self.dispatch_view(EmptyAnyRoleView,self.engineer,)

    def test_missing_get_object_is_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.dispatch_view(MissingObjectView, self.engineer,)
