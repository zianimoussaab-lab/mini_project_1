"""Smoke test for the database layer.

Run from the project root:

    python -m scripts.test_connection

It connects to MongoDB, inserts a temporary user, exercises every
CRUD method, and removes the test user before exiting. No persistent
state is left behind.
"""

import sys
import uuid

from src.database import Database, DatabaseError
from src.user_model import User
from src.user_repository import DuplicatePhoneError, UserRepository


def main() -> int:
    print("[1/6] Connecting to MongoDB...")
    try:
        Database.connect()
    except DatabaseError as exc:
        print(f"  FAILED: {exc}")
        return 1
    print("       OK")

    repo = UserRepository()
    print(f"[2/6] Current user count: {repo.count()}")

    sample = User(
        first_name="Test",
        last_name="User",
        birth_date="2000-01-15",
        birth_place="Oum El Bouaghi",
        phone_number=f"+213{uuid.uuid4().int % 10**9:09d}",
    )
    print(f"[3/6] Inserting sample user (user_id={sample.user_id})...")
    repo.create(sample)
    print("       OK")

    print("[4/6] Verifying duplicate phone is rejected...")
    duplicate = User(
        first_name="Other",
        last_name="Person",
        birth_date="1995-06-01",
        birth_place="Algiers",
        phone_number=sample.phone_number,
    )
    try:
        repo.create(duplicate)
    except DuplicatePhoneError:
        print("       OK (duplicate correctly rejected)")
    else:
        print("       FAILED: duplicate phone was accepted")
        return 1

    print("[5/6] Updating birth_place and re-reading...")
    repo.update(sample.user_id, {"birth_place": "Constantine"})
    fetched = repo.get_by_id(sample.user_id)
    assert fetched is not None and fetched.birth_place == "Constantine"
    print("       OK")

    print("[6/6] Deleting the sample user...")
    deleted = repo.delete(sample.user_id)
    assert deleted is True
    print("       OK")

    Database.close()
    print("\nAll database checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
