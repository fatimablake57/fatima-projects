"""Normalize synthetic HL7 v2 ORU and FHIR R4 Observation samples."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIELDS = ("source", "patient_ref", "code", "display", "value", "unit", "effective_at", "status")


def parse_hl7(text: str) -> list[dict[str, str]]:
    patient_ref = ""
    observations = []
    for line in text.splitlines():
        fields = line.rstrip("\r").split("|")
        if fields[0] == "PID":
            patient_ref = fields[3].split("^")[0] if len(fields) > 3 else ""
        elif fields[0] == "OBX":
            if len(fields) < 14:
                raise ValueError("HL7 OBX segment is missing required fields")
            code_parts = fields[3].split("^")
            if not patient_ref or not fields[5] or not code_parts[0]:
                raise ValueError("HL7 observation requires a patient reference, code, and value")
            timestamp = fields[14] if len(fields) > 14 else ""
            effective_at = (
                f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}T"
                f"{timestamp[8:10]}:{timestamp[10:12]}:{timestamp[12:14]}Z"
                if len(timestamp) >= 14
                else timestamp
            )
            observations.append(
                {
                    "source": "HL7v2",
                    "patient_ref": patient_ref,
                    "code": code_parts[0],
                    "display": code_parts[1] if len(code_parts) > 1 else "",
                    "value": fields[5],
                    "unit": fields[6],
                    "effective_at": effective_at,
                    "status": fields[11] if len(fields) > 11 else "",
                }
            )
    return observations


def parse_fhir(bundle: dict) -> list[dict[str, str]]:
    if bundle.get("resourceType") != "Bundle":
        raise ValueError("FHIR input must be a Bundle")
    observations = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") != "Observation":
            continue
        codings = resource.get("code", {}).get("coding", [])
        if not codings:
            raise ValueError("FHIR Observation must contain at least one code")
        code = codings[0]
        subject = resource.get("subject", {}).get("reference", "")
        quantity = resource.get("valueQuantity", {})
        value = quantity.get("value")
        if not subject or value is None:
            raise ValueError("FHIR Observation requires subject and valueQuantity.value")
        observations.append(
            {
                "source": "FHIR",
                "patient_ref": subject.rsplit("/", 1)[-1],
                "code": str(code.get("code", "")),
                "display": str(code.get("display") or resource.get("code", {}).get("text", "")),
                "value": str(value),
                "unit": str(quantity.get("unit", "")),
                "effective_at": str(resource.get("effectiveDateTime", "")),
                "status": str(resource.get("status", "")),
            }
        )
    return observations


def write_observations(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def run(hl7_path: Path, fhir_path: Path, output_path: Path) -> int:
    hl7_rows = parse_hl7(hl7_path.read_text(encoding="utf-8"))
    fhir_bundle = json.loads(fhir_path.read_text(encoding="utf-8"))
    fhir_rows = parse_fhir(fhir_bundle)
    rows = hl7_rows + fhir_rows
    write_observations(output_path, rows)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hl7", type=Path, default=ROOT / "data" / "hl7" / "synthetic_oru.hl7")
    parser.add_argument("--fhir", type=Path, default=ROOT / "data" / "fhir" / "synthetic_bundle.json")
    parser.add_argument("--output", type=Path, default=ROOT / "output" / "normalized_observations.csv")
    args = parser.parse_args()
    count = run(args.hl7, args.fhir, args.output)
    print(f"Normalized {count} synthetic observations to {args.output}")


if __name__ == "__main__":
    main()
