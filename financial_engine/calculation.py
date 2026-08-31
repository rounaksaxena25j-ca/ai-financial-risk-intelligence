"""
CALCULATION MODULE
============================================================
Single source of truth for every number derived from the
standardized financial data.

Why this file exists:
Previously, ratio/growth/health-score logic was duplicated in
app.py (Dashboard, Cross-Statement Intelligence) AND risk_engine.py
(assess_collection, assess_inventory, assess_leverage), each with
its OWN thresholds. That meant the Dashboard tab and the Risk tab
could show different verdicts on the same data.

Rule going forward: nothing outside this file computes a ratio,
a year-over-year change, or a health score. Everything else
(the UI, the Analytical Review Engine) calls into this module
and displays what it returns.
============================================================
"""

import pandas as pd


# ============================================================
# BASIC SAFE MATH
# ============================================================

def safe_ratio(numerator, denominator):
    """
    Divide two numbers safely. Returns None (never 0, never an
    error) if either value is missing or the denominator is zero,
    so the UI can honestly show "Not Available" instead of a
    misleading number like 0.00.
    """
    try:
        if numerator is None or denominator is None:
            return None

        if pd.isna(numerator) or pd.isna(denominator):
            return None

        if float(denominator) == 0:
            return None

        return float(numerator) / float(denominator)

    except Exception:
        return None


def yoy(current, previous):
    """
    Year-over-year percentage change: (current - previous) / |previous| * 100.
    Returns None if either value is missing or previous is zero
    (division by zero would otherwise be undefined).
    """
    try:
        if current is None or previous is None:
            return None

        if pd.isna(current) or pd.isna(previous):
            return None

        if float(previous) == 0:
            return None

        return ((float(current) - float(previous)) / abs(float(previous))) * 100

    except Exception:
        return None


# ============================================================
# METRIC EXTRACTION HELPERS
# ============================================================

def get_value(data, key):
    """
    Safely pull one metric out of the standardized financial_data
    dict. Returns None for missing/NaN/non-numeric values instead
    of raising an error.
    """
    if not isinstance(data, dict):
        return None

    value = data.get(key)

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    try:
        return float(value)
    except Exception:
        return None


def get_change(data, metric_key):
    """
    Convenience wrapper: given financial_data and a metric key
    like "revenue", returns the YoY % change using
    <metric_key> and previous_<metric_key>.
    """
    current = get_value(data, metric_key)
    previous = get_value(data, f"previous_{metric_key}")
    return yoy(current, previous)


# ============================================================
# CORE METRICS BUNDLE
# ============================================================
# One function that computes every number the rest of the app
# needs, once, from the standardized financial_data dict.
# The UI and the Analytical Review Engine both call this and
# read off the same dictionary — this is what guarantees they
# never disagree.
# ============================================================

def compute_all_metrics(financial_data):
    """
    Given the standardized financial_data dict (from
    extraction.extract_financial_data), compute every ratio and
    growth figure the app needs, in one place.

    Returns a dict with two sections:
      "values"  -> current-year figures, growth %, and ratios
      "growth"  -> just the YoY % changes, grouped for convenience
    """

    d = financial_data

    # ---- raw current/previous pairs ----
    revenue = get_value(d, "revenue")
    previous_revenue = get_value(d, "previous_revenue")

    net_profit = get_value(d, "net_profit")
    previous_net_profit = get_value(d, "previous_net_profit")

    receivables = get_value(d, "trade_receivables")
    previous_receivables = get_value(d, "previous_trade_receivables")

    inventory = get_value(d, "inventory")
    previous_inventory = get_value(d, "previous_inventory")

    debt = get_value(d, "total_debt")
    previous_debt = get_value(d, "previous_total_debt")

    equity = get_value(d, "total_equity")
    previous_equity = get_value(d, "previous_total_equity")

    ocf = get_value(d, "operating_cash_flow")
    previous_ocf = get_value(d, "previous_operating_cash_flow")

    current_assets = get_value(d, "current_assets")
    current_liabilities = get_value(d, "current_liabilities")

    # ---- growth (YoY %) ----
    revenue_growth = yoy(revenue, previous_revenue)
    profit_growth = yoy(net_profit, previous_net_profit)
    receivable_growth = yoy(receivables, previous_receivables)
    inventory_growth = yoy(inventory, previous_inventory)
    debt_growth = yoy(debt, previous_debt)
    equity_growth = yoy(equity, previous_equity)
    ocf_growth = yoy(ocf, previous_ocf)

    # ---- ratios ----
    current_ratio = safe_ratio(current_assets, current_liabilities)

    quick_assets = None
    if current_assets is not None and inventory is not None:
        quick_assets = current_assets - inventory

    quick_ratio = safe_ratio(quick_assets, current_liabilities)
    debt_equity = safe_ratio(debt, equity)
    profit_margin = safe_ratio(net_profit, revenue)
    ocf_margin = safe_ratio(ocf, revenue)

    values = {
        "revenue": revenue, "previous_revenue": previous_revenue,
        "net_profit": net_profit, "previous_net_profit": previous_net_profit,
        "receivables": receivables, "previous_receivables": previous_receivables,
        "inventory": inventory, "previous_inventory": previous_inventory,
        "debt": debt, "previous_debt": previous_debt,
        "equity": equity, "previous_equity": previous_equity,
        "ocf": ocf, "previous_ocf": previous_ocf,
        "current_assets": current_assets,
        "current_liabilities": current_liabilities,

        "current_ratio": current_ratio,
        "quick_ratio": quick_ratio,
        "debt_equity": debt_equity,
        "profit_margin": profit_margin,
        "ocf_margin": ocf_margin,
    }

    growth = {
        "revenue_growth": revenue_growth,
        "profit_growth": profit_growth,
        "receivable_growth": receivable_growth,
        "inventory_growth": inventory_growth,
        "debt_growth": debt_growth,
        "equity_growth": equity_growth,
        "ocf_growth": ocf_growth,
    }

    return {
        "values": values,
        "growth": growth
    }


