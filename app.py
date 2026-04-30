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
# Constants and helpers
# --------------------------------------------------------------------------- #

# Country code dropdown. Algeria is intentionally first so it is the default.
COUNTRIES = {
    "Algeria (+213)": "+213",
    "Morocco (+212)": "+212",
    "Tunisia (+216)": "+216",
    "Libya (+218)": "+218",
    "Egypt (+20)": "+20",
    "France (+33)": "+33",
    "Spain (+34)": "+34",
    "Italy (+39)": "+39",
    "Germany (+49)": "+49",
    "United Kingdom (+44)": "+44",
    "United States (+1)": "+1",
    "Turkey (+90)": "+90",
    "Saudi Arabia (+966)": "+966",
    "United Arab Emirates (+971)": "+971",
}

DISPLAY_DATE_FORMAT = "%d/%m/%Y"


def format_date_display(iso_date: str) -> str:
    """Convert YYYY-MM-DD storage format to DD/MM/YYYY for display."""
    try:
        return datetime.strptime(iso_date, DATE_FORMAT).strftime(DISPLAY_DATE_FORMAT)
    except ValueError:
        return iso_date


def split_phone(full: str) -> tuple[str, str]:
    """Return (country_label, local_digits) for a stored phone number."""
    for label, code in COUNTRIES.items():
        if full.startswith(code):
            return label, full[len(code):]
    first_label = next(iter(COUNTRIES))
    return first_label, full.lstrip("+")


# --------------------------------------------------------------------------- #
# Bootstrap
# --------------------------------------------------------------------------- #


@st.cache_resource(show_spinner="Connecting to MongoDB...")
def get_repository() -> UserRepository:
    Database.connect()
    return UserRepository()


ADD_FORM_DEFAULTS = {
    "add_first_name": "",
    "add_last_name": "",
    "add_birth_date": None,
    "add_birth_place": "",
    "add_country": next(iter(COUNTRIES)),
    "add_phone_local": "",
}


def init_state() -> None:
    st.session_state.setdefault("search_query", "")
    st.session_state.setdefault("selected_user_id", None)
    st.session_state.setdefault("delete_target_id", None)
    st.session_state.setdefault("flash", None)
    for key, default in ADD_FORM_DEFAULTS.items():
        st.session_state.setdefault(key, default)


def clear_add_form() -> None:
    for key, default in ADD_FORM_DEFAULTS.items():
        st.session_state[key] = default


