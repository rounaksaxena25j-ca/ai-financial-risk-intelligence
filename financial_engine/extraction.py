import re
import math
import pandas as pd
import numpy as np


# ============================================================
# AI FINANCIAL EXTRACTION ENGINE
# ROBUST / FORMAT-INDEPENDENT VERSION
# ============================================================
#
# Main improvements:
#
# 1. SAFE text normalization
#    - Does NOT remove genuine financial words.
#
# 2. STRICT metric matching
#    - Exact labels get highest priority.
#    - Dangerous partial matches are rejected.
#
# 3. FINANCIAL STATEMENT AWARENESS
#    - Revenue / profit -> P&L
#    - Receivables / inventory / assets / liabilities / equity
#      -> Balance Sheet
#    - Operating cash flow -> Cash Flow
#    - Notes are used mainly as supporting evidence.
#
# 4. YEAR HEADER DETECTION
#    - Handles:
#        2025  2024
#        Current Year / Previous Year
#        FY 2025 / FY 2024
#        Year ended 31 March 2025 / 2024
#
# 5. PREVIOUS YEAR SAFETY
#    - Never silently duplicates current year.
#
# 6. CROSS-SHEET VALIDATION
#    - Suspicious candidates are rejected.
#
# 7. NO COMPANY-SPECIFIC EXCEL STRUCTURE
#    - Designed for different workbook layouts.
#
# ============================================================


# ============================================================
# STANDARD METRICS
# ============================================================

METRIC_ALIASES = {

    "revenue": [
        "revenue",
        "revenue from operations",
        "revenue from operation",
        "sales",
        "sales turnover",
        "turnover",
        "net sales",
        "total revenue",
        "income from operations",
        "income from operation",
        "operating revenue"
    ],

    "net_profit": [
        "net profit",
        "net profit after tax",
        "profit after tax",
        "profit for the year",
        "profit for period",
        "profit for the period",
        "profit attributable to owners",
        "profit attributable to equity holders",
        "profit attributable to shareholders",
        "profit for the financial year",
        "profit loss for the period",
        "profit loss for the period from continuing operations",
        "profit for the period from continuing operations",
        "profit/(loss) for the period",
        "profit/(loss) for the period from continuing operations",
        "profit after tax attributable to owners",
        "pat"
    ],

    "trade_receivables": [
        "trade receivables",
        "trade receivable",
        "accounts receivable",
        "account receivables",
        "sundry debtors",
        "trade debtors",
        "debtor",
        "debtors",
        "receivables from customers"
    ],

    "inventory": [
        "inventory",
        "inventories",
        "stock",
        "stocks",
        "inventory and stock",
        "inventories and stock"
    ],

    "total_debt": [
        "total debt",
        "total borrowings",
        "borrowings",
        "loans and borrowings",
        "loans borrowings",
        "financial debt",
        "interest bearing borrowings",
        "interest bearing debt",
        "secured borrowings",
        "unsecured borrowings"
    ],

    "total_equity": [
        "total equity",
        "shareholders equity",
        "shareholder equity",
        "shareholders funds",
        "shareholders fund",
        "total shareholders funds",
        "owners equity",
        "owners funds",
        "net worth",
        "total equity attributable to owners",
        "equity attributable to owners"
    ],

    "operating_cash_flow": [
        "operating cash flow",
        "cash flow from operating activities",
        "net cash from operating activities",
        "net cash generated from operating activities",
        "cash generated from operations",
        "cash generated from operating activities",
        "cash flows from operating activities"
    ],

    "current_assets": [
        "current assets",
        "total current assets"
    ],

    "current_liabilities": [
        "current liabilities",
        "total current liabilities"
    ]
}



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
        "creditors",
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


# ============================================================
# METRIC -> EXPECTED STATEMENT
# ============================================================

METRIC_STATEMENT = {

    "revenue": "pnl",

    "net_profit": "pnl",

    "trade_receivables": "balance_sheet",

    "trade_payables": "balance_sheet",

    "inventory": "balance_sheet",

    "total_debt": "balance_sheet",

    "total_equity": "balance_sheet",

    "operating_cash_flow": "cash_flow",

    "current_assets": "balance_sheet",

    "current_liabilities": "balance_sheet"
}


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(value):

    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    text = str(value).strip().lower()

    if not text:
        return ""

    # Financial symbols
    text = text.replace("&", " and ")
    text = text.replace("/", " ")
    text = text.replace("\\", " ")
    text = text.replace("_", " ")
    text = text.replace("–", "-")
    text = text.replace("—", "-")

    # --------------------------------------------------------
    # REMOVE ONLY TRUE LABEL PREFIXES
    # --------------------------------------------------------
    #
    # Examples:
    #   (a) Revenue
    #   a) Revenue
    #   (iv) Revenue
    #   iv. Revenue
    #   1. Revenue
    #
    # IMPORTANT:
    # We DO NOT remove arbitrary alphabetic words.
    #

    text = re.sub(
        r"^\s*\(\s*[a-z]{1,3}\s*\)\s*",
        "",
        text
    )

    text = re.sub(
        r"^\s*[a-z]{1,3}\s*[\.\:\)]\s*",
        "",
        text
    )

    text = re.sub(
        r"^\s*\(\s*\d+\s*\)\s*",
        "",
        text
    )

    text = re.sub(
        r"^\s*\d+\s*[\.\:\)]\s*",
        "",
        text
    )

    # Remove punctuation
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def compact_text(value):
    return normalize_text(value).replace(" ", "")


