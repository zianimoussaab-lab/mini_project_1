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
from st_keyup import st_keyup

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
    st.session_state.setdefault("view", "list")
    st.session_state.setdefault("editing_user_id", None)
    st.session_state.setdefault("search_query", "")
    st.session_state.setdefault("users_table_rev", 0)
    st.session_state.setdefault("flash", None)
    for key, default in ADD_FORM_DEFAULTS.items():
        st.session_state.setdefault(key, default)


def clear_add_form() -> None:
    for key, default in ADD_FORM_DEFAULTS.items():
        st.session_state[key] = default


def goto_list() -> None:
    st.session_state["view"] = "list"
    st.session_state["editing_user_id"] = None


def goto_create() -> None:
    st.session_state["view"] = "create"


def goto_edit(user_id: int) -> None:
    st.session_state["view"] = "edit"
    st.session_state["editing_user_id"] = user_id


def flash(kind: str, message: str) -> None:
    st.session_state["flash"] = (kind, message)


# --------------------------------------------------------------------------- #
# Confirmation dialogs
# --------------------------------------------------------------------------- #


@st.dialog("Confirm deletion")
def confirm_bulk_delete(repo: UserRepository, user_ids: list) -> None:
    n = len(user_ids)
    if n == 1:
        st.markdown(
            "Are you sure you want to delete this user? "
            "This action cannot be undone."
        )
    else:
        st.markdown(
            f"Are you sure you want to delete **{n} users**? "
            "This action cannot be undone."
        )
    col_yes, col_no = st.columns(2)
    if col_yes.button(
        "Confirm", type="primary", use_container_width=True, key="dlg_bulk_yes"
    ):
        deleted = sum(1 for uid in user_ids if repo.delete(uid))
        st.session_state["users_table_rev"] = (
            st.session_state.get("users_table_rev", 0) + 1
        )
        flash("success", f"{deleted} user(s) deleted.")
        st.rerun()
    if col_no.button("Cancel", use_container_width=True, key="dlg_bulk_no"):
        st.rerun()


@st.dialog("Confirm deletion")
def confirm_single_delete(repo: UserRepository, user: User) -> None:
    st.markdown(
        f"Are you sure you want to delete **{user.first_name} {user.last_name}**? "
        "This action cannot be undone."
    )
    col_yes, col_no = st.columns(2)
    if col_yes.button(
        "Confirm", type="primary", use_container_width=True, key="dlg_single_yes"
    ):
        repo.delete(user.user_id)
        flash("success", "User deleted.")
        goto_list()
        st.rerun()
    if col_no.button("Cancel", use_container_width=True, key="dlg_single_no"):
        st.rerun()


def render_flash() -> None:
    pending = st.session_state.get("flash")
    if not pending:
        return
    kind, message = pending
    {"success": st.success, "error": st.error, "info": st.info}.get(kind, st.info)(message)
    st.session_state["flash"] = None


# --------------------------------------------------------------------------- #
# Styles
# --------------------------------------------------------------------------- #


