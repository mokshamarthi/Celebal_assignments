"""
report_cli.py
-------------
Command-line reporting tool for the E-Commerce Order Analytics System.

Usage (interactive):
    python report_cli.py

Usage (non-interactive, scriptable):
    python report_cli.py --report revenue --start 2025-01-01 --end 2025-01-31
    python report_cli.py --report top_customers --start 2025-01-01 --end 2025-03-31
    python report_cli.py --report retention

Supported --report values: revenue, top_customers, retention, summary

If --start/--end are omitted, the tool will prompt interactively for
report type (daily/weekly/monthly) and a date range, then print a
summary report:
    - Total orders, revenue, unique customers
    - Top 3 products
    - Comparison with the previous period of equal length (% change)

Every report is also written out as a .csv file under
output/sample_reports/, alongside the console table, so results can be
opened in a spreadsheet or reused elsewhere.

Only the standard library + sqlite3 are used, per the project spec.
"""

import argparse
import csv
import os
import sqlite3
import sys
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
DB_FILE = os.path.join(PROJECT_ROOT, "ecommerce.db")
REPORTS_FOLDER = os.path.join(PROJECT_ROOT, "output", "sample_reports")


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def open_connection():
    if not os.path.exists(DB_FILE):
        print(f"Database not found at {DB_FILE}. Run load_db.py first.")
        sys.exit(1)
    return sqlite3.connect(DB_FILE)


def parse_date(text_value: str) -> datetime:
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text_value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Could not parse date: {text_value}")


def print_table(headers, data_rows):
    if not data_rows:
        print("  (no data for this period)")
        return
    col_widths = [len(str(h)) for h in headers]
    for row in data_rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    header_line = "  ".join(str(h).ljust(col_widths[i]) for i, h in enumerate(headers))
    print(header_line)
    print("-" * len(header_line))
    for row in data_rows:
        print("  ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)))


def save_csv(file_name, headers, data_rows):
    os.makedirs(REPORTS_FOLDER, exist_ok=True)
    dest_path = os.path.join(REPORTS_FOLDER, file_name)
    with open(dest_path, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(data_rows)
    print(f"\nSaved CSV -> {dest_path}")
    return dest_path


# ----------------------------------------------------------------------
# Core report logic
# ----------------------------------------------------------------------
def period_summary(connection, range_start: datetime, range_end: datetime):
    """Returns (order_total, revenue_total, buyer_total, top3_products)."""
    start_text = range_start.strftime("%Y-%m-%d %H:%M:%S")
    end_text = range_end.strftime("%Y-%m-%d %H:%M:%S")

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT COUNT(DISTINCT o.order_id),
               COALESCE(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)), 0),
               COUNT(DISTINCT o.customer_id)
        FROM orders o
        LEFT JOIN order_items oi ON oi.order_id = o.order_id
        WHERE o.order_date BETWEEN ? AND ?
        """,
        (start_text, end_text),
    )
    order_total, revenue_total, buyer_total = cursor.fetchone()

    cursor.execute(
        """
        SELECT p.product_name,
               SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)) AS revenue
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.order_id
        JOIN products p ON p.product_id = oi.product_id
        WHERE o.order_date BETWEEN ? AND ?
        GROUP BY p.product_id, p.product_name
        ORDER BY revenue DESC
        LIMIT 3
        """,
        (start_text, end_text),
    )
    leading_products = cursor.fetchall()

    return order_total, round(revenue_total or 0, 2), buyer_total, leading_products


def pct_change(current_value, previous_value):
    if previous_value in (None, 0):
        return None
    return round((current_value - previous_value) / previous_value * 100, 2)


def run_summary_report(connection, range_start: datetime, range_end: datetime, label: str = "Selected Period"):
    order_total, revenue_total, buyer_total, leading_products = period_summary(connection, range_start, range_end)

    span_length = range_end - range_start
    prior_end = range_start - timedelta(seconds=1)
    prior_start = prior_end - span_length
    prior_orders, prior_revenue, prior_buyers, _ = period_summary(connection, prior_start, prior_end)

    print(f"\n{label}: {range_start.date()} to {range_end.date()}")
    print("=" * 50)
    print(f"Total orders     : {order_total}")
    print(f"Total revenue    : {revenue_total}")
    print(f"Unique customers : {buyer_total}")

    print("\nTop 3 products:")
    print_table(["Product", "Revenue"], [(name, round(rev, 2)) for name, rev in leading_products])

    print(f"\nComparison with previous period ({prior_start.date()} to {prior_end.date()}):")
    comparison_rows = [
        ("Orders", order_total, prior_orders, pct_change(order_total, prior_orders)),
        ("Revenue", revenue_total, prior_revenue, pct_change(revenue_total, prior_revenue)),
        ("Unique customers", buyer_total, prior_buyers, pct_change(buyer_total, prior_buyers)),
    ]
    print_table(["Metric", "Current", "Previous", "% Change"], comparison_rows)

    file_tag = f"summary_{range_start.date()}_{range_end.date()}.csv"
    save_csv(
        file_tag,
        ["metric", "current", "previous", "pct_change"],
        comparison_rows,
    )


def run_top_customers(connection, range_start: datetime, range_end: datetime, cap: int = 10):
    start_text, end_text = range_start.strftime("%Y-%m-%d %H:%M:%S"), range_end.strftime("%Y-%m-%d %H:%M:%S")
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT c.customer_id, c.customer_name,
               ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)), 2) AS lifetime_value
        FROM orders o
        JOIN customers c ON c.customer_id = o.customer_id
        JOIN order_items oi ON oi.order_id = o.order_id
        WHERE o.order_date BETWEEN ? AND ?
        GROUP BY c.customer_id, c.customer_name
        ORDER BY lifetime_value DESC
        LIMIT ?
        """,
        (start_text, end_text, cap),
    )
    ranked_customers = cursor.fetchall()
    print(f"\nTop {cap} customers ({range_start.date()} to {range_end.date()}):")
    print_table(["customer_id", "customer_name", "total_value"], ranked_customers)

    file_tag = f"top_customers_{range_start.date()}_{range_end.date()}.csv"
    save_csv(file_tag, ["customer_id", "customer_name", "total_value"], ranked_customers)


