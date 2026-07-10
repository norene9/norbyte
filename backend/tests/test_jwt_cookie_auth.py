import os
import sys
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from app.main import app


class JwtCookieAuthTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def test_login_sets_http_only_jwt_cookies(self):
        create_response = self.client.post(
            "/api/v1/users/",
            json={"username": "alice", "email": "alice@example.com", "password": "secret"},
        )
        self.assertEqual(create_response.status_code, 200)

        login_response = self.client.post(
            "/api/v1/auth/login",
            json={"username": "alice", "password": "secret"},
        )

        self.assertEqual(login_response.status_code, 200)
        self.assertIn("access_token", login_response.cookies)
        set_cookie = login_response.headers.get("set-cookie", "")
        self.assertIn("HttpOnly", set_cookie)
        self.assertIn("Secure", set_cookie)

    def test_protected_routes_require_auth_cookie(self):
        response = self.client.get("/api/v1/projects/")
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
