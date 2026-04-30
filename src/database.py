"""MongoDB connection management and index setup."""

from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from src.config import (
    CONNECTION_TIMEOUT_MS,
    MONGO_COLLECTION,
    MONGO_DB_NAME,
    MONGO_URI,
)


class DatabaseError(Exception):
    """Raised when the database cannot be reached or initialized."""


class Database:
    """Singleton-style holder for the MongoDB client and users collection."""

    _client: MongoClient | None = None
    _collection: Collection | None = None

    @classmethod
    def connect(cls) -> Collection:
        if cls._collection is not None:
            return cls._collection
        try:
            cls._client = MongoClient(
                MONGO_URI, serverSelectionTimeoutMS=CONNECTION_TIMEOUT_MS
            )
            # Force a round-trip so failures surface immediately.
            cls._client.admin.command("ping")
        except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
            raise DatabaseError(f"Could not connect to MongoDB at {MONGO_URI}: {exc}") from exc

        cls._collection = cls._client[MONGO_DB_NAME][MONGO_COLLECTION]
        cls._ensure_indexes()
        return cls._collection

    @classmethod
    def get_collection(cls) -> Collection:
        if cls._collection is None:
            cls.connect()
        return cls._collection  # type: ignore[return-value]

    @classmethod
    def close(cls) -> None:
        if cls._client is not None:
            cls._client.close()
        cls._client = None
        cls._collection = None

    @classmethod
    def _ensure_indexes(cls) -> None:
        # user_id is the application-level primary key.
        cls._collection.create_index([("user_id", ASCENDING)], unique=True)
        # phone_number must be unique per the project spec.
        cls._collection.create_index([("phone_number", ASCENDING)], unique=True)
