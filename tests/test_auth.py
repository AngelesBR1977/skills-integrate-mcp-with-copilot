import json
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException
from starlette.requests import Request

from src.auth import (
    SESSION_COOKIE_NAME,
    create_session_token,
    get_session_username,
    hash_password,
    load_teacher_accounts,
    require_teacher,
    verify_password,
)


def make_request(session_token: str | None = None) -> Request:
    headers = []
    if session_token is not None:
        headers.append(
            (b"cookie", f"{SESSION_COOKIE_NAME}={session_token}".encode("ascii"))
        )
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": headers,
        "client": ("testclient", 123),
        "server": ("testserver", 80),
        "root_path": "",
    }
    return Request(scope)


class TeacherAuthTests(unittest.TestCase):
    def test_password_hash_verifies_without_storing_plaintext(self) -> None:
        credentials = hash_password("test-password")

        self.assertNotIn("test-password", json.dumps(credentials))
        self.assertTrue(
            verify_password(
                "test-password",
                credentials["salt"],
                credentials["password_hash"],
            )
        )
        self.assertFalse(
            verify_password(
                "wrong-password",
                credentials["salt"],
                credentials["password_hash"],
            )
        )

    def test_load_teacher_accounts_validates_json_credentials(self) -> None:
        credentials = hash_password("test-password")
        with tempfile.TemporaryDirectory() as directory:
            teachers_file = Path(directory) / "teachers.json"
            teachers_file.write_text(
                json.dumps(
                    {
                        "teachers": [
                            {"username": "teacher", **credentials},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                load_teacher_accounts(teachers_file),
                [{"username": "teacher", **credentials}],
            )

    def test_missing_teacher_file_returns_setup_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            teachers_file = Path(directory) / "missing-teachers.json"

            with self.assertRaises(HTTPException) as error:
                load_teacher_accounts(teachers_file)

        self.assertEqual(error.exception.status_code, 503)

    def test_signed_session_is_accepted_and_tampering_is_rejected(self) -> None:
        token = create_session_token("teacher")

        self.assertEqual(get_session_username(make_request(token)), "teacher")
        self.assertIsNone(get_session_username(make_request(token + "x")))

    def test_protected_action_requires_teacher_session(self) -> None:
        with self.assertRaises(HTTPException) as error:
            require_teacher(make_request())

        self.assertEqual(error.exception.status_code, 401)
        self.assertEqual(
            require_teacher(make_request(create_session_token("teacher"))),
            "teacher",
        )


if __name__ == "__main__":
    unittest.main()
