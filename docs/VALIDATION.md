# Validation record

## Executed checks

- Python unit tests cover NOI, lender constraints, loan rounding, debt-service scaling, amortization roll-forward and directional stress behaviour.
- The Excel Audit sheet verifies that the recommended loan does not exceed any stated capacity.
- The Excel Audit sheet reconciles principal reduction to the maturity balance and verifies the payment identity.
- Base Python outputs are compared manually with the Excel Summary and Debt Schedule outputs.
- Every workbook sheet was rendered and visually inspected for clipping and formula errors.

## Base-case agreement

| Output | Excel | Python |
|---|---:|---:|
| Year 1 NOI | CAD 3,288,000 | CAD 3,288,000 |
| Recommended loan | CAD 33,500,000 | CAD 33,500,000 |
| Binding constraint | DSCR | DSCR |
| Maturity balance | CAD 30,017,889 | CAD 30,017,889 rounded |

## Unverified items

- No live transaction, borrower or tenant data was used.
- No independent appraiser, lender or real-estate professional reviewed the assumptions.
- No Argus Enterprise model was created.
- The Streamlit interface is locally runnable but is not a production underwriting system.

