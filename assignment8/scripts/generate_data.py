"""
generate_data.py
-----------------
Builds 4 raw CSV files for the E-Commerce Order Analytics System:
    - customers.csv
    - products.csv
    - orders.csv
    - order_items.csv

Deliberate data-quality problems are seeded in so the cleaning stage
(clean_data.py) has real work to do:
    - ~5% of orders carry a blank/NULL customer_id
    - ~3% of order_items carry a negative quantity (returns)
    - Some order_date values are stored as DD-MM-YYYY instead of
      YYYY-MM-DD HH:MM:SS
    - Some product names carry stray whitespace / inconsistent casing
    - ~2% of customer emails are malformed (no '@' or no domain)
    - A small slice of order_items point at an order_id that was never
      created, to exercise referential-integrity checks downstream.

Run:
    python generate_data.py
"""

import csv
import os
import random
from datetime import datetime, timedelta

from faker import Faker

fake_data = Faker()
Faker.seed(42)
random.seed(42)

# ----------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------
CUSTOMER_COUNT = 500
PRODUCT_COUNT = 500
ORDER_COUNT = 500
# order_items is intentionally larger than orders since a single order
# can contain several line items
ORDER_LINE_COUNT = 1500

DEST_FOLDER = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
os.makedirs(DEST_FOLDER, exist_ok=True)

CATEGORY_MAP = {
    "Electronics": ["Phones", "Laptops", "Accessories", "Cameras"],
    "Clothing": ["Men", "Women", "Kids", "Footwear"],
    "Home": ["Kitchen", "Furniture", "Decor", "Garden"],
    "Books": ["Fiction", "Non-Fiction", "Comics", "Education"],
}

ACCOUNT_TIERS = ["REGULAR", "PREMIUM", "VIP"]
FULFILLMENT_STATES = ["PLACED", "SHIPPED", "DELIVERED", "CANCELLED", "RETURNED"]
# weighted so DELIVERED is the most common outcome
STATE_WEIGHTS = [0.15, 0.15, 0.50, 0.10, 0.10]

RANGE_START = datetime(2024, 1, 1)
RANGE_END = datetime(2026, 7, 19)  # "today" for this project


def pick_random_datetime(earliest: datetime, latest: datetime) -> datetime:
    span = latest - earliest
    offset_seconds = random.randint(0, int(span.total_seconds()))
    return earliest + timedelta(seconds=offset_seconds)


def scramble_product_label(label: str) -> str:
    """Randomly mangle a product name's spacing/casing."""
    roll = random.random()
    if roll < 0.10:
        return f"  {label.upper()}  "
    elif roll < 0.20:
        return label.lower()
    elif roll < 0.28:
        return f" {label}"
    return label


def build_customer_email(full_name: str, seq: int) -> str:
    """Return a mostly-valid, sometimes-broken email address."""
    handle = f"{full_name.lower().replace(' ', '.')}{seq}"
    if random.random() < 0.02:  # 2% invalid emails
        flaw = random.choice(["no_at", "no_domain"])
        if flaw == "no_at":
            return f"{handle}example.com"
        else:
            return f"{handle}@"
    return f"{handle}@{fake_data.free_email_domain()}"


# ----------------------------------------------------------------------
# 1. customers.csv
# ----------------------------------------------------------------------
def build_customer_records():
    records = []
    for seq in range(1, CUSTOMER_COUNT + 1):
        full_name = fake_data.name()
        signup_dt = pick_random_datetime(RANGE_START, RANGE_END)
        records.append(
            {
                "customer_id": seq,
                "customer_name": full_name,
                "email": build_customer_email(full_name, seq),
                "registration_date": signup_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "customer_type": random.choices(
                    ACCOUNT_TIERS, weights=[0.6, 0.3, 0.1]
                )[0],
            }
        )

    dest_path = os.path.join(DEST_FOLDER, "customers.csv")
    with open(dest_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "customer_id",
                "customer_name",
                "email",
                "registration_date",
                "customer_type",
            ],
        )
        writer.writeheader()
        writer.writerows(records)

    print(f"Wrote {len(records)} rows -> {dest_path}")
    return records


