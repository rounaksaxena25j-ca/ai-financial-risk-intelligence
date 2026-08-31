import math


# ============================================================
# FINANCIAL RISK ENGINE
# ============================================================
#
# Purpose:
# Convert standardized financial data into:
#
# Risk Level
# Evidence
# Financial Impact
# Recommended Action
#
# Rule:
# NEVER invent a risk when required data is unavailable.
# ============================================================


# ============================================================
# HELPERS
# ============================================================

def get(data, key):
    return data.get(key)


def change(data, metric):

    current = get(data, metric)

    previous = get(
        data,
        f"previous_{metric}"
    )

    if current is None or previous is None:
        return None

    if previous == 0:
        return None

    return (
        (current - previous)
        /
        abs(previous)
    ) * 100


def ratio(
    numerator,
    denominator
):

    if numerator is None:
        return None

    if denominator is None:
        return None

    if denominator == 0:
        return None

    return numerator / denominator


def fmt_percent(value):

    if value is None:
        return "Not available"

    return f"{value:+.1f}%"


def fmt_number(value):

    if value is None:
        return "Not available"

    return f"{value:,.2f}"


def unavailable():

    return {

        "level":
            "NOT AVAILABLE",

        "evidence":
            "Insufficient financial data to reliably assess this risk.",

        "financial_impact":
            "Cannot determine financial impact from the available information.",

        "recommended_action":
            "Provide the missing financial information for a reliable assessment."
    }


# ============================================================
# LIQUIDITY RISK
# ============================================================

def assess_liquidity(data):

    current_assets = get(
        data,
        "current_assets"
    )

    current_liabilities = get(
        data,
        "current_liabilities"
    )

    current_ratio = ratio(
        current_assets,
        current_liabilities
    )

    if current_ratio is None:

        return unavailable()

    if current_ratio < 1:

        return {

            "level":
                "HIGH",

            "evidence":
                f"Current ratio is {current_ratio:.2f}, "
                "indicating that current liabilities exceed "
                "current assets.",

            "financial_impact":
                "The company may face pressure in meeting "
                "short-term obligations.",

            "recommended_action":
                "Strengthen working-capital management, "
                "accelerate collections and review short-term "
                "funding requirements."
        }

    if current_ratio < 1.5:

        return {

            "level":
                "MEDIUM",

            "evidence":
                f"Current ratio is {current_ratio:.2f}, "
                "providing only a moderate short-term liquidity cushion.",

            "financial_impact":
                "Unexpected working-capital requirements "
                "could place pressure on near-term liquidity.",

            "recommended_action":
                "Monitor cash balances, receivables and "
                "short-term obligations closely."
        }

    return {

        "level":
            "LOW",

        "evidence":
            f"Current ratio is {current_ratio:.2f}, "
            "indicating a reasonable current-asset cushion.",

        "financial_impact":
            "No major liquidity pressure is indicated "
            "by the available current-asset information.",

        "recommended_action":
            "Continue monitoring working capital and "
            "maintain adequate liquidity buffers."
    }


# ============================================================
# COLLECTION RISK
# ============================================================

def assess_collection(data):

    receivable_change = change(
        data,
        "trade_receivables"
    )

    revenue_change = change(
        data,
        "revenue"
    )

    if (
        receivable_change is None
        or revenue_change is None
    ):

        return unavailable()

    gap = (
        receivable_change
        -
        revenue_change
    )

    if gap > 20:

        return {

            "level":
                "HIGH",

            "evidence":
                f"Trade receivables increased "
                f"{receivable_change:.1f}% while revenue "
                f"changed {revenue_change:.1f}%.",

            "financial_impact":
                "Receivables growing substantially faster "
                "than revenue can delay cash conversion and "
                "increase working-capital requirements.",

            "recommended_action":
                "Tighten customer credit controls, "
                "prioritize overdue collections and review "
                "customer payment terms."
        }

    if gap > 10:

        return {

            "level":
                "MEDIUM",

            "evidence":
                f"Trade receivables increased "
                f"{receivable_change:.1f}% compared with "
                f"revenue growth of {revenue_change:.1f}%.",

            "financial_impact":
                "The difference may indicate emerging "
                "collection pressure.",

            "recommended_action":
                "Monitor receivable ageing and strengthen "
                "collection follow-ups."
        }

    return {

        "level":
            "LOW",

        "evidence":
            f"Trade receivables changed "
            f"{receivable_change:.1f}% compared with "
            f"revenue change of {revenue_change:.1f}%.",

        "financial_impact":
            "No significant receivables-growth imbalance "
            "was identified.",

        "recommended_action":
            "Continue monitoring receivable ageing "
            "and customer payment behaviour."
    }


