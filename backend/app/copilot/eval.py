"""Small eval set for the copilot (`python -m app.copilot.eval` from backend/).

Runs `app.copilot.engine.answer()` against ~25 natural-language questions
spanning every intent, whether or not an AI key is configured (if one is
present, this exercises the real online path; if not, it exercises the
offline router -- either way every question must produce a valid
AnswerContract). Prints a pass/fail table and a summary line.

Pass criteria per question:
  1. The result validates as an AnswerContract (guaranteed by type, but we
     re-validate via round-tripping through JSON to catch any accidental
     malformed nested data).
  2. `narrative` is non-empty.
  3. If the question implies a recommendation is expected, at least one
     Recommendation is present with a non-null `impact`.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass

from app.copilot.engine import answer
from app.schemas import AnswerContract

USER_ID = "demo-priya"


@dataclass
class Case:
    question: str
    expects_recommendation: bool = False


CASES: list[Case] = [
    # spending summary
    Case("How am I doing financially?"),
    Case("What's my spending like this month?"),
    Case("Summarize my expenses."),
    Case("Where is my money going?"),
    # savings
    Case("What's my savings rate?", expects_recommendation=True),
    Case("Am I saving enough?", expects_recommendation=True),
    Case("Do I have a healthy nest egg?", expects_recommendation=True),
    # debt
    Case("How much debt do I have?"),
    Case("Tell me about my credit card balance.", expects_recommendation=True),
    Case("What's my EMI situation?"),
    Case("Should I worry about my loan?", expects_recommendation=True),
    # cash flow / upcoming risk
    Case("What's my cash flow looking like?"),
    Case("Will I run out of money this month?"),
    Case("Am I at risk of an overdraft?"),
    Case("Is there a gap coming up in my cash flow?"),
    # affordability
    Case("Can I afford a ₹60,000 phone next month?", expects_recommendation=True),
    Case("Should I buy a ₹15,000 jacket?", expects_recommendation=True),
    Case("Can I afford a vacation?"),  # no amount -> data gap, not a crash
    # recommendations
    Case("What should I do to improve my finances?", expects_recommendation=True),
    Case("How can I improve my health score?", expects_recommendation=True),
    Case("Any recommendations for me?", expects_recommendation=True),
    Case("Give me some tips."),
    # edge cases / ambiguous / fallback
    Case("Why is my score low?"),
    Case("What happens if I pay off my credit card faster?", expects_recommendation=True),
    Case("Am I spending more than people like me?"),
    Case("asdkjashdkj random gibberish 12345"),
]


def _has_recommendation_with_impact(result: AnswerContract) -> bool:
    return any(r.impact is not None for r in result.recommendations)


def run() -> tuple[list[dict], int, int]:
    rows: list[dict] = []
    passed = 0
    for case in CASES:
        row = {"question": case.question, "status": "FAIL", "reason": ""}
        try:
            result = answer(USER_ID, case.question)
            # Round-trip to catch any accidental malformed nested data.
            AnswerContract.model_validate_json(result.model_dump_json())

            reasons = []
            if not result.narrative.strip():
                reasons.append("empty narrative")
            if case.expects_recommendation and not _has_recommendation_with_impact(result):
                reasons.append("expected a recommendation with impact, got none")

            if reasons:
                row["reason"] = "; ".join(reasons)
            else:
                row["status"] = "PASS"
                passed += 1
        except Exception as exc:  # eval itself must never crash the loop
            row["reason"] = f"raised: {exc!r}"
        rows.append(row)
    return rows, passed, len(CASES)


def main() -> int:
    # Windows terminals often default to a legacy codepage (cp1252) that
    # can't encode the rupee sign used throughout our questions/answers;
    # force UTF-8 stdout so `python -m app.copilot.eval` doesn't crash on
    # printing, without affecting the actual pass/fail logic above.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    rows, passed, total = run()
    width = max(len(r["question"]) for r in rows) + 2
    print(f"{'STATUS':<6} {'QUESTION':<{width}} REASON")
    print("-" * (6 + width + 30))
    for r in rows:
        print(f"{r['status']:<6} {r['question']:<{width}} {r['reason']}")
    print("-" * (6 + width + 30))
    pct = 100.0 * passed / total if total else 0.0
    print(f"Passed {passed}/{total} ({pct:.1f}%)")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
