"""User domain model with field-level validation."""

import re
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Optional

DATE_FORMAT = "%Y-%m-%d"
PHONE_PATTERN = re.compile(r"^\+?[0-9]{8,15}$")

REQUIRED_FIELDS = (
    "first_name",
    "last_name",
    "birth_date",
    "birth_place",
    "phone_number",
)


class ValidationError(ValueError):
    """Raised when a User instance fails validation."""


@dataclass
class User:
    first_name: str
    last_name: str
    birth_date: str  # stored as 'YYYY-MM-DD'
    birth_place: str
    phone_number: str
    user_id: Optional[int] = None  # assigned by the repository on insert

    def validate(self) -> None:
        for name in REQUIRED_FIELDS:
            value = getattr(self, name)
            if value is None or not str(value).strip():
                raise ValidationError(f"Field '{name}' cannot be empty.")

        try:
            parsed = datetime.strptime(self.birth_date, DATE_FORMAT).date()
        except ValueError as exc:
            raise ValidationError("Birth date must follow the YYYY-MM-DD format.") from exc
        if parsed > date.today():
            raise ValidationError("Birth date cannot be in the future.")

        if not PHONE_PATTERN.match(self.phone_number):
            raise ValidationError(
                "Phone number must contain 8 to 15 digits and may start with '+'."
            )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(
            user_id=data.get("user_id"),
            first_name=data["first_name"],
            last_name=data["last_name"],
            birth_date=data["birth_date"],
            birth_place=data["birth_place"],
            phone_number=data["phone_number"],
        )
