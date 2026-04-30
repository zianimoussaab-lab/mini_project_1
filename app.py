"""Streamlit GUI for the Advanced User Management System.

Run from the project root:

    streamlit run app.py

Requires a running MongoDB instance reachable through the URI in `.env`.
"""

import os
import sys
from datetime import date, datetime

# Make `src.*` importable when Streamlit launches this file.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

from src.database import Database, DatabaseError
from src.user_model import DATE_FORMAT, User, ValidationError
from src.user_repository import DuplicatePhoneError, UserRepository


st.set_page_config(
    page_title="User Management System",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------------------------------- #
# Bootstrap
# --------------------------------------------------------------------------- #


@st.cache_resource(show_spinner="Connecting to MongoDB...")
def get_repository() -> UserRepository:
    Database.connect()
    return UserRepository()


def init_state() -> None:
    st.session_state.setdefault("search_query", "")
    st.session_state.setdefault("selected_user_id", None)
    st.session_state.setdefault("delete_target_id", None)
    st.session_state.setdefault("flash", None)


def flash(kind: str, message: str) -> None:
    st.session_state["flash"] = (kind, message)


def render_flash() -> None:
    pending = st.session_state.get("flash")
    if not pending:
        return
    kind, message = pending
    {"success": st.success, "error": st.error, "info": st.info}.get(kind, st.info)(message)
    st.session_state["flash"] = None


# --------------------------------------------------------------------------- #
# Add User
# --------------------------------------------------------------------------- #


def page_add_user(repo: UserRepository) -> None:
    st.subheader("Add a new user")
    st.caption("All fields are required. Phone number must be unique across users.")

    with st.form("add_user_form", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        first_name = col_a.text_input("First name")
        last_name = col_b.text_input("Last name")

        col_c, col_d = st.columns(2)
        birth_date = col_c.date_input(
            "Birth date",
            value=None,
            min_value=date(1900, 1, 1),
            max_value=date.today(),
            format="YYYY-MM-DD",
        )
        birth_place = col_d.text_input("Birth place")

        phone_number = st.text_input(
            "Phone number",
            placeholder="+213XXXXXXXXX",
            help="8 to 15 digits, may start with '+'.",
        )

        submitted = st.form_submit_button("Add user", type="primary", use_container_width=True)

    if submitted:
        try:
            user = User(
                first_name=first_name.strip(),
                last_name=last_name.strip(),
                birth_date=birth_date.strftime(DATE_FORMAT) if birth_date else "",
                birth_place=birth_place.strip(),
                phone_number=phone_number.strip(),
            )
            user_id = repo.create(user)
            flash("success", f"User added (ID: {user_id}).")
            st.rerun()
        except (ValidationError, DuplicatePhoneError) as exc:
            st.error(str(exc))


# --------------------------------------------------------------------------- #
# Browse / Search / Edit / Delete
# --------------------------------------------------------------------------- #


def page_browse(repo: UserRepository) -> None:
    st.subheader("Browse users")

    query = st.text_input(
        "Search",
        value=st.session_state["search_query"],
        placeholder="Filter by name, phone, place, birth date, or ID",
        label_visibility="collapsed",
    )
    st.session_state["search_query"] = query

    users = repo.search(query) if query.strip() else repo.get_all()

    if not users:
        st.info("No users match your search." if query else "No users yet. Add one from the 'Add user' tab.")
        return

    rows = [
        {
            "ID": u.user_id,
            "First Name": u.first_name,
            "Last Name": u.last_name,
            "Birth Date": u.birth_date,
            "Birth Place": u.birth_place,
            "Phone Number": u.phone_number,
        }
        for u in users
    ]
    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID": st.column_config.TextColumn(width="small"),
            "Phone Number": st.column_config.TextColumn(width="medium"),
        },
    )

    st.markdown(f"**{len(users)}** user(s) shown.")
    st.divider()

    options = {
        f"{u.first_name} {u.last_name}  -  {u.phone_number}": u.user_id for u in users
    }
    pick = st.selectbox(
        "Select a user to edit or delete",
        options=["-"] + list(options.keys()),
        index=0,
    )
    if pick != "-":
        selected = repo.get_by_id(options[pick])
        if selected:
            render_edit_panel(repo, selected)


def render_edit_panel(repo: UserRepository, user: User) -> None:
    st.markdown(f"#### Editing `{user.user_id}`")

    with st.form(f"edit_form_{user.user_id}"):
        col_a, col_b = st.columns(2)
        first_name = col_a.text_input("First name", value=user.first_name)
        last_name = col_b.text_input("Last name", value=user.last_name)

        col_c, col_d = st.columns(2)
        try:
            birth_default = datetime.strptime(user.birth_date, DATE_FORMAT).date()
        except ValueError:
            birth_default = None
        birth_date = col_c.date_input(
            "Birth date",
            value=birth_default,
            min_value=date(1900, 1, 1),
            max_value=date.today(),
            format="YYYY-MM-DD",
        )
        birth_place = col_d.text_input("Birth place", value=user.birth_place)

        phone_number = st.text_input("Phone number", value=user.phone_number)

        save_clicked = st.form_submit_button("Save changes", type="primary", use_container_width=True)

    delete_clicked = st.button(
        "Delete this user",
        key=f"delete_btn_{user.user_id}",
        type="secondary",
        use_container_width=True,
    )

    if save_clicked:
        try:
            updates = {
                "first_name": first_name.strip(),
                "last_name": last_name.strip(),
                "birth_date": birth_date.strftime(DATE_FORMAT) if birth_date else "",
                "birth_place": birth_place.strip(),
                "phone_number": phone_number.strip(),
            }
            repo.update(user.user_id, updates)
            flash("success", "User updated.")
            st.rerun()
        except (ValidationError, DuplicatePhoneError) as exc:
            st.error(str(exc))

    if delete_clicked:
        st.session_state["delete_target_id"] = user.user_id

    if st.session_state.get("delete_target_id") == user.user_id:
        st.warning(
            f"Are you sure you want to delete **{user.first_name} {user.last_name}**? "
            "This action cannot be undone."
        )
        col_yes, col_no = st.columns(2)
        if col_yes.button("Yes, delete", key=f"confirm_del_{user.user_id}", type="primary", use_container_width=True):
            repo.delete(user.user_id)
            st.session_state["delete_target_id"] = None
            flash("success", "User deleted.")
            st.rerun()
        if col_no.button("Cancel", key=f"cancel_del_{user.user_id}", use_container_width=True):
            st.session_state["delete_target_id"] = None
            st.rerun()


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #


def main() -> None:
    init_state()

    try:
        repo = get_repository()
    except DatabaseError as exc:
        st.error(f"Database connection failed: {exc}")
        st.info("Make sure MongoDB is running and `.env` is configured correctly.")
        st.stop()
        return

    with st.sidebar:
        st.title("User Management")
        st.caption("Advanced User Management System")
        st.divider()
        st.metric("Total users", repo.count())
        st.divider()
        st.caption("MongoDB-backed CRUD with Streamlit.")

    st.title("Users")
    render_flash()

    tab_browse, tab_add = st.tabs(["Browse / Edit", "Add user"])
    with tab_browse:
        page_browse(repo)
    with tab_add:
        page_add_user(repo)


if __name__ == "__main__":
    main()