# ============================================================
# NUMBER PARSING
# ============================================================


def repair_row_numeric_scale(values, label=None):
    if values is None:
        return values
    values=list(values)
    numeric=[]
    for value in values:
        try:
            if value is not None and not isinstance(value, bool):
                n=float(value)
                if math.isfinite(n) and n != 0:
                    numeric.append(abs(n))
        except (TypeError, ValueError):
            pass
    if len(numeric) < 3:
        return values
    median_value=float(np.median(numeric))
    if median_value == 0:
        return values
    repaired=[]
    for value in values:
        try:
            if value is None or isinstance(value, bool):
                repaired.append(value)
                continue
            n=float(value)
            ratio=abs(n)/median_value if n != 0 else 1
            if ratio < 0.001: n*=1000
            elif ratio > 1000: n/=1000
            repaired.append(n)
        except (TypeError, ValueError):
            repaired.append(value)
    return repaired

def parse_number(value):

    if value is None:
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float, np.integer, np.floating)):

        try:

            if pd.isna(value):
                return None

            value = float(value)

            if math.isfinite(value):
                return value

        except Exception:
            return None

        return None

    try:

        text = str(value).strip()

        if not text:
            return None

        lower = text.lower()

        # Reject date/header strings before extracting numbers.
        # Prevents values such as As On 31/03/2025 from becoming 31.

        if re.search(
            r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
            text
        ):
            return None

        if re.search(
            r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b",
            text
        ):
            return None


        if lower in {
            "na",
            "n/a",
            "nil",
            "none",
            "-",
            "--",
            "not available",
            "not applicable"
        }:
            return None

        text = text.replace("₹", "")
        text = text.replace("rs.", "")
        text = text.replace("rs ", "")
        text = text.replace("inr", "")
        text = text.replace("usd", "")
        text = text.replace("$", "")
        text = text.replace("€", "")
        text = text.replace("£", "")

        negative = False

        if text.startswith("(") and text.endswith(")"):
            negative = True
            text = text[1:-1]

        text = text.replace(",", "")
        text = text.replace(" ", "")

        match = re.search(
            r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?",
            text
        )

        if not match:
            return None

        number = float(match.group())

        if negative:
            number = -abs(number)

        if not math.isfinite(number):
            return None

        return number

    except Exception:
        return None


# ============================================================
# YEAR DETECTION
# ============================================================

YEAR_PATTERN = re.compile(
    r"(?:19|20)\d{2}"
)


def extract_years_from_text(text):

    if text is None:
        return []

    return [
        int(x)
        for x in YEAR_PATTERN.findall(str(text))
    ]


def is_year_value(value):

    years = extract_years_from_text(value)

    return any(
        1900 <= year <= 2100
        for year in years
    )


# ============================================================
# SEMANTIC YEAR ROLE
# ============================================================

def detect_header_year_role(value):

    text = normalize_text(value)

    if not text:
        return None

    previous_patterns = [
        'previous year',
        'previous period',
        'prior year',
        'prior period',
        'preceding year',
        'comparative year',
        'comparative period',
        'last year',
        'previous'
    ]

    current_patterns = [
        'current year',
        'current period',
        'current',
        'this year',
        'this period',
        'reporting period',
        'reporting year'
    ]

    if any(pattern in text for pattern in previous_patterns):
        return 'previous'

    if any(pattern in text for pattern in current_patterns):
        return 'current'

    # Financial statements commonly use:
    # 'For the year ended March 31, 2025'
    # 'Amount as on 31/03/2025'
    # These are period headers, but do not explicitly say current.
    # The semantic detector will use the year to determine which is current.
    if any(pattern in text for pattern in [
        'year ended',
        'year ending',
        'for the year',
        'for year ended',
        
        'as on'
    ]):
        return 'period'

    return None


# ============================================================
# YEAR COLUMN DETECTION
# ============================================================

def find_year_columns(df):

    if df is None or df.empty:
        return {}

    max_header_rows = min(len(df), 20)

    # Prefer a genuine financial header row containing
    # multiple distinct years.
    for header_row in range(max_header_rows):

        year_cells = []

        for col in range(df.shape[1]):

            found = extract_years_from_text(
                df.iat[header_row, col]
            )

            valid = [
                y for y in found
                if 1900 <= y <= 2100
            ]

            if valid:
                year_cells.append(
                    (col, max(valid))
                )

        distinct_years = {
            year for _, year in year_cells
        }

        if len(distinct_years) >= 2:

            candidates = {}

            for col, year in year_cells:
                candidates[col] = year

            return candidates

    # Fallback: inspect DataFrame column names.

    candidates = {}

    for col_idx, column_name in enumerate(df.columns):

        found = extract_years_from_text(
            column_name
        )

        valid_years = [
            year for year in found
            if 1900 <= year <= 2100
        ]

        if valid_years:
            candidates[col_idx] = max(valid_years)

    if candidates:
        return candidates

    return {}


