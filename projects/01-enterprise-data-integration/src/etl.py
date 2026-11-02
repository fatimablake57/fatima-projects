"""Validated customer/order CSV integration demo using only the Python standard library."""

from __future__ import annotations

import argparse
import csv
from datetime import date
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CUSTOMER_FIELDS = ("customer_id", "name", "segment")
ORDER_FIELDS = ("order_id", "customer_id", "order_date", "amount")
OUTPUT_FIELDS = ("customer_id", "customer_name", "segment", "order_id", "order_date", "amount")


def read_csv(path: Path, required_headers: tuple[str, ...]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        headers = reader.fieldnames or []
        missing = [field for field in required_headers if field not in headers]
        if missing:
            raise ValueError(f"{path}: missing required columns: {', '.join(missing)}")
        return [{key: value or "" for key, value in row.items()} for row in reader]


def integrate(
    customers: list[dict[str, str]], orders: list[dict[str, str]]
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    customer_by_id: dict[str, dict[str, str]] = {}
    for customer in customers:
        customer_id = customer["customer_id"].strip()
        if not customer_id or not customer["name"].strip():
            raise ValueError("Customer records require a non-empty ID and name")
        if customer_id in customer_by_id:
            raise ValueError(f"Duplicate customer_id: {customer_id}")
        customer_by_id[customer_id] = customer

    integrated = []
    rejected = []
    seen_orders: set[str] = set()
    for row in orders:
        order_id = row["order_id"].strip()
        reason = ""
        if not order_id:
            reason = "missing_order_id"
        elif order_id in seen_orders:
            reason = "duplicate_order_id"
        customer_id = row["customer_id"].strip()
        if not reason and customer_id not in customer_by_id:
            reason = "unknown_customer"
        try:
            order_date = date.fromisoformat(row["order_date"].strip())
        except ValueError:
            order_date = None
            if not reason:
                reason = "invalid_order_date"
        try:
            amount = Decimal(row["amount"].strip())
            if not amount.is_finite() or amount <= 0:
                raise InvalidOperation
        except InvalidOperation:
            amount = None
            if not reason:
                reason = "invalid_amount"
        if reason:
            rejected.append({**row, "reason": reason})
            continue

        seen_orders.add(order_id)
        customer = customer_by_id[customer_id]
        integrated.append(
            {
                "customer_id": customer_id,
                "customer_name": customer["name"].strip(),
                "segment": customer["segment"].strip(),
                "order_id": order_id,
                "order_date": order_date.isoformat(),
                "amount": f"{amount:.2f}",
            }
        )
    return integrated, rejected


def write_csv(path: Path, fieldnames: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run(data_dir: Path, output_dir: Path) -> dict[str, int]:
    customers = read_csv(data_dir / "customers.csv", CUSTOMER_FIELDS)
    orders = read_csv(data_dir / "orders.csv", ORDER_FIELDS)
    integrated, rejected = integrate(customers, orders)
    write_csv(output_dir / "customer_orders.csv", OUTPUT_FIELDS, integrated)
    write_csv(output_dir / "rejected_orders.csv", ORDER_FIELDS + ("reason",), rejected)
    summary = {"integrated": len(integrated), "rejected": len(rejected)}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "run_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output")
    args = parser.parse_args()
    print(json.dumps(run(args.data_dir, args.output_dir), indent=2))


if __name__ == "__main__":
    main()
