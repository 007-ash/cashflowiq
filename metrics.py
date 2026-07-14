import statistics
from collections.abc import Sequence
from decimal import Decimal

from models import Category, Direction, Transaction


MonthKey = tuple[int, int]
Band = tuple[float, float, int]


def _score_from_bands(
    value: int | float,
    bands: Sequence[Band],
) -> int:
    for band in bands:
        low, high, score = band
        if low <= value < high:
            return score

    raise ValueError(f"No scoring band matched value {value}")

# monthly total


def _income_by_month(
    transactions: Sequence[Transaction],
) -> dict[MonthKey, Decimal]:
    totals: dict[MonthKey, Decimal] = {}

    for transaction in transactions:
        if transaction.category != Category.income:
            continue

        month_key = (
            transaction.date.year,
            transaction.date.month,
        )

        current_total = totals.get(month_key, Decimal("0"))
        totals[month_key] = current_total + transaction.amount

    return totals

# contain raw CoV
# normalized score
# data-sufficient flag

# -inf / inf at the ends guarantee every CoV lands in exactly one band


INCOME_BANDS: list[Band] = [
    (float("-inf"), 0.10, 100),   # steady          -> Excellent
    (0.10, 0.20, 80),             # slight bounce    -> Good
    (0.20, 0.35, 55),             # moderate bounce  -> Fair
    (0.35, 0.55, 30),             # jumpy            -> Weak
    (0.55, float("inf"), 10),     # very jumpy       -> Poor
]


def income_stability(transactions: Sequence[Transaction]) -> tuple[float, int]:
    monthly_totals = list(_income_by_month(
        transactions).values())   # get monthly incomes

    # need 2+ months to see bounce
    if len(monthly_totals) < 2:
        raise ValueError("Need at least 2 months of income")

    # money -> plain numbers
    values = [float(total) for total in monthly_totals]

    # the average
    average = statistics.mean(values)
    # cannot divide by zero
    if average == 0:
        raise ValueError("Income average is zero")

    # how much it bounces
    spread = statistics.pstdev(values)
    # coefficient of variation.
    cov = spread / average

    # look up the grade
    score = _score_from_bands(cov, INCOME_BANDS)
    # hand back both
    return (cov, score)


EXPENSE_BANDS: list[Band] = [
    (float("-inf"), 0.40, 100),   # <40% of income committed -> Excellent
    (0.40, 0.60, 80),             # 40-60%                   -> Good
    (0.60, 0.75, 55),             # 60-75%                   -> Fair
    (0.75, 0.90, 30),             # 75-90%                   -> Weak
    (0.90, float("inf"), 10),     # >90%                     -> Poor
]


def recurring_expense_ratio(transactions: Sequence[Transaction]) -> tuple[float, int]:
    total_expenses = sum(
        (t.amount for t in transactions if t.category == Category.recurring_expense),
        Decimal("0"),
    )
    total_income = sum(
        (t.amount for t in transactions if t.category == Category.income),
        Decimal("0"),
    )

    if total_income == 0:                                  # can't divide by zero income
        raise ValueError("No income to compare expenses against")

    ratio = float(total_expenses / total_income)    # the metric
    score = _score_from_bands(ratio, EXPENSE_BANDS)        # grade it
    return (ratio, score)


OVERDRAFT_COUNT_BANDS: list[Band] = [
    (float("-inf"), 1.0, 100),   # 0 fees - excellent
    (1.0, 2.0, 70),              # 1 fee - clear warning
    (2.0, 3.0, 45),              # 2 fees - material concern
    (3.0, 4.0, 25),              # 3 fees - severe concern
    (4.0, float("inf"), 10),     # 4+ fees - persistent distress
]


# returns a count
def overdraft_count(transactions: Sequence[Transaction]) -> tuple[int, int]:
    # In the current seed data, Category.fee represents overdraft or NSF fees.
    fee_count = sum(
        1 for transaction in transactions if transaction.category == Category.fee)
    score = _score_from_bands(fee_count, OVERDRAFT_COUNT_BANDS)
    return (fee_count, score)


NET_CASH_FLOW_BANDS: list[Band] = [
    (float("-inf"), -0.30, 10),   # rapid deterioration -> Poor
    (-0.30, -0.10, 30),           # declining
    (-0.10, 0.10, 55),            # stable
    (0.10, 0.40, 80),             # improving
    (0.40, float("inf"), 100),    # strongly improving -> Excellent
]


def net_cash_flow_ratio(transactions: Sequence[Transaction]) -> tuple[float, int]:
    total_income = sum((t.amount for t in transactions if t.category ==
                       Category.income),            Decimal("0"))
    total_recurring_expenses = sum((t.amount for t in transactions if t.category ==
                                    Category.recurring_expense), Decimal("0"))
    # In the current seed data, Category.fee represents overdraft/NSF events only.
    total_fees = sum((t.amount for t in transactions if t.category ==
                     Category.fee),               Decimal("0"))
    total_other_spending = sum((t.amount for t in transactions if t.category ==
                                Category.other and t.direction == Direction.withdrawal),
                               Decimal("0"))

    if total_income == 0:
        raise ValueError("No income to measure cash-flow ratio against")

    net = (
        total_income
        - total_recurring_expenses
        - total_fees
        - total_other_spending
    )

    ratio = float(net / total_income)
    score = _score_from_bands(ratio, NET_CASH_FLOW_BANDS)
    return (ratio, score)


WEIGHTS = {
    "income_stability": 0.15,
    "recurring_expense_ratio": 0.25,
    "overdraft_count": 0.30,
    "net_cash_flow_ratio": 0.30,
}


def score_account(transactions: Sequence[Transaction]) -> dict[str, object]:
    """Round once, after weighting, for presentation and tier assignment.

    The metrics module intentionally keeps a fail-fast policy here. The report
    endpoint can translate any ValueError into an HTTP response without this
    helper needing to know about HTTP semantics.
    """
    income_raw, income_score = income_stability(transactions)
    recurring_expense_raw, recurring_expense_score = recurring_expense_ratio(
        transactions)
    overdraft_raw, overdraft_score = overdraft_count(transactions)
    net_cash_flow_raw, net_cash_flow_score = net_cash_flow_ratio(transactions)

    weighted_total = (
        (income_score * WEIGHTS["income_stability"])
        + (recurring_expense_score * WEIGHTS["recurring_expense_ratio"])
        + (overdraft_score * WEIGHTS["overdraft_count"])
        + (net_cash_flow_score * WEIGHTS["net_cash_flow_ratio"])
    )
    # compute the weighted score, round once to an integer for presentation and tiering
    overall_score = int(round(weighted_total))

    if overall_score >= 80:
        risk_tier = "low"
    elif overall_score >= 60:
        risk_tier = "moderate"
    elif overall_score >= 40:
        risk_tier = "elevated"
    else:
        risk_tier = "high"

    return {
        "overall_score": overall_score,
        "risk_tier": risk_tier,
        "signals": {
            "income_stability": {
                "raw": income_raw,
                "score": income_score,
            },
            "recurring_expense_ratio": {
                "raw": recurring_expense_raw,
                "score": recurring_expense_score,
            },
            "overdraft_count": {
                "raw": overdraft_raw,
                "score": overdraft_score,
            },
            "net_cash_flow_ratio": {
                "raw": net_cash_flow_raw,
                "score": net_cash_flow_score,
            },
        },
    }
