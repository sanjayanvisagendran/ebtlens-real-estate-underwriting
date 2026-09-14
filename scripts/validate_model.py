"""Print reproducible base-case results and cross-check loan mechanics."""

import json
from pathlib import Path

from debtlens.model import amortization_schedule, load_case, loan_sizing


root = Path(__file__).parents[1]
case = load_case(root / "data" / "case_study.json")
result = loan_sizing(case)
schedule = amortization_schedule(
    result["recommended_loan"],
    case["loan"]["interest_rate"],
    case["loan"]["amortization_years"],
    case["loan"]["term_years"],
)
payload = {
    **result,
    "balance_at_maturity": schedule[-1]["ending_balance"],
    "schedule_months": len(schedule),
}
print(json.dumps(payload, indent=2))

