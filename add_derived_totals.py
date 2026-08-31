from pathlib import Path

p = Path(r".\financial_engine\extraction.py")
s = p.read_text(encoding="utf-8")

marker = "# ============================================================\n# FINANCIAL DATA STANDARDIZATION"

insert = r'''
# ============================================================
# DERIVED FINANCIAL TOTALS
# ============================================================

def derive_missing_totals(merged_results):

    result = dict(merged_results)

    def value(metric, year):

        info = result.get(metric)

        if not info:
            return None

        return info.get(year)

    def make_entry(
        metric,
        current,
        previous,
        label
    ):

        result[metric] = {

            "current": current,

            "previous": previous,

            "score": 85,

            "raw_score": 85,

            "sheet": "Derived from financial statement components",

            "statement_type": "balance_sheet",

            "label": label,

            "current_year": None,

            "previous_year": None
        }

    def sum_metrics(metrics, year):

        values = []

        for metric in metrics:

            v = value(
                metric,
                year
            )

            if v is not None:
                values.append(v)

        if not values:
            return None

        return sum(values)

    # --------------------------------------------------------
    # CURRENT ASSETS
    # --------------------------------------------------------

    if value(
        "current_assets",
        "current"
    ) is None:

        current = sum_metrics(
            [
                "inventory",
                "trade_receivables",
                "cash",
                "short_term_loans_advances",
                "other_current_assets"
            ],
            "current"
        )

        previous = sum_metrics(
            [
                "inventory",
                "trade_receivables",
                "cash",
                "short_term_loans_advances",
                "other_current_assets"
            ],
            "previous"
        )

        if current is not None:

            make_entry(
                "current_assets",
                current,
                previous,
                "Derived Current Assets"
            )

    # --------------------------------------------------------
    # CURRENT LIABILITIES
    # --------------------------------------------------------

    if value(
        "current_liabilities",
        "current"
    ) is None:

        current = sum_metrics(
            [
                "short_term_borrowings",
                "trade_payables",
                "other_current_liabilities",
                "short_term_provisions"
            ],
            "current"
        )

        previous = sum_metrics(
            [
                "short_term_borrowings",
                "trade_payables",
                "other_current_liabilities",
                "short_term_provisions"
            ],
            "previous"
        )

        if current is not None:

            make_entry(
                "current_liabilities",
                current,
                previous,
                "Derived Current Liabilities"
            )

    # --------------------------------------------------------
    # TOTAL DEBT
    # --------------------------------------------------------

    if value(
        "total_debt",
        "current"
    ) is None:

        current = sum_metrics(
            [
                "long_term_borrowings",
                "short_term_borrowings"
            ],
            "current"
        )

        previous = sum_metrics(
            [
                "long_term_borrowings",
                "short_term_borrowings"
            ],
            "previous"
        )

        if current is not None:

            make_entry(
                "total_debt",
                current,
                previous,
                "Derived Total Debt"
            )

    # --------------------------------------------------------
    # TOTAL EQUITY
    # --------------------------------------------------------

    if value(
        "total_equity",
        "current"
    ) is None:

        current = sum_metrics(
            [
                "share_capital",
                "reserves"
            ],
            "current"
        )

        previous = sum_metrics(
            [
                "share_capital",
                "reserves"
            ],
            "previous"
        )

        if current is not None:

            make_entry(
                "total_equity",
                current,
                previous,
                "Derived Total Equity"
            )

    return result


'''

if marker not in s:
    raise SystemExit(
        "ERROR: insertion point not found"
    )

s = s.replace(
    marker,
    insert + marker,
    1
)

old = '''    financial_data = standardize_financial_data(
        merged_results
    )'''

new = '''    merged_results = derive_missing_totals(
        merged_results
    )

    financial_data = standardize_financial_data(
        merged_results
    )'''

if old not in s:
    raise SystemExit(
        "ERROR: standardization call not found"
    )

s = s.replace(
    old,
    new,
    1
)

p.write_text(
    s,
    encoding="utf-8"
)

print(
    "DERIVED TOTALS ADDED SUCCESSFULLY"
)