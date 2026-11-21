
import csv
from pathlib import Path


# Locate the project directory
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Locate the raw dataset folder
RAW_DIR = PROJECT_ROOT / "data" / "raw"


def inspect_csv(file_path):
    """Return the headers and total records of a CSV file."""

    with file_path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        columns = reader.fieldnames or []
        row_count = sum(1 for _ in reader)

    return columns, row_count


def main():

    if not RAW_DIR.exists():
        raise SystemExit(f"Dataset directory not found: {RAW_DIR}")

    csv_files = sorted(RAW_DIR.glob("*.csv"))

    if not csv_files:
        raise SystemExit("No CSV files found in data/raw/")

    print("\nCOMMERCEFLOW — SOURCE INVENTORY")
    print("=" * 65)

    for file_path in csv_files:

        columns, row_count = inspect_csv(file_path)

        print(f"\nFile: {file_path.name}")
        print(f"Rows: {row_count:,}")
        print(f"Columns ({len(columns)}):")

        for column in columns:
            print(f"  - {column}")

        print("-" * 65)


if __name__ == "__main__":
    main()
