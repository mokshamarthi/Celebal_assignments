"""
load_db.py
----------
Creates the SQLite database (ecommerce.db) from sql/schema.sql and loads
the cleaned CSV files from data/cleaned/ into it. Prints row counts so
you can verify the load matches the CSVs (and that referential
integrity holds, since order_items with orphaned order_ids were
dropped during cleaning).

Run:
    python load_db.py
"""

import os
import sqlite3
import pandas as pd

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
CLEANED_FOLDER = os.path.join(PROJECT_ROOT, "data", "cleaned")
SCHEMA_FILE = os.path.join(PROJECT_ROOT, "sql", "schema.sql")
DB_FILE = os.path.join(PROJECT_ROOT, "ecommerce.db")


def build_database():
    # start fresh each time
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

    connection = sqlite3.connect(DB_FILE)
    with open(SCHEMA_FILE) as schema_handle:
        connection.executescript(schema_handle.read())

    customer_table = pd.read_csv(os.path.join(CLEANED_FOLDER, "customers_clean.csv"))
    product_table = pd.read_csv(os.path.join(CLEANED_FOLDER, "products_clean.csv"))
    order_table = pd.read_csv(os.path.join(CLEANED_FOLDER, "orders_clean.csv"))
    line_item_table = pd.read_csv(os.path.join(CLEANED_FOLDER, "order_items_clean.csv"))

    customer_table.to_sql("customers", connection, if_exists="append", index=False)
    product_table.to_sql("products", connection, if_exists="append", index=False)
    order_table.to_sql("orders", connection, if_exists="append", index=False)
    line_item_table.to_sql("order_items", connection, if_exists="append", index=False)

    connection.commit()

    for table_name in ["customers", "products", "orders", "order_items"]:
        row_total = connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"{table_name}: {row_total} rows loaded")

    connection.close()
    print(f"\nDatabase built at {DB_FILE}")


if __name__ == "__main__":
    build_database()
