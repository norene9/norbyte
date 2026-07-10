import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import HTTPException

from app.core.security import require_admin


class UserRouterAuthTests(unittest.TestCase):
    def test_admin_role_is_allowed(self):
        self.assertIsNone(require_admin("admin"))

    def test_non_admin_role_is_rejected(self):
        with self.assertRaises(HTTPException) as context:
            require_admin("user")

        self.assertEqual(context.exception.status_code, 403)
        self.assertIn("Only admins", str(context.exception.detail))


if __name__ == "__main__":
    unittest.main()