# ============================================================
# DETERMINE CURRENT / PREVIOUS COLUMNS
# ============================================================

def determine_year_columns(df):

    year_map = find_year_columns(df)

    if not year_map:
        return (
            None,
            None,
            None,
            None
        )

    candidates = []

    for col, year in year_map.items():

        if 1900 <= year <= 2100:

            candidates.append(
                (col, year)
            )

    candidates.sort(
        key=lambda x: (
            x[1],
            x[0]
        ),
        reverse=True
    )

    if not candidates:
        return (
            None,
            None,
            None,
            None
        )

    current_col = candidates[0][0]
    current_year = candidates[0][1]

    previous_col = None
    previous_year = None

    for col, year in candidates[1:]:

        if col != current_col:

            previous_col = col
            previous_year = year
            break

    return (
        current_col,
        previous_col,
        current_year,
        previous_year
    )


# ============================================================
# IMPROVED HEADER YEAR DETECTION
# ============================================================

def detect_semantic_year_columns(df):

    if df is None or df.empty:
        return (None, None, None, None)

    rows_to_check = min(len(df), 20)
    candidates = []

    for row in range(rows_to_check):
        for col in range(df.shape[1]):
            value = df.iat[row, col]

            if pd.isna(value):
                continue

            text = normalize_text(value)
            years = extract_years_from_text(value)

            if not text or not years:
                continue

            if not any(x in text for x in ['year ended','year ending','for the year','for year ended','as on']):
                continue

            role = detect_header_year_role(value)

            if role in {'current', 'previous', 'period'}:
                for year in years:
                    if 1900 <= year <= 2100:
                        candidates.append((col, year, row, role))

    if not candidates:
        return (None, None, None, None)

    # Prefer explicit current/previous roles when available.
    explicit_current = [x for x in candidates if x[3] == 'current']
    explicit_previous = [x for x in candidates if x[3] == 'previous']

    if explicit_current:
        explicit_current.sort(key=lambda x: (x[2], x[0]))
        current_col, current_year = explicit_current[0][0], explicit_current[0][1]
    else:
        current_col, current_year = max(candidates, key=lambda x: x[1])[:2]

    if explicit_previous:
        explicit_previous = [x for x in explicit_previous if x[0] != current_col]
        if explicit_previous:
            explicit_previous.sort(key=lambda x: (x[2], x[0]))
            previous_col, previous_year = explicit_previous[0][0], explicit_previous[0][1]
        else:
            previous_col, previous_year = None, None
    else:
        previous_candidates = [x for x in candidates if x[0] != current_col and x[1] < current_year]
        if previous_candidates:
            previous_col, previous_year = max(previous_candidates, key=lambda x: x[1])[:2]
        else:
            previous_col, previous_year = None, None

    return (current_col, previous_col, current_year, previous_year)


def exact_alias_match(label, aliases):

    normalized = normalize_text(label)

    for alias in aliases:

        alias_normalized = normalize_text(alias)

        if normalized == alias_normalized:
            return True

        if compact_text(normalized) == compact_text(
            alias_normalized
        ):
            return True

    return False


def label_score(label, alias):

    a = normalize_text(label)
    b = normalize_text(alias)

    if not a or not b:
        return 0

    # Exact
    if a == b:
        return 100

    # Compact exact
    if compact_text(a) == compact_text(b):
        return 98

    # --------------------------------------------------------
    # DO NOT allow dangerous substring matching.
    # --------------------------------------------------------

    a_tokens = a.split()
    b_tokens = b.split()

    a_set = set(a_tokens)
    b_set = set(b_tokens)

    if not b_set:
        return 0

    # Exact token set
    if a_set == b_set:
        return 96

    # Alias must be fully contained as tokens
    if b_set.issubset(a_set):

        extra_tokens = len(a_set - b_set)

        if extra_tokens == 0:
            return 96

        if extra_tokens == 1:
            return 82

        return 68

    overlap = len(
        a_set.intersection(b_set)
    )

    if overlap == 0:
        return 0

    # Single generic words are intentionally weak
    if len(b_set) == 1:
        return 35

    ratio = overlap / len(b_set)

    return ratio * 65


# ============================================================
# BEST METRIC MATCH
# ============================================================

