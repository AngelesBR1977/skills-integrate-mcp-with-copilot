import json
import os
from getpass import getpass
from pathlib import Path

from src.auth import hash_password

teachers_file = Path(__file__).parent / "teachers.json"


def main() -> None:
    username = input("Teacher username: ").strip()
    if not username:
        raise SystemExit("Username cannot be empty.")

    password = getpass("Teacher password: ")
    if not password:
        raise SystemExit("Password cannot be empty.")
    if password != getpass("Confirm password: "):
        raise SystemExit("Passwords do not match.")

    if teachers_file.exists():
        try:
            data = json.loads(teachers_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit("teachers.json contains invalid JSON.") from exc
    else:
        data = {"teachers": []}

    if not isinstance(data, dict) or not isinstance(data.get("teachers"), list):
        raise SystemExit("teachers.json must contain a teachers list.")

    if any(
        isinstance(teacher, dict)
        and isinstance(teacher.get("username"), str)
        and teacher["username"].casefold() == username.casefold()
        for teacher in data["teachers"]
    ):
        raise SystemExit("That teacher username already exists.")

    data["teachers"].append(
        {
            "username": username,
            **hash_password(password),
        }
    )
    teachers_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.chmod(teachers_file, 0o600)
    print(f"Added teacher account {username!r} to {teachers_file}.")


if __name__ == "__main__":
    main()