def run_retention_report(connection):
    query_path = os.path.join(PROJECT_ROOT, "sql", "cohort_analysis.sql")
    with open(query_path) as handle:
        query_text = handle.read()
    cursor = connection.cursor()
    cursor.execute(query_text)
    cohort_rows = cursor.fetchall()
    print("\nCohort retention (month 0-3):")
    headers = ["cohort_month", "cohort_size", "month_index", "active_customers", "retention_%"]
    print_table(headers, cohort_rows)

    save_csv("retention_report.csv", headers, cohort_rows)


# ----------------------------------------------------------------------
# Date-range helpers for daily/weekly/monthly report types
# ----------------------------------------------------------------------
def default_range_for_type(cadence: str, anchor_date: datetime):
    if cadence == "daily":
        range_start = datetime(anchor_date.year, anchor_date.month, anchor_date.day)
        range_end = range_start + timedelta(days=1) - timedelta(seconds=1)
    elif cadence == "weekly":
        week_start = anchor_date - timedelta(days=anchor_date.weekday())
        range_start = datetime(week_start.year, week_start.month, week_start.day)
        range_end = range_start + timedelta(days=7) - timedelta(seconds=1)
    elif cadence == "monthly":
        range_start = datetime(anchor_date.year, anchor_date.month, 1)
        if anchor_date.month == 12:
            range_end = datetime(anchor_date.year + 1, 1, 1) - timedelta(seconds=1)
        else:
            range_end = datetime(anchor_date.year, anchor_date.month + 1, 1) - timedelta(seconds=1)
    else:
        raise ValueError("report type must be one of daily/weekly/monthly")
    return range_start, range_end


# ----------------------------------------------------------------------
# CLI entry points
# ----------------------------------------------------------------------
def interactive_mode(connection):
    cadence = ""
    while cadence not in ("daily", "weekly", "monthly"):
        cadence = input("Report type (daily/weekly/monthly): ").strip().lower()

    anchor_text = input("Anchor date for the period (YYYY-MM-DD), or blank for most recent order date: ").strip()
    if anchor_text:
        try:
            anchor_date = parse_date(anchor_text)
        except ValueError as err:
            print(err)
            return
    else:
        cursor = connection.cursor()
        cursor.execute("SELECT MAX(order_date) FROM orders")
        latest_date = cursor.fetchone()[0]
        anchor_date = parse_date(latest_date.split(" ")[0]) if latest_date else datetime.now()

    range_start, range_end = default_range_for_type(cadence, anchor_date)
    run_summary_report(connection, range_start, range_end, label=f"{cadence.capitalize()} Report")


def main():
    parser = argparse.ArgumentParser(description="E-Commerce Order Analytics CLI")
    parser.add_argument(
        "--report",
        choices=["summary", "revenue", "top_customers", "retention"],
        help="Report type to run non-interactively",
    )
    parser.add_argument("--start", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", help="End date YYYY-MM-DD")
    parser.add_argument("--period-type", choices=["daily", "weekly", "monthly"], default="monthly")
    args = parser.parse_args()

    connection = open_connection()

    try:
        if args.report is None:
            interactive_mode(connection)
        elif args.report == "retention":
            run_retention_report(connection)
        elif args.report == "top_customers":
            range_start = parse_date(args.start) if args.start else datetime(2024, 1, 1)
            range_end = parse_date(args.end) if args.end else datetime.now()
            run_top_customers(connection, range_start, range_end)
        else:  # summary or revenue
            if args.start and args.end:
                range_start, range_end = parse_date(args.start), parse_date(args.end)
            else:
                cursor = connection.cursor()
                cursor.execute("SELECT MAX(order_date) FROM orders")
                latest_date = cursor.fetchone()[0]
                anchor_date = parse_date(latest_date.split(" ")[0]) if latest_date else datetime.now()
                range_start, range_end = default_range_for_type(args.period_type, anchor_date)
            run_summary_report(connection, range_start, range_end)
    finally:
        connection.close()


if __name__ == "__main__":
    main()
