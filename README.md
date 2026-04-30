# Advanced User Management System

A Python-based User Management System with a GUI and a MongoDB NoSQL backend.
Implements full CRUD (Create, Read, Update, Delete) operations on a `users`
collection through a graphical interface.

## Stack

- **Language:** Python 3.10+
- **Database:** MongoDB
- **GUI:** Tkinter / Streamlit (added in `feature/gui`)
- **Driver:** PyMongo

## Features (planned)

- Add a new user via an input form (validated)
- Display all users in a table view
- Search across every field
- Update an existing user
- Delete a user (with confirmation)
- Unique `user_id` (UUID4) per user
- Unique `phone_number` enforced at the database layer

## User document schema

| Field          | Type   | Notes                          |
| -------------- | ------ | ------------------------------ |
| `user_id`      | string | UUID4, unique (primary key)    |
| `first_name`   | string | required                       |
| `last_name`    | string | required                       |
| `birth_date`   | string | `YYYY-MM-DD`                   |
| `birth_place`  | string | required                       |
| `phone_number` | string | unique, 8-15 digits, optional + |

## Setup

1. Install MongoDB locally (or use a MongoDB Atlas cluster).
2. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux / macOS
   source venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` and adjust the connection string if needed:

   ```bash
   cp .env.example .env
   ```

5. Verify the database connection:

   ```bash
   python -m scripts.test_connection
   ```

## Project structure

```
mini_project_1/
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── scripts/
│   └── test_connection.py
└── src/
    ├── __init__.py
    ├── config.py
    ├── database.py
    ├── user_model.py
    └── user_repository.py
```

## Branching model

- `main`        — stable releases
- `develop`     — integration branch
- `feature/database` — database layer (this milestone)
- `feature/gui` — graphical interface (next milestone)