def best_metric_match(label):

    best_key = None
    best_score = 0

    normalized_label = normalize_text(label)

    # Strong semantic recognition for common financial labels
    semantic_metric_terms = {
        'revenue': {'revenue','sales','turnover','income from operations','sales and services'},
        'net_profit': {'profit for the year','profit after tax','net profit','profit attributable','profit loss for the period','profit for the period from continuing operations'},
        'total_equity': {'net worth','shareholders equity','shareholders funds','total equity'},
    }

    for metric_key, terms in semantic_metric_terms.items():
        for term in terms:
            if term in normalized_label:
                return metric_key, 120

    if not normalized_label:
        return (None, 0)

    # --------------------------------------------------------
    # 1. Exact / compact alias match gets highest priority.
    # --------------------------------------------------------
    all_aliases = {}

    all_aliases.update(METRIC_ALIASES)

    if "COMPONENT_ALIASES" in globals():
        all_aliases.update(COMPONENT_ALIASES)

    for metric_key, aliases in all_aliases.items():
        if exact_alias_match(normalized_label, aliases):
            return (metric_key, 100)

    # --------------------------------------------------------
    # 2. Parenthetical alias match.
    #    Handles labels such as:
    #    Value of Sales and Services (Revenue)
    #    Turnover (Revenue)
    #    Profit for the Year (Net Profit)
    # --------------------------------------------------------
    parenthetical_parts = re.findall(r'\\(([^()]*)\\)', str(label))

    for part in parenthetical_parts:
        part_normalized = normalize_text(part)

        for metric_key, aliases in METRIC_ALIASES.items():
            if exact_alias_match(part_normalized, aliases):
                return (metric_key, 99)

    # --------------------------------------------------------
    # 3. General scoring.
    # --------------------------------------------------------
    for metric_key, aliases in all_aliases.items():

        for alias in aliases:

            score = label_score(
                normalized_label,
                alias
            )

            if score > best_score:
                best_score = score
                best_key = metric_key

    # --------------------------------------------------------
    # Strong threshold.
    # --------------------------------------------------------
    if best_score < 75:
        return (None, best_score)

    # --------------------------------------------------------
    # Dangerous generic labels.
    # --------------------------------------------------------
    dangerous_labels = {
        'profit',
        'assets',
        'liabilities',
        'equity',
        'debt',
        'borrowings',
        'revenue',
        'sales',
        'receivables',
        'stock'
    }

    if normalized_label in dangerous_labels:

        aliases_for_best = METRIC_ALIASES.get(best_key, [])

        if exact_alias_match(normalized_label, aliases_for_best):
            return (best_key, best_score)

        return (None, best_score)

    return (best_key, best_score)


# ============================================================
# SHEET TYPE DETECTION
# ============================================================

def classify_sheet(sheet_name, df=None):

    text = normalize_text(sheet_name)

    if ("ratio" in text or "ratios" in text or "analysis" in text):
        return "ratio"

    # Sheet name
    if (
        "balance sheet" in text
        or "financial position" in text
        or "statement of financial position" in text
    ):
        return "balance_sheet"

    if (
        "profit and loss" in text
        or "profit loss" in text
        or "statement of profit" in text
        or "income statement" in text
        or "p and l" in text
        or "p l" in text
    ):
        return "pnl"

    if (
        "cash flow" in text
        or "cashflow" in text
        or "cash flows" in text
    ):
        return "cash_flow"

    # --------------------------------------------------------
    # If sheet name isn't informative, inspect content.
    # --------------------------------------------------------

    content = ""

    if df is not None and not df.empty:

        sample = df.iloc[
            :min(len(df), 30),
            :min(df.shape[1], 8)
        ]

        content = " ".join(
            normalize_text(x)
            for x in sample.astype(str).values.flatten()
        )

    if (
        "cash flow from operating activities" in content
        or "cash flows from operating activities" in content
    ):
        return "cash_flow"

    if (
        "balance sheet" in content
        or "statement of financial position" in content
        or "current assets" in content
        or "current liabilities" in content
    ):
        return "balance_sheet"

    if (
        "revenue from operations" in content
        or "profit after tax" in content
        or "profit for the year" in content
    ):
        return "pnl"

    return "unknown"


# ============================================================
# LABEL COLUMN DETECTION
# ============================================================

def find_label_column(df):

    if df is None or df.empty:
        return None

    best_col = None
    best_score = -1

    for col in range(df.shape[1]):

        score = 0

        rows_to_check = min(
            len(df),
            150
        )

        for row in range(rows_to_check):

            value = df.iat[row, col]

            if value is None:
                continue

            text = normalize_text(value)

            if not text:
                continue

            metric, metric_score = best_metric_match(
                text
            )

            if metric is not None:
                score += metric_score

        if score > best_score:

            best_score = score
            best_col = col

    return best_col


# ============================================================
# ROW VALUE EXTRACTION
# ============================================================

def extract_row_values(
    df,
    row_index,
    label_col,
    current_col,
    previous_col
):

    current_value = None
    previous_value = None

    # --------------------------------------------------------
    # First: use identified year columns.
    # --------------------------------------------------------

    if (
        current_col is not None
        and current_col < df.shape[1]
    ):

        current_value = parse_number(
            df.iat[
                row_index,
                current_col
            ]
        )

    if (
        previous_col is not None
        and previous_col < df.shape[1]
    ):

        previous_value = parse_number(
            df.iat[
                row_index,
                previous_col
            ]
        )

    # --------------------------------------------------------
    # Collect numeric cells.
    # --------------------------------------------------------

    numeric_cells = []

    for col in range(df.shape[1]):

        if col == label_col:
            continue

        value = parse_number(
            df.iat[
                row_index,
                col
            ]
        )

        if value is not None:

            numeric_cells.append(
                (
                    col,
                    value
                )
            )

    # --------------------------------------------------------
    # Fallback:
    # use first numeric cells AFTER label column.
    # --------------------------------------------------------

    right_side = [
        item
        for item in numeric_cells
        if item[0] > label_col
    ]

    if current_value is None and right_side:

        current_value = right_side[0][1]

    if previous_value is None and len(right_side) >= 2:

        previous_value = right_side[1][1]

    # --------------------------------------------------------
    # NEVER duplicate current into previous.
    # --------------------------------------------------------

    if (
        current_value is not None
        and previous_value is not None
        and current_value == previous_value
    ):

        # Do not automatically assume duplicate values are wrong
        # in the accounting sense, but if both columns are actually
        # the same column, the caller will remove previous_col.
        pass

    return (
        current_value,
        previous_value
    )


