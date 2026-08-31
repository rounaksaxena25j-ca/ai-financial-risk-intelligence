from pathlib import Path

p = Path(r".\financial_engine\extraction.py")
s = p.read_text(encoding="utf-8")

marker = "# ============================================================\n# METRIC -> EXPECTED STATEMENT"

insert = r'''
# ============================================================
# COMPONENT METRIC ALIASES
# ============================================================

COMPONENT_ALIASES = {

    "share_capital": [
        "share capital",
        "equity share capital",
        "paid up share capital",
        "paid-up share capital",
        "issued share capital"
    ],

    "reserves": [
        "reserves",
        "reserve and surplus",
        "reserve & surplus",
        "reserves and surplus",
        "retained earnings",
        "reserves and retained earnings",
        "other reserves"
    ],

    "long_term_borrowings": [
        "long term borrowings",
        "long-term borrowings",
        "non current borrowings",
        "non-current borrowings",
        "long term debt",
        "non current debt",
        "non-current debt"
    ],

    "short_term_borrowings": [
        "short term borrowings",
        "short-term borrowings",
        "current borrowings",
        "short term debt",
        "current debt"
    ],

    "trade_payables": [
        "trade payables",
        "trade payable",
        "accounts payable",
        "account payable",
        "sundry creditors",
        "trade creditors",
        "creditors"
    ],

    "other_current_liabilities": [
        "other current liabilities",
        "other current liability",
        "other current liabilites"
    ],

    "short_term_provisions": [
        "short term provisions",
        "short-term provisions",
        "current provisions",
        "provisions"
    ],

    "cash": [
        "cash",
        "cash and cash equivalents",
        "cash & cash equivalents",
        "cash and bank balances",
        "cash and bank balance",
        "bank balances",
        "cash balances"
    ],

    "short_term_loans_advances": [
        "short term loans and advances",
        "short-term loans and advances",
        "loans and advances",
        "short term loans",
        "short-term loans",
        "current loans and advances"
    ],

    "other_current_assets": [
        "other current assets",
        "other current asset"
    ]
}


'''

if marker not in s:
    raise SystemExit("ERROR: insertion point not found")

s = s.replace(marker, insert + marker, 1)

p.write_text(s, encoding="utf-8")

print("COMPONENT ALIASES ADDED SUCCESSFULLY")