from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    import google.generativeai as genai
except ImportError:
    genai = None


# Change this value before sharing the app.
OWNER_PASSWORD = st.secrets["OWNER_PASSWORD"]
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
GEMINI_MODEL = "gemini-2.5-flash"

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
RECEIPTS_DIR = APP_DIR / "receipts"
SHORTFALL_PHOTOS_DIR = APP_DIR / "shortfall_photos"
EXPENSES_FILE = DATA_DIR / "expenses.csv"
SHORTFALLS_FILE = DATA_DIR / "shortfalls.csv"

EXPENSE_COLUMNS = [
    "id",
    "date",
    "amount",
    "store_name",
    "items",
    "receipt_path",
    "created_at",
]
SHORTFALL_COLUMNS = [
    "id",
    "date",
    "item_name",
    "urgency",
    "notes",
    "photo_path",
    "status",
    "created_at",
]
URGENCY_OPTIONS = ["Low", "Medium", "Urgent"]

TRANSLATIONS = {
    "English": {
        "submit_receipt": "Submit Receipt",
        "report_shortfall": "Report Shortfall",
        "receipt_instruction": "Upload a receipt, tap Read Receipt with AI, review the details, then submit.",
        "upload_receipt": "Upload Receipt",
        "receipt_help": "Take a photo of the receipt or upload from gallery.",
        "read_with_ai": "Read Receipt with AI",
        "reading_receipt": "Reading receipt with Gemini...",
        "ai_success": "Receipt read successfully. Please review and edit the details.",
        "ai_failed": "Gemini could not read this receipt. Enter the details manually and submit.",
        "gemini_package_missing": "Gemini package is missing. Install it with: pip install google-generativeai",
        "gemini_key_missing": "Add your Gemini API key to GEMINI_API_KEY near the top of app.py.",
        "amount_spent": "Amount Spent ($)",
        "store_name": "Store Name",
        "store_placeholder": "Store name (if available)",
        "items_bought": "Items Bought (one per line)",
        "items_placeholder": "Milk\nBread\nEggs",
        "receipt_required": "Please take or upload a receipt photo.",
        "amount_required": "Enter an amount greater than zero.",
        "receipt_success": "Receipt submitted successfully.",
        "receipt_save_error": "The receipt could not be saved. Please try again.",
        "shortfall_instruction": "Tell the owner what is running low or finished.",
        "upload_item_photo": "Upload Item Photo",
        "item_name": "Item Name",
        "item_placeholder": "e.g. Milk powder, diapers, rice",
        "urgency": "Urgency",
        "low": "Low",
        "medium": "Medium",
        "urgent": "Urgent",
        "notes": "Notes (optional)",
        "notes_placeholder": "Add any useful details",
        "submit_shortfall": "Submit Shortfall",
        "photo_required": "Please take or upload an item photo.",
        "item_required": "Enter the item name.",
        "shortfall_success": "Shortfall reported successfully.",
        "shortfall_save_error": "The shortfall could not be saved. Please try again.",
    },
    "Burmese (Myanmar)": {
        "submit_receipt": "ပြေစာတင်ရန်",
        "report_shortfall": "လိုအပ်နေသော ပစ္စည်း တင်ပြရန်",
        "receipt_instruction": "ပြေစာကို တင်ပါ၊ AI ဖြင့် ဖတ်ရန် နှိပ်ပါ၊ အချက်အလက်များကို စစ်ဆေးပြီး တင်ပါ။",
        "upload_receipt": "ပြေစာ အပ်လုဒ်တင်ရန်",
        "receipt_help": "ပြေစာကို ဓာတ်ပုံရိုက်ပါ သို့မဟုတ် ဖုန်းဓာတ်ပုံများထဲမှ ရွေးတင်ပါ။",
        "read_with_ai": "AI ဖြင့် ပြေစာဖတ်ရန်",
        "reading_receipt": "Gemini ဖြင့် ပြေစာဖတ်နေသည်...",
        "ai_success": "ပြေစာကို ဖတ်ပြီးပါပြီ။ အချက်အလက်များကို စစ်ဆေးပြီး လိုအပ်သလို ပြင်ပါ။",
        "ai_failed": "Gemini က ပြေစာကို မဖတ်နိုင်ပါ။ အချက်အလက်များကို ကိုယ်တိုင်ဖြည့်ပြီး တင်ပါ။",
        "gemini_package_missing": "Gemini package မရှိသေးပါ။ ဤ command ဖြင့် ထည့်ပါ: pip install google-generativeai",
        "gemini_key_missing": "app.py အပေါ်ပိုင်းရှိ GEMINI_API_KEY တွင် Gemini API key ကို ထည့်ပါ။",
        "amount_spent": "သုံးစွဲသည့် ငွေပမာဏ ($)",
        "store_name": "ဆိုင်အမည်",
        "store_placeholder": "ဆိုင်အမည် (ရှိပါက)",
        "items_bought": "ဝယ်ယူခဲ့သော ပစ္စည်းများ (တစ်ကြောင်းလျှင် တစ်မျိုး)",
        "items_placeholder": "နို့\nပေါင်မုန့်\nကြက်ဥ",
        "receipt_required": "ပြေစာဓာတ်ပုံကို ရိုက်ပါ သို့မဟုတ် တင်ပါ။",
        "amount_required": "သုညထက်ကြီးသော ငွေပမာဏကို ဖြည့်ပါ။",
        "receipt_success": "ပြေစာကို အောင်မြင်စွာ တင်ပြီးပါပြီ။",
        "receipt_save_error": "ပြေစာကို သိမ်း၍မရပါ။ ထပ်မံကြိုးစားပါ။",
        "shortfall_instruction": "ကုန်လုနီးပါး သို့မဟုတ် ကုန်သွားသော ပစ္စည်းကို ပိုင်ရှင်ထံ အသိပေးပါ။",
        "upload_item_photo": "ပစ္စည်းဓာတ်ပုံ တင်ရန်",
        "item_name": "ပစ္စည်းအမည်",
        "item_placeholder": "ဥပမာ - နို့မှုန့်၊ ဒိုင်ပါ၊ ဆန်",
        "urgency": "အရေးပေါ်အဆင့်",
        "low": "နည်း",
        "medium": "အလယ်အလတ်",
        "urgent": "အရေးပေါ်",
        "notes": "မှတ်ချက် (မဖြည့်လည်းရသည်)",
        "notes_placeholder": "လိုအပ်သော အသေးစိတ်အချက်များ ဖြည့်ပါ",
        "submit_shortfall": "လိုအပ်ချက် တင်ရန်",
        "photo_required": "ပစ္စည်းဓာတ်ပုံကို ရိုက်ပါ သို့မဟုတ် တင်ပါ။",
        "item_required": "ပစ္စည်းအမည်ကို ဖြည့်ပါ။",
        "shortfall_success": "လိုအပ်နေသော ပစ္စည်းကို အောင်မြင်စွာ တင်ပြီးပါပြီ။",
        "shortfall_save_error": "လိုအပ်ချက်ကို သိမ်း၍မရပါ။ ထပ်မံကြိုးစားပါ။",
    },
}