# ============================================================
# HEALTH SCORE
# ============================================================
# Moved as-is from app.py, unchanged in logic — just relocated
# so it lives with everything else that computes a number.
# ============================================================

def compute_health_score(metrics):
    """
    Given the dict returned by compute_all_metrics(), compute an
    overall financial health score (0-100) and label.

    Returns a dict: {
        "score": int or None,
        "label": str,
        "components": [(area_name, score), ...]
    }
    """

    v = metrics["values"]
    g = metrics["growth"]

    current_ratio = v["current_ratio"]
    debt_equity = v["debt_equity"]
    profit_margin = v["profit_margin"]
    ocf = v["ocf"]
    ocf_growth = g["ocf_growth"]
    receivable_growth = g["receivable_growth"]
    revenue_growth = g["revenue_growth"]
    profit_growth = g["profit_growth"]

    components = []

    if current_ratio is not None:
        if current_ratio >= 2:
            score = 100
        elif current_ratio >= 1.5:
            score = 85
        elif current_ratio >= 1:
            score = 65
        elif current_ratio >= 0.75:
            score = 40
        else:
            score = 20
        components.append(("Liquidity", score))

    if debt_equity is not None:
        if debt_equity <= 0.5:
            score = 100
        elif debt_equity <= 1:
            score = 85
        elif debt_equity <= 1.5:
            score = 70
        elif debt_equity <= 2:
            score = 50
        else:
            score = 25
        components.append(("Leverage", score))

    if profit_margin is not None:
        if profit_margin >= 0.20:
            score = 100
        elif profit_margin >= 0.15:
            score = 90
        elif profit_margin >= 0.10:
            score = 75
        elif profit_margin >= 0.05:
            score = 60
        elif profit_margin >= 0:
            score = 45
        else:
            score = 20
        components.append(("Profitability", score))

    if ocf is not None:
        if ocf > 0:
            if ocf_growth is not None and ocf_growth > 10:
                score = 95
            elif ocf_growth is not None and ocf_growth >= 0:
                score = 80
            else:
                score = 65
        else:
            score = 20
        components.append(("Cash Flow", score))

    if receivable_growth is not None and revenue_growth is not None:
        gap = receivable_growth - revenue_growth
        if gap <= 0:
            score = 95
        elif gap <= 5:
            score = 80
        elif gap <= 10:
            score = 65
        elif gap <= 20:
            score = 45
        else:
            score = 25
        components.append(("Working Capital", score))

    if profit_growth is not None and ocf_growth is not None:
        if profit_growth > 0 and ocf_growth > 0:
            score = 90
        elif profit_growth > 0 and ocf_growth <= 0:
            score = 35
        elif profit_growth <= 0 and ocf_growth > 0:
            score = 65
        else:
            score = 45
        components.append(("Earnings Quality", score))

    if components:
        health_score = round(sum(s for _, s in components) / len(components))
    else:
        health_score = None

    if health_score is None:
        health_label = "NOT AVAILABLE"
    elif health_score >= 80:
        health_label = "STRONG"
    elif health_score >= 65:
        health_label = "HEALTHY"
    elif health_score >= 50:
        health_label = "WATCH"
    elif health_score >= 35:
        health_label = "WEAK"
    else:
        health_label = "CRITICAL"

    return {
        "score": health_score,
        "label": health_label,
        "components": components
    }
