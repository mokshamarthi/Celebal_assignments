-- ============================================================
-- schema.sql
-- Schema for the E-Commerce Order Analytics System (SQLite)
-- ============================================================

DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id       INTEGER PRIMARY KEY,
    customer_name     TEXT NOT NULL,
    email             TEXT,
    registration_date TEXT NOT NULL,
    customer_type     TEXT CHECK (customer_type IN ('REGULAR', 'PREMIUM', 'VIP'))
);

CREATE TABLE products (
    product_id   INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    category     TEXT NOT NULL,
    subcategory  TEXT,
    cost_price   REAL NOT NULL CHECK (cost_price >= 0)
);

CREATE TABLE orders (
    order_id     INTEGER PRIMARY KEY,
    customer_id  INTEGER,                 -- nullable: some orders have missing customer_id
    order_date   TEXT NOT NULL,
    status       TEXT CHECK (status IN ('PLACED','SHIPPED','DELIVERED','CANCELLED','RETURNED')),
    region_code  TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE order_items (
    item_id           INTEGER PRIMARY KEY,
    order_id          INTEGER NOT NULL,
    product_id        INTEGER NOT NULL,
    quantity          INTEGER NOT NULL,   -- can be negative (return)
    unit_price        REAL NOT NULL CHECK (unit_price >= 0),
    discount_percent  REAL NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_order_date  ON orders(order_date);
CREATE INDEX idx_items_order_id     ON order_items(order_id);
CREATE INDEX idx_items_product_id   ON order_items(product_id);