def translate(key: str) -> str:
    language = st.session_state.get("helper_language", "English")
    return TRANSLATIONS[language][key]


def write_csv(records: pd.DataFrame, csv_path: Path, columns: list[str]) -> None:
    """Write a CSV through a temporary file to avoid partially written data."""
    temporary_path = csv_path.with_name(f".{csv_path.name}.{uuid.uuid4().hex}.tmp")
    try:
        records.reindex(columns=columns).to_csv(temporary_path, index=False)
        temporary_path.replace(csv_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def initialise_csv(csv_path: Path, columns: list[str]) -> None:
    if not csv_path.exists():
        write_csv(pd.DataFrame(columns=columns), csv_path, columns)
        return

    try:
        records = pd.read_csv(csv_path, keep_default_na=False)
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        records = pd.DataFrame(columns=columns)

    if list(records.columns) != columns:
        for column in columns:
            if column not in records.columns:
                records[column] = ""
        write_csv(records, csv_path, columns)


def initialise_storage() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    RECEIPTS_DIR.mkdir(exist_ok=True)
    SHORTFALL_PHOTOS_DIR.mkdir(exist_ok=True)
    initialise_csv(EXPENSES_FILE, EXPENSE_COLUMNS)
    initialise_csv(SHORTFALLS_FILE, SHORTFALL_COLUMNS)


def load_csv(csv_path: Path, columns: list[str]) -> pd.DataFrame:
    try:
        records = pd.read_csv(csv_path, keep_default_na=False)
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        return pd.DataFrame(columns=columns)

    for column in columns:
        if column not in records.columns:
            records[column] = ""
    return records[columns]


def load_expenses() -> pd.DataFrame:
    expenses = load_csv(EXPENSES_FILE, EXPENSE_COLUMNS)
    expenses["amount"] = pd.to_numeric(expenses["amount"], errors="coerce").fillna(0.0)
    return expenses


def load_shortfalls() -> pd.DataFrame:
    return load_csv(SHORTFALLS_FILE, SHORTFALL_COLUMNS)


def safe_filename(filename: str, label: str) -> str:
    uploaded_path = Path(filename)
    stem = re.sub(r"[^A-Za-z0-9_-]+", "-", uploaded_path.stem).strip("-") or label
    suffix = uploaded_path.suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png"}:
        suffix = ".jpg"
    return f"{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:8]}-{stem}{suffix}"


def stored_image_path(relative_path: str, allowed_folder: Path) -> Path | None:
    """Return a stored image path only when it remains inside its allowed folder."""
    if not relative_path:
        return None
    try:
        candidate = (APP_DIR / relative_path).resolve()
        candidate.relative_to(allowed_folder.resolve())
        return candidate
    except (OSError, ValueError):
        return None


def parse_items(value: object) -> list[str]:
    if value is None or pd.isna(value):
        return []

    text = str(value).strip()
    if not text:
        return []

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except (json.JSONDecodeError, TypeError):
        pass

    return [item.strip() for item in re.split(r"[\n,;]+", text) if item.strip()]


def read_receipt_with_gemini(receipt) -> tuple[float, str, list[str]]:
    if genai is None:
        raise RuntimeError("package_missing")
    if not GEMINI_API_KEY or GEMINI_API_KEY == "paste-your-key-here":
        raise RuntimeError("key_missing")

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)
    prompt = """
Read this shopping receipt and return only valid JSON with this exact structure:
{
  "amount": 0.0,
  "store_name": "",
  "items": ["item name"]
}

Rules:
- amount is the final total actually paid, as a number without a currency symbol.
- store_name is the merchant/store name, or an empty string if unavailable.
- items contains only purchased grocery or product names.
- Exclude prices, totals, taxes, discounts, payment methods, and receipt metadata.
- Keep useful quantities or sizes when clearly visible.
- If the receipt is unclear, use 0, an empty string, or an empty list as appropriate.
"""
    image_part = {
        "mime_type": receipt.type or "image/jpeg",
        "data": receipt.getvalue(),
    }
    response = model.generate_content(
        [prompt, image_part],
        generation_config={"response_mime_type": "application/json"},
    )

    response_text = response.text.strip()
    if response_text.startswith("```"):
        response_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", response_text)
    result = json.loads(response_text)

    amount = max(0.0, float(result.get("amount", 0)))
    store_name = str(result.get("store_name", "")).strip()
    raw_items = result.get("items", [])
    if not isinstance(raw_items, list):
        raw_items = []
    items = [str(item).strip() for item in raw_items if str(item).strip()]
    return amount, store_name, items


