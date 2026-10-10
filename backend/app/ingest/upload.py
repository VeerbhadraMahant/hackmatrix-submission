"""CSV/JSON bank-statement upload ingestion.

`parse_transaction_csv` accepts a reasonably flexible CSV export and returns
`TransactionRow` objects ready for insertion. It tolerates common bank-export
quirks:
  - a single signed "amount" column, OR separate debit/credit columns
  - date formats DD/MM/YYYY and YYYY-MM-DD (also DD-MM-YYYY, MM/DD/YYYY when
    unambiguous)
  - currency symbols / thousands separators in amount cells ("₹1,200.00")
  - a missing/blank category column -- filled in via `app.ingest.categorize`
  - varying header casing/spacing ("Transaction Date", "Narration", ...)
"""
from __future__ import annotations

import io
import re

import pandas as pd

_ISO_DATE_RE = re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}")

from app.ingest.categorize import categorize
from app.models import TransactionRow
from app.schemas import TxnCategory

_DATE_COLS = ["date", "transaction date", "txn date", "value date", "posting date"]
_DESC_COLS = ["description", "merchant", "narration", "particulars", "details", "payee"]
_AMOUNT_COLS = ["amount", "txn amount", "transaction amount"]
_DEBIT_COLS = ["debit", "withdrawal", "withdrawal amt", "withdrawal amt.", "debit amount"]
_CREDIT_COLS = ["credit", "deposit", "deposit amt", "deposit amt.", "credit amount"]
_CATEGORY_COLS = ["category", "txn category"]


def _find_col(columns: list[str], candidates: list[str]) -> str | None:
    normalized = {c.strip().lower(): c for c in columns}
    for candidate in candidates:
        if candidate in normalized:
            return normalized[candidate]
    return None


def _clean_amount(value) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    if not s:
        return None
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1]
    s = s.replace("₹", "").replace("Rs.", "").replace("Rs", "").replace(",", "").replace("INR", "").strip()
    if s.upper().endswith("DR"):
        negative = True
        s = s[:-2].strip()
    if s.upper().endswith("CR"):
        s = s[:-2].strip()
    if not s:
        return None
    try:
        amount = float(s)
    except ValueError:
        return None
    return -abs(amount) if negative else amount


def parse_transaction_csv(
    file_bytes: bytes,
    user_id: str = "",
    account_id: str = "",
) -> list[TransactionRow]:
    """Parse a bank-export CSV into TransactionRow objects.

    `user_id`/`account_id` are stamped onto every row (typically filled in
    by the caller/route from the URL path), but are optional here so this
    function stays usable as a pure parser in tests.
    """
    df = pd.read_csv(io.BytesIO(file_bytes))
    if df.empty:
        return []

    columns = list(df.columns)
    date_col = _find_col(columns, _DATE_COLS)
    desc_col = _find_col(columns, _DESC_COLS)
    amount_col = _find_col(columns, _AMOUNT_COLS)
    debit_col = _find_col(columns, _DEBIT_COLS)
    credit_col = _find_col(columns, _CREDIT_COLS)
    category_col = _find_col(columns, _CATEGORY_COLS)

    if date_col is None or desc_col is None:
        raise ValueError(
            "CSV must include a date column and a description/merchant column "
            f"(got columns: {columns})"
        )
    if amount_col is None and debit_col is None and credit_col is None:
        raise ValueError(
            "CSV must include either an 'amount' column or 'debit'/'credit' columns "
            f"(got columns: {columns})"
        )

    date_series = df[date_col].astype(str)
    sample = next((v for v in date_series if v and v.lower() != "nan"), "")
    is_iso_style = bool(_ISO_DATE_RE.match(sample.strip()))
    # Year-first (ISO, e.g. YYYY-MM-DD) is unambiguous -- dayfirst must be
    # left as the default there or pandas misreads it. Day-first formats
    # (DD/MM/YYYY) need dayfirst=True explicitly.
    dates = pd.to_datetime(date_series, dayfirst=not is_iso_style, errors="coerce")

    rows: list[TransactionRow] = []
    for i in range(len(df)):
        parsed_date = dates.iloc[i]
        if pd.isna(parsed_date):
            continue  # skip unparseable rows rather than failing the whole batch

        merchant = str(df[desc_col].iloc[i]).strip()
        if not merchant or merchant.lower() == "nan":
            continue

        if amount_col is not None:
            amount = _clean_amount(df[amount_col].iloc[i])
        else:
            debit = _clean_amount(df[debit_col].iloc[i]) if debit_col else None
            credit = _clean_amount(df[credit_col].iloc[i]) if credit_col else None
            debit = abs(debit) if debit else 0.0
            credit = abs(credit) if credit else 0.0
            amount = credit - debit

        if amount is None:
            continue

        category: TxnCategory
        raw_category = str(df[category_col].iloc[i]).strip() if category_col else ""
        if raw_category and raw_category.lower() != "nan":
            try:
                category = TxnCategory(raw_category.lower().replace(" ", "_"))
            except ValueError:
                category = categorize(merchant, amount)
        else:
            category = categorize(merchant, amount)

        rows.append(
            TransactionRow(
                user_id=user_id,
                account_id=account_id,
                date=parsed_date.date(),
                amount=float(amount),
                merchant=merchant,
                category=category.value,
                description=merchant,
                is_recurring=False,
                recurring_group_id=None,
            )
        )

    return rows