# ============================================================
# INVENTORY RISK
# ============================================================

def assess_inventory(data):

    inventory_change = change(
        data,
        "inventory"
    )

    revenue_change = change(
        data,
        "revenue"
    )

    if (
        inventory_change is None
        or revenue_change is None
    ):

        return unavailable()

    gap = (
        inventory_change
        -
        revenue_change
    )

    if gap > 20:

        return {

            "level":
                "HIGH",

            "evidence":
                f"Inventory increased "
                f"{inventory_change:.1f}% while revenue "
                f"changed {revenue_change:.1f}%.",

            "financial_impact":
                "Excess inventory can lock up cash and "
                "increase the risk of slow-moving or "
                "obsolete stock.",

            "recommended_action":
                "Review inventory ageing, stock turnover "
                "and procurement levels."
        }

    if gap > 10:

        return {

            "level":
                "MEDIUM",

            "evidence":
                f"Inventory growth of "
                f"{inventory_change:.1f}% exceeded revenue "
                f"growth of {revenue_change:.1f}%.",

            "financial_impact":
                "Working capital may be increasingly tied "
                "up in inventory.",

            "recommended_action":
                "Monitor slow-moving inventory and "
                "align procurement with demand."
        }

    return {

        "level":
            "LOW",

        "evidence":
            f"Inventory changed "
            f"{inventory_change:.1f}% compared with "
            f"revenue change of {revenue_change:.1f}%.",

        "financial_impact":
            "No significant inventory-growth imbalance "
            "was identified.",

        "recommended_action":
            "Continue monitoring inventory turnover "
            "and stock ageing."
    }


# ============================================================
# LEVERAGE RISK
# ============================================================

def assess_leverage(data):

    debt_change = change(
        data,
        "total_debt"
    )

    equity_change = change(
        data,
        "total_equity"
    )

    if (
        debt_change is None
        or equity_change is None
    ):

        return unavailable()

    gap = (
        debt_change
        -
        equity_change
    )

    if gap > 20:

        return {

            "level":
                "HIGH",

            "evidence":
                f"Debt changed {debt_change:.1f}% "
                f"while equity changed {equity_change:.1f}%.",

            "financial_impact":
                "Debt increasing substantially faster than "
                "equity can increase financial leverage and "
                "debt-servicing pressure.",

            "recommended_action":
                "Review borrowing plans, debt maturity "
                "profile and debt-servicing capacity."
        }

    if gap > 10:

        return {

            "level":
                "MEDIUM",

            "evidence":
                f"Debt growth of {debt_change:.1f}% "
                f"exceeded equity growth of "
                f"{equity_change:.1f}%.",

            "financial_impact":
                "Financial leverage may be increasing.",

            "recommended_action":
                "Monitor leverage ratios and ensure "
                "future borrowing is supported by cash generation."
        }

    return {

        "level":
            "LOW",

        "evidence":
            f"Debt changed {debt_change:.1f}% "
            f"compared with equity change "
            f"of {equity_change:.1f}%.",

        "financial_impact":
            "No significant debt-versus-equity "
            "growth imbalance was identified.",

        "recommended_action":
            "Continue monitoring leverage and "
            "debt-servicing capacity."
    }


# ============================================================
# PROFITABILITY RISK
# ============================================================

def assess_profitability(data):

    revenue_change = change(
        data,
        "revenue"
    )

    profit_change = change(
        data,
        "net_profit"
    )

    if (
        revenue_change is None
        or profit_change is None
    ):

        return unavailable()

    gap = (
        revenue_change
        -
        profit_change
    )

    if profit_change < 0 and revenue_change > 0:

        return {

            "level":
                "HIGH",

            "evidence":
                f"Revenue changed "
                f"{revenue_change:.1f}% while net profit "
                f"changed {profit_change:.1f}%.",

            "financial_impact":
                "Revenue growth is not translating into "
                "profit growth, indicating potential "
                "margin pressure.",

            "recommended_action":
                "Review pricing, operating costs, product "
                "mix and gross-margin performance."
        }

    if gap > 15:

        return {

            "level":
                "MEDIUM",

            "evidence":
                f"Revenue grew "
                f"{revenue_change:.1f}% while profit grew "
                f"{profit_change:.1f}%.",

            "financial_impact":
                "Profit growth is lagging revenue growth, "
                "which may indicate margin compression.",

            "recommended_action":
                "Investigate cost growth and operating "
                "margin trends."
        }

    return {

        "level":
            "LOW",

        "evidence":
            f"Revenue changed "
            f"{revenue_change:.1f}% and net profit changed "
            f"{profit_change:.1f}%.",

        "financial_impact":
            "No major adverse revenue-to-profit growth "
            "relationship was identified.",

        "recommended_action":
            "Continue monitoring profitability and margins."
    }


