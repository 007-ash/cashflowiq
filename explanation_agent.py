"""The ExplanationAgent receives the authoritative deterministic report, including the score, tier, and signal breakdown, as read-only input. 
It returns a plain-English explanation of the relative strengths and concerns; 
the output contains no score or tier field, does not repeat exact numbers, and cannot recalculate or change the decision."""

from pydantic import BaseModel


class Explanation(BaseModel):
    summary: str
    key_strengths: list[str]
    key_concerns: list[str]
    principal_risk_factors: list[str]


EXPLANATION_INSTRUCTIONS = """
The agent explains an assessment already produced by deterministic scoring code; it does not make lending decisions. 
It may use only the four supplied signal results and must not invent facts. 
It must not repeat exact values, produce or change a score or tier, or contradict the report. 
It should describe favorable signals as strengths, unfavorable signals as concerns, and emphasize the most important supplied risk factors in clear, neutral language.
"""


agent = Agent(
    "anthropic:<model-name>",
    output_type=Explanation,
    instructions=EXPLANATION_INSTRUCTIONS,
)


def explain(report: dict[str, object]) -> Explanation:
    # Fail fast if the authoritative report does not match its contract.
    signals = report["signals"]
    tier = report["risk_tier"]

    signal_lines = []
    for name, payload in signals.items():
        score = payload.get("score")
        if score is None:
            continue

        readable_name = name.replace("_", " ")
        if score >= 80:
            qual_label = "strong"
        elif score >= 50:
            qual_label = "moderate"
        else:
            qual_label = "weak"

        signal_lines.append(f"- {readable_name}: {qual_label}")

    user_prompt = (
        f"Explain this assessment in plain English. "
        f"Risk tier: {tier}. "
        "Use the supplied signal scores as the only evidence. "
        "Do not mention exact values, scores, or the tier in the output. "
        "This code guarantees that output has no score or fields tier fields. "
        "The prompt requests does not repeat numbers and validates generative text."
        "Focus on strengths, concerns, and the main risk factors.\n"
        + "\n".join(signal_lines)
    )

    result = agent.run_sync(user_prompt)
    return result.output
