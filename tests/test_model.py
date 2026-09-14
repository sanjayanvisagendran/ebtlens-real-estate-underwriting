import unittest
from copy import deepcopy
from pathlib import Path

from debtlens.model import (
    amortization_schedule,
    annual_debt_service,
    lender_annual_irr,
    load_case,
    loan_sizing,
    operating_forecast,
    scenario,
    validate_case,
)


CASE_PATH = Path(__file__).parents[1] / "data" / "case_study.json"


class DebtLensTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = load_case(CASE_PATH)
        cls.result = loan_sizing(cls.case)

    def test_year_one_noi(self):
        self.assertAlmostEqual(self.result["year_one_noi"], 3_288_000, places=2)

    def test_recommended_loan_is_rounded_down(self):
        self.assertEqual(self.result["recommended_loan"], 33_500_000)

    def test_dscr_is_binding(self):
        self.assertEqual(self.result["binding_constraint"], "dscr")
        self.assertGreaterEqual(self.result["dscr"], self.case["loan"]["minimum_dscr"])

    def test_credit_limits(self):
        self.assertLessEqual(self.result["ltv"], self.case["loan"]["maximum_ltv"])
        self.assertGreaterEqual(self.result["debt_yield"], self.case["loan"]["minimum_debt_yield"])
        self.assertTrue(self.result["base_limits_pass"])
        self.assertTrue(self.result["refinance_limits_pass"])

    def test_schedule_rolls_forward(self):
        rows = amortization_schedule(33_500_000, 0.0575, 25, 5)
        self.assertEqual(len(rows), 60)
        for previous, current in zip(rows, rows[1:]):
            self.assertAlmostEqual(previous["ending_balance"], current["beginning_balance"], places=6)
        self.assertAlmostEqual(rows[-1]["ending_balance"], 30_017_888.53, places=2)

    def test_payment_identity(self):
        rows = amortization_schedule(33_500_000, 0.0575, 25, 5)
        for row in rows:
            self.assertAlmostEqual(row["payment"], row["interest"] + row["principal"], places=6)

    def test_maturity_metrics_reconcile(self):
        self.assertAlmostEqual(self.result["maturity_balance"], 30_017_888.53, places=2)
        self.assertAlmostEqual(self.result["maturity_noi"], 3_723_395.37, places=2)
        self.assertAlmostEqual(self.result["exit_value"], 62_056_589.50, places=2)
        self.assertAlmostEqual(self.result["maturity_ltv"], 0.4837179867, places=8)
        self.assertAlmostEqual(self.result["refinance_dscr"], 1.4960817681, places=8)

    def test_higher_vacancy_reduces_dscr_capacity(self):
        self.assertLess(scenario(self.case, vacancy_rate=0.10)["dscr_capacity"], self.result["dscr_capacity"])

    def test_higher_rate_reduces_dscr_capacity(self):
        self.assertLess(scenario(self.case, interest_rate=0.07)["dscr_capacity"], self.result["dscr_capacity"])

    def test_higher_credit_spread_reduces_capacity(self):
        stressed = scenario(self.case, credit_spread=0.035)
        self.assertLess(stressed["dscr_capacity"], self.result["dscr_capacity"])

    def test_higher_exit_cap_increases_maturity_ltv(self):
        stressed = scenario(self.case, exit_cap_rate=0.07)
        self.assertLess(stressed["exit_value"], self.result["exit_value"])
        self.assertGreater(stressed["maturity_ltv"], self.result["maturity_ltv"])

    def test_higher_refinance_rate_reduces_refinance_dscr(self):
        stressed = scenario(self.case, refinance_interest_rate=0.08)
        self.assertLess(stressed["refinance_dscr"], self.result["refinance_dscr"])

    def test_operating_forecast_has_five_years(self):
        rows = operating_forecast(self.case)
        self.assertEqual([row["year"] for row in rows], [1, 2, 3, 4, 5])
        self.assertGreater(rows[-1]["noi"], rows[0]["noi"])

    def test_debt_service_scales_with_principal(self):
        one = annual_debt_service(1, 0.0575, 25)
        million = annual_debt_service(1_000_000, 0.0575, 25)
        self.assertAlmostEqual(million, one * 1_000_000, places=6)

    def test_zero_rate_debt_service(self):
        self.assertEqual(annual_debt_service(1_000_000, 0, 20), 50_000)

    def test_fee_increases_lender_irr(self):
        no_fee = lender_annual_irr(33_500_000, 0.0575, 25, 5, 0)
        with_fee = lender_annual_irr(33_500_000, 0.0575, 25, 5, 0.01)
        effective_contract_rate = (1 + 0.0575 / 12) ** 12 - 1
        self.assertAlmostEqual(no_fee, effective_contract_rate, places=8)
        self.assertGreater(with_fee, no_fee)

    def test_invalid_exit_cap_is_rejected(self):
        invalid = deepcopy(self.case)
        invalid["valuation"]["exit_cap_rate"] = 0
        with self.assertRaises(ValueError):
            validate_case(invalid)


if __name__ == "__main__":
    unittest.main()
