# Validation record

## Automated checks
The repository contains 17 unit tests covering NOI, lender constraints, loan rounding, debt-service scaling, zero-rate debt service, amortization roll-forward, payment identity, maturity reconciliation, lender IRR, input validation and directional stresses for vacancy, note rate, credit spread, exit cap rate and refinance rate.

GitHub Actions runs the test suite and regenerates the base-case console output on Python 3.11 and 3.12 for pushes and pull requests. A green workflow badge is evidence that the remote checks completed for the current commit; the existence of a workflow file alone is not.

## Base-case reconciliation
| Output | Excel | Python |
|---|---:|---:|
| Year 1 NOI | CAD 3,288,000 | CAD 3,288,000 |
| Recommended loan | CAD 33,500,000 | CAD 33,500,000 |
| Binding constraint | DSCR | DSCR |
| Maturity balance | CAD 30,017,889 | CAD 30,017,889 rounded |

The Excel audit sheet covers the original base underwriting and amortization checks. Refinance metrics and lender IRR are Python/dashboard additions and are not claimed as Excel-reconciled.

## Python-only maturity outputs
| Output | Base result |
|---|---:|
| Year 5 NOI | CAD 3,723,395 |
| Exit value at 6.00% | CAD 62,056,590 |
| Maturity LTV | 48.4% |
| Refinance DSCR at 6.75% | 1.50x |
| Lender annual IRR incl. 1% fee | 6.16% |

## Unverified items
- No live transaction, borrower or tenant data was used.
- No independent appraiser, lender or real-estate professional reviewed the assumptions.
- No Argus Enterprise model was created.
- No default, prepayment, recovery or probability-weighted return model is included.
- The Streamlit interface is locally runnable but is not a production underwriting system.
