"""Print reproducible base-case results for review or report regeneration."""

import json
from pathlib import Path

from debtlens.model import load_case, loan_sizing


root = Path(__file__).parents[1]
case = load_case(root / "data" / "case_study.json")
result = loan_sizing(case)
print(json.dumps(result, indent=2))
