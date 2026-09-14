"""Auditable commercial real-estate debt underwriting calculations.

The functions are deliberately small and deterministic. They use synthetic
case inputs and are not a substitute for professional underwriting.
"""

from __future__ import annotations

import json
import math
from copy import deepcopy
from pathlib import Path
from typing import Any


def load_case(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        case = json.load(handle)
    validate_case(case)
    return case


def validate_case(case: dict[str, Any]) -> None:
    property_data = case["property"]
    valuation = case["valuation"]
    loan = case["loan"]
    positive_fields = {
        "area_sf": property_data["area_sf"],
        "base_rent_psf": property_data["base_rent_psf"],
        "operating_expense_psf": property_data["operating_expense_psf"],
        "underwriting_cap_rate": valuation["underwriting_cap_rate"],
        "exit_cap_rate": valuation["exit_cap_rate"],
        "requested_amount": loan["requested_amount"],
        "interest_rate": loan["interest_rate"],
        "amortization_years": loan["amortization_years"],
        "term_years": loan["term_years"],
        "refinance_interest_rate": loan["refinance_interest_rate"],
        "refinance_amortization_years": loan["refinance_amortization_years"],
        "loan_increment": loan["loan_increment"],
    }
    for name, value in positive_fields.items():
        if value <= 0:
            raise ValueError(f"{name} must be positive")

    if not 0 <= property_data["vacancy_rate"] < 1:
        raise ValueError("vacancy_rate must be between 0 and 1")
    for name in ("annual_rent_growth", "annual_other_income_growth", "annual_expense_growth"):
        if property_data[name] <= -1:
            raise ValueError(f"{name} must exceed -100%")

    if loan["term_years"] > loan["amortization_years"]:
        raise ValueError("loan term cannot exceed amortization")
    for name in ("maximum_ltv", "minimum_debt_yield", "maximum_maturity_ltv"):
        if not 0 < loan[name] < 1:
            raise ValueError(f"{name} must be between 0 and 1")
    for name in ("minimum_dscr", "minimum_refinance_dscr"):
        if loan[name] <= 1:
            raise ValueError(f"{name} must exceed 1.0x")
    if not 0 <= loan["origination_fee_rate"] < 1:
        raise ValueError("origination_fee_rate must be between 0 and 1")
    if loan["benchmark_rate"] < 0 or loan["credit_spread"] < 0:
        raise ValueError("benchmark_rate and credit_spread cannot be negative")
    if not case["comparables"]:
        raise ValueError("at least one comparable sale is required")


def annual_debt_service(principal: float, annual_rate: float, amortization_years: int) -> float:
    if principal < 0 or annual_rate < 0 or amortization_years <= 0:
        raise ValueError("principal and annual rate cannot be negative; amortization must be positive")
    if principal == 0:
        return 0.0
    if annual_rate == 0:
        return principal / amortization_years
    monthly_rate = annual_rate / 12
    periods = amortization_years * 12
    payment = principal * monthly_rate / (1 - (1 + monthly_rate) ** -periods)
    return payment * 12


def operating_forecast(case: dict[str, Any], years: int = 5) -> list[dict[str, float]]:
    validate_case(case)
    if years <= 0:
        raise ValueError("years must be positive")
    p = case["property"]
    rows: list[dict[str, float]] = []
    rent = p["base_rent_psf"]
    other = p["other_income_psf"]
    expense = p["operating_expense_psf"]
    for year in range(1, years + 1):
        gross_potential_income = p["area_sf"] * (rent + other)
        vacancy_loss = gross_potential_income * p["vacancy_rate"]
        effective_gross_income = gross_potential_income - vacancy_loss
        operating_expenses = p["area_sf"] * expense
        noi = effective_gross_income - operating_expenses
        rows.append(
            {
                "year": year,
                "base_rent_psf": rent,
                "other_income_psf": other,
                "vacancy_rate": p["vacancy_rate"],
                "gross_potential_income": gross_potential_income,
                "vacancy_loss": vacancy_loss,
                "effective_gross_income": effective_gross_income,
                "operating_expenses": operating_expenses,
                "noi": noi,
            }
        )
        rent *= 1 + p["annual_rent_growth"]
        other *= 1 + p["annual_other_income_growth"]
        expense *= 1 + p["annual_expense_growth"]
    return rows


def comparable_value(case: dict[str, Any]) -> float:
    adjusted_prices = [
        comp["sale_price"] / comp["area_sf"] * (1 + comp["adjustment"])
        for comp in case["comparables"]
    ]
    return sum(adjusted_prices) / len(adjusted_prices) * case["property"]["area_sf"]


def amortization_schedule(
    principal: float,
    annual_rate: float,
    amortization_years: int,
    term_years: int,
) -> list[dict[str, float]]:
    if term_years <= 0 or term_years > amortization_years:
        raise ValueError("term must be positive and cannot exceed amortization")
    monthly_rate = annual_rate / 12
    payment = annual_debt_service(principal, annual_rate, amortization_years) / 12
    balance = principal
    rows: list[dict[str, float]] = []
    for month in range(1, term_years * 12 + 1):
        interest = balance * monthly_rate
        principal_paid = payment - interest
        ending_balance = max(0.0, balance - principal_paid)
        rows.append(
            {
                "month": month,
                "beginning_balance": balance,
                "payment": payment,
                "interest": interest,
                "principal": principal_paid,
                "ending_balance": ending_balance,
            }
        )
        balance = ending_balance
    return rows


def lender_annual_irr(
    principal: float,
    annual_rate: float,
    amortization_years: int,
    term_years: int,
    origination_fee_rate: float = 0.0,
) -> float:
    """Return annualized lender IRR from funding, payments, fee and balloon."""

    if not 0 <= origination_fee_rate < 1:
        raise ValueError("origination_fee_rate must be between 0 and 1")
    schedule = amortization_schedule(principal, annual_rate, amortization_years, term_years)
    cash_flows = [-principal * (1 - origination_fee_rate)]
    cash_flows.extend(row["payment"] for row in schedule)
    cash_flows[-1] += schedule[-1]["ending_balance"]

    def npv(monthly_rate: float) -> float:
        return sum(cash_flow / (1 + monthly_rate) ** month for month, cash_flow in enumerate(cash_flows))

    low, high = -0.999999, 1.0
    while npv(high) > 0 and high < 128:
        high *= 2
    if npv(low) * npv(high) > 0:
        raise ValueError("cash flows do not produce a unique lender IRR")
    for _ in range(200):
        midpoint = (low + high) / 2
        if npv(midpoint) > 0:
            low = midpoint
        else:
            high = midpoint
    monthly_irr = (low + high) / 2
    return (1 + monthly_irr) ** 12 - 1


def loan_sizing(case: dict[str, Any]) -> dict[str, float | str | bool]:
    validate_case(case)
    loan = case["loan"]
    forecast = operating_forecast(case, years=loan["term_years"])
    year_one_noi = forecast[0]["noi"]
    maturity_noi = forecast[-1]["noi"]

    income_value = year_one_noi / case["valuation"]["underwriting_cap_rate"]
    sales_value = comparable_value(case)
    underwritten_value = min(income_value, sales_value)
    ltv_capacity = underwritten_value * loan["maximum_ltv"]
    debt_service_constant = annual_debt_service(1.0, loan["interest_rate"], loan["amortization_years"])
    dscr_capacity = year_one_noi / loan["minimum_dscr"] / debt_service_constant
    debt_yield_capacity = year_one_noi / loan["minimum_debt_yield"]
    capacities = {
        "requested_amount": loan["requested_amount"],
        "ltv": ltv_capacity,
        "dscr": dscr_capacity,
        "debt_yield": debt_yield_capacity,
    }
    raw_recommendation = min(capacities.values())
    recommended_loan = math.floor(raw_recommendation / loan["loan_increment"]) * loan["loan_increment"]
    annual_service = annual_debt_service(recommended_loan, loan["interest_rate"], loan["amortization_years"])
    binding_constraint = min(capacities, key=capacities.get)

    schedule = amortization_schedule(
        recommended_loan,
        loan["interest_rate"],
        loan["amortization_years"],
        loan["term_years"],
    )
    maturity_balance = schedule[-1]["ending_balance"]
    exit_value = maturity_noi / case["valuation"]["exit_cap_rate"]
    maturity_ltv = maturity_balance / exit_value
    refinance_debt_service = annual_debt_service(
        maturity_balance,
        loan["refinance_interest_rate"],
        loan["refinance_amortization_years"],
    )
    refinance_dscr = maturity_noi / refinance_debt_service
    lender_irr = lender_annual_irr(
        recommended_loan,
        loan["interest_rate"],
        loan["amortization_years"],
        loan["term_years"],
        loan["origination_fee_rate"],
    )

    ltv = recommended_loan / underwritten_value
    dscr = year_one_noi / annual_service
    debt_yield = year_one_noi / recommended_loan
    base_limits_pass = (
        ltv <= loan["maximum_ltv"] + 1e-12
        and dscr + 1e-12 >= loan["minimum_dscr"]
        and debt_yield + 1e-12 >= loan["minimum_debt_yield"]
    )
    refinance_limits_pass = (
        maturity_ltv <= loan["maximum_maturity_ltv"] + 1e-12
        and refinance_dscr + 1e-12 >= loan["minimum_refinance_dscr"]
    )
    recommendation = "Proceed with conditions" if base_limits_pass and refinance_limits_pass else "Do not proceed"

    return {
        "year_one_noi": year_one_noi,
        "maturity_noi": maturity_noi,
        "income_value": income_value,
        "comparable_value": sales_value,
        "underwritten_value": underwritten_value,
        "requested_amount": loan["requested_amount"],
        "ltv_capacity": ltv_capacity,
        "dscr_capacity": dscr_capacity,
        "debt_yield_capacity": debt_yield_capacity,
        "recommended_loan": recommended_loan,
        "ltv": ltv,
        "annual_debt_service": annual_service,
        "dscr": dscr,
        "debt_yield": debt_yield,
        "binding_constraint": binding_constraint,
        "maturity_balance": maturity_balance,
        "exit_value": exit_value,
        "maturity_ltv": maturity_ltv,
        "refinance_interest_rate": loan["refinance_interest_rate"],
        "refinance_debt_service": refinance_debt_service,
        "refinance_dscr": refinance_dscr,
        "lender_annual_irr": lender_irr,
        "base_limits_pass": base_limits_pass,
        "refinance_limits_pass": refinance_limits_pass,
        "recommendation": recommendation,
    }


def scenario(
    case: dict[str, Any],
    *,
    vacancy_rate: float | None = None,
    benchmark_rate: float | None = None,
    credit_spread: float | None = None,
    interest_rate: float | None = None,
    cap_rate: float | None = None,
    exit_cap_rate: float | None = None,
    refinance_interest_rate: float | None = None,
) -> dict[str, float | str | bool]:
    changed = deepcopy(case)
    if vacancy_rate is not None:
        changed["property"]["vacancy_rate"] = vacancy_rate
    if benchmark_rate is not None:
        changed["loan"]["benchmark_rate"] = benchmark_rate
    if credit_spread is not None:
        changed["loan"]["credit_spread"] = credit_spread
    if benchmark_rate is not None or credit_spread is not None:
        changed["loan"]["interest_rate"] = (
            changed["loan"]["benchmark_rate"] + changed["loan"]["credit_spread"]
        )
    if interest_rate is not None:
        changed["loan"]["interest_rate"] = interest_rate
    if cap_rate is not None:
        changed["valuation"]["underwriting_cap_rate"] = cap_rate
    if exit_cap_rate is not None:
        changed["valuation"]["exit_cap_rate"] = exit_cap_rate
    if refinance_interest_rate is not None:
        changed["loan"]["refinance_interest_rate"] = refinance_interest_rate
    return loan_sizing(changed)
