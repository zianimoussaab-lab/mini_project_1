"""CRUD operations on the users collection."""

import re
from typing import List, Optional

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from src.database import Database
from src.user_model import User, ValidationError


class DuplicatePhoneError(ValueError):
    """Raised when an insert/update would break the unique phone constraint."""


COUNTER_COLLECTION = "counters"
USERS_COUNTER_ID = "users_seq"


class UserRepository:
    def __init__(self) -> None:
        self.collection = Database.get_collection()
        self.counters = self.collection.database[COUNTER_COLLECTION]

    def _next_user_id(self) -> int:
        """Atomically allocate the next sequential user_id (starts at 1)."""
        result = self.counters.find_one_and_update(
            {"_id": USERS_COUNTER_ID},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return int(result["seq"])

    def create(self, user: User) -> int:
        user.validate()
        user.user_id = self._next_user_id()
        try:
            self.collection.insert_one(user.to_dict())
        except DuplicateKeyError as exc:
            if "phone_number" in str(exc):
                raise DuplicatePhoneError(
                    f"Phone number '{user.phone_number}' is already registered."
                ) from exc
            raise
        return user.user_id

    def get_by_id(self, user_id: int) -> Optional[User]:
        doc = self.collection.find_one({"user_id": user_id}, {"_id": 0})
        return User.from_dict(doc) if doc else None

    def get_all(self) -> List[User]:
        cursor = self.collection.find({}, {"_id": 0}).sort("user_id", 1)
        return [User.from_dict(doc) for doc in cursor]

    def search(self, query: str) -> List[User]:
        if not query or not query.strip():
            return self.get_all()
        regex = {"$regex": re.escape(query), "$options": "i"}
        or_clauses = [
            {"first_name": regex},
            {"last_name": regex},
            {"birth_date": regex},
            {"birth_place": regex},
            {"phone_number": regex},
        ]
        # user_id is numeric; only match if the query parses as an int.
        try:
            or_clauses.append({"user_id": int(query.strip())})
        except ValueError:
            pass
        cursor = self.collection.find({"$or": or_clauses}, {"_id": 0}).sort("user_id", 1)
        return [User.from_dict(doc) for doc in cursor]

    def update(self, user_id: int, updates: dict) -> bool:
        # user_id is immutable.
        updates = {k: v for k, v in updates.items() if k != "user_id"}
        if not updates:
            return False

        existing = self.get_by_id(user_id)
        if existing is None:
            return False

        merged = User.from_dict({**existing.to_dict(), **updates})
        merged.validate()

        try:
            result = self.collection.update_one(
                {"user_id": user_id}, {"$set": updates}
            )
        except DuplicateKeyError as exc:
            raise DuplicatePhoneError(
                f"Phone number '{updates.get('phone_number')}' is already registered."
            ) from exc
        return result.matched_count > 0

    def delete(self, user_id: int) -> bool:
        result = self.collection.delete_one({"user_id": user_id})
        return result.deleted_count > 0

    def count(self) -> int:
        return self.collection.count_documents({})


__all__ = ["UserRepository", "DuplicatePhoneError", "ValidationError"]
