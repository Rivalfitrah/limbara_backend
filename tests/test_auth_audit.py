import os
import unittest

from app.services.auth_audit_service import log_auth_event


class AuthAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["JWT_SECRET_KEY"] = "test-secret-key-with-at-least-32-characters"

    def test_auth_log_does_not_contain_raw_identifier(self):
        with self.assertLogs("limbara.auth", level="INFO") as captured:
            log_auth_event("login", "failed", "private@example.com")

        output = " ".join(captured.output)
        self.assertNotIn("private@example.com", output)
        self.assertIn("action=login", output)
        self.assertIn("outcome=failed", output)


if __name__ == "__main__":
    unittest.main()
