"""CRUD operations on the users collection."""

import re
from typing import List, Optional

from pymongo.errors import DuplicateKeyError

from src.database import Database
from src.user_model import User, ValidationError


class DuplicatePhoneError(ValueError):
    """Raised when an insert/update would break the unique phone constraint."""


class UserRepository:
    def __init__(self) -> None:
        self.collection = Database.get_collection()

    def create(self, user: User) -> str:
        user.validate()
        try:
            self.collection.insert_one(user.to_dict())
        except DuplicateKeyError as exc:
            if "phone_number" in str(exc):
                raise DuplicatePhoneError(
                    f"Phone number '{user.phone_number}' is already registered."
                ) from exc
            raise
        return user.user_id

    def get_by_id(self, user_id: str) -> Optional[User]:
        doc = self.collection.find_one({"user_id": user_id}, {"_id": 0})
        return User.from_dict(doc) if doc else None

    def get_all(self) -> List[User]:
        cursor = self.collection.find({}, {"_id": 0})
        return [User.from_dict(doc) for doc in cursor]

    def search(self, query: str) -> List[User]:
        if not query or not query.strip():
            return self.get_all()
        regex = {"$regex": re.escape(query), "$options": "i"}
        filt = {
            "$or": [
                {"user_id": regex},
                {"first_name": regex},
                {"last_name": regex},
                {"birth_date": regex},
                {"birth_place": regex},
                {"phone_number": regex},
            ]
        }
        cursor = self.collection.find(filt, {"_id": 0})
        return [User.from_dict(doc) for doc in cursor]

    def update(self, user_id: str, updates: dict) -> bool:
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

    def delete(self, user_id: str) -> bool:
        result = self.collection.delete_one({"user_id": user_id})
        return result.deleted_count > 0

    def count(self) -> int:
        return self.collection.count_documents({})


__all__ = ["UserRepository", "DuplicatePhoneError", "ValidationError"]