def inject_app_styles() -> None:
    """Global app CSS: sidebar polish, visible input borders, form ergonomics."""
    st.markdown(
        """
        <style>
        /* ---------- Sidebar ---------- */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #F9FAFB 0%, #EEF2FF 100%);
            border-right: 1px solid #E5E7EB;
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] hr {
            border-color: #E5E7EB;
            margin: 1rem 0;
        }

        /* ---------- Input visibility ---------- */
        [data-baseweb="input"],
        [data-baseweb="select"] > div:first-child {
            background-color: #FFFFFF !important;
            border: 1.5px solid #D1D5DB !important;
            border-radius: 8px !important;
            box-shadow: 0 1px 2px rgba(17, 24, 39, 0.04);
            transition: border-color 0.15s ease, box-shadow 0.15s ease;
        }
        [data-baseweb="input"]:focus-within,
        [data-baseweb="select"]:focus-within > div:first-child {
            border-color: #4F46E5 !important;
            box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.18) !important;
        }
        [data-baseweb="input"]:hover,
        [data-baseweb="select"]:hover > div:first-child {
            border-color: #9CA3AF !important;
        }

        /* ---------- Form ergonomics ---------- */
        /* Visually capitalize each word in name fields as the user types. */
        input[aria-label^="First name"],
        input[aria-label^="Last name"] {
            text-transform: capitalize;
        }
        /* Tighten the gap between columns within forms. */
        div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] {
            gap: 0.35rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


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
    # Apply a pending clear (set on the previous run after a successful add or reset).
    # We must do this BEFORE the widgets are instantiated, otherwise Streamlit
    # forbids assigning to widget-keyed session_state.
    if st.session_state.pop("_add_form_should_clear", False):
        clear_add_form()

    st.subheader("Add a new user")

    with st.form("add_user_form", clear_on_submit=False):
        col_a, col_b = st.columns(2)
        first_name = col_a.text_input("First name :red[*]", key="add_first_name")
        last_name = col_b.text_input("Last name :red[*]", key="add_last_name")

        col_c, col_d = st.columns(2)
        birth_date = col_c.date_input(
            "Birth date :red[*]",
            min_value=date(1900, 1, 1),
            max_value=date.today(),
            format="DD/MM/YYYY",
            key="add_birth_date",
        )
        birth_place = col_d.text_input("Birth place :red[*]", key="add_birth_place")

        col_country, col_phone, _ = st.columns([1.5, 8, 2.5])
        country_label = col_country.selectbox(
            "Country :red[*]",
            options=list(COUNTRIES.keys()),
            key="add_country",
        )
        country_code = COUNTRIES[country_label]
        phone_local = col_phone.text_input(
            "Phone number :red[*]",
            placeholder="e.g. 555123456",
            help=f"Country code {country_code} is added automatically.",
            key="add_phone_local",
        )

        # Compact button strip: both buttons inside a narrow nested column.
        button_strip, _ = st.columns([3, 9])
        with button_strip:
            btn_add, btn_reset = st.columns(2)
            submitted = btn_add.form_submit_button(
                "Add user", type="primary", use_container_width=True
            )
            reset_clicked = btn_reset.form_submit_button(
                "Reset", use_container_width=True
            )

    if reset_clicked:
        st.session_state["_add_form_should_clear"] = True
        st.rerun()

    if submitted:
        try:
            phone_full = f"{country_code}{phone_local.strip().lstrip('0')}"
            user = User(
                first_name=first_name.strip().title(),
                last_name=last_name.strip().title(),
                birth_date=birth_date.strftime(DATE_FORMAT) if birth_date else "",
                birth_place=birth_place.strip(),
                phone_number=phone_full,
            )
            user_id = repo.create(user)
            st.session_state["_add_form_should_clear"] = True
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
            "Birth Date": format_date_display(u.birth_date),
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

    current_country_label, current_local = split_phone(user.phone_number)

    with st.form(f"edit_form_{user.user_id}"):
        col_a, col_b = st.columns(2)
        first_name = col_a.text_input("First name :red[*]", value=user.first_name)
        last_name = col_b.text_input("Last name :red[*]", value=user.last_name)

        col_c, col_d = st.columns(2)
        try:
            birth_default = datetime.strptime(user.birth_date, DATE_FORMAT).date()
        except ValueError:
            birth_default = None
        birth_date = col_c.date_input(
            "Birth date :red[*]",
            value=birth_default,
            min_value=date(1900, 1, 1),
            max_value=date.today(),
            format="DD/MM/YYYY",
        )
        birth_place = col_d.text_input("Birth place :red[*]", value=user.birth_place)

        country_options = list(COUNTRIES.keys())
        col_country, col_phone, _ = st.columns([1.5, 8, 2.5])
        country_label = col_country.selectbox(
            "Country :red[*]",
            options=country_options,
            index=country_options.index(current_country_label),
        )
        country_code = COUNTRIES[country_label]
        phone_local = col_phone.text_input(
            "Phone number :red[*]",
            value=current_local,
            help=f"Country code {country_code} is added automatically.",
        )

        save_clicked = st.form_submit_button("Save changes", type="primary", use_container_width=True)

    delete_clicked = st.button(
        "Delete this user",
        key=f"delete_btn_{user.user_id}",
        type="secondary",
        use_container_width=True,
    )

    if save_clicked:
        try:
            phone_full = f"{country_code}{phone_local.strip().lstrip('0')}"
            updates = {
                "first_name": first_name.strip().title(),
                "last_name": last_name.strip().title(),
                "birth_date": birth_date.strftime(DATE_FORMAT) if birth_date else "",
                "birth_place": birth_place.strip(),
                "phone_number": phone_full,
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
    inject_app_styles()

    try:
        repo = get_repository()
    except DatabaseError as exc:
        st.error(f"Database connection failed: {exc}")
        st.info("Make sure MongoDB is running and `.env` is configured correctly.")
        st.stop()
        return

    with st.sidebar:
        st.markdown(
            """
            <div style="
                background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                color: transparent;
                font-size: 2.1rem;
                font-weight: 800;
                margin: 0.5rem 0 0.1rem 0;
                letter-spacing: -0.025em;
                line-height: 1.1;
            ">User Management</div>
            <div style="
                color: #6B7280;
                font-size: 0.82rem;
                margin-bottom: 0.5rem;
                letter-spacing: 0.02em;
            ">Advanced User Management System</div>
            """,
            unsafe_allow_html=True,
        )
        st.divider()
        total = repo.count()
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
                color: white;
                padding: 1.5rem 1rem;
                border-radius: 14px;
                text-align: center;
                margin: 0.5rem 0 1rem 0;
                box-shadow: 0 6px 18px rgba(79, 70, 229, 0.25);
            ">
                <div style="font-size: 2.75rem; font-weight: 800; line-height: 1;">{total}</div>
                <div style="
                    font-size: 0.78rem;
                    opacity: 0.95;
                    margin-top: 0.4rem;
                    letter-spacing: 0.12em;
                    text-transform: uppercase;
                    font-weight: 600;
                ">Total users</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.title("Users")
    render_flash()

    tab_browse, tab_add = st.tabs(["Browse / Edit", "Add user"])
    with tab_browse:
        page_browse(repo)
    with tab_add:
        page_add_user(repo)


if __name__ == "__main__":
    main()
