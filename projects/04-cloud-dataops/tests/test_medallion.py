import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "medallion.py"
SPEC = importlib.util.spec_from_file_location("dataops_medallion", MODULE_PATH)
medallion = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(medallion)
DATA = Path(__file__).resolve().parents[1] / "data" / "events.csv"


class MedallionTests(unittest.TestCase):
    def test_validates_event_and_rejects_bad_timestamp(self):
        seen = set()
        normalized, reason = medallion.validate(
            {"event_id": "E1", "event_time": "2025-01-01T00:00:00Z", "event_type": "payment", "amount": "1.2"},
            seen,
        )
        self.assertEqual(normalized["amount"], "1.20")
        self.assertEqual(reason, "")
        rejected, reason = medallion.validate(
            {"event_id": "E2", "event_time": "bad", "event_type": "claim", "amount": "1"}, seen
        )
        self.assertIsNone(rejected)
        self.assertEqual(reason, "invalid_event_time")

    def test_summarizes_by_date_and_type(self):
        rows = [
            {"event_time": "2025-01-01T00:00:00Z", "event_type": "payment", "amount": "1.20"},
            {"event_time": "2025-01-01T02:00:00Z", "event_type": "payment", "amount": "2.30"},
        ]
        self.assertEqual(
            medallion.daily_summary(rows),
            [{"event_date": "2025-01-01", "event_type": "payment", "event_count": "2", "total_amount": "3.50"}],
        )

    def test_run_writes_layers_quarantine_and_source_hash(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "lakehouse"
            manifest = medallion.run(DATA, target)
            self.assertEqual(manifest["silver_records"], 4)
            self.assertEqual(manifest["quarantined_records"], 2)
            self.assertEqual(json.loads((target / "manifest.json").read_text())["status"], "success")
            self.assertTrue((target / "bronze" / "events.csv").is_file())
            self.assertTrue((target / "gold" / "daily_summary.csv").is_file())


if __name__ == "__main__":
    unittest.main()
