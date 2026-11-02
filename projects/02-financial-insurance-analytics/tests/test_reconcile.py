import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "reconcile.py"
SPEC = importlib.util.spec_from_file_location("financial_reconcile", MODULE_PATH)
reconcile_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reconcile_module)


class ReconciliationTests(unittest.TestCase):
    def test_exact_cents_and_variances(self):
        self.assertEqual(reconcile_module.to_cents("12.34"), 1234)
        with self.assertRaises(ValueError):
            reconcile_module.to_cents("1.001")
        with sqlite3.connect(":memory:") as connection:
            connection.row_factory = sqlite3.Row
            reconcile_module.initialize(connection)
            reconcile_module.load_records(
                connection,
                [{"policy_id": "P1", "expected_premium": "12.34", "expected_commission": "1.00"}],
                [{"payment_id": "T1", "policy_id": "P1", "amount": "12.34", "paid_at": "2025-01-01"}],
                [],
            )
            result = reconcile_module.reconcile(connection)[0]
            self.assertEqual(result["premium_variance_cents"], 0)
            self.assertEqual(result["commission_variance_cents"], -100)
            self.assertFalse(result["reconciled"])

    def test_sample_data_reconciles_matched_policy_and_flags_exceptions(self):
        data_dir = Path(__file__).resolve().parents[1] / "data"
        with tempfile.TemporaryDirectory() as temp_dir:
            rows = reconcile_module.run(data_dir, Path(temp_dir))
        by_id = {row["policy_id"]: row for row in rows}
        self.assertTrue(by_id["POL-001"]["reconciled"])
        self.assertEqual(by_id["POL-002"]["premium_variance_cents"], -1000)
        self.assertEqual(by_id["POL-003"]["actual_premium_cents"], 0)


if __name__ == "__main__":
    unittest.main()
