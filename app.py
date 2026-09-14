from pathlib import Path

import pandas as pd
import streamlit as st

from debtlens.model import amortization_schedule, load_case, loan_sizing, operating_forecast, scenario


ROOT = Path(__file__).parent
case = load_case(ROOT / "data" / "case_study.json")

st.set_page_config(page_title="DebtLens", page_icon="🏢", layout="wide")
st.title("DebtLens")
st.caption("Commercial real-estate debt underwriting lab using a fictional Metro Vancouver industrial property.")

with st.sidebar:
    st.header("Underwriting assumptions")
    vacancy = st.slider("Year 1 vacancy", 0.0, 0.20, float(case["property"]["vacancy_rate"]), 0.005)
    interest = st.slider("Interest rate", 0.03, 0.09, float(case["loan"]["interest_rate"]), 0.0025)
    cap_rate = st.slider("Capitalization rate", 0.04, 0.08, float(case["valuation"]["underwriting_cap_rate"]), 0.0025)
    st.info("All data and transaction details are synthetic. Change the assumptions to inspect the credit effect.")

result = scenario(case, vacancy_rate=vacancy, interest_rate=interest, cap_rate=cap_rate)
cols = st.columns(5)
cols[0].metric("Recommended loan", f"${result['recommended_loan']/1_000_000:.1f}M")
cols[1].metric("Underwritten value", f"${result['underwritten_value']/1_000_000:.1f}M")
cols[2].metric("LTV", f"{result['ltv']:.1%}")
cols[3].metric("DSCR", f"{result['dscr']:.2f}x")
cols[4].metric("Debt yield", f"{result['debt_yield']:.1%}")

if result["dscr"] >= case["loan"]["minimum_dscr"] and result["ltv"] <= case["loan"]["maximum_ltv"]:
    st.success(f"Proceed with conditions. Binding constraint: {result['binding_constraint'].replace('_', ' ').title()}.")
else:
    st.error("The selected assumptions do not satisfy the base credit limits.")

left, right = st.columns(2)
with left:
    st.subheader("Loan sizing capacities")
    capacities = pd.DataFrame(
        {
            "Capacity": ["Requested", "LTV", "DSCR", "Debt yield"],
            "Amount": [result["requested_amount"], result["ltv_capacity"], result["dscr_capacity"], result["debt_yield_capacity"]],
        }
    ).set_index("Capacity")
    st.bar_chart(capacities)
with right:
    st.subheader("Five-year net operating income")
    forecast = pd.DataFrame(operating_forecast(case)).set_index("year")
    st.line_chart(forecast[["noi"]])

st.subheader("Selected-case metrics")
st.dataframe(
    pd.DataFrame(
        [
            ("Year 1 NOI", result["year_one_noi"]),
            ("Income value", result["income_value"]),
            ("Comparable value", result["comparable_value"]),
            ("Annual debt service", result["annual_debt_service"]),
        ],
        columns=["Metric", "CAD"],
    ),
    hide_index=True,
    width="stretch",
)

schedule = amortization_schedule(
    result["recommended_loan"], interest, case["loan"]["amortization_years"], case["loan"]["term_years"]
)
with st.expander("Inspect amortization schedule"):
    st.dataframe(pd.DataFrame(schedule), hide_index=True, width="stretch")

st.warning("Learning prototype only. It does not contain borrower financials, lease abstracts, legal review, environmental reports or third-party valuations.")
