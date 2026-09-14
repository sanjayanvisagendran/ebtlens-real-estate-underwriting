# DebtLens

[![tests](../../actions/workflows/tests.yml/badge.svg)](../../actions/workflows/tests.yml)

**Inspect the property cash flow. Size the loan. Stress the refinance. Explain the credit decision.**

DebtLens is a commercial real-estate debt underwriting portfolio lab built around a fictional Metro Vancouver industrial property. It combines an auditable Excel model, matching Python calculations, a Streamlit scenario interface, automated tests and a preliminary investment memorandum.

All property, borrower and comparable-sale details are synthetic. This project does not represent professional underwriting experience, an actual transaction or an affiliation with QuadReal Property Group.

## Base-case conclusion

The fictional borrower requests CAD 36.0 million. The model recommends CAD 33.5 million because the 1.30x minimum DSCR is the binding lender constraint. A separate maturity test estimates the balloon against Year 5 NOI, a 6.00% exit cap rate and a 6.75% refinance rate.

| Metric | Base result |
|---|---:|
| Year 1 NOI | CAD 3.288M |
| Underwritten value | CAD 56.922M |
| Recommended loan | CAD 33.500M |
| LTV | 58.9% |
| DSCR | 1.30x |
| Debt yield | 9.8% |
| Five-year maturity balance | CAD 30.018M |
| Exit value | CAD 62.057M |
| Maturity LTV | 48.4% |
| Refinance DSCR | 1.50x |
| Lender annual IRR incl. 1% fee | 6.16% |

![DebtLens Excel summary](docs/assets/excel-summary.png)

## Repository contents

- `model/DebtLens_Underwriting_Model.xlsx`: assumptions, operating forecast, comparable sales, loan sizing, amortization, sensitivities and audit checks.
- `app.py`: interactive review of vacancy, benchmark rate, credit spread, cap rates and refinance rate.
- `src/debtlens/model.py`: deterministic Python implementation of sizing, amortization, refinance and lender-return mechanics.
- `docs/INVESTMENT_MEMO.md`: preliminary recommendation, risks and approval conditions.
- `docs/METHODOLOGY.md`: calculation definitions and model logic.
- `docs/VALIDATION.md`: executed checks, reconciliations and unverified items.
- `docs/REVIEW_QUESTIONS.md`: interview questions for explaining the model.

## Run the Python checks

Requires Python 3.11+.

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
python scripts/validate_model.py
```

## Run the dashboard

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## What the model demonstrates

- Five-year property cash-flow forecasting.
- Income-capitalization and comparable-sales valuation.
- Loan sizing using requested amount, LTV, DSCR and debt-yield limits.
- Fixed-rate monthly amortization and balloon-balance calculation.
- Benchmark-rate and credit-spread decomposition.
- Exit-value, maturity-LTV and refinance-DSCR analysis.
- Lender cash-flow IRR including payments, an assumed fee and balloon repayment.
- Automated checks for calculation identities and directional stress behaviour.
- Explicit due-diligence gaps, credit conditions and audit checks.

## Scope of the Excel workbook

The workbook remains the visual base-underwriting artifact and reconciles Year 1 NOI, loan sizing and maturity balance with Python. The new refinancing and lender-IRR metrics are implemented in Python and the Streamlit dashboard; they are not presented as Excel-verified outputs.

## AI-assisted development

AI assistance was used to accelerate scaffolding, propose edge cases, review formula references and improve documentation. Sanjayan Visagendran is responsible for reviewing assumptions, running the checks, tracing calculations and explaining the credit recommendation. AI output is treated as draft material until independently checked.

## Important limitations

- No actual borrower, tenant, lease, market or transaction data is included.
- Comparable sales are fictional and do not support a real valuation.
- Refinance metrics assume the full modeled balloon is refinanced; lender IRR assumes contractual performance and repayment.
- The model omits taxes, reserves, tenant improvements, leasing commissions, legal structure, guarantees and construction-loan mechanics.
- No Argus Enterprise model or third-party appraisal is included.
- Passing tests establishes internal consistency for stated assumptions, not investment suitability.

## Suggested next step

Ask a real-estate debt professional to identify one missing diligence item or model assumption. Record the feedback, make the change yourself and explain why the credit conclusion did or did not change.

## License

MIT. See `LICENSE`.