# ============================================================
# CASH-FLOW RISK
# ============================================================

def assess_cash_flow(data):

    ocf_change = change(
        data,
        "operating_cash_flow"
    )

    revenue_change = change(
        data,
        "revenue"
    )

    if ocf_change is None:

        return unavailable()

    if ocf_change < -20:

        return {

            "level":
                "HIGH",

            "evidence":
                f"Operating cash flow declined "
                f"{abs(ocf_change):.1f}%.",

            "financial_impact":
                "Weakening operating cash generation can "
                "reduce internally generated liquidity.",

            "recommended_action":
                "Investigate working-capital movements, "
                "cash collections and operating cash conversion."
        }

    if ocf_change < -10:

        return {

            "level":
                "MEDIUM",

            "evidence":
                f"Operating cash flow declined "
                f"{abs(ocf_change):.1f}%.",

            "financial_impact":
                "The decline may indicate emerging "
                "cash-conversion pressure.",

            "recommended_action":
                "Monitor operating cash flow and "
                "working-capital movements."
        }

    return {

        "level":
            "LOW",

        "evidence":
            f"Operating cash flow changed "
            f"{ocf_change:+.1f}% compared with the previous year.",

        "financial_impact":
            "No major adverse operating-cash-flow "
            "movement was identified.",

        "recommended_action":
            "Continue monitoring operating cash generation."
    }


# ============================================================
# EARNINGS QUALITY RISK
# ============================================================

def assess_earnings_quality(data):

    profit_change = change(
        data,
        "net_profit"
    )

    ocf_change = change(
        data,
        "operating_cash_flow"
    )

    receivable_change = change(
        data,
        "trade_receivables"
    )

    revenue_change = change(
        data,
        "revenue"
    )

    if (
        profit_change is None
        or ocf_change is None
    ):

        return unavailable()

    if (
        profit_change > 10
        and ocf_change < -10
    ):

        evidence = (
            f"Net profit increased "
            f"{profit_change:.1f}% while operating "
            f"cash flow declined "
            f"{abs(ocf_change):.1f}%."
        )

        if (
            receivable_change is not None
            and revenue_change is not None
            and receivable_change
            > revenue_change + 10
        ):

            evidence += (
                f" Trade receivables also increased "
                f"{receivable_change:.1f}%, materially "
                f"faster than revenue."
            )

        return {

            "level":
                "HIGH",

            "evidence":
                evidence,

            "financial_impact":
                "The divergence between accounting profit "
                "and operating cash generation may indicate "
                "working-capital pressure or weaker "
                "cash conversion.",

            "recommended_action":
                "Reconcile profit with operating cash flow "
                "and investigate receivables, inventory "
                "and other working-capital movements."
        }

    if (
        profit_change > 10
        and ocf_change < 0
    ):

        return {

            "level":
                "MEDIUM",

            "evidence":
                f"Net profit increased "
                f"{profit_change:.1f}% while operating "
                f"cash flow declined "
                f"{abs(ocf_change):.1f}%.",

            "financial_impact":
                "Profit growth is not fully supported "
                "by operating cash generation.",

            "recommended_action":
                "Monitor cash conversion and "
                "working-capital movements."
        }

    return {

        "level":
            "LOW",

        "evidence":
            "No significant divergence between "
            "profit growth and operating cash-flow "
            "movement was identified.",

        "financial_impact":
            "No major earnings-quality warning is "
            "indicated by the available data.",

        "recommended_action":
            "Continue monitoring profit-to-cash conversion."
    }


# ============================================================
# MANAGEMENT SUMMARY
# ============================================================

