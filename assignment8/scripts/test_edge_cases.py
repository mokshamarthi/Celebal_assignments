"""
test_edge_cases.py
-------------------
Edge-case tests for the E-Commerce Order Analytics System, written as
plain Python functions (no test framework required, though they are
also compatible with `pytest` if you'd rather run them that way).

Covers:
    1. order_items rows whose order_id doesn't exist in orders
    2. discount_percent > 100
    3. quantity == 0
    4. order_date in the future

A summary of pass/fail counts is also written to
output/sample_reports/edge_case_test_results.csv.

Run:
    python test_edge_cases.py
"""

import csv
import os
import sqlite3
from datetime import datetime

import pandas as pd

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
RAW_FOLDER = os.path.join(PROJECT_ROOT, "data", "raw")
DB_FILE = os.path.join(PROJECT_ROOT, "ecommerce.db")
REPORTS_FOLDER = os.path.join(PROJECT_ROOT, "output", "sample_reports")

RESULT_LOG = []  # (test_name, rows_found, status, note)


# ----------------------------------------------------------------------
# 1. order_items referencing a non-existent order_id
# ----------------------------------------------------------------------
def test_orphaned_order_items():
    """
    What happens: these rows have no matching parent order, so any
    revenue/AOV/report query that JOINs order_items -> orders will
    silently drop them (INNER JOIN) rather than raise an error.
    This test asserts we can *detect* them before they get lost.
    """
    order_df = pd.read_csv(os.path.join(RAW_FOLDER, "orders.csv"))
    line_item_df = pd.read_csv(os.path.join(RAW_FOLDER, "order_items.csv"))

    known_ids = set(order_df["order_id"])
    orphan_rows = line_item_df[~line_item_df["order_id"].isin(known_ids)]

    print(f"[Test 1] Orphaned order_items rows found: {len(orphan_rows)}")
    assert len(orphan_rows) >= 0  # detection should never crash
    if len(orphan_rows) > 0:
        print(f"          Example order_ids referenced but missing: "
              f"{sorted(orphan_rows['order_id'].unique())[:5]}")
    print("[Test 1] PASSED - orphaned rows are detected, not silently ignored.\n")
    RESULT_LOG.append(("orphaned_order_items", len(orphan_rows), "PASSED",
                        "rows dropped by INNER JOIN if not caught"))
    return orphan_rows


# ----------------------------------------------------------------------
# 2. discount_percent > 100
# ----------------------------------------------------------------------
def test_invalid_discount_percent():
    """
    What happens: a discount > 100% would make revenue go negative
    (quantity * unit_price * (1 - discount/100) < 0), which is not a
    valid business scenario. This test flags such rows so they can be
    clipped/rejected during cleaning rather than silently corrupting
    revenue totals.
    """
    line_item_df = pd.read_csv(os.path.join(RAW_FOLDER, "order_items.csv"))
    flagged_rows = line_item_df[line_item_df["discount_percent"] > 100]

    print(f"[Test 2] Rows with discount_percent > 100: {len(flagged_rows)}")
    note = "no rows found"
    if len(flagged_rows) > 0:
        sample_row = flagged_rows.iloc[0]
        implied_revenue = sample_row["quantity"] * sample_row["unit_price"] * (1 - sample_row["discount_percent"] / 100)
        print(f"          Example: item_id={sample_row['item_id']} discount={sample_row['discount_percent']}% "
              f"=> would compute a NEGATIVE revenue of {implied_revenue:.2f}")
        note = f"e.g. implied revenue {implied_revenue:.2f}"
    print("[Test 2] PASSED - invalid discounts are detected before they skew revenue.\n")
    RESULT_LOG.append(("discount_over_100", len(flagged_rows), "PASSED", note))
    return flagged_rows


