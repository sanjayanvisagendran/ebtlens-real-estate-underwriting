from pathlib import Path

import pandas as pd
import streamlit as st

from debtlens.model import amortization_schedule, load_case, operating_forecast, scenario


ROOT = Path(__file__).parent
case = load_case(ROOT / "data" / "case_study.json")

st.set_page_config(page_title="DebtLens", page_icon="🏢", layout="wide")
st.title("DebtLens")
st.caption("Commercial real-estate debt underwriting lab using a fictional Metro Vancouver industrial property.")

with st.sidebar:
    st.header("Underwriting assumptions")
    vacancy = st.slider("Year 1 vacancy", 0.0, 0.20, float(case["property"]["vacancy_rate"]), 0.005)
    benchmark_rate = st.slider("Benchmark rate", 0.01, 0.07, float(case["loan"]["benchmark_rate"]), 0.0025)
    credit_spread = st.slider("Credit spread", 0.005, 0.05, float(case["loan"]["credit_spread"]), 0.0025)
    cap_rate = st.slider("Underwriting cap rate", 0.04, 0.08, float(case["valuation"]["underwriting_cap_rate"]), 0.0025)
    exit_cap_rate = st.slider("Exit cap rate", 0.04, 0.09, float(case["valuation"]["exit_cap_rate"]), 0.0025)
    refinance_rate = st.slider("Refinance rate", 0.03, 0.10, float(case["loan"]["refinance_interest_rate"]), 0.0025)
    note_rate = benchmark_rate + credit_spread
    st.metric("Calculated note rate", f"{note_rate:.2%}")
    st.info("All data and transaction details are synthetic. Change the assumptions to inspect the credit effect.")

result = scenario(
    case,
    vacancy_rate=vacancy,
    benchmark_rate=benchmark_rate,
    credit_spread=credit_spread,
    cap_rate=cap_rate,
    exit_cap_rate=exit_cap_rate,
    refinance_interest_rate=refinance_rate,
)

first_row = st.columns(4)
first_row[0].metric("Recommended loan", f"CAD {result['recommended_loan']/1_000_000:.1f}M")
first_row[1].metric("Underwritten value", f"CAD {result['underwritten_value']/1_000_000:.1f}M")
first_row[2].metric("LTV", f"{result['ltv']:.1%}")
first_row[3].metric("DSCR", f"{result['dscr']:.2f}x")

second_row = st.columns(4)
second_row[0].metric("Debt yield", f"{result['debt_yield']:.1%}")
second_row[1].metric("Maturity LTV", f"{result['maturity_ltv']:.1%}")
second_row[2].metric("Refinance DSCR", f"{result['refinance_dscr']:.2f}x")
second_row[3].metric("Lender annual IRR", f"{result['lender_annual_irr']:.2%}")

if result["recommendation"] == "Proceed with conditions":
    st.success(
        f"Proceed with conditions. Binding sizing constraint: "
        f"{result['binding_constraint'].replace('_', ' ').title()}."
    )
else:
    st.error("The selected assumptions breach at least one base or refinance credit limit.")

left, right = st.columns(2)
with left:
    st.subheader("Loan sizing capacities")
    capacities = pd.DataFrame(
        {
            "Capacity": ["Requested", "LTV", "DSCR", "Debt yield"],
            "Amount": [
                result["requested_amount"],
                result["ltv_capacity"],
                result["dscr_capacity"],
                result["debt_yield_capacity"],
            ],
        }
    ).set_index("Capacity")
    st.bar_chart(capacities)
with right:
    st.subheader("Five-year net operating income")
    forecast = pd.DataFrame(operating_forecast(case)).set_index("year")
    st.line_chart(forecast[["noi"]])

st.subheader("Selected-case credit review")
st.dataframe(
    pd.DataFrame(
        [
            ("Year 1 NOI", result["year_one_noi"], "CAD"),
            ("Year 5 NOI", result["maturity_noi"], "CAD"),
            ("Income value", result["income_value"], "CAD"),
            ("Comparable value", result["comparable_value"], "CAD"),
            ("Annual debt service", result["annual_debt_service"], "CAD"),
            ("Maturity balance", result["maturity_balance"], "CAD"),
            ("Exit value", result["exit_value"], "CAD"),
            ("Maturity LTV", result["maturity_ltv"], "ratio"),
            ("Refinance DSCR", result["refinance_dscr"], "ratio"),
            ("Lender annual IRR", result["lender_annual_irr"], "ratio"),
        ],
        columns=["Metric", "Value", "Unit"],
    ),
    hide_index=True,
    width="stretch",
)

schedule = amortization_schedule(
    result["recommended_loan"],
    note_rate,
    case["loan"]["amortization_years"],
    case["loan"]["term_years"],
)
with st.expander("Inspect amortization schedule"):
    st.dataframe(pd.DataFrame(schedule), hide_index=True, width="stretch")

st.warning(
    "Learning prototype only. It does not contain borrower financials, lease abstracts, "
    "legal review, environmental reports or third-party valuations."
)
