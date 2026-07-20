"""
clean_data.py
-------------
Loads the raw CSVs from data/raw/, cleans them, validates referential
integrity, and writes cleaned CSVs to data/cleaned/. Also saves a
report summarising every issue found and fixed, both as a readable
.txt file and a structured .csv file.

Functions:
    clean_orders(df)               -> fixes date formats, handles NULL customer_ids
    clean_products(df)             -> normalizes product names (trim + title case)
    validate_emails(df)            -> returns list of customer_ids with invalid emails
    check_referential_integrity()  -> finds order_items that reference non-existent orders

Run:
    python clean_data.py
"""

import csv
import os
import re
import pandas as pd

SOURCE_FOLDER = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
DEST_FOLDER = os.path.join(os.path.dirname(__file__), "..", "data", "cleaned")
os.makedirs(DEST_FOLDER, exist_ok=True)

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ----------------------------------------------------------------------
# clean_orders
# ----------------------------------------------------------------------
def clean_orders(source_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Fix order_date formats (accepts both 'YYYY-MM-DD HH:MM:SS' and the
    malformed 'DD-MM-YYYY') and handle NULL / empty customer_id values.

    Returns (fixed_df, tally)
    """
    fixed_df = source_df.copy()
    tally = {"bad_date_format_fixed": 0, "missing_customer_id": 0}

    def normalize_date(raw_value):
        if pd.isna(raw_value) or str(raw_value).strip() == "":
            return pd.NaT
        text = str(raw_value).strip()
        # Try the correct format first
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return pd.to_datetime(text, format=fmt)
            except ValueError:
                pass
        # Fall back to the known "wrong" DD-MM-YYYY format
        try:
            parsed = pd.to_datetime(text, format="%d-%m-%Y")
            tally["bad_date_format_fixed"] += 1
            return parsed
        except ValueError:
            return pd.NaT

    fixed_df["order_date"] = fixed_df["order_date"].apply(normalize_date)

    # Missing / NULL customer_id -> standardize to pandas NA and count
    fixed_df["customer_id"] = fixed_df["customer_id"].replace("", pd.NA)
    tally["missing_customer_id"] = int(fixed_df["customer_id"].isna().sum())

    return fixed_df, tally


# ----------------------------------------------------------------------
# clean_products
# ----------------------------------------------------------------------
def clean_products(source_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Normalize product names: strip whitespace and apply title case.
    Returns (fixed_df, tally)
    """
    fixed_df = source_df.copy()
    original_labels = fixed_df["product_name"].copy()

    fixed_df["product_name"] = (
        fixed_df["product_name"].astype(str).str.strip().str.title()
    )

    changed_count = int((original_labels.astype(str) != fixed_df["product_name"]).sum())
    tally = {"product_names_normalized": changed_count}
    return fixed_df, tally


# ----------------------------------------------------------------------
# validate_emails
# ----------------------------------------------------------------------
def validate_emails(customer_df: pd.DataFrame) -> list:
    """
    Returns a list of customer_ids whose email address is invalid
    (missing '@' or missing a domain / TLD).
    """
    flagged_ids = []
    for _, record in customer_df.iterrows():
        address = str(record.get("email", ""))
        if not EMAIL_PATTERN.match(address):
            flagged_ids.append(record["customer_id"])
    return flagged_ids


# ----------------------------------------------------------------------
# check_referential_integrity
# ----------------------------------------------------------------------
def check_referential_integrity(order_df: pd.DataFrame, line_item_df: pd.DataFrame) -> pd.DataFrame:
    """
    Finds order_items rows whose order_id does not exist in orders.
    Returns the offending rows as a DataFrame.
    """
    known_order_ids = set(order_df["order_id"])
    orphan_mask = ~line_item_df["order_id"].isin(known_order_ids)
    return line_item_df[orphan_mask]


# ----------------------------------------------------------------------
# Main pipeline
# ----------------------------------------------------------------------
def main():
    log_lines = []
    csv_rows = []  # (source_file, issue, count)

    log_lines.append("E-Commerce Data Cleaning Report")
    log_lines.append("=" * 40)

    # Load raw data
    customer_df = pd.read_csv(os.path.join(SOURCE_FOLDER, "customers.csv"), dtype={"customer_id": "Int64"})
    product_df = pd.read_csv(os.path.join(SOURCE_FOLDER, "products.csv"))
    order_df = pd.read_csv(os.path.join(SOURCE_FOLDER, "orders.csv"), dtype={"customer_id": "Int64"})
    line_item_df = pd.read_csv(os.path.join(SOURCE_FOLDER, "order_items.csv"))

    # --- clean orders ---
    fixed_orders, order_tally = clean_orders(order_df)
    log_lines.append("\n[orders.csv]")
    log_lines.append(f"  - Rows with bad DD-MM-YYYY date format fixed: {order_tally['bad_date_format_fixed']}")
    log_lines.append(f"  - Rows with missing/NULL customer_id: {order_tally['missing_customer_id']}")
    csv_rows.append(("orders.csv", "bad_date_format_fixed", order_tally["bad_date_format_fixed"]))
    csv_rows.append(("orders.csv", "missing_customer_id", order_tally["missing_customer_id"]))

    # --- clean products ---
    fixed_products, product_tally = clean_products(product_df)
    log_lines.append("\n[products.csv]")
    log_lines.append(f"  - Product names normalized (trimmed/title-cased): {product_tally['product_names_normalized']}")
    csv_rows.append(("products.csv", "product_names_normalized", product_tally["product_names_normalized"]))

    # --- validate emails ---
    bad_email_ids = validate_emails(customer_df)
    log_lines.append("\n[customers.csv]")
    log_lines.append(f"  - customer_ids with invalid emails: {len(bad_email_ids)}")
    if bad_email_ids:
        preview = bad_email_ids[:10]
        log_lines.append(f"    e.g. {preview}{' ...' if len(bad_email_ids) > 10 else ''}")
    csv_rows.append(("customers.csv", "invalid_email_customer_ids", len(bad_email_ids)))

    # --- referential integrity ---
    orphan_lines = check_referential_integrity(fixed_orders, line_item_df)
    log_lines.append("\n[order_items.csv]")
    log_lines.append(f"  - Rows referencing a non-existent order_id: {len(orphan_lines)}")
    if len(orphan_lines):
        log_lines.append(f"    example order_ids: {sorted(orphan_lines['order_id'].unique().tolist())[:10]}")
    csv_rows.append(("order_items.csv", "orphaned_order_id_rows", len(orphan_lines)))

    # drop the orphaned order_items rows before writing cleaned data
    fixed_line_items = line_item_df[~line_item_df.index.isin(orphan_lines.index)].copy()

    # quantity / discount sanity counts (informational only - kept in data
    # for edge-case testing, just reported here)
    negative_qty_count = int((fixed_line_items["quantity"] < 0).sum())
    zero_qty_count = int((fixed_line_items["quantity"] == 0).sum())
    over_discount_count = int((fixed_line_items["discount_percent"] > 100).sum())
    log_lines.append(f"  - Negative quantity rows (returns): {negative_qty_count}")
    log_lines.append(f"  - Zero quantity rows: {zero_qty_count}")
    log_lines.append(f"  - discount_percent > 100 rows: {over_discount_count}")
    csv_rows.append(("order_items.csv", "negative_quantity_rows", negative_qty_count))
    csv_rows.append(("order_items.csv", "zero_quantity_rows", zero_qty_count))
    csv_rows.append(("order_items.csv", "discount_over_100_rows", over_discount_count))

    # --- write cleaned files ---
    customer_df.to_csv(os.path.join(DEST_FOLDER, "customers_clean.csv"), index=False)
    fixed_products.to_csv(os.path.join(DEST_FOLDER, "products_clean.csv"), index=False)
    fixed_orders.to_csv(os.path.join(DEST_FOLDER, "orders_clean.csv"), index=False)
    fixed_line_items.to_csv(os.path.join(DEST_FOLDER, "order_items_clean.csv"), index=False)

    log_lines.append("\nCleaned files written to data/cleaned/")

    report_text = "\n".join(log_lines)
    print(report_text)

    reports_folder = os.path.join(os.path.dirname(__file__), "..", "output", "sample_reports")
    os.makedirs(reports_folder, exist_ok=True)

    # readable .txt report
    txt_path = os.path.join(reports_folder, "cleaning_report.txt")
    with open(txt_path, "w") as handle:
        handle.write(report_text)

    # structured .csv report
    csv_path = os.path.join(reports_folder, "cleaning_report.csv")
    with open(csv_path, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["source_file", "issue", "count"])
        writer.writerows(csv_rows)

    print(f"\nSaved report -> {txt_path}")
    print(f"Saved report -> {csv_path}")


if __name__ == "__main__":
    main()