# ============================================================
# METRIC-SPECIFIC ACCEPTANCE RULES
# ============================================================

def metric_label_is_valid(
    metric_key,
    label,
    score
):

    normalized = normalize_text(label)

    if not normalized:
        return False

    # --------------------------------------------------------
    # Revenue
    # --------------------------------------------------------

    if metric_key == "revenue":

        invalid_terms = [
            "other income",
            "finance income",
            "interest income",
            "tax income",
            "fixed assets sales",
            "fixed asset sales",
            "sale of fixed assets",
            "profit on sale of fixed assets"
        ]

        if any(
            term in normalized
            for term in invalid_terms
        ):
            return False

    # --------------------------------------------------------
    # Net profit
    # --------------------------------------------------------

    if metric_key == "net_profit":

        required_patterns = [
            "net profit",
            "profit after tax",
            "profit for the year",
            "profit for period",
            "profit attributable",
            "profit for the period from continuing operations",
            "profit loss for the period"
        ]

        if not any(
            pattern in normalized
            for pattern in required_patterns
        ):
            return False

    # --------------------------------------------------------
    # Trade receivables
    # --------------------------------------------------------

    if metric_key == "trade_receivables":

        if normalized in {
            "receivables",
            "debtors"
        }:
            return False

    # --------------------------------------------------------
    # Total debt
    # --------------------------------------------------------

    if metric_key == "total_debt":

        # Individual borrowings are not automatically total debt.
        if normalized in {
            "term borrowings",
            "short term borrowings",
            "long term borrowings",
            "bank borrowings",
            "secured borrowings",
            "unsecured borrowings"
        }:
            return False

    # --------------------------------------------------------
    # Total equity
    # --------------------------------------------------------

    if metric_key == "total_equity":

        if normalized in {
            "equity",
            "share capital",
            "reserves",
            "retained earnings"
        }:
            return False

    # --------------------------------------------------------
    # Current assets
    # --------------------------------------------------------

    if metric_key == "current_assets":

        if normalized not in {
            "current assets",
            "total current assets"
        }:
            return False

    # --------------------------------------------------------
    # Current liabilities
    # --------------------------------------------------------

    if metric_key == "current_liabilities":

        if normalized not in {
            "current liabilities",
            "total current liabilities"
        }:
            return False

    return True


# ============================================================
# SHEET COMPATIBILITY
# ============================================================

def sheet_compatibility(
    metric_key,
    statement_type
):

    expected = METRIC_STATEMENT.get(
        metric_key
    )

    if statement_type == expected:
        return 1.0

    # Ratio / analysis sheets must NEVER be used as primary sources.
    if statement_type == "ratio":
        return 0.0

    # Notes can support balance-sheet metrics,
    # but should not beat the actual Balance Sheet.
    if (
        expected == "balance_sheet"
        and statement_type == "notes"
    ):
        return 0.70

    # Unknown sheets are weak evidence.
    if statement_type == "unknown":
        return 0.40

    return 0.10


# ============================================================
# SHEET EXTRACTION
# ============================================================