def inject_app_styles() -> None:
    """Global app CSS: sidebar polish, top bar, visible inputs, form ergonomics."""
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

        /* ---------- Top bar ---------- */
        .topbar-wrap {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.6rem 1.5rem 0.6rem 1.5rem;
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            margin: 0 0 1.25rem 0;
            box-shadow: 0 1px 3px rgba(17, 24, 39, 0.05);
        }
        .topbar-nav {
            display: flex;
            align-items: center;
            gap: 1.5rem;
            margin-left: 0.5rem;
        }
        .topbar-nav .nav-item {
            font-weight: 600;
            font-size: 0.95rem;
            color: #4F46E5;
            padding: 0.35rem 0.75rem;
            border-radius: 8px;
            background: #EEF2FF;
            border: 1px solid #C7D2FE;
        }
        .topbar-user {
            display: flex;
            align-items: center;
            gap: 0.65rem;
        }
        .topbar-avatar {
            width: 34px;
            height: 34px;
            border-radius: 50%;
            background: linear-gradient(135deg, #4F46E5, #7C3AED);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 0.95rem;
            box-shadow: 0 2px 6px rgba(79, 70, 229, 0.3);
        }
        .topbar-username {
            color: #111827;
            font-weight: 600;
            font-size: 0.95rem;
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
        input[aria-label^="First name"],
        input[aria-label^="Last name"] {
            text-transform: capitalize;
        }
        div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] {
            gap: 0.35rem;
        }

        /* ---------- Red delete (icon-only) button inside forms ---------- */
        /* Targets any form button whose label is a Material Symbol (i.e. our
           bin icon). The save button uses plain text, so it's untouched. */
        div[data-testid="stForm"] button:has(span[class*="material-"]) {
            background: #DC2626 !important;
            border-color: #DC2626 !important;
            color: #FFFFFF !important;
            box-shadow: 0 2px 6px rgba(220, 38, 38, 0.25) !important;
        }
        div[data-testid="stForm"] button:has(span[class*="material-"]):hover {
            background: #B91C1C !important;
            border-color: #B91C1C !important;
        }
        div[data-testid="stForm"] button:has(span[class*="material-"]) span[class*="material-"] {
            color: #FFFFFF !important;
            font-size: 1.2rem !important;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Top bar
# --------------------------------------------------------------------------- #


def render_top_bar() -> None:
    """Sticky-style header with a Users menu (left) and admin avatar (right)."""
    # The static parts of the top bar (avatar + admin label) are pure HTML.
    # The Users navigation item must be a real Streamlit button so it can
    # trigger reruns, so we approximate the layout with columns.
    bar_left, _, bar_right = st.columns([3, 5, 3])

    with bar_left:
        # The button mimics the styled .nav-item via Streamlit's primary type.
        if st.button("Users", key="nav_users", type="primary"):
            goto_list()
            st.rerun()

    with bar_right:
        st.markdown(
            """
            <div class="topbar-user" style="justify-content: flex-end; padding-top: 0.35rem;">
                <div class="topbar-avatar">A</div>
                <span class="topbar-username">admin</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        '<hr style="margin: 0.25rem 0 1.25rem 0; border: none; border-top: 1px solid #E5E7EB;">',
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# List view
# --------------------------------------------------------------------------- #


def page_users_list(repo: UserRepository) -> None:
    # The action bar lives in this slot at the top of the page; it gets
    # filled in AFTER the dataframe renders so it can read the live selection.
    action_slot = st.empty()

    st.markdown("### Users")

    # st_keyup triggers a rerun on every keystroke (with a small debounce)
    # so the list filters as the user types instead of waiting for Enter.
    query = st_keyup(
        "Search",
        value=st.session_state["search_query"],
        placeholder="Filter by name, phone, place, birth date, or ID",
        debounce=250,
        label_visibility="collapsed",
        key="search_keyup",
    )
    st.session_state["search_query"] = query or ""

    users = repo.search(query) if query.strip() else repo.get_all()

    # Empty state — only the Create button is meaningful.
    if not users:
        with action_slot.container():
            create_col, _ = st.columns([1, 6])
            if create_col.button(
                "+ Create",
                key="btn_create_empty",
                type="primary",
                use_container_width=True,
            ):
                goto_create()
                st.rerun()
        st.info(
            "No users match your search."
            if query
            else "No users yet. Click **+ Create** to add one."
        )
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

    # The dataframe key embeds a revision counter so we can force a fresh
    # selection state after a bulk delete (otherwise stale row indices
    # could point past the end of the new shorter list).
    table_rev = st.session_state["users_table_rev"]
    event = st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row",
        column_config={
            "ID": st.column_config.NumberColumn(width="small"),
            "Phone Number": st.column_config.TextColumn(width="medium"),
        },
        key=f"users_table_{table_rev}",
    )

    selected_indices = event.selection.rows
    selected_user_ids = [users[i].user_id for i in selected_indices]
    n_selected = len(selected_user_ids)

    # Render the action bar based on how many rows are currently selected.
    with action_slot.container():
        if n_selected == 0:
            create_col, _ = st.columns([1, 6])
            if create_col.button(
                "+ Create", key="btn_create", type="primary", use_container_width=True
            ):
                goto_create()
                st.rerun()
        elif n_selected == 1:
            cols = st.columns([1, 1, 1, 5])
            if cols[0].button(
                "+ Create", key="btn_create", type="primary", use_container_width=True
            ):
                goto_create()
                st.rerun()
            if cols[1].button(
                "Edit", key="btn_edit", type="secondary", use_container_width=True
            ):
                goto_edit(selected_user_ids[0])
                st.rerun()
            if cols[2].button(
                "Delete", key="btn_delete", type="secondary", use_container_width=True
            ):
                confirm_bulk_delete(repo, list(selected_user_ids))
        else:
            # 2 or more selected — Edit hidden, only Create + Delete.
            cols = st.columns([1, 1, 5])
            if cols[0].button(
                "+ Create", key="btn_create", type="primary", use_container_width=True
            ):
                goto_create()
                st.rerun()
            if cols[1].button(
                f"Delete ({n_selected})",
                key="btn_delete",
                type="secondary",
                use_container_width=True,
            ):
                confirm_bulk_delete(repo, list(selected_user_ids))

    st.caption(
        f"{len(users)} user(s) shown — tick a row to enable Edit / Delete."
    )


# --------------------------------------------------------------------------- #
# Create view
# --------------------------------------------------------------------------- #


def page_create_user(repo: UserRepository) -> None:
    # Apply a pending clear from the previous run (after a successful add or reset).
    # Must happen BEFORE the form widgets are instantiated.
    if st.session_state.pop("_add_form_should_clear", False):
        clear_add_form()

    if st.button("< Back to list", key="back_from_create"):
        goto_list()
        st.rerun()

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
            goto_list()
            st.rerun()
        except (ValidationError, DuplicatePhoneError) as exc:
            st.error(str(exc))


# --------------------------------------------------------------------------- #
# Edit view
# --------------------------------------------------------------------------- #


def page_edit_user(repo: UserRepository, user_id: int | None) -> None:
    if st.button("< Back to list", key="back_from_edit"):
        goto_list()
        st.rerun()

    if user_id is None:
        st.error("No user selected.")
        return

    user = repo.get_by_id(user_id)
    if user is None:
        st.error(f"User #{user_id} no longer exists.")
        return

    current_country_label, current_local = split_phone(user.phone_number)

    with st.form(f"edit_form_{user.user_id}"):
        # Header row: title on the left, red icon delete button on the right.
        # The delete button is a form_submit_button because Streamlit forbids
        # st.button inside an st.form. The CSS in inject_app_styles() makes
        # the icon-only button render in red.
        title_col, _, del_col = st.columns([6, 5, 1.2])
        title_col.markdown(f"### Edit user #{user.user_id}")
        delete_clicked = del_col.form_submit_button(
            ":material/delete:",
            help="Delete this user",
            type="primary",
            use_container_width=True,
        )

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

        save_clicked = st.form_submit_button(
            "Save changes", type="primary", use_container_width=True
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
            goto_list()
            st.rerun()
        except (ValidationError, DuplicatePhoneError) as exc:
            st.error(str(exc))

    if delete_clicked:
        confirm_single_delete(repo, user)


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #


def render_sidebar(repo: UserRepository) -> None:
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

    render_sidebar(repo)
    render_top_bar()
    render_flash()

    view = st.session_state.get("view", "list")
    if view == "list":
        page_users_list(repo)
    elif view == "create":
        page_create_user(repo)
    elif view == "edit":
        page_edit_user(repo, st.session_state.get("editing_user_id"))
    else:
        # Defensive fallback if state is somehow corrupted.
        goto_list()
        st.rerun()


if __name__ == "__main__":
    main()
