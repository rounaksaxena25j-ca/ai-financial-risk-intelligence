"""
Test harness for financial_engine.extraction

Builds several synthetic worksheets representing different
real-world financial statement layouts (as pandas DataFrames,
the same shape you'd get from pd.read_excel(..., header=None)),
each with KNOWN ground-truth current/previous values baked in.

Runs extract_financial_data() against each and checks:
  - was the metric detected at all?
  - does the "current" value match the ground-truth CURRENT value?
  - does the "previous" value match the ground-truth PREVIOUS value?
    (this is the check that catches a current/previous swap)

Run:  python3 run_tests.py
"""

import sys
import os
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from financial_engine.extraction import extract_financial_data


def row(*cells):
    return list(cells)


def make_df(rows):
    width = max(len(r) for r in rows)
    padded = [r + [None] * (width - len(r)) for r in rows]
    return pd.DataFrame(padded)


# ============================================================
# TEST CASE DEFINITIONS
# Each case: (name, {sheet_name: df}, ground_truth)
# ground_truth: {metric_key: (current_value, previous_value)}
# ============================================================

CASES = []

# ------------------------------------------------------------
# 1. Standard layout: dated headers, current LEFT of previous
# ------------------------------------------------------------
df1 = make_df([
    row("ABC Manufacturing Limited"),
    row("Balance Sheet as at 31 March 2025"),
    row("(All amounts in Rs. Lakhs)"),
    row(),
    row("Particulars", "Note", "As at 31.03.2025", "As at 31.03.2024"),
    row("Trade Receivables", "12", 4500, 3800),
    row("Inventories", "13", 2100, 1900),
    row("Total Debt", "14", 5000, 4600),
    row("Total Equity", "15", 8200, 7100),
    row("Current Assets", "", 9000, 7800),
    row("Current Liabilities", "", 4200, 3600),
])
CASES.append((
    "1_standard_current_left",
    {"Balance Sheet": df1},
    {
        "trade_receivables": (4500, 3800),
        "inventory": (2100, 1900),
        "total_debt": (5000, 4600),
        "total_equity": (8200, 7100),
    }
))

# ------------------------------------------------------------
# 2. Reversed layout: previous year LEFT, current year RIGHT
#    (common alternate convention)
# ------------------------------------------------------------
df2 = make_df([
    row("XYZ Traders Pvt Ltd"),
    row("Balance Sheet"),
    row(),
    row("Particulars", "Note", "As at 31.03.2024", "As at 31.03.2025"),
    row("Trade Receivables", "", 2200, 3100),
    row("Inventories", "", 1500, 1750),
    row("Total Debt", "", 3000, 2600),
])
CASES.append((
    "2_reversed_previous_left",
    {"Balance Sheet": df2},
    {
        "trade_receivables": (3100, 2200),
        "inventory": (1750, 1500),
        "total_debt": (2600, 3000),
    }
))

# ------------------------------------------------------------
# 3. Semantic headers ("Current Year"/"Previous Year") PLUS a
#    stray incorporation-year mention elsewhere on the sheet.
#    This is the exact scenario the earlier bug mishandled.
# ------------------------------------------------------------
df3 = make_df([
    row("PQR Industries Limited (incorporated in the year 2010)"),
    row("Statement of Profit and Loss"),
    row(),
    row("Particulars", "Note", "Current Year", "Previous Year"),
    row("Revenue From Operations", "", 12000, 10500),
    row("Net Profit", "", 1800, 1450),
])
CASES.append((
    "3_semantic_headers_with_stray_year",
    {"P&L": df3},
    {
        "revenue": (12000, 10500),
        "net_profit": (1800, 1450),
    }
))

# ------------------------------------------------------------
# 4. FY-range style headers: "2024-25" / "2023-24"
# ------------------------------------------------------------
df4 = make_df([
    row("LMN Enterprises"),
    row("Profit & Loss Account"),
    row(),
    row("Particulars", "FY 2024-25", "FY 2023-24"),
    row("Turnover", 9800, 8700),
    row("Profit After Tax", 1250, 1010),
])
CASES.append((
    "4_fy_range_headers",
    {"P&L": df4},
    {
        "revenue": (9800, 8700),
        "net_profit": (1250, 1010),
    }
))