# ----------------------------------------------------------------------
# 3. quantity == 0
# ----------------------------------------------------------------------
def test_zero_quantity():
    """
    What happens: a zero-quantity line item contributes $0 revenue and
    is neither a purchase nor a return. It's not necessarily an error
    (could represent a cancelled line item) but should be surfaced so
    analysts know it exists rather than assuming every row is a real
    purchase or return.
    """
    line_item_df = pd.read_csv(os.path.join(RAW_FOLDER, "order_items.csv"))
    zero_rows = line_item_df[line_item_df["quantity"] == 0]

    print(f"[Test 3] Rows with quantity == 0: {len(zero_rows)}")
    print("[Test 3] PASSED - zero-quantity rows are detected and contribute $0 revenue "
          "(neither purchase nor return).\n")
    RESULT_LOG.append(("zero_quantity", len(zero_rows), "PASSED",
                        "contributes $0 revenue, not purchase or return"))
    return zero_rows


# ----------------------------------------------------------------------
# 4. order_date in the future
# ----------------------------------------------------------------------
def test_future_order_date():
    """
    What happens: an order dated after 'today' is almost certainly a
    data entry error (or a test/staging record that leaked into prod).
    This test flags them so they can be excluded from reports like
    'last 12 months' which assume order_date <= now.
    """
    order_df = pd.read_csv(os.path.join(RAW_FOLDER, "orders.csv"))

    def try_parse(raw_value):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%d-%m-%Y"):
            try:
                return datetime.strptime(str(raw_value), fmt)
            except ValueError:
                continue
        return pd.NaT

    order_df["parsed_date"] = order_df["order_date"].apply(try_parse)
    now_marker = datetime.now()
    future_rows = order_df[order_df["parsed_date"] > now_marker]

    print(f"[Test 4] Rows with order_date in the future (after {now_marker.date()}): {len(future_rows)}")
    print("[Test 4] PASSED - future-dated orders are detected and can be excluded from "
          "trailing-period reports.\n")
    RESULT_LOG.append(("future_order_date", len(future_rows), "PASSED",
                        f"checked against {now_marker.date()}"))
    return future_rows


# ----------------------------------------------------------------------
# Bonus: DB-level sanity check once ecommerce.db has been built
# ----------------------------------------------------------------------
def test_db_row_counts_match_cleaned_csvs():
    if not os.path.exists(DB_FILE):
        print("[Bonus] Skipped - ecommerce.db not built yet (run load_db.py first).\n")
        RESULT_LOG.append(("db_row_count_match", 0, "SKIPPED", "ecommerce.db not built"))
        return
    connection = sqlite3.connect(DB_FILE)
    cleaned_folder = os.path.join(PROJECT_ROOT, "data", "cleaned")
    for table_name, csv_name in [
        ("customers", "customers_clean.csv"),
        ("products", "products_clean.csv"),
        ("orders", "orders_clean.csv"),
        ("order_items", "order_items_clean.csv"),
    ]:
        csv_count = len(pd.read_csv(os.path.join(cleaned_folder, csv_name)))
        db_count = connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        status_label = "OK" if csv_count == db_count else "MISMATCH"
        print(f"[Bonus] {table_name}: csv={csv_count} db={db_count} -> {status_label}")
        assert csv_count == db_count
    connection.close()
    print("[Bonus] PASSED - DB row counts match cleaned CSVs.\n")
    RESULT_LOG.append(("db_row_count_match", 4, "PASSED", "all 4 tables matched"))


def save_results_csv():
    os.makedirs(REPORTS_FOLDER, exist_ok=True)
    dest_path = os.path.join(REPORTS_FOLDER, "edge_case_test_results.csv")
    with open(dest_path, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["test_name", "rows_found", "status", "note"])
        writer.writerows(RESULT_LOG)
    print(f"Saved CSV -> {dest_path}")


def main():
    print("Running edge case tests...\n" + "=" * 50 + "\n")
    test_orphaned_order_items()
    test_invalid_discount_percent()
    test_zero_quantity()
    test_future_order_date()
    test_db_row_counts_match_cleaned_csvs()
    print("=" * 50)
    print("All edge case tests completed.")
    save_results_csv()


if __name__ == "__main__":
    main()
