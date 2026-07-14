import pytest
from pydantic_ai import models
from pydantic_ai.models.test import TestModel

from explanation_agent import Explanation, agent, explain


# Fail the test suite rather than accidentally calling a paid model.
models.ALLOW_MODEL_REQUESTS = False


def test_explain_returns_structured_explanation_without_live_api():
    john_report = {
        "signals": {
            "income_stability": {"score": 100},
            "recurring_expense_ratio": {"score": 10},
            "overdraft_count": {"score": 45},
            "net_cash_flow_ratio": {"score": 30},
        },
    }

    canned_output = {
        "summary": "Income stability is a strength, while the remaining signals are concerns.",
        "key_strengths": ["Income stability"],
        "key_concerns": [
            "Recurring expense ratio",
            "Overdraft count",
            "Net cash flow ratio",
        ],
        "principal_risk_factors": [
            "Recurring expense ratio",
            "Overdraft count",
            "Net cash flow ratio",
        ],
    }

    # Replaces the LLM with deterministic local Python behavior and supplies data matching Explanation schema.
    test_model = TestModel(custom_output_args=canned_output)

    with agent.override(model=test_model):
        result = explain(john_report)

    assert isinstance(result, Explanation)
    assert result.model_dump() == canned_output


def test_explain_rejects_missing_signal_score():  # fail-fast test
    broken_report = {
        "signals": {
            "income_stability": {"score": None},
        },
    }

    with pytest.raises(ValueError, match="missing a score"):
        explain(broken_report)