# ----------------------------------------------------------------------
# 2. products.csv
# ----------------------------------------------------------------------
def build_product_records():
    records = []
    for seq in range(1, PRODUCT_COUNT + 1):
        category = random.choice(list(CATEGORY_MAP.keys()))
        subcategory = random.choice(CATEGORY_MAP[category])
        base_label = f"{fake_data.word().capitalize()} {subcategory[:-1] if subcategory.endswith('s') else subcategory}"
        records.append(
            {
                "product_id": seq,
                "product_name": scramble_product_label(base_label),
                "category": category,
                "subcategory": subcategory,
                "cost_price": round(random.uniform(5, 500), 2),
            }
        )

    dest_path = os.path.join(DEST_FOLDER, "products.csv")
    with open(dest_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "product_id",
                "product_name",
                "category",
                "subcategory",
                "cost_price",
            ],
        )
        writer.writeheader()
        writer.writerows(records)

    print(f"Wrote {len(records)} rows -> {dest_path}")
    return records


# ----------------------------------------------------------------------
# 3. orders.csv
# ----------------------------------------------------------------------
def build_order_records(customer_records):
    known_customer_ids = [row["customer_id"] for row in customer_records]
    records = []
    for seq in range(1, ORDER_COUNT + 1):
        placed_at = pick_random_datetime(RANGE_START, RANGE_END)

        # ~5% missing customer_id
        if random.random() < 0.05:
            buyer_id = ""  # empty -> treated as NULL
        else:
            buyer_id = random.choice(known_customer_ids)

        # some order dates written in wrong format DD-MM-YYYY (no time)
        if random.random() < 0.08:
            date_text = placed_at.strftime("%d-%m-%Y")
        else:
            date_text = placed_at.strftime("%Y-%m-%d %H:%M:%S")

        records.append(
            {
                "order_id": seq,
                "customer_id": buyer_id,
                "order_date": date_text,
                "status": random.choices(FULFILLMENT_STATES, weights=STATE_WEIGHTS)[0],
                "region_code": random.choice(["N", "S", "E", "W", "C"]),
            }
        )

    dest_path = os.path.join(DEST_FOLDER, "orders.csv")
    with open(dest_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["order_id", "customer_id", "order_date", "status", "region_code"],
        )
        writer.writeheader()
        writer.writerows(records)

    print(f"Wrote {len(records)} rows -> {dest_path}")
    return records


# ----------------------------------------------------------------------
# 4. order_items.csv
# ----------------------------------------------------------------------
def build_order_line_records(order_records, product_records):
    known_order_ids = [row["order_id"] for row in order_records]
    known_product_ids = [row["product_id"] for row in product_records]
    cost_lookup = {row["product_id"]: row["cost_price"] for row in product_records}

    records = []
    for seq in range(1, ORDER_LINE_COUNT + 1):
        # ~99% reference a real order, ~1% intentionally broken (referential
        # integrity issue) so check_referential_integrity() has something
        # to find
        if random.random() < 0.01:
            linked_order_id = max(known_order_ids) + random.randint(1, 50)
        else:
            linked_order_id = random.choice(known_order_ids)

        linked_product_id = random.choice(known_product_ids)
        line_price = round(cost_lookup[linked_product_id] * random.uniform(1.2, 2.5), 2)

        # 3% negative quantity == returns
        if random.random() < 0.03:
            unit_count = -random.randint(1, 5)
        else:
            unit_count = random.randint(1, 5)
            # small chance of a zero-quantity edge case row
            if random.random() < 0.005:
                unit_count = 0

        discount_pct = random.choice([0, 0, 0, 5, 10, 15, 20, 25, 30])
        # tiny chance of an out-of-range discount to exercise edge-case tests
        if random.random() < 0.003:
            discount_pct = random.choice([105, 150])

        records.append(
            {
                "item_id": seq,
                "order_id": linked_order_id,
                "product_id": linked_product_id,
                "quantity": unit_count,
                "unit_price": line_price,
                "discount_percent": discount_pct,
            }
        )

    dest_path = os.path.join(DEST_FOLDER, "order_items.csv")
    with open(dest_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "item_id",
                "order_id",
                "product_id",
                "quantity",
                "unit_price",
                "discount_percent",
            ],
        )
        writer.writeheader()
        writer.writerows(records)

    print(f"Wrote {len(records)} rows -> {dest_path}")
    return records


def main():
    print("Generating raw datasets with intentional data-quality issues...")
    customer_records = build_customer_records()
    product_records = build_product_records()
    order_records = build_order_records(customer_records)
    build_order_line_records(order_records, product_records)
    print("Done. Raw files are in data/raw/")


if __name__ == "__main__":
    main()
