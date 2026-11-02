"""Local synthetic event pipeline demonstrating bronze, silver, gold, and DataOps metadata."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3


ROOT = Path(__file__).resolve().parents[1]
INPUT_FIELDS = ("event_id", "event_time", "event_type", "amount")
ALLOWED_EVENT_TYPES = {"payment", "claim", "adjustment"}


def load_events(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        headers = reader.fieldnames or []
        missing = [field for field in INPUT_FIELDS if field not in headers]
        if missing:
            raise ValueError(f"{path}: missing required columns: {', '.join(missing)}")
        return [{key: value or "" for key, value in row.items()} for row in reader]


def validate(row: dict[str, str], seen_ids: set[str]) -> tuple[dict[str, str] | None, str]:
    event_id = row["event_id"].strip()
    if not event_id:
        return None, "missing_event_id"
    if event_id in seen_ids:
        return None, "duplicate_event_id"
    try:
        timestamp = datetime.fromisoformat(row["event_time"].replace("Z", "+00:00"))
    except ValueError:
        return None, "invalid_event_time"
    event_type = row["event_type"].strip().lower()
    if event_type not in ALLOWED_EVENT_TYPES:
        return None, "unknown_event_type"
    try:
        amount = Decimal(row["amount"])
        if not amount.is_finite() or amount < 0:
            raise InvalidOperation
        cents = amount * 100
        if cents != cents.to_integral_value():
            raise InvalidOperation
    except InvalidOperation:
        return None, "invalid_amount"
    if timestamp.tzinfo is None:
        return None, "event_time_requires_timezone"
    seen_ids.add(event_id)
    return {
        "event_id": event_id,
        "event_time": timestamp.isoformat().replace("+00:00", "Z"),
        "event_type": event_type,
        "amount": f"{amount:.2f}",
    }, ""


def write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def daily_summary(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    with sqlite3.connect(":memory:") as connection:
        connection.execute(
            "CREATE TABLE events (event_date TEXT NOT NULL, event_type TEXT NOT NULL, amount_cents INTEGER NOT NULL)"
        )
        connection.executemany(
            "INSERT INTO events VALUES (?, ?, ?)",
            [
                (row["event_time"][:10], row["event_type"], int(Decimal(row["amount"]) * 100))
                for row in rows
            ],
        )
        result = connection.execute(
            """
            SELECT event_date, event_type, COUNT(*) AS event_count,
                   SUM(amount_cents) AS total_amount_cents
            FROM events
            GROUP BY event_date, event_type
            ORDER BY event_date, event_type
            """
        ).fetchall()
    return [
        {
            "event_date": row[0],
            "event_type": row[1],
            "event_count": str(row[2]),
            "total_amount": f"{row[3] // 100}.{row[3] % 100:02d}",
        }
        for row in result
    ]


def run(input_path: Path, lakehouse_dir: Path) -> dict[str, int | str]:
    source_bytes = input_path.read_bytes()
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    lakehouse_dir.mkdir(parents=True, exist_ok=True)
    bronze_path = lakehouse_dir / "bronze" / input_path.name
    bronze_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(input_path, bronze_path)

    clean = []
    quarantine = []
    seen_ids: set[str] = set()
    for row in load_events(bronze_path):
        normalized, reason = validate(row, seen_ids)
        if reason:
            quarantine.append({**row, "reason": reason})
        else:
            clean.append(normalized)

    silver_dir = lakehouse_dir / "silver"
    write_csv(silver_dir / "clean_events.csv", INPUT_FIELDS, clean)
    write_csv(silver_dir / "quarantined_events.csv", INPUT_FIELDS + ("reason",), quarantine)
    gold_rows = daily_summary(clean)
    write_csv(
        lakehouse_dir / "gold" / "daily_summary.csv",
        ("event_date", "event_type", "event_count", "total_amount"),
        gold_rows,
    )
    manifest: dict[str, int | str] = {
        "source_file": input_path.name,
        "source_sha256": source_hash,
        "bronze_records": len(clean) + len(quarantine),
        "silver_records": len(clean),
        "quarantined_records": len(quarantine),
        "gold_rows": len(gold_rows),
        "status": "success",
    }
    (lakehouse_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data" / "events.csv")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output" / "lakehouse")
    args = parser.parse_args()
    print(json.dumps(run(args.input, args.output_dir), indent=2))


if __name__ == "__main__":
    main()
