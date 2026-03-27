"""Load Open Food Facts France CSV export into BigQuery products_selected."""
import csv
import gzip
import os
import sys
from datetime import datetime, timezone
from google.cloud import bigquery

CSV_PATH = os.environ.get("OFF_CSV_PATH", r"C:\Users\QURISK\AppData\Local\Temp\off_fr.csv.gz")
PROJECT_ID = "prisme-wamba-2026"
DATASET = "prisme_dataset"
TABLE = "products_selected"
TARGET = 10_000


def parse_row(row: dict) -> dict | None:
    code = (row.get("code") or "").strip()
    product_name = (row.get("product_name") or "").strip()
    image_url = (row.get("image_url") or row.get("image_front_url") or "").strip()

    if not code or not product_name or not image_url:
        return None
    if not image_url.startswith("http"):
        return None

    last_modified = None
    ts = row.get("last_modified_t")
    if ts:
        try:
            last_modified = datetime.utcfromtimestamp(int(ts)).isoformat() + "Z"
        except (ValueError, OSError):
            pass

    return {
        "ean": code[:50],
        "product_name": product_name[:500],
        "brands": (row.get("brands") or "")[:200],
        "categories": (row.get("categories") or "")[:500],
        "ingredients_text": (row.get("ingredients_text") or "")[:2000],
        "nutriscore_grade": (row.get("nutriscore_grade") or "")[:1] or None,
        "quantity": (row.get("quantity") or "")[:100],
        "packaging": (row.get("packaging") or "")[:200],
        "image_url": image_url[:1000],
        "image_small_url": (row.get("image_small_url") or "")[:1000] or None,
        "country_code": "FR",
        "last_modified_t": last_modified,
        "ingestion_timestamp": datetime.now(timezone.utc).isoformat(),
    }


def main():
    client = bigquery.Client(project=PROJECT_ID)
    table_id = f"{PROJECT_ID}.{DATASET}.{TABLE}"

    # Check if already loaded
    result = client.query(f"SELECT COUNT(*) AS n FROM `{table_id}`").result()
    existing = next(iter(result))["n"]
    if existing > 0:
        print(f"Already {existing} products in BQ. Delete and rerun to reload.")
        sys.exit(0)

    print(f"Reading {CSV_PATH}...")
    products = []
    seen = set()

    with gzip.open(CSV_PATH, "rt", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for i, row in enumerate(reader):
            if len(products) >= TARGET:
                break
            parsed = parse_row(row)
            if parsed and parsed["ean"] not in seen:
                seen.add(parsed["ean"])
                products.append(parsed)
            if (i + 1) % 10000 == 0:
                print(f"  Scanned {i+1} rows, collected {len(products)}")

    print(f"Parsed {len(products)} valid products. Loading to BigQuery...")

    chunk_size = 500
    for i in range(0, len(products), chunk_size):
        chunk = products[i:i + chunk_size]
        errors = client.insert_rows_json(table_id, chunk)
        if errors:
            print(f"BQ errors at row {i}: {errors[:2]}")
        else:
            print(f"  Loaded rows {i} to {min(i + chunk_size, len(products))}")

    print(f"Done: {len(products)} products loaded.")


if __name__ == "__main__":
    main()
