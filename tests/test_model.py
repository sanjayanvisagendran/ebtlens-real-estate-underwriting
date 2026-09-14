import unittest
from pathlib import Path

from debtlens.model import amortization_schedule, annual_debt_service, load_case, loan_sizing, operating_forecast, scenario


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

    def test_higher_vacancy_reduces_dscr_capacity(self):
        base = self.result["dscr_capacity"]
        stressed = scenario(self.case, vacancy_rate=0.10)["dscr_capacity"]
        self.assertLess(stressed, base)

    def test_higher_rate_reduces_dscr_capacity(self):
        base = self.result["dscr_capacity"]
        stressed = scenario(self.case, interest_rate=0.07)["dscr_capacity"]
        self.assertLess(stressed, base)

    def test_operating_forecast_has_five_years(self):
        rows = operating_forecast(self.case)
        self.assertEqual([row["year"] for row in rows], [1, 2, 3, 4, 5])
        self.assertGreater(rows[-1]["noi"], rows[0]["noi"])

    def test_debt_service_scales_with_principal(self):
        one = annual_debt_service(1, 0.0575, 25)
        million = annual_debt_service(1_000_000, 0.0575, 25)
        self.assertAlmostEqual(million, one * 1_000_000, places=6)


if __name__ == "__main__":
    unittest.main()
