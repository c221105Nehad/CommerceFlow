
import csv
from pathlib import Path
from collections import Counter
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


def report_cardinality(name, counts):

    multiple_groups = sum(
        1 for count in counts.values() if count > 1
    )

    extra_rows = sum(
        count - 1
        for count in counts.values()
        if count > 1
    )

    maximum = max(counts.values(), default=0)

    print(f"\n{name}")
    print("-" * 60)
    print(f"Distinct parent keys: {len(counts):,}")
    print(f"Keys associated with multiple records: {multiple_groups:,}")
    print(f"Additional associated records: {extra_rows:,}")
    print(f"Maximum records per key: {maximum:,}")


# --------------------------------------------------
# 1. RELATIONSHIP CARDINALITY
# --------------------------------------------------

def investigate_cardinality():

    orders_per_customer = Counter()
    items_per_order = Counter()
    payments_per_order = Counter()
    reviews_per_order = Counter()
    items_per_product = Counter()
    items_per_seller = Counter()

    for row in read_rows("olist_orders_dataset.csv"):

        customer_id = clean(row["customer_id"])

        if customer_id:
            orders_per_customer[customer_id] += 1

    for row in read_rows("olist_order_items_dataset.csv"):

        order_id = clean(row["order_id"])
        product_id = clean(row["product_id"])
        seller_id = clean(row["seller_id"])

        if order_id:
            items_per_order[order_id] += 1

        if product_id:
            items_per_product[product_id] += 1

        if seller_id:
            items_per_seller[seller_id] += 1

    for row in read_rows("olist_order_payments_dataset.csv"):

        order_id = clean(row["order_id"])

        if order_id:
            payments_per_order[order_id] += 1

    for row in read_rows("olist_order_reviews_dataset.csv"):

        order_id = clean(row["order_id"])

        if order_id:
            reviews_per_order[order_id] += 1

    print("\n1. RELATIONSHIP CARDINALITY")
    print("=" * 65)

    report_cardinality(
        "Orders per customer_id",
        orders_per_customer
    )

    report_cardinality(
        "Items per order",
        items_per_order
    )

    report_cardinality(
        "Payments per order",
        payments_per_order
    )

    report_cardinality(
        "Reviews per order",
        reviews_per_order
    )

    report_cardinality(
        "Order items per product",
        items_per_product
    )

    report_cardinality(
        "Order items per seller",
        items_per_seller
    )


# --------------------------------------------------
# 2. REPEAT CUSTOMERS
# --------------------------------------------------

def investigate_repeat_customers():

    customer_records_per_buyer = Counter()

    for row in read_rows("olist_customers_dataset.csv"):

        unique_id = clean(row["customer_unique_id"])

        if unique_id:
            customer_records_per_buyer[unique_id] += 1

    repeat_buyers = sum(
        1 for count in customer_records_per_buyer.values()
        if count > 1
    )

    print("\n\n2. REPEAT CUSTOMER INVESTIGATION")
    print("=" * 65)

    print(
        f"Distinct actual customers: "
        f"{len(customer_records_per_buyer):,}"
    )

    print(f"Customers with multiple customer_id records: {repeat_buyers:,}")

    print(
        f"Maximum customer records per actual customer: "
        f"{max(customer_records_per_buyer.values(), default=0):,}"
    )


# --------------------------------------------------
# 3. MISSING PRODUCT METADATA USAGE
# --------------------------------------------------

def investigate_incomplete_products():

    metadata_columns = [
        "product_category_name",
        "product_name_lenght",
        "product_description_lenght",
        "product_photos_qty",
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    ]

    incomplete_product_ids = set()

    for row in read_rows("olist_products_dataset.csv"):

        product_id = clean(row["product_id"])

        missing = any(
            not clean(row[column])
            for column in metadata_columns
        )

        if missing and product_id:
            incomplete_product_ids.add(product_id)

    used_incomplete_products = set()
    affected_items = 0

    for row in read_rows("olist_order_items_dataset.csv"):

        product_id = clean(row["product_id"])

        if product_id in incomplete_product_ids:
            used_incomplete_products.add(product_id)
            affected_items += 1

    print("\n\n3. INCOMPLETE PRODUCT USAGE")
    print("=" * 65)

    print(f"Incomplete product records: {len(incomplete_product_ids):,}")
    print(f"Incomplete products appearing in orders: {len(used_incomplete_products):,}")
    print(f"Order-item records referencing incomplete products: {affected_items:,}")


# --------------------------------------------------
# 4. TIMESTAMP CHRONOLOGY
# --------------------------------------------------

def parse_datetime(value):

    value = clean(value)

    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def investigate_timestamp_chronology():

    pairs = [
        (
            "purchase_vs_approval",
            "order_purchase_timestamp",
            "order_approved_at",
        ),
        (
            "approval_vs_carrier",
            "order_approved_at",
            "order_delivered_carrier_date",
        ),
        (
            "carrier_vs_delivery",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
        ),
    ]

    violations = Counter()
    invalid_timestamps = Counter()
    delivered_missing = []

    for row in read_rows("olist_orders_dataset.csv"):

        status = clean(row["order_status"])

        parsed = {}

        timestamp_columns = {
            column
            for _, first, second in pairs
            for column in (first, second)
        }

        for column in timestamp_columns:

            value = clean(row[column])

            if value:
                parsed[column] = parse_datetime(value)

                if parsed[column] is None:
                    invalid_timestamps[column] += 1

        # Check whether chronological order is violated.
        for name, first, second in pairs:

            earlier = parsed.get(first)
            later = parsed.get(second)

            if earlier and later and earlier > later:
                violations[name] += 1

        # Delivered orders should normally have
        # all three operational milestone timestamps.
        if status == "delivered":

            required = [
                "order_approved_at",
                "order_delivered_carrier_date",
                "order_delivered_customer_date",
            ]

            missing = [
                column for column in required
                if not clean(row[column])
            ]

            if missing:
                delivered_missing.append(
                    (row["order_id"], missing)
                )

    print("\n\n4. TIMESTAMP CHRONOLOGY")
    print("=" * 65)

    for name, _, _ in pairs:
        print(f"{name}: {violations[name]:,} violations")

    print("\nInvalid timestamp formats:")

    if invalid_timestamps:
        for column, count in invalid_timestamps.items():
            print(f"{column}: {count:,}")
    else:
        print("No invalid timestamp formats detected.")

    print(
        f"\nDelivered orders with missing milestones: "
        f"{len(delivered_missing):,}"
    )

    for order_id, missing in delivered_missing[:10]:

        print(
            f"Order: {order_id} | "
            f"Missing: {', '.join(missing)}"
        )


# --------------------------------------------------
# 5. GEOLOCATION CARDINALITY
# --------------------------------------------------

def investigate_geolocation():

    zip_counts = Counter()

    for row in read_rows("olist_geolocation_dataset.csv"):

        prefix = clean(row["geolocation_zip_code_prefix"])

        if prefix:
            zip_counts[prefix] += 1

    print("\n\n5. GEOLOCATION INVESTIGATION")
    print("=" * 65)

    report_cardinality(
        "Geolocation observations per ZIP prefix",
        zip_counts
    )


def main():

    if not RAW_DIR.exists():
        raise SystemExit("Raw dataset directory not found.")

    investigate_cardinality()
    investigate_repeat_customers()
    investigate_incomplete_products()
    investigate_timestamp_chronology()
    investigate_geolocation()

    print("\n\nRELATIONSHIP VALIDATION COMPLETED.")


if __name__ == "__main__":
    main()
