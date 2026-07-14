"""Generate structured explanations from qualitative signal assessments.

The agent receives qualitative labels derived from the authoritative
deterministic report. Its output schema contains no score or risk-tier fields
and cannot replace the deterministic result.
"""
from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent


class Explanation(BaseModel):
    summary: str
    key_strengths: list[str]
    key_concerns: list[str]
    principal_risk_factors: list[str]


EXPLANATION_INSTRUCTIONS = """
Explain an assessment already produced by deterministic scoring code.
Use only the supplied signal names and qualitative assessments.

Describe strong signals as strengths and weak signals as concerns.
List the weak signals as principal risk factors using neutral language.

Do not mention an overall score or risk tier.
Do not state or imply causes, future outcomes, account balances,
financial reserves, or circumstances not explicitly supplied.
Do not add numerical values or invent facts.
"""


agent = Agent(
    # For a short explanation task, use the lower-cost Haiku model.
    "anthropic:claude-haiku-4-5-20251001",
    output_type=Explanation,
    instructions=EXPLANATION_INSTRUCTIONS,
    defer_model_check=True,
)


def explain(report: dict[str, Any]) -> Explanation:
    signals = report["signals"]

    signal_lines = []
    for name, payload in signals.items():
        score = payload["score"]
        if score is None:
            raise ValueError("Signal is missing a score.")

        readable_name = name.replace("_", " ")

        if score >= 80:
            qualitative_label = "strong"
        elif score >= 55:
            qualitative_label = "moderate"
        else:
            qualitative_label = "weak"

        signal_lines.append(
            f"- {readable_name}: {qualitative_label}"
        )

    user_prompt = (
        "Produce an explanation from these qualitative signal assessments:\n"
        + "\n".join(signal_lines)
    )

    result = agent.run_sync(user_prompt)
    return result.output
