
import csv
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"


def read_rows(filename):

    path = RAW_DIR / filename

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        yield from csv.DictReader(file)


def clean(value):
    return value.strip() if value else ""


def parse_datetime(value):

    value = clean(value)

    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


# --------------------------------------------------
# 1. ORDERS WITHOUT CHILD RECORDS
# --------------------------------------------------

def investigate_order_coverage():

    orders = {}

    for row in read_rows("olist_orders_dataset.csv"):

        order_id = clean(row["order_id"])
        status = clean(row["order_status"])

        orders[order_id] = status

    child_files = {
        "Order items": "olist_order_items_dataset.csv",
        "Payments": "olist_order_payments_dataset.csv",
        "Reviews": "olist_order_reviews_dataset.csv",
    }

    print("\n1. ORDER CHILD-RECORD COVERAGE")
    print("=" * 70)

    for label, filename in child_files.items():

        associated_orders = {
            clean(row["order_id"])
            for row in read_rows(filename)
            if clean(row["order_id"])
        }

        missing_orders = set(orders) - associated_orders

        status_counts = Counter(
            orders[order_id]
            for order_id in missing_orders
        )

        print(f"\n{label}")
        print("-" * 60)

        print(f"Orders without associated records: {len(missing_orders):,}")

        print("Breakdown by order status:")

        for status, count in sorted(status_counts.items()):
            print(f"  {status}: {count:,}")

        print("Sample order IDs:")

        for order_id in sorted(missing_orders)[:5]:
            print(f"  {order_id}")


# --------------------------------------------------
# 2. TIMESTAMP CHRONOLOGY ANOMALIES
# --------------------------------------------------

def investigate_chronology():

    comparisons = [
        (
            "Approval vs Carrier",
            "order_approved_at",
            "order_delivered_carrier_date",
        ),
        (
            "Carrier vs Customer Delivery",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
        ),
    ]

    violation_counts = defaultdict(Counter)
    samples = defaultdict(list)

    for row in read_rows("olist_orders_dataset.csv"):

        order_id = clean(row["order_id"])
        status = clean(row["order_status"])

        for name, first_column, second_column in comparisons:

            first = parse_datetime(row[first_column])
            second = parse_datetime(row[second_column])

            if first and second and first > second:

                violation_counts[name][status] += 1

                if len(samples[name]) < 10:

                    samples[name].append({
                        "order_id": order_id,
                        "status": status,
                        "first": first.isoformat(),
                        "second": second.isoformat(),
                    })

    print("\n\n2. TIMESTAMP CHRONOLOGY INVESTIGATION")
    print("=" * 70)

    for name, _, _ in comparisons:

        print(f"\n{name}")
        print("-" * 60)

        total = sum(violation_counts[name].values())

        print(f"Total violations: {total:,}")
        print("Violations by order status:")

        for status, count in sorted(violation_counts[name].items()):
            print(f"  {status}: {count:,}")

        print("\nSample records:")

        for sample in samples[name]:

            print(
                f"Order: {sample['order_id']} | "
                f"Status: {sample['status']}"
            )

            print(
                f"  First event:  {sample['first']}"
            )

            print(
                f"  Second event: {sample['second']}"
            )


def main():

    if not RAW_DIR.exists():
        raise SystemExit("Raw data directory not found.")

    investigate_order_coverage()
    investigate_chronology()

    print("\n\nFINAL SOURCE INVESTIGATION COMPLETED.")


if __name__ == "__main__":
    main()
