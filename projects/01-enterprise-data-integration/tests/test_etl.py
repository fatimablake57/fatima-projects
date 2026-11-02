import importlib.util
from pathlib import Path
import tempfile
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "etl.py"
SPEC = importlib.util.spec_from_file_location("enterprise_etl", MODULE_PATH)
etl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(etl)


class IntegrationTests(unittest.TestCase):
    def test_integrates_valid_orders_and_quarantines_invalid_rows(self):
        customers = [{"customer_id": "C1", "name": "Example", "segment": "retail"}]
        orders = [
            {"order_id": "O1", "customer_id": "C1", "order_date": "2025-01-01", "amount": "10.5"},
            {"order_id": "O2", "customer_id": "C9", "order_date": "2025-01-01", "amount": "1"},
            {"order_id": "O3", "customer_id": "C1", "order_date": "bad-date", "amount": "1"},
            {"order_id": "O4", "customer_id": "C1", "order_date": "2025-01-01", "amount": "-1"},
        ]
        integrated, rejected = etl.integrate(customers, orders)
        self.assertEqual(integrated[0]["amount"], "10.50")
        self.assertEqual([row["reason"] for row in rejected], [
            "unknown_customer", "invalid_order_date", "invalid_amount"
        ])

    def test_invalid_order_does_not_reserve_id(self):
        customers = [{"customer_id": "C1", "name": "Example", "segment": "retail"}]
        orders = [
            {"order_id": "O1", "customer_id": "C1", "order_date": "bad", "amount": "10"},
            {"order_id": "O1", "customer_id": "C1", "order_date": "2025-01-01", "amount": "10"},
        ]
        integrated, rejected = etl.integrate(customers, orders)
        self.assertEqual(len(integrated), 1)
        self.assertEqual(rejected[0]["reason"], "invalid_order_date")

    def test_rejects_duplicate_customer_ids(self):
        customers = [
            {"customer_id": "C1", "name": "One", "segment": "retail"},
            {"customer_id": "C1", "name": "Two", "segment": "business"},
        ]
        with self.assertRaisesRegex(ValueError, "Duplicate customer_id"):
            etl.integrate(customers, [])

    def test_run_writes_outputs_and_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_dir = root / "data"
            data_dir.mkdir()
            (data_dir / "customers.csv").write_text(
                "customer_id,name,segment\nC1,Example,retail\n", encoding="utf-8"
            )
            (data_dir / "orders.csv").write_text(
                "order_id,customer_id,order_date,amount\nO1,C1,2025-01-01,2\n", encoding="utf-8"
            )
            result = etl.run(data_dir, root / "out")
            self.assertEqual(result, {"integrated": 1, "rejected": 0})
            self.assertTrue((root / "out" / "customer_orders.csv").is_file())


if __name__ == "__main__":
    unittest.main()