def save_receipt(amount: float, store_name: str, items: list[str], receipt) -> None:
    destination = RECEIPTS_DIR / safe_filename(receipt.name, "receipt")
    destination.write_bytes(receipt.getbuffer())

    row = pd.DataFrame(
        [
            {
                "id": uuid.uuid4().hex,
                "date": date.today().isoformat(),
                "amount": round(amount, 2),
                "store_name": store_name.strip(),
                "items": json.dumps(items, ensure_ascii=False),
                "receipt_path": destination.relative_to(APP_DIR).as_posix(),
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
        ],
        columns=EXPENSE_COLUMNS,
    )
    row.to_csv(EXPENSES_FILE, mode="a", header=False, index=False)


def save_shortfall(item_name: str, urgency: str, notes: str, photo) -> None:
    destination = SHORTFALL_PHOTOS_DIR / safe_filename(photo.name, "shortfall")
    destination.write_bytes(photo.getbuffer())

    row = pd.DataFrame(
        [
            {
                "id": uuid.uuid4().hex,
                "date": date.today().isoformat(),
                "item_name": item_name.strip(),
                "urgency": urgency,
                "notes": notes.strip(),
                "photo_path": destination.relative_to(APP_DIR).as_posix(),
                "status": "Open",
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
        ],
        columns=SHORTFALL_COLUMNS,
    )
    row.to_csv(SHORTFALLS_FILE, mode="a", header=False, index=False)


def delete_receipt(receipt_id: str) -> bool:
    expenses = load_expenses()
    matching_rows = expenses.loc[expenses["id"] == receipt_id]
    if matching_rows.empty:
        return False

    try:
        for relative_path in matching_rows["receipt_path"]:
            image_path = stored_image_path(str(relative_path), RECEIPTS_DIR)
            if image_path and image_path.is_file():
                image_path.unlink()
        remaining = expenses.loc[expenses["id"] != receipt_id]
        write_csv(remaining, EXPENSES_FILE, EXPENSE_COLUMNS)
    except OSError:
        return False
    return True


def resolve_shortfall(shortfall_id: str) -> bool:
    shortfalls = load_shortfalls()
    matching = shortfalls["id"] == shortfall_id
    if not matching.any():
        return False

    shortfalls.loc[matching, "status"] = "Resolved"
    try:
        write_csv(shortfalls, SHORTFALLS_FILE, SHORTFALL_COLUMNS)
    except OSError:
        return False
    return True


def format_date(value: object) -> str:
    parsed = pd.to_datetime(value, errors="coerce")
    return parsed.strftime("%d %b %Y") if pd.notna(parsed) else "Unknown date"


def show_receipt_dashboard(expenses: pd.DataFrame) -> None:
    today = date.today()
    expense_dates = pd.to_datetime(expenses["date"], errors="coerce")
    today_mask = expense_dates.dt.date == today
    month_mask = (expense_dates.dt.year == today.year) & (expense_dates.dt.month == today.month)

    first_left, first_right = st.columns(2)
    first_left.metric("Receipts Today", int(today_mask.sum()))
    first_right.metric("Spent Today", f"${expenses.loc[today_mask, 'amount'].sum():,.2f}")

    second_left, second_right = st.columns(2)
    second_left.metric("This Month", f"{int(month_mask.sum())} receipts")
    second_right.metric(
        "This Month Spent",
        f"${expenses.loc[month_mask, 'amount'].sum():,.2f}",
    )
    st.metric("All Time Spent", f"${expenses['amount'].sum():,.2f}")


def show_monthly_item_summary(expenses: pd.DataFrame) -> None:
    st.subheader("Items Bought This Month")
    today = date.today()
    expense_dates = pd.to_datetime(expenses["date"], errors="coerce")
    month_records = expenses.loc[
        (expense_dates.dt.year == today.year) & (expense_dates.dt.month == today.month)
    ]

    counts: Counter[str] = Counter()
    display_names: dict[str, str] = {}
    for value in month_records["items"]:
        for item in parse_items(value):
            normalized = " ".join(item.casefold().split())
            if normalized:
                counts[normalized] += 1
                display_names.setdefault(normalized, item)

    if not counts:
        st.info("No items recorded this month.")
        return

    for normalized, count in counts.most_common():
        suffix = f" × {count}" if count > 1 else ""
        st.write(f"• {display_names[normalized]}{suffix}")


def show_open_shortfalls() -> None:
    st.subheader("Open Shortfalls")
    shortfalls = load_shortfalls()
    open_shortfalls = shortfalls.loc[shortfalls["status"].str.casefold() == "open"].copy()

    if open_shortfalls.empty:
        st.info("No open shortfalls.")
        return

    open_shortfalls = open_shortfalls.sort_values(
        ["created_at", "date"], ascending=False
    )

    for record in open_shortfalls.itertuples(index=False):
        with st.container(border=True):
            st.markdown(f"### {record.item_name}")
            st.caption(f"{format_date(record.date)} · {record.urgency}")
            if record.notes:
                st.write(record.notes)

            image_path = stored_image_path(str(record.photo_path), SHORTFALL_PHOTOS_DIR)
            if image_path and image_path.is_file():
                st.image(str(image_path), use_column_width=True)
            else:
                st.caption("Item photo is unavailable.")

            if st.button(
                "Mark as Resolved",
                key=f"resolve_{record.id}",
                use_container_width=True,
            ):
                if resolve_shortfall(str(record.id)):
                    st.session_state.owner_message = "Shortfall marked as resolved."
                else:
                    st.session_state.owner_error = "That shortfall could not be found."
                st.rerun()


def show_receipt_history(expenses: pd.DataFrame) -> None:
    st.subheader("Receipt History")
    if expenses.empty:
        st.info("No receipts submitted yet.")
        return

    records = expenses.sort_values(["created_at", "date"], ascending=False)
    for record in records.itertuples(index=False):
        with st.container(border=True):
            st.markdown(f"**{format_date(record.date)} · ${record.amount:,.2f}**")
            st.write(f"**Store:** {record.store_name or 'Not recorded'}")
            item_list = parse_items(record.items)
            st.write(f"**Items:** {', '.join(item_list) if item_list else 'Not recorded'}")

            image_path = stored_image_path(str(record.receipt_path), RECEIPTS_DIR)
            if image_path and image_path.is_file():
                with st.expander("View receipt photo"):
                    st.image(str(image_path), use_column_width=True)
            else:
                st.caption("Receipt photo is unavailable.")

            if st.button(
                "Delete Receipt",
                key=f"delete_{record.id}",
                use_container_width=True,
            ):
                if delete_receipt(str(record.id)):
                    st.session_state.owner_message = "Receipt deleted successfully."
                else:
                    st.session_state.owner_error = "That receipt could not be found."
                st.rerun()


def show_owner_view() -> None:
    if message := st.session_state.pop("owner_message", None):
        st.success(message)
    if error := st.session_state.pop("owner_error", None):
        st.error(error)

    expenses = load_expenses()
    st.subheader("Spending Dashboard")
    show_receipt_dashboard(expenses)
    st.divider()
    show_monthly_item_summary(expenses)
    st.divider()
    show_open_shortfalls()
    st.divider()
    show_receipt_history(expenses)


st.set_page_config(
    page_title="Groceries and Inventory Tracker",
    page_icon="🛒",
    layout="centered",
)
initialise_storage()

st.markdown(
    """
    <style>
    .block-container {max-width: 680px; padding-top: 3.5rem; padding-bottom: 3rem;}
    h1 {font-size: 2.25rem !important;}
    div[data-testid="stNumberInput"] input,
    div[data-testid="stTextInput"] input {font-size: 1.25rem; min-height: 3rem;}
    div[data-testid="stFormSubmitButton"] button {min-height: 3.25rem; font-size: 1.05rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

if "owner_panel_open" not in st.session_state:
    st.session_state.owner_panel_open = False
if "owner_authenticated" not in st.session_state:
    st.session_state.owner_authenticated = False

title_column, owner_icon_column = st.columns([6, 1])
with title_column:
    st.title("Groceries and Inventory Tracker")
with owner_icon_column:
    owner_icon = "🔓" if st.session_state.owner_authenticated else "🔐"
    if st.button(
        owner_icon,
        help="Owner Login",
        key="owner_login_icon",
        use_container_width=True,
    ):
        st.session_state.owner_panel_open = not st.session_state.owner_panel_open
        st.rerun()

if st.session_state.owner_panel_open:
    with st.container(border=True):
        if st.session_state.owner_authenticated:
            owner_title, logout_column = st.columns([4, 1])
            owner_title.header("Owner View")
            if logout_column.button("Log Out", use_container_width=True):
                st.session_state.owner_authenticated = False
                st.session_state.owner_panel_open = False
                st.session_state.pop("owner_password", None)
                st.rerun()
            show_owner_view()
        else:
            st.header("Owner Login")
            with st.form("owner_login_form"):
                entered_password = st.text_input(
                    "Owner password",
                    type="password",
                    key="owner_password",
                )
                login_submitted = st.form_submit_button(
                    "Log In",
                    type="primary",
                    use_container_width=True,
                )

            if login_submitted:
                if entered_password == OWNER_PASSWORD:
                    st.session_state.owner_authenticated = True
                    st.rerun()
                else:
                    st.error("Incorrect password.")

st.selectbox(
    "Language / ဘာသာစကား",
    ["English", "Burmese (Myanmar)"],
    key="helper_language",
)
submit_tab, shortfall_tab = st.tabs(
    [translate("submit_receipt"), translate("report_shortfall")]
)

with submit_tab:
    st.header(translate("submit_receipt"))
    st.write(translate("receipt_instruction"))

    if "receipt_form_number" not in st.session_state:
        st.session_state.receipt_form_number = 0
    if st.session_state.pop("receipt_saved", False):
        st.success(translate("receipt_success"))

    form_number = st.session_state.receipt_form_number
    amount_key = f"receipt_amount_{form_number}"
    store_key = f"receipt_store_{form_number}"
    items_key = f"receipt_items_{form_number}"
    for key, default in [(amount_key, 0.0), (store_key, ""), (items_key, "")]:
        if key not in st.session_state:
            st.session_state[key] = default

    receipt = st.file_uploader(
        translate("upload_receipt"),
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=False,
        help=translate("receipt_help"),
        key=f"receipt_upload_{form_number}",
    )
    st.caption(translate("receipt_help"))

    if receipt is not None:
        receipt_hash = hashlib.sha256(receipt.getvalue()).hexdigest()
        hash_key = f"receipt_hash_{form_number}"
        if st.session_state.get(hash_key) != receipt_hash:
            st.session_state[hash_key] = receipt_hash
            st.session_state[amount_key] = 0.0
            st.session_state[store_key] = ""
            st.session_state[items_key] = ""

        if st.button(translate("read_with_ai"), use_container_width=True):
            if genai is None:
                st.error(translate("gemini_package_missing"))
            elif not GEMINI_API_KEY or GEMINI_API_KEY == "paste-your-key-here":
                st.error(translate("gemini_key_missing"))
            else:
                try:
                    with st.spinner(translate("reading_receipt")):
                        ai_amount, ai_store, ai_items = read_receipt_with_gemini(receipt)
                    st.session_state[amount_key] = ai_amount
                    st.session_state[store_key] = ai_store
                    st.session_state[items_key] = "\n".join(ai_items)
                    st.success(translate("ai_success"))
                except Exception:
                    st.error(translate("ai_failed"))
    else:
        st.button(translate("read_with_ai"), use_container_width=True, disabled=True)

    with st.form(f"receipt_form_{form_number}"):
        amount = st.number_input(
            translate("amount_spent"),
            min_value=0.0,
            step=0.01,
            format="%.2f",
            key=amount_key,
        )
        store_name = st.text_input(
            translate("store_name"),
            placeholder=translate("store_placeholder"),
            key=store_key,
        )
        items_text = st.text_area(
            translate("items_bought"),
            placeholder=translate("items_placeholder"),
            key=items_key,
            height=150,
        )
        receipt_submitted = st.form_submit_button(
            translate("submit_receipt"),
            type="primary",
            use_container_width=True,
        )

    if receipt_submitted:
        if receipt is None:
            st.error(translate("receipt_required"))
        elif amount <= 0:
            st.error(translate("amount_required"))
        else:
            try:
                items = [line.strip() for line in items_text.splitlines() if line.strip()]
                save_receipt(amount, store_name, items, receipt)
                st.session_state.receipt_form_number += 1
                st.session_state.receipt_saved = True
                st.rerun()
            except OSError:
                st.error(translate("receipt_save_error"))

with shortfall_tab:
    st.header(translate("report_shortfall"))
    st.write(translate("shortfall_instruction"))

    with st.form("shortfall_form", clear_on_submit=True):
        shortfall_photo = st.file_uploader(
            translate("upload_item_photo"),
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=False,
            key="shortfall_photo",
        )
        item_name = st.text_input(
            translate("item_name"),
            placeholder=translate("item_placeholder"),
        )
        urgency = st.selectbox(
            translate("urgency"),
            URGENCY_OPTIONS,
            index=1,
            format_func=lambda value: translate(value.casefold()),
        )
        notes = st.text_area(
            translate("notes"),
            placeholder=translate("notes_placeholder"),
            height=100,
        )
        shortfall_submitted = st.form_submit_button(
            translate("submit_shortfall"),
            type="primary",
            use_container_width=True,
        )

    if shortfall_submitted:
        if shortfall_photo is None:
            st.error(translate("photo_required"))
        elif not item_name.strip():
            st.error(translate("item_required"))
        else:
            try:
                save_shortfall(item_name, urgency, notes, shortfall_photo)
                st.success(translate("shortfall_success"))
            except OSError:
                st.error(translate("shortfall_save_error"))
