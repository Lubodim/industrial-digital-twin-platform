from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from core.request import (
    get_authenticated_user,
    get_client_computer_name,
    get_client_ip,
    get_request_method,
    get_request_path,
    get_user_agent,
)


User = get_user_model()


class CoreRequestTests(TestCase):

    def setUp(self):

        self.factory = RequestFactory()

        self.user = User.objects.create_user(
            username="request-user",
            password="password",
        )

    def build_request(self):

        request = self.factory.get(
            "/digital-twins/",
            HTTP_USER_AGENT="Chrome",
            REMOTE_ADDR="192.168.0.15",
            HTTP_X_COMPUTER_NAME="PC-01",
        )

        request.user = self.user

        return request

    def test_client_ip(self):

        self.assertEqual(
            get_client_ip(
                self.build_request(),
            ),
            "192.168.0.15",
        )

    def test_computer_name(self):

        self.assertEqual(
            get_client_computer_name(
                self.build_request(),
            ),
            "PC-01",
        )

    def test_user_agent(self):

        self.assertEqual(
            get_user_agent(
                self.build_request(),
            ),
            "Chrome",
        )

    def test_request_path(self):

        self.assertEqual(
            get_request_path(
                self.build_request(),
            ),
            "/digital-twins/",
        )

    def test_request_method(self):

        self.assertEqual(
            get_request_method(
                self.build_request(),
            ),
            "GET",
        )

    def test_authenticated_user(self):

        self.assertEqual(
            get_authenticated_user(
                self.build_request(),
            ),
            self.user,
        )