def build_management_summary(
    risks
):

    high_risks = []

    medium_risks = []

    for name, result in risks.items():

        if result["level"] == "HIGH":

            high_risks.append(name)

        elif result["level"] == "MEDIUM":

            medium_risks.append(name)


    if high_risks:

        return (
            "Management attention is required in "
            + ", ".join(high_risks)
            + ". The identified signals indicate "
              "areas where financial performance, "
              "cash conversion or balance-sheet "
              "strength may require corrective action."
        )

    if medium_risks:

        return (
            "The financial information indicates "
            "moderate areas of management attention "
            "in "
            + ", ".join(medium_risks)
            + ". These areas should be monitored "
              "closely before they develop into "
              "material financial pressure."
        )

    return (
        "No major financial risk signal was identified "
        "from the available information. Management "
        "should continue monitoring liquidity, "
        "working capital, leverage, profitability "
        "and cash generation."
    )


# ============================================================
# OVERALL RISK
# ============================================================

def calculate_overall_risk(
    risks
):

    weights = {

        "HIGH":
            3,

        "MEDIUM":
            2,

        "LOW":
            1
    }

    scores = []

    for result in risks.values():

        level = result["level"]

        if level in weights:

            scores.append(
                weights[level]
            )

    if not scores:

        return {

            "level":
                "NOT AVAILABLE",

            "score":
                None
        }

    score = (
        sum(scores)
        /
        len(scores)
    )

    if score >= 2.5:

        level = "HIGH"

    elif score >= 1.7:

        level = "MEDIUM"

    else:

        level = "LOW"

    return {

        "level":
            level,

        "score":
            score
    }


# ============================================================
# MAIN RISK ENGINE
# ============================================================

def generate_financial_intelligence(
    financial_data
):
    assessments = {
        "Liquidity Risk":
            assess_liquidity(
                financial_data
            ),
        "Collection Risk":
            assess_collection(
                financial_data
            ),
        "Inventory Risk":
            assess_inventory(
                financial_data
            ),
        "Leverage Risk":
            assess_leverage(
                financial_data
            ),
        "Profitability Risk":
            assess_profitability(
                financial_data
            ),
        "Cash-Flow Risk":
            assess_cash_flow(
                financial_data
            ),
        "Earnings Quality Risk":
            assess_earnings_quality(
                financial_data
            )
    }
    # --------------------------------------------------------
    # ALL ASSESSMENTS ARE DISPLAYED
    #
    # HIGH    = genuine high-risk signal
    # MEDIUM  = genuine moderate-risk signal
    # LOW     = assessed and no significant exception found
    # NOT AVAILABLE = insufficient financial information
    # --------------------------------------------------------
    overall = calculate_overall_risk(
        assessments
    )
    high_risks = []
    medium_risks = []
    low_risks = []
    unavailable_risks = []
    for name, result in assessments.items():
        if not isinstance(result, dict):
            continue
        level = result.get(
            "level",
            "NOT AVAILABLE"
        )
        if level == "HIGH":
            high_risks.append(name)
        elif level == "MEDIUM":
            medium_risks.append(name)
        elif level == "LOW":
            low_risks.append(name)
        else:
            unavailable_risks.append(name)
    # --------------------------------------------------------
    # MANAGEMENT SUMMARY
    # --------------------------------------------------------
    if high_risks:
        management_summary = (
            "High-risk financial signals were identified in: "
            + ", ".join(high_risks)
            + ". These areas require priority investigation."
        )
    elif medium_risks:
        management_summary = (
            "Moderate financial signals were identified in: "
            + ", ".join(medium_risks)
            + ". These areas should be reviewed."
        )
    elif low_risks and not unavailable_risks:
        management_summary = (
            "No significant financial risk was identified "
            "from the available financial statements."
        )
    elif unavailable_risks and not high_risks and not medium_risks:
        management_summary = (
            "The available financial statements contain "
            "insufficient information to produce a reliable "
            "complete risk assessment."
        )
    else:
        management_summary = (
            "The financial statements contain a mixture of "
            "assessed areas and areas where additional data "
            "is required."
        )
    return {
        # Complete assessment set.
        # Nothing is hidden.
        "assessments":
            assessments,
        # Risk & Investigation receives every assessment.
        "risks":
            assessments,
        "overall_risk":
            overall,
        "management_summary":
            management_summary,
        "risk_counts": {
            "HIGH":
                len(high_risks),
            "MEDIUM":
                len(medium_risks),
            "LOW":
                len(low_risks),
            "NOT AVAILABLE":
                len(unavailable_risks)
        }
    }
