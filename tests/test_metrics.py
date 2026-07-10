from metrics import (
    _income_by_month,
    _score_from_bands,
    income_stability,
    overdraft_count,
    net_cash_flow_ratio,
    score_account,
    WEIGHTS,
)
from models import Transaction, Category, Direction
from decimal import Decimal
from datetime import date
import pytest

BANDS = [
    (float("-inf"), 0.10, 100),
    (0.10, 0.25, 75),
    (0.25, 0.50, 45),
    (0.50, float("inf"), 15),
]


def test_bands_pick_the_right_score():
    assert _score_from_bands(0.05, BANDS) == 100
    # low-inclusive edge lands in the upper band
    assert _score_from_bands(0.10, BANDS) == 75
    assert _score_from_bands(0.40, BANDS) == 45
    assert _score_from_bands(2.00, BANDS) == 15


def test_bands_raise_when_value_uncovered():
    with pytest.raises(ValueError):
        _score_from_bands(0.5, [(0.0, 0.1, 100)])   # 0.5 falls in no band


def test_income_by_month_groups_and_filters():
    txns = [
        Transaction(date=date(2026, 4, 1),  amount=Decimal(
            "2900"), category=Category.income),
        Transaction(date=date(2026, 4, 15), amount=Decimal(
            "2900"), category=Category.income),
        Transaction(date=date(2026, 5, 1),  amount=Decimal(
            "2900"), category=Category.income),
        Transaction(date=date(2026, 4, 20), amount=Decimal("2000"),
                    category=Category.recurring_expense),  # excluded
    ]
    assert _income_by_month(txns) == {(2026, 4): Decimal(
        "5800"), (2026, 5): Decimal("2900")}


def test_income_stability_steady_income_scores_high():
    txns = [
        Transaction(date=date(2026, 4, 1), amount=Decimal(
            "2900"), category=Category.income),
        Transaction(date=date(2026, 5, 1), amount=Decimal(
            "2900"), category=Category.income),
        Transaction(date=date(2026, 6, 1), amount=Decimal(
            "2900"), category=Category.income),
    ]
    cov, score = income_stability(txns)
    assert cov == 0.0        # identical months -> zero bounce
    assert score == 100      # zero bounce -> top band


def test_overdraft_count_returns_count_and_score():
    txns = [
        Transaction(date=date(2026, 4, 1), amount=Decimal(
            "50"), category=Category.fee),
        Transaction(date=date(2026, 5, 1), amount=Decimal(
            "50"), category=Category.fee),
        Transaction(date=date(2026, 6, 1), amount=Decimal(
            "50"), category=Category.fee),
        Transaction(date=date(2026, 6, 2), amount=Decimal(
            "50"), category=Category.fee),
        Transaction(date=date(2026, 6, 15), amount=Decimal(
            "5000"), category=Category.income)  # excluded
    ]

    count, score = overdraft_count(txns)

    assert count == 4
    assert score == 10


def test_net_cash_flow_boundary_is_low_inclusive():
    txns = [
        Transaction(
            date=date(2026, 4, 1),
            amount=Decimal("1000"),
            category=Category.income,
            direction=Direction.deposit,
        ),
        Transaction(
            date=date(2026, 4, 15),
            amount=Decimal("700"),
            category=Category.recurring_expense,
            direction=Direction.withdrawal,
        ),
        Transaction(
            date=date(2026, 4, 20),
            amount=Decimal("200"),
            category=Category.other,
            direction=Direction.withdrawal,
        ),
    ]

    ratio, score = net_cash_flow_ratio(txns)

    assert ratio == pytest.approx(0.10)
    assert score == 80


def test_net_cash_flow_interior():
    txns = [
        Transaction(
            date=date(2026, 4, 1),
            amount=Decimal("1000"),
            category=Category.income,
            direction=Direction.deposit,
        ),
        Transaction(
            date=date(2026, 4, 15),
            amount=Decimal("700"),
            category=Category.recurring_expense,
            direction=Direction.withdrawal,
        ),
    ]

    ratio, score = net_cash_flow_ratio(txns)

    assert ratio == pytest.approx(0.30)
    assert score == 80


def test_score_account_returns_weighted_breakdown():
    txns = [
        Transaction(
            date=date(2026, 4, 1),
            amount=Decimal("1000"),
            category=Category.income,
            direction=Direction.deposit,
        ),
        Transaction(
            date=date(2026, 5, 1),
            amount=Decimal("1000"),
            category=Category.income,
            direction=Direction.deposit,
        ),
        Transaction(
            date=date(2026, 4, 15),
            amount=Decimal("1000"),
            category=Category.recurring_expense,
            direction=Direction.withdrawal,
        ),
    ]

    result = score_account(txns)

    assert sum(WEIGHTS.values()) == pytest.approx(1.0)
    assert result["overall_score"] == 95
    assert result["risk_tier"] == "low"
    assert set(result["signals"].keys()) == {
        "income_stability",
        "recurring_expense_ratio",
        "overdraft_count",
        "net_cash_flow_ratio",
    }
    assert result["signals"]["income_stability"]["score"] == 100
    assert result["signals"]["recurring_expense_ratio"]["score"] == 80
    assert result["signals"]["overdraft_count"]["score"] == 100
    assert result["signals"]["net_cash_flow_ratio"]["score"] == 100

    expected_score = int(round(
        (100 * WEIGHTS["income_stability"])
        + (80 * WEIGHTS["recurring_expense_ratio"])
        + (100 * WEIGHTS["overdraft_count"])
        + (100 * WEIGHTS["net_cash_flow_ratio"])
    ))
    assert result["overall_score"] == expected_score


def test_score_account_tier_boundary_at_eighty():
    txns = [
        Transaction(
            date=date(2026, 4, 1),
            amount=Decimal("1000"),
            category=Category.income,
            direction=Direction.deposit,
        ),
        Transaction(
            date=date(2026, 5, 1),
            amount=Decimal("1000"),
            category=Category.income,
            direction=Direction.deposit,
        ),
        Transaction(
            date=date(2026, 4, 15),
            amount=Decimal("1000"),
            category=Category.recurring_expense,
            direction=Direction.withdrawal,
        ),
        Transaction(
            date=date(2026, 4, 20),
            amount=Decimal("400"),
            category=Category.other,
            direction=Direction.withdrawal,
        ),
        Transaction(
            date=date(2026, 4, 25),
            amount=Decimal("50"),
            category=Category.fee,
            direction=Direction.withdrawal,
        ),
    ]

    result = score_account(txns)

    assert result["overall_score"] == 80
    assert result["risk_tier"] == "low"


def test_score_account_propagates_metric_errors():
    txns = [
        Transaction(
            date=date(2026, 4, 1),
            amount=Decimal("1000"),
            category=Category.recurring_expense,
            direction=Direction.withdrawal,
        )
    ]

    with pytest.raises(ValueError, match="Need at least 2 months of income"):
        score_account(txns)