# ------------------------------------------------------------
# 5. Deep preamble: header row pushed past row 12 (rows_to_check
#    limit in the semantic/year scan)
# ------------------------------------------------------------
preamble_rows = [row(f"Preamble line {i}") for i in range(14)]
df5 = make_df(preamble_rows + [
    row("Particulars", "As at 31.03.2025", "As at 31.03.2024"),
    row("Trade Receivables", 5200, 4700),
    row("Total Equity", 9100, 8300),
])
CASES.append((
    "5_deep_preamble_header_below_row12",
    {"Balance Sheet": df5},
    {
        "trade_receivables": (5200, 4700),
        "total_equity": (9100, 8300),
    }
))

# ------------------------------------------------------------
# 6. Alternate/uncommon labels not in METRIC_ALIASES
#    (expected to legitimately come back MISSING, not wrong)
# ------------------------------------------------------------
df6 = make_df([
    row("Particulars", "Current Year", "Previous Year"),
    row("Cost of Materials Consumed", 4000, 3500),
    row("Employee Benefit Expense", 1200, 1100),
])
CASES.append((
    "6_labels_outside_alias_list",
    {"P&L": df6},
    {}  # no ground truth expected -- checking these stay MISSING, not wrong
))

# ------------------------------------------------------------
# 7. Merged-cell simulation: header text only in one of the two
#    columns that visually represent one merged year header,
#    with the real numbers offset one column to the right.
# ------------------------------------------------------------
df7 = make_df([
    row("Particulars", "As at 31.03.2025", None, "As at 31.03.2024", None),
    row("Trade Receivables", None, 3300, None, 2900),
])
CASES.append((
    "7_merged_header_offset_data",
    {"Balance Sheet": df7},
    {
        # Documented as a KNOWN LIMITATION -- not asserted strictly,
        # just reported.
    }
))

# ------------------------------------------------------------
# 8. Standalone + Consolidated side-by-side (two current/previous
#    pairs on one sheet) -- documented known limitation.
# ------------------------------------------------------------
df8 = make_df([
    row("Particulars", "Standalone", "", "Consolidated", ""),
    row("Particulars", "Current Year", "Previous Year", "Current Year", "Previous Year"),
    row("Revenue From Operations", 5000, 4500, 5600, 5000),
])
CASES.append((
    "8_standalone_and_consolidated_blocks",
    {"P&L": df8},
    {
        # Ambiguous by design -- reported, not strictly asserted.
    }
))


# ============================================================
# RUN
# ============================================================

def run_case(name, workbook, ground_truth):
    financial_data, validation_report = extract_financial_data(workbook)

    lines = [f"\n=== {name} ==="]

    if not ground_truth:
        detected = {
            k: (financial_data.get(k), financial_data.get(f"previous_{k}"))
            for k in financial_data
            if not k.startswith("_") and not k.startswith("previous_")
            and financial_data.get(k) is not None
        }
        lines.append(f"  (no strict ground truth -- reporting only)")
        lines.append(f"  Detected non-null metrics: {detected}")
        return lines, None

    all_pass = True

    for metric, (exp_current, exp_previous) in ground_truth.items():
        got_current = financial_data.get(metric)
        got_previous = financial_data.get(f"previous_{metric}")

        current_ok = got_current == exp_current
        previous_ok = got_previous == exp_previous

        status = "PASS" if (current_ok and previous_ok) else "FAIL"
        if status == "FAIL":
            all_pass = False

        swap_note = ""
        if not current_ok and got_current == exp_previous:
            swap_note = "  <-- looks SWAPPED with previous"
        if not previous_ok and got_previous == exp_current:
            swap_note = "  <-- looks SWAPPED with current"

        lines.append(
            f"  [{status}] {metric:22s} "
            f"expected current={exp_current}, previous={exp_previous} | "
            f"got current={got_current}, previous={got_previous}{swap_note}"
        )

    return lines, all_pass


def main():
    total = 0
    passed = 0
    informational = 0

    for name, workbook, ground_truth in CASES:
        lines, result = run_case(name, workbook, ground_truth)
        print("\n".join(lines))

        if result is None:
            informational += 1
        else:
            total += 1
            if result:
                passed += 1

    print("\n" + "=" * 60)
    print(f"RESULT: {passed}/{total} strict test cases passed "
          f"({informational} informational-only cases reported above)")
    print("=" * 60)


if __name__ == "__main__":
    main()