def extract_from_sheet(
    df,
    sheet_name=""
):

    results = {}

    if df is None or df.empty:
        return results

    working = df.copy()

    statement_type = classify_sheet(
        sheet_name,
        working
    )

    # Notes
    if statement_type == "unknown":

        sheet_text = normalize_text(
            sheet_name
        )

        if (
            "note" in sheet_text
            or "notes" in sheet_text
            or "schedule" in sheet_text
        ):
            statement_type = "notes"

    label_col = find_label_column(
        working
    )

    if label_col is None:
        return results

    # --------------------------------------------------------
    # YEAR DETECTION
    # --------------------------------------------------------

    # --------------------------------------------------------
    # YEAR DETECTION
    # --------------------------------------------------------
    #
    # Prefer determine_year_columns() because it validates
    # actual financial-year columns and avoids false years
    # from CIN numbers, dates, notes, etc.
    #
    # Semantic detection is used only as a fallback.
    # --------------------------------------------------------

    (
        current_col,
        previous_col,
        current_year,
        previous_year
    ) = determine_year_columns(
        working
    )

    if current_col is None:

        (
            semantic_current_col,
            semantic_previous_col,
            semantic_current_year,
            semantic_previous_year
        ) = detect_semantic_year_columns(
            working
        )

        current_col = semantic_current_col
        previous_col = semantic_previous_col
        current_year = semantic_current_year
        previous_year = semantic_previous_year

    # --------------------------------------------------------
    # Same-column protection
    # --------------------------------------------------------

    if (
        current_col is not None
        and previous_col is not None
        and current_col == previous_col
    ):

        previous_col = None
        previous_year = None

    # --------------------------------------------------------
    # --------------------------------------------------------
    # Scan rows
    # --------------------------------------------------------

    for row_index in range(
        len(working)
    ):

        label_value = working.iat[
            row_index,
            label_col
        ]

        label = normalize_text(
            label_value
        )

        if not label:
            continue

        metric_key, score = best_metric_match(
            label
        )

        if metric_key is None:
            continue

        if not metric_label_is_valid(
            metric_key,
            label,
            score
        ):
            continue

        # ----------------------------------------------------
        # Statement compatibility
        # ----------------------------------------------------

        compatibility = sheet_compatibility(
            metric_key,
            statement_type
        )

        if compatibility <= 0:
            continue

        (
            current_value,
            previous_value
        ) = extract_row_values(
            working,
            row_index,
            label_col,
            current_col,
            previous_col
        )

        if (
            current_value is None
            and previous_value is None
        ):
            continue

        final_score = (
            score * compatibility
        )

        entry = {

            "current": current_value,

            "previous": previous_value,

            "score": final_score,

            "raw_score": score,

            "sheet": sheet_name,

            "statement_type": statement_type,

            "label": label,

            "current_year": current_year,

            "previous_year": previous_year
        }

        existing = results.get(
            metric_key
        )

        if existing is None:

            results[metric_key] = entry

        elif final_score > existing["score"]:

            results[metric_key] = entry

    # --------------------------------------------------------
    # TRADE PAYABLE PARENT / CHILD AGGREGATION
    # --------------------------------------------------------
    #
    # Some balance sheets show:
    #
    # (b) Trade Payables
    #     Total outstanding dues of micro and small enterprise
    #     Total outstanding dues of other creditors
    #
    # The parent row has no numbers, so aggregate its detail rows.
    # --------------------------------------------------------
    if (
    "trade_payables" not in results
    or results["trade_payables"].get("current") is None
):
        for _tp_row in range(len(working)):
            _tp_label = normalize_text(
                working.iat[_tp_row, label_col]
            )
            if not _tp_label:
                continue
            if _tp_label not in {
                "trade payables",
                "trade payable"
            } and not (
                _tp_label.startswith("(b) trade payable")
                or _tp_label.startswith("(b) trade payables")
            ):
                continue
            _tp_current_total = 0
            _tp_previous_total = 0
            _tp_current_found = False
            _tp_previous_found = False
            for _child_row in range(
                _tp_row + 1,
                min(len(working), _tp_row + 15)
            ):
                _child_label = normalize_text(
                    working.iat[_child_row, label_col]
                )
                if not _child_label:
                    continue
                # Stop at the next balance-sheet component.
                if (
                    "other current liabil" in _child_label
                    or "short term provision" in _child_label
                    or "short-term provision" in _child_label
                    or _child_label.startswith("total")
                ):
                    break
                # Only aggregate trade-payable detail rows.
                if not (
                    "outstanding dues" in _child_label
                    or "customer credit" in _child_label
                    or "credit balances" in _child_label
                ):
                    continue
                _child_current, _child_previous = extract_row_values(
                    working,
                    _child_row,
                    label_col,
                    current_col,
                    previous_col
                )
                if _child_current is not None:
                    _tp_current_total += _child_current
                    _tp_current_found = True
                if _child_previous is not None:
                    _tp_previous_total += _child_previous
                    _tp_previous_found = True
            if _tp_current_found or _tp_previous_found:
                results["trade_payables"] = {
                    "current": (
                        _tp_current_total
                        if _tp_current_found
                        else None
                    ),
                    "previous": (
                        _tp_previous_total
                        if _tp_previous_found
                        else None
                    ),
                    "score": 118,
                    "raw_score": 118,
                    "sheet": sheet_name,
                    "statement_type": statement_type,
                    "label": "Trade Payables (aggregated from detail rows)",
                    "current_year": current_year,
                    "previous_year": previous_year
                }
                break
    return results


# ============================================================
# SHEET PRIORITY
# ============================================================

def sheet_priority(sheet_name):

    text = normalize_text(
        sheet_name
    )

    if (
        "balance sheet" in text
        or "statement of financial position" in text
        or "financial position" in text
    ):
        return 100

    if (
        "profit and loss" in text
        or "profit loss" in text
        or "income statement" in text
        or "statement of profit" in text
        or "p and l" in text
        or "p l" in text
    ):
        return 95

    if (
        "cash flow" in text
        or "cashflow" in text
    ):
        return 90

    if (
        "financial statement" in text
        or "financials" in text
    ):
        return 80

    if (
        "note" in text
        or "notes" in text
        or "schedule" in text
    ):
        return 60

    return 40


# ============================================================
# MERGE SHEET RESULTS
# ============================================================

