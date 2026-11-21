
import csv
from pathlib import Path
from collections import Counter


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"


# Candidate keys to investigate.
# These are hypotheses, not yet database constraints.
CANDIDATE_KEYS = {
    "olist_customers_dataset.csv": ["customer_id"],
    "olist_orders_dataset.csv": ["order_id"],
    "olist_order_items_dataset.csv": [
        "order_id", "order_item_id"
    ],
    "olist_order_payments_dataset.csv": [
        "order_id", "payment_sequential"
    ],
    "olist_order_reviews_dataset.csv": ["review_id"],
    "olist_products_dataset.csv": ["product_id"],
    "olist_sellers_dataset.csv": ["seller_id"],
    "product_category_name_translation.csv": [
        "product_category_name"
    ],
}

# Foreign-key relationships to validate.
FOREIGN_KEYS = [
    (
        "olist_orders_dataset.csv",
        "customer_id",
        "olist_customers_dataset.csv",
        "customer_id",
    ),
    (
        "olist_order_items_dataset.csv",
        "order_id",
        "olist_orders_dataset.csv",
        "order_id",
    ),
    (
        "olist_order_items_dataset.csv",
        "product_id",
        "olist_products_dataset.csv",
        "product_id",
    ),
    (
        "olist_order_items_dataset.csv",
        "seller_id",
        "olist_sellers_dataset.csv",
        "seller_id",
    ),
    (
        "olist_order_payments_dataset.csv",
        "order_id",
        "olist_orders_dataset.csv",
        "order_id",
    ),
    (
        "olist_order_reviews_dataset.csv",
        "order_id",
        "olist_orders_dataset.csv",
        "order_id",
    ),
    (
        "olist_products_dataset.csv",
        "product_category_name",
        "product_category_name_translation.csv",
        "product_category_name",
    ),
]


def normalize(value):
    """Convert missing values to empty strings and trim whitespace."""
    return value.strip() if value is not None else ""


def read_csv_rows(file_path):
    """Yield CSV records without loading the whole file into memory."""
    with file_path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError(f"Missing CSV headers: {file_path.name}")

        yield from reader


def audit_table(filename, key_columns=None):

    file_path = RAW_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(file_path)

    missing_counts = Counter()
    seen_keys = set()

    total_rows = 0
    null_key_rows = 0
    duplicate_key_rows = 0

    for row in read_csv_rows(file_path):

        total_rows += 1

        # Check missing values in every column.
        for column, value in row.items():
            if normalize(value) == "":
                missing_counts[column] += 1

        # Check candidate-key integrity.
        if key_columns:
            key = tuple(
                normalize(row.get(column))
                for column in key_columns
            )

            if any(value == "" for value in key):
                null_key_rows += 1

            elif key in seen_keys:
                duplicate_key_rows += 1

            else:
                seen_keys.add(key)

    print(f"\nTABLE: {filename}")
    print("=" * 65)
    print(f"Total rows: {total_rows:,}")

    print("\nMISSING VALUES:")

    if missing_counts:
        for column, count in missing_counts.items():
            percentage = count / total_rows * 100

            print(
                f"{column}: {count:,} "
                f"({percentage:.2f}%)"
            )
    else:
        print("No missing values detected.")

    print("\nCANDIDATE KEY CHECK:")

    if key_columns:
        print(f"Key columns: {key_columns}")
        print(f"Rows with missing key: {null_key_rows:,}")
        print(f"Duplicate key occurrences: {duplicate_key_rows:,}")

    else:
        print("No candidate key configured.")


def load_column_values(filename, column):

    values = set()
    file_path = RAW_DIR / filename

    for row in read_csv_rows(file_path):
        value = normalize(row.get(column))

        if value:
            values.add(value)

    return values


def validate_foreign_key(
    child_file,
    child_column,
    parent_file,
    parent_column
):

    parent_values = load_column_values(
        parent_file,
        parent_column
    )

    total_values = 0
    unmatched_values = 0
    sample_unmatched = set()

    for row in read_csv_rows(RAW_DIR / child_file):

        value = normalize(row.get(child_column))

        # Null or blank references are handled separately
        # by the missing-value assessment.
        if not value:
            continue

        total_values += 1

        if value not in parent_values:
            unmatched_values += 1

            if len(sample_unmatched) < 5:
                sample_unmatched.add(value)

    print(
        f"\n{child_file}.{child_column}"
        f" -> {parent_file}.{parent_column}"
    )

    print(f"Non-null references: {total_values:,}")
    print(f"Unmatched references: {unmatched_values:,}")

    if sample_unmatched:
        print(f"Unmatched examples: {sorted(sample_unmatched)}")


def main():

    if not RAW_DIR.exists():
        raise SystemExit("Raw dataset directory not found.")

    print("\nCOMMERCEFLOW — DATA QUALITY REPORT")
    print("=" * 65)

    # 1. Table profiling
    for filename, key_columns in CANDIDATE_KEYS.items():
        audit_table(filename, key_columns)

    # 2. Foreign-key validation
    print("\n\nFOREIGN KEY VALIDATION")
    print("=" * 65)

    for relationship in FOREIGN_KEYS:
        validate_foreign_key(*relationship)

    print("\n\nDATA QUALITY ASSESSMENT COMPLETED.")


if __name__ == "__main__":
    main()
