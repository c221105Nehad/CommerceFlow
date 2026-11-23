
import csv
from pathlib import Path
from collections import Counter, defaultdict


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


# --------------------------------------------------
# 1. INVESTIGATE DUPLICATE REVIEW IDS
# --------------------------------------------------

def investigate_reviews():

    filename = "olist_order_reviews_dataset.csv"

    review_ids = Counter()
    review_order_pairs = Counter()
    full_rows = Counter()
    orders_per_review = defaultdict(set)
    scores_per_review = defaultdict(set)

    for row in read_rows(filename):

        review_id = clean(row["review_id"])
        order_id = clean(row["order_id"])
        score = clean(row["review_score"])

        review_ids[review_id] += 1

        review_order_pairs[(review_id, order_id)] += 1

        # Compare complete records.
        row_signature = tuple(sorted(row.items()))
        full_rows[row_signature] += 1

        orders_per_review[review_id].add(order_id)
        scores_per_review[review_id].add(score)

    repeated_groups = {
        key: count
        for key, count in review_ids.items()
        if count > 1
    }

    duplicate_id_occurrences = sum(
        count - 1 for count in repeated_groups.values()
    )

    duplicate_pair_occurrences = sum(
        count - 1
        for count in review_order_pairs.values()
        if count > 1
    )

    exact_duplicate_occurrences = sum(
        count - 1
        for count in full_rows.values()
        if count > 1
    )

    multiple_order_ids = sum(
        1 for order_set in orders_per_review.values()
        if len(order_set) > 1
    )

    print("\n1. REVIEW ID INVESTIGATION")
    print("=" * 65)

    print(f"Total rows: {sum(review_ids.values()):,}")
    print(f"Distinct review IDs: {len(review_ids):,}")
    print(f"Repeated review ID groups: {len(repeated_groups):,}")
    print(f"Repeated ID occurrences: {duplicate_id_occurrences:,}")
    print(f"Repeated (review_id, order_id) occurrences: {duplicate_pair_occurrences:,}")
    print(f"Exact duplicate row occurrences: {exact_duplicate_occurrences:,}")
    print(f"Review IDs associated with multiple orders: {multiple_order_ids:,}")

    print("\nSample repeated review IDs:")

    for review_id, count in Counter(repeated_groups).most_common(10):
        print(
            f"{review_id}: {count} rows | "
            f"Orders: {sorted(orders_per_review[review_id])[:5]} | "
            f"Scores: {sorted(scores_per_review[review_id])}"
        )


# --------------------------------------------------
# 2. INVESTIGATE MISSING ORDER TIMESTAMPS
# --------------------------------------------------

def investigate_order_timestamps():

    filename = "olist_orders_dataset.csv"

    timestamp_columns = [
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
    ]

    stats = defaultdict(Counter)

    for row in read_rows(filename):

        status = clean(row["order_status"]) or "MISSING_STATUS"

        stats[status]["total"] += 1

        for column in timestamp_columns:
            if not clean(row[column]):
                stats[status][column] += 1

    print("\n\n2. ORDER TIMESTAMP INVESTIGATION")
    print("=" * 85)

    for status, values in sorted(stats.items()):

        total = values["total"]

        print(f"\nOrder status: {status}")
        print(f"Total orders: {total:,}")

        for column in timestamp_columns:

            missing = values[column]
            percentage = missing / total * 100

            print(
                f"  {column}: "
                f"{missing:,} missing ({percentage:.2f}%)"
            )


# --------------------------------------------------
# 3. INVESTIGATE MISSING PRODUCT METADATA
# --------------------------------------------------

def investigate_products():

    filename = "olist_products_dataset.csv"

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

    missing_patterns = Counter()

    translation_values = {
        clean(row["product_category_name"])
        for row in read_rows(
            "product_category_name_translation.csv"
        )
    }

    unmatched_categories = Counter()
    total_rows = 0

    for row in read_rows(filename):

        total_rows += 1

        missing_fields = tuple(
            column
            for column in metadata_columns
            if not clean(row[column])
        )

        missing_patterns[missing_fields] += 1

        category = clean(row["product_category_name"])

        if category and category not in translation_values:
            unmatched_categories[category] += 1

    print("\n\n3. PRODUCT METADATA INVESTIGATION")
    print("=" * 85)

    print(f"Total product records: {total_rows:,}")

    print("\nMissing-value patterns:")

    for pattern, count in missing_patterns.most_common():

        description = ", ".join(pattern) if pattern else "No missing fields"

        print(f"{count:,} rows: {description}")

    print("\nUntranslated product categories:")

    if unmatched_categories:

        for category, count in unmatched_categories.items():
            print(f"{category}: {count:,} products")

    else:
        print("No unmatched categories.")


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    if not RAW_DIR.exists():
        raise SystemExit("Raw dataset directory not found.")

    investigate_reviews()
    investigate_order_timestamps()
    investigate_products()

    print("\n\nANOMALY INVESTIGATION COMPLETED.")


if __name__ == "__main__":
    main()
