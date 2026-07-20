# E-Commerce Order Analytics System

An end-to-end analytics pipeline that generates messy e-commerce data,
cleans it, loads it into SQLite, and answers business questions with
SQL (joins, aggregations, window functions, CTEs) plus a command-line
reporting tool.

## Architecture

```
raw CSVs  --generate_data.py-->  data/raw/
data/raw/ --clean_data.py------>  data/cleaned/  (+ cleaning report)
data/cleaned/ --load_db.py----->  ecommerce.db (SQLite)
ecommerce.db --sql/*.sql-------->  analytics answers
ecommerce.db --report_cli.py---->  ad-hoc summary / top-customer / retention reports
```

Everything runs locally — no external services required, just Python
3.10+ and the `pandas` / `faker` packages for the generation & cleaning
steps (the CLI tool itself only uses the standard library + `sqlite3`,
per the project spec).

## Folder structure

```
ecommerce-analytics-system/
├── data/
│   ├── raw/                  # generated, messy CSVs
│   └── cleaned/               # cleaned CSVs, ready to load
├── scripts/
│   ├── generate_data.py       # Part 1: data generation
│   ├── clean_data.py          # Part 2: cleaning + validation report
│   ├── load_db.py             # loads cleaned CSVs into SQLite
│   ├── report_cli.py          # Part 4: CLI reporting tool
│   └── test_edge_cases.py     # Part 5: edge case tests
├── sql/
│   ├── schema.sql              # table definitions + constraints + indexes
│   ├── aggregations.sql        # basic + intermediate queries (Q1-Q6)
│   ├── window_functions.sql    # advanced queries (Q7-Q14, Q16)
│   └── cohort_analysis.sql     # Q15: cohort/retention analysis
├── output/
│   └── sample_reports/         # example output from a real run
├── ecommerce.db                 # generated SQLite database (after load_db.py)
└── README.md
```

## How to run

```bash
cd scripts

# 1. Generate 4 raw CSVs (500+ rows each) with intentional data issues
python generate_data.py

# 2. Clean the data, validate it, write cleaned CSVs + a text report
python clean_data.py

# 3. Build ecommerce.db and load the cleaned CSVs into it
python load_db.py

# 4. Run the SQL analysis files directly against the DB, e.g.:
sqlite3 ../ecommerce.db < ../sql/aggregations.sql
sqlite3 ../ecommerce.db < ../sql/window_functions.sql
sqlite3 ../ecommerce.db < ../sql/cohort_analysis.sql

# 5. Use the CLI reporting tool
python report_cli.py                         # interactive mode
python report_cli.py --report summary --start 2025-01-01 --end 2025-03-31
python report_cli.py --report top_customers --start 2024-01-01 --end 2026-07-19
python report_cli.py --report retention

# 6. Run the edge-case tests
python test_edge_cases.py
```

## Data model

| Table | Key columns |
|---|---|
| `customers` | `customer_id` (PK), `customer_name`, `email`, `registration_date`, `customer_type` |
| `products` | `product_id` (PK), `product_name`, `category`, `subcategory`, `cost_price` |
| `orders` | `order_id` (PK), `customer_id` (FK, nullable), `order_date`, `status`, `region_code` |
| `order_items` | `item_id` (PK), `order_id` (FK), `product_id` (FK), `quantity`, `unit_price`, `discount_percent` |

`revenue = quantity × unit_price × (1 − discount_percent / 100)` is the
formula used consistently across every query.

## Intentional data quality issues (and how they're handled)

| Issue | Where | Handling |
|---|---|---|
| 5% of orders missing `customer_id` | `generate_data.py` | Kept as NULL in `orders`; queries that need a customer (e.g. top customers) naturally exclude them via `INNER JOIN` |
| 3% of `order_items` with negative quantity | `generate_data.py` | Treated as returns; used directly in return-rate queries (Q5, Q6) |
| Some `order_date` in `DD-MM-YYYY` format | `generate_data.py` | `clean_orders()` detects and reparses into the standard format |
| Messy product names (spacing/casing) | `generate_data.py` | `clean_products()` trims whitespace and applies title case |
| 2% invalid emails | `generate_data.py` | `validate_emails()` returns the offending `customer_id`s (kept in data, not silently dropped, so the business can follow up) |
| `order_items` referencing a non-existent `order_id` | `generate_data.py` (~1% of rows) | `check_referential_integrity()` finds them; `clean_data.py` drops them before loading into SQLite so foreign keys stay valid |
| `discount_percent` > 100, `quantity` == 0, future `order_date` | `generate_data.py` (rare, for edge-case testing) | Covered by `test_edge_cases.py`, which documents the effect of each and confirms it's detectable rather than silently corrupting reports |

## SQL query index

**Basic** — `sql/aggregations.sql`
1. Total revenue per category
2. Top 10 customers by total order value
3. Month-wise order count for the last 12 months

**Intermediate** — `sql/aggregations.sql`
4. Customers who placed orders but never had anything delivered
5. Products with more returns than purchases
6. Return rate per category

**Advanced** — `sql/window_functions.sql` + `sql/cohort_analysis.sql`
7. Running total of revenue per region (`SUM() OVER`)
8. Product ranking per category (`DENSE_RANK()`)
9. Days between consecutive orders per customer (`LAG()`), flags "At Risk" customers
10. Multi-level CTE: monthly revenue per customer → High/Medium/Low → counts per month
11. Customer quartiles by lifetime value (`NTILE(4)`)
12. Year-over-year monthly revenue comparison
13. First vs. most recent purchased category per customer (`FIRST_VALUE`/`LAST_VALUE`)
14. Cumulative revenue distribution (% of revenue from top customers)
15. Cohort retention analysis by registration month (`sql/cohort_analysis.sql`)
16. Frequently-bought-together product pairs (self-join, deduplicated A<B)

## CLI reporting tool

`scripts/report_cli.py` supports both an interactive mode (prompts for
report type and a date) and flags for scripting:

```
--report {summary,revenue,top_customers,retention}
--start YYYY-MM-DD
--end YYYY-MM-DD
--period-type {daily,weekly,monthly}   # used when --start/--end omitted
```

The `summary`/`revenue` report prints total orders, revenue, unique
customers, the top 3 products, and a % change comparison against the
immediately preceding period of equal length.

## Sample output

See `output/sample_reports/` for real output from a full run. Every
report is saved as both a readable console/`.txt` capture and a
structured `.csv` file (so results can be opened directly in a
spreadsheet):
- `cleaning_report.txt` / `cleaning_report.csv` — issues found/fixed during Part 2
- `summary_report_console.txt` / `summary_<start>_<end>.csv` — CLI summary report example
- `top_customers_console.txt` / `top_customers_<start>_<end>.csv` — CLI top-customers example
- `retention_console.txt` / `retention_report.csv` — CLI cohort retention example
- `edge_case_test_results.csv` — Part 5 test output (pass/fail + row counts per test)

## Edge cases covered (`scripts/test_edge_cases.py`)

1. `order_items` referencing a non-existent `order_id` → detected before it silently disappears via `INNER JOIN`
2. `discount_percent` > 100 → would produce negative revenue; flagged before it skews totals
3. `quantity == 0` → contributes $0 revenue, neither a purchase nor a return; surfaced rather than assumed
4. `order_date` in the future → flagged so trailing-period reports (e.g. "last 12 months") aren't polluted
5. Bonus: DB row counts are checked against the cleaned CSVs after `load_db.py`, to confirm the load (and referential-integrity drop) was applied consistently
