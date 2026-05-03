"""Seed the users collection with realistic Algerian mock data.

Run from the project root after MongoDB is up:

    python -m scripts.seed_users

Idempotent: phone numbers are deterministic (seeded RNG), so re-running
this script after a successful run will simply skip every record with a
"phone already exists" notice. To start fresh, drop the `users` and
`counters` collections first.
"""

import random
import sys
from datetime import date

from src.database import Database, DatabaseError
from src.user_model import User
from src.user_repository import DuplicatePhoneError, UserRepository


FIRST_NAMES = [
    # Male
    "Mohamed", "Ahmed", "Ali", "Karim", "Omar", "Yacine", "Bilal", "Sofiane",
    "Rachid", "Said", "Nabil", "Hicham", "Younes", "Mehdi", "Riad", "Adel",
    "Walid", "Anis", "Faycal", "Tarek", "Mounir", "Abdelkader", "Brahim",
    # Female
    "Fatima", "Amina", "Khadija", "Yasmine", "Sara", "Nadia", "Samira",
    "Houria", "Lamia", "Soraya", "Imane", "Salima", "Karima", "Naima",
    "Wassila", "Asma", "Linda", "Meriem",
]

LAST_NAMES = [
    "Belkacem", "Boudiaf", "Hamidi", "Haddad", "Saadi", "Cherif", "Belaid",
    "Khelifi", "Mansouri", "Brahimi", "Boumediene", "Slimani", "Bensalem",
    "Ziani", "Bouchareb", "Mostefai", "Aissaoui", "Ouali", "Khaldi", "Lounis",
    "Yahiaoui", "Benyahia", "Touati", "Saidi", "Mokrani", "Benabbas",
    "Laidi", "Zerouali", "Berkane", "Belmokhtar",
]

# Wilayas / major Algerian cities used as birth places.
BIRTH_PLACES = [
    "Algiers", "Oran", "Constantine", "Annaba", "Blida", "Batna", "Setif",
    "Sidi Bel Abbes", "Biskra", "Tlemcen", "Bejaia", "Skikda", "Tiaret",
    "Bechar", "Mostaganem", "El Oued", "Ouargla", "Ghardaia", "Tizi Ouzou",
    "Djelfa", "Oum El Bouaghi", "Adrar", "Tamanrasset", "Bordj Bou Arreridj",
    "Mascara", "Chlef", "Medea", "Jijel", "Boumerdes", "Tipaza",
]


def random_birth_date(rng: random.Random) -> str:
    year = rng.randint(1955, 2005)
    month = rng.randint(1, 12)
    # Cap the day at 28 to avoid worrying about month length.
    day = rng.randint(1, 28)
    return date(year, month, day).isoformat()


def random_algerian_phone(rng: random.Random) -> str:
    """Return a +213 mobile number (operator prefix 5, 6, or 7)."""
    operator = rng.choice("567")
    rest = "".join(str(rng.randint(0, 9)) for _ in range(8))
    return f"+213{operator}{rest}"


def main(target: int = 35) -> int:
    print("Connecting to MongoDB...")
    try:
        Database.connect()
    except DatabaseError as exc:
        print(f"  FAILED: {exc}")
        return 1

    repo = UserRepository()
    before = repo.count()
    print(f"  OK (current user count: {before})")
    print(f"\nSeeding {target} Algerian users...\n")

    rng = random.Random(42)  # deterministic so reruns produce the same data
    inserted = 0
    skipped = 0
    for _ in range(target):
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        user = User(
            first_name=first,
            last_name=last,
            birth_date=random_birth_date(rng),
            birth_place=rng.choice(BIRTH_PLACES),
            phone_number=random_algerian_phone(rng),
        )
        try:
            new_id = repo.create(user)
        except DuplicatePhoneError:
            skipped += 1
            continue
        inserted += 1
        print(
            f"  [{new_id:>3}] {first:<12} {last:<14} "
            f"{user.phone_number}  {user.birth_date}  {user.birth_place}"
        )

    print(f"\nInserted: {inserted}   Skipped (duplicate phone): {skipped}")
    print(f"Total users now: {repo.count()}")
    Database.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
