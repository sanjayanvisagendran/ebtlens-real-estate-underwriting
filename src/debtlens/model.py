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
    loan = case["loan"]
    positive_fields = {
        "area_sf": property_data["area_sf"],
        "base_rent_psf": property_data["base_rent_psf"],
        "operating_expense_psf": property_data["operating_expense_psf"],
        "requested_amount": loan["requested_amount"],
        "interest_rate": loan["interest_rate"],
        "amortization_years": loan["amortization_years"],
        "term_years": loan["term_years"],
        "loan_increment": loan["loan_increment"],
    }
    for name, value in positive_fields.items():
        if value <= 0:
            raise ValueError(f"{name} must be positive")
    for name in ("vacancy_rate",):
        if not 0 <= property_data[name] < 1:
            raise ValueError(f"{name} must be between 0 and 1")
    if loan["term_years"] > loan["amortization_years"]:
        raise ValueError("loan term cannot exceed amortization")
    for name in ("maximum_ltv", "minimum_debt_yield"):
        if not 0 < loan[name] < 1:
            raise ValueError(f"{name} must be between 0 and 1")
    if loan["minimum_dscr"] <= 1:
        raise ValueError("minimum_dscr must exceed 1.0x")


def annual_debt_service(principal: float, annual_rate: float, amortization_years: int) -> float:
    monthly_rate = annual_rate / 12
    periods = amortization_years * 12
    payment = principal * monthly_rate / (1 - (1 + monthly_rate) ** -periods)
    return payment * 12


def operating_forecast(case: dict[str, Any], years: int = 5) -> list[dict[str, float]]:
    validate_case(case)
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


def loan_sizing(case: dict[str, Any]) -> dict[str, float | str]:
    validate_case(case)
    year_one_noi = operating_forecast(case, years=1)[0]["noi"]
    loan = case["loan"]
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
    return {
        "year_one_noi": year_one_noi,
        "income_value": income_value,
        "comparable_value": sales_value,
        "underwritten_value": underwritten_value,
        "requested_amount": loan["requested_amount"],
        "ltv_capacity": ltv_capacity,
        "dscr_capacity": dscr_capacity,
        "debt_yield_capacity": debt_yield_capacity,
        "recommended_loan": recommended_loan,
        "ltv": recommended_loan / underwritten_value,
        "annual_debt_service": annual_service,
        "dscr": year_one_noi / annual_service,
        "debt_yield": year_one_noi / recommended_loan,
        "binding_constraint": binding_constraint,
        "recommendation": "Proceed with conditions",
    }


def amortization_schedule(principal: float, annual_rate: float, amortization_years: int, term_years: int) -> list[dict[str, float]]:
    monthly_rate = annual_rate / 12
    payment = annual_debt_service(principal, annual_rate, amortization_years) / 12
    balance = principal
    rows: list[dict[str, float]] = []
    for month in range(1, term_years * 12 + 1):
        interest = balance * monthly_rate
        principal_paid = payment - interest
        ending_balance = balance - principal_paid
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


def scenario(case: dict[str, Any], *, vacancy_rate: float | None = None, interest_rate: float | None = None, cap_rate: float | None = None) -> dict[str, float | str]:
    changed = deepcopy(case)
    if vacancy_rate is not None:
        changed["property"]["vacancy_rate"] = vacancy_rate
    if interest_rate is not None:
        changed["loan"]["interest_rate"] = interest_rate
    if cap_rate is not None:
        changed["valuation"]["underwriting_cap_rate"] = cap_rate
    return loan_sizing(changed)