def merge_results(sheet_results):

    final = {}

    for sheet_name, metrics in sheet_results.items():

        priority = sheet_priority(
            sheet_name
        )

        for metric_key, info in metrics.items():

            base_score = info.get(
                "score",
                0
            )

            # Statement-specific priority
            statement_type = info.get(
                "statement_type",
                "unknown"
            )

            expected = METRIC_STATEMENT.get(
                metric_key
            )

            if statement_type == expected:
                statement_bonus = 25

            elif (
                expected == "balance_sheet"
                and statement_type == "notes"
            ):
                statement_bonus = 5

            else:
                statement_bonus = 0

            score = (
                base_score
                + priority * 0.15
                + statement_bonus
            )

            entry = {

                "current": info.get(
                    "current"
                ),

                "previous": info.get(
                    "previous"
                ),

                "score": score,

                "raw_score": info.get(
                    "raw_score",
                    0
                ),

                "sheet": sheet_name,

                "statement_type": statement_type,

                "label": info.get(
                    "label",
                    ""
                ),

                "current_year": info.get(
                    "current_year"
                ),

                "previous_year": info.get(
                    "previous_year"
                )
            }

            existing = final.get(
                metric_key
            )

            if existing is None:

                final[metric_key] = entry
                continue

            # ------------------------------------------------
            # Prefer candidates with both years.
            # ------------------------------------------------

            existing_complete = (
                existing["current"] is not None
                and existing["previous"] is not None
            )

            new_complete = (
                entry["current"] is not None
                and entry["previous"] is not None
            )

            if (
                new_complete
                and not existing_complete
            ):

                final[metric_key] = entry
                continue

            # ------------------------------------------------
            # Otherwise highest quality score wins.
            # ------------------------------------------------

            if entry["score"] > existing["score"]:

                final[metric_key] = entry

    return final



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


# ============================================================
# FINANCIAL DATA STANDARDIZATION
# ============================================================

def standardize_financial_data(
    merged_results
):

    data = {}

    all_metric_keys = list(METRIC_ALIASES.keys()) + [
        key for key in COMPONENT_ALIASES.keys()
        if key not in METRIC_ALIASES
    ]
    for metric_key in all_metric_keys:

        info = merged_results.get(
            metric_key
        )

        if info is None:

            data[metric_key] = None

            data[
                f"previous_{metric_key}"
            ] = None

        else:

            data[metric_key] = info.get(
                "current"
            )

            data[
                f"previous_{metric_key}"
            ] = info.get(
                "previous"
            )

    data["_extraction_metadata"] = {

        metric_key:
            merged_results.get(
                metric_key,
                {}
            )

        for metric_key
        in METRIC_ALIASES.keys()
    }

    return data


# ============================================================
# ACCOUNTING VALIDATION
# ============================================================

def accounting_validation(
    financial_data
):

    warnings = []

    # --------------------------------------------------------
    # Current assets should not be below inventory alone.
    # --------------------------------------------------------

    current_assets = financial_data.get(
        "current_assets"
    )

    inventory = financial_data.get(
        "inventory"
    )

    if (
        current_assets is not None
        and inventory is not None
        and current_assets < inventory
    ):

        warnings.append(
            "Current Assets is lower than Inventory. "
            "Extraction should be reviewed."
        )

    # --------------------------------------------------------
    # Current liabilities should be positive in normal cases.
    # --------------------------------------------------------

    current_liabilities = financial_data.get(
        "current_liabilities"
    )

    if (
        current_liabilities is not None
        and current_liabilities == 31
    ):

        warnings.append(
            "Current Liabilities extracted as 31. "
            "This looks like a non-financial/header value."
        )

    # --------------------------------------------------------
    # Debt = 31 is suspicious.
    # --------------------------------------------------------

    total_debt = financial_data.get(
        "total_debt"
    )

    if total_debt == 31:

        warnings.append(
            "Total Debt extracted as 31. "
            "This is likely a false match."
        )

    # --------------------------------------------------------
    # Equity = very small number is suspicious.
    # --------------------------------------------------------

    total_equity = financial_data.get(
        "total_equity"
    )

    if (
        total_equity is not None
        and abs(total_equity) < 100
    ):

        warnings.append(
            "Total Equity appears unusually small. "
            "Extraction should be reviewed."
        )

    return warnings


# ============================================================
# VALIDATION REPORT
# ============================================================

def build_validation_report(
    financial_data,
    merged_results
):

    rows = []

    accounting_warnings = accounting_validation(
        financial_data
    )

    all_metric_keys = list(METRIC_ALIASES.keys()) + [
        key for key in COMPONENT_ALIASES.keys()
        if key not in METRIC_ALIASES
    ]
    for metric_key in all_metric_keys:

        info = merged_results.get(
            metric_key
        )

        current = financial_data.get(
            metric_key
        )

        previous = financial_data.get(
            f"previous_{metric_key}"
        )

        display_name = (
            metric_key
            .replace("_", " ")
            .title()
        )

        if current is None:

            status = "MISSING"

            details = (
                "No reliable numeric value "
                "was detected."
            )

        elif previous is None:

            status = "PARTIAL"

            details = (
                "Current-year value detected, "
                "but previous-year value was "
                "not reliably identified."
            )

        else:

            status = "AVAILABLE"

            details = (
                f"Current and previous-year "
                f"values detected. Source: "
                f"{info.get('sheet', 'Unknown sheet')}. "
                f"Matched label: "
                f"{info.get('label', '')}."
            )

        rows.append({
            "Metric": display_name,
            "Status": status,
            "Details": details
        })

    # Add accounting warnings
    for warning in accounting_warnings:

        rows.append({
            "Metric": "ACCOUNTING VALIDATION",
            "Status": "WARNING",
            "Details": warning
        })

    return rows


