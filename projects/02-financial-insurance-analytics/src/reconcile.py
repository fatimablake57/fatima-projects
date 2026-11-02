"""Synthetic policy, payment, and commission reconciliation using SQLite."""

from __future__ import annotations

import argparse
import csv
from contextlib import closing
from decimal import Decimal, InvalidOperation
from pathlib import Path
import sqlite3


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "sql" / "schema.sql"
QUERY_PATH = ROOT / "sql" / "reconciliation.sql"


def load_csv(path: Path, fields: tuple[str, ...]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        headers = reader.fieldnames or []
        missing = [field for field in fields if field not in headers]
        if missing:
            raise ValueError(f"{path}: missing required columns: {', '.join(missing)}")
        return [{key: value or "" for key, value in row.items()} for row in reader]


def to_cents(value: str) -> int:
    try:
        amount = Decimal(value)
        if not amount.is_finite() or amount < 0:
            raise InvalidOperation
        cents = amount * 100
        if cents != cents.to_integral_value():
            raise InvalidOperation
    except InvalidOperation as error:
        raise ValueError(f"Invalid non-negative amount with at most two decimals: {value!r}") from error
    return int(cents)


def initialize(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    connection.execute("PRAGMA foreign_keys = ON")


def load_records(
    connection: sqlite3.Connection,
    policies: list[dict[str, str]],
    payments: list[dict[str, str]],
    commissions: list[dict[str, str]],
) -> None:
    with connection:
        connection.execute("DELETE FROM payments")
        connection.execute("DELETE FROM commissions")
        connection.execute("DELETE FROM policies")
        connection.executemany(
            "INSERT INTO policies VALUES (?, ?, ?)",
            [
                (r["policy_id"], to_cents(r["expected_premium"]), to_cents(r["expected_commission"]))
                for r in policies
            ],
        )
        connection.executemany(
            "INSERT INTO payments VALUES (?, ?, ?, ?)",
            [(r["payment_id"], r["policy_id"], to_cents(r["amount"]), r["paid_at"]) for r in payments],
        )
        connection.executemany(
            "INSERT INTO commissions VALUES (?, ?, ?, ?)",
            [(r["commission_id"], r["policy_id"], to_cents(r["amount"]), r["paid_at"]) for r in commissions],
        )


def reconcile(connection: sqlite3.Connection) -> list[dict[str, int | str | bool]]:
    rows = connection.execute(QUERY_PATH.read_text(encoding="utf-8")).fetchall()
    result = []
    for row in rows:
        reconciled = row["premium_variance_cents"] == 0 and row["commission_variance_cents"] == 0
        result.append({**dict(row), "reconciled": reconciled})
    return result


def run(data_dir: Path, output_dir: Path) -> list[dict[str, int | str | bool]]:
    policies = load_csv(data_dir / "policies.csv", ("policy_id", "expected_premium", "expected_commission"))
    payments = load_csv(data_dir / "payments.csv", ("payment_id", "policy_id", "amount", "paid_at"))
    commissions = load_csv(data_dir / "commissions.csv", ("commission_id", "policy_id", "amount", "paid_at"))
    output_dir.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(output_dir / "reconciliation.db")) as connection:
        connection.row_factory = sqlite3.Row
        initialize(connection)
        load_records(connection, policies, payments, commissions)
        rows = reconcile(connection)

    report_path = output_dir / "reconciliation.csv"
    fields = tuple(rows[0].keys()) if rows else (
        "policy_id", "expected_premium_cents", "actual_premium_cents", "premium_variance_cents",
        "expected_commission_cents", "actual_commission_cents", "commission_variance_cents", "reconciled",
    )
    with report_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output")
    args = parser.parse_args()
    rows = run(args.data_dir, args.output_dir)
    reconciled = sum(row["reconciled"] for row in rows)
    print(f"Policies: {len(rows)}; fully reconciled: {reconciled}; exceptions: {len(rows) - reconciled}")


if __name__ == "__main__":
    main()
