import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "interop.py"
SPEC = importlib.util.spec_from_file_location("healthcare_interop", MODULE_PATH)
interop = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(interop)
DATA = Path(__file__).resolve().parents[1] / "data"


class InteroperabilityTests(unittest.TestCase):
    def test_parses_hl7_observations(self):
        rows = interop.parse_hl7((DATA / "hl7" / "synthetic_oru.hl7").read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["patient_ref"], "SYNTH-PAT-001")
        self.assertEqual(rows[0]["effective_at"], "2025-01-15T10:20:00Z")

    def test_parses_fhir_observations(self):
        bundle = json.loads((DATA / "fhir" / "synthetic_bundle.json").read_text(encoding="utf-8"))
        rows = interop.parse_fhir(bundle)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["patient_ref"], "SYNTH-PAT-002")
        self.assertEqual(rows[0]["value"], "36.8")

    def test_rejects_non_bundle(self):
        with self.assertRaisesRegex(ValueError, "must be a Bundle"):
            interop.parse_fhir({"resourceType": "Patient"})

    def test_run_writes_combined_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "observations.csv"
            count = interop.run(
                DATA / "hl7" / "synthetic_oru.hl7",
                DATA / "fhir" / "synthetic_bundle.json",
                output,
            )
            self.assertEqual(count, 3)
            self.assertEqual(len(output.read_text(encoding="utf-8").splitlines()), 4)


if __name__ == "__main__":
    unittest.main()