# ============================================================
# MAIN EXTRACTION FUNCTION
# ============================================================

def extract_financial_data(
    workbook_data
):

    if not isinstance(
        workbook_data,
        dict
    ):

        raise ValueError(
            "Workbook data must be a dictionary "
            "of worksheet names and DataFrames."
        )

    sheet_results = {}

    for sheet_name, df in workbook_data.items():

        if not isinstance(
            df,
            pd.DataFrame
        ):
            continue

        try:

            result = extract_from_sheet(
                df,
                sheet_name
            )

            sheet_results[
                sheet_name
            ] = result

        except Exception:

            sheet_results[
                sheet_name
            ] = {}

    merged_results = merge_results(
        sheet_results
    )

    merged_results = derive_missing_totals(
        merged_results
    )

    financial_data = standardize_financial_data(
        merged_results
    )

    validation_report = build_validation_report(
        financial_data,
        merged_results
    )

    return (
        financial_data,
        validation_report
    )


# ============================================================
# COMPANY NAME DETECTION
# ============================================================

GENERIC_COMPANY_TERMS = {

    "balance sheet",
    "profit and loss",
    "profit and loss account",
    "statement of profit and loss",
    "statement of financial position",
    "cash flow statement",
    "cash flow",
    "financial statements",
    "financial statement",
    "notes to accounts",
    "notes to financial statements",
    "particulars",
    "amount",
    "year ended",
    "for the year ended",
    "in rupees",
    "in rs",
    "in lakhs",
    "in crores",
    "in millions",
    "in thousands"
}


def is_probable_company_name(
    value
):

    if value is None:
        return False

    try:

        if pd.isna(value):
            return False

    except Exception:
        pass

    text = str(value).strip()

    if not text:
        return False

    normalized = normalize_text(
        text
    )

    if not normalized:
        return False

    if normalized in GENERIC_COMPANY_TERMS:
        return False

    if len(text) > 150:
        return False

    if parse_number(text) is not None:
        return False

    bad_terms = [

        "auditor",
        "chartered accountant",
        "independent auditor",
        "registered office",
        "cin",
        "llp",
        "notes forming part",
        "basis of preparation",
        "report of",
        "directors report"
    ]

    if any(
        term in normalized
        for term in bad_terms
    ):
        return False

    if not re.search(
        r"[A-Za-z]",
        text
    ):
        return False

    return True


def detect_company_name(
    workbook_data,
    filename=""
):

    candidates = []

    if isinstance(
        workbook_data,
        dict
    ):

        ordered_sheets = sorted(
            workbook_data.items(),
            key=lambda item:
                sheet_priority(
                    item[0]
                ),
            reverse=True
        )

        for sheet_name, df in ordered_sheets:

            if not isinstance(
                df,
                pd.DataFrame
            ):
                continue

            rows_to_check = min(
                len(df),
                12
            )

            cols_to_check = min(
                df.shape[1],
                6
            )

            for row in range(
                rows_to_check
            ):

                for col in range(
                    cols_to_check
                ):

                    value = df.iat[
                        row,
                        col
                    ]

                    if not is_probable_company_name(
                        value
                    ):
                        continue

                    text = str(value).strip()

                    normalized = normalize_text(
                        text
                    )

                    corporate_bonus = 0

                    if any(
                        x in normalized
                        for x in [
                            "private limited",
                            "pvt ltd",
                            "limited",
                            "ltd",
                            "llp",
                            "inc",
                            "corporation",
                            "corp"
                        ]
                    ):

                        corporate_bonus = 30

                    position_bonus = max(
                        0,
                        15 - row * 2
                    )

                    score = (
                        sheet_priority(
                            sheet_name
                        )
                        + corporate_bonus
                        + position_bonus
                    )

                    candidates.append(
                        (
                            score,
                            text
                        )
                    )

    if filename:

        base = str(filename)

        base = re.sub(
            r"\.(xlsx|xls|csv)$",
            "",
            base,
            flags=re.IGNORECASE
        )

        base = re.sub(
            r"[_\-]+",
            " ",
            base
        )

        base = re.sub(
            r"\b(19|20)\d{2}\b",
            "",
            base
        )

        base = re.sub(
            r"\s+",
            " ",
            base
        ).strip()

        if base:

            candidates.append(
                (
                    20,
                    base
                )
            )

    if candidates:

        candidates.sort(
            key=lambda x: x[0],
            reverse=True
        )

        return candidates[0][1]

    return "Financial Analysis"


# ============================================================
# DEBUG SUMMARY
# ============================================================

def extraction_debug_summary(
    workbook_data
):

    summary = []

    if not isinstance(
        workbook_data,
        dict
    ):
        return summary

    for sheet_name, df in workbook_data.items():

        if not isinstance(
            df,
            pd.DataFrame
        ):
            continue

        result = extract_from_sheet(
            df,
            sheet_name
        )

        summary.append({

            "Sheet": sheet_name,

            "Statement Type":
                classify_sheet(
                    sheet_name,
                    df
                ),

            "Rows":
                len(df),

            "Columns":
                len(df.columns),

            "Metrics Detected":
                len(result),

            "Detected Metrics":
                ", ".join(
                    result.keys()
                )
        })

    return summary

















