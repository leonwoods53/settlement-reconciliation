"""Create the database and load CSV files into it.

Usage:
    python -m recon.load data/trades.csv data/settlements.csv
"""

import csv
import sqlite3
import sys
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

SCHEMA = Path(__file__).parent.parent / "schema.sql"
DEFAULT_DB = "recon.db"

TRADE_COLUMNS = [
    "client_trade_id", "buyer", "seller", "asset", "quantity",
    "price", "currency", "traded_at", "settlement_date",
]
SETTLEMENT_COLUMNS = [
    "settlement_id", "counterparty", "asset", "amount",
    "settlement_date", "settled_at",
]


class LoadError(Exception):
    """A row in a CSV file is invalid. Nothing from the file is loaded."""


def connect(db_path=DEFAULT_DB):
    """Open the database and create the tables if they don't exist."""
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA.read_text())
    return conn


def check_decimal(value, field, positive=True):
    """Return value as a Decimal, or raise if it isn't a valid number."""
    try:
        number = Decimal(value)
    except InvalidOperation:
        raise ValueError(f"{field} is not a number: {value!r}")
    if not number.is_finite():
        raise ValueError(f"{field} is not a number: {value!r}")
    if positive and number <= 0:
        raise ValueError(f"{field} must be greater than 0: {value!r}")
    return number


def check_timestamp(value, field):
    try:
        datetime.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{field} is not an ISO timestamp: {value!r}")


def check_date(value, field):
    try:
        date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{field} is not a date (YYYY-MM-DD): {value!r}")


def check_trade(row):
    check_decimal(row["quantity"], "quantity")
    check_decimal(row["price"], "price")
    check_timestamp(row["traded_at"], "traded_at")
    check_date(row["settlement_date"], "settlement_date")


def check_settlement(row):
    # Signed: negative means the counterparty received it.
    check_decimal(row["amount"], "amount", positive=False)
    check_date(row["settlement_date"], "settlement_date")
    check_timestamp(row["settled_at"], "settled_at")


def load_csv(conn, csv_path, table, columns, check_row):
    """Load every row of a CSV into a table, or none if any row is bad.

    Returns the number of rows loaded.
    """
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        missing = set(columns) - set(reader.fieldnames or [])
        if missing:
            raise LoadError(f"{csv_path}: missing columns {sorted(missing)}")

        placeholders = ", ".join("?" for _ in columns)
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"

        count = 0
        # `with conn` is one transaction: it commits if the block
        # finishes, and rolls back everything if an error is raised.
        with conn:
            # Line 1 is the header, so data starts on line 2.
            for line, row in enumerate(reader, start=2):
                try:
                    for col in columns:
                        if not (row[col] or "").strip():
                            raise ValueError(f"{col} is empty")
                    check_row(row)
                    conn.execute(sql, [row[col].strip() for col in columns])
                except (ValueError, sqlite3.IntegrityError) as e:
                    raise LoadError(f"{csv_path} line {line}: {e}") from e
                count += 1
    return count


def load_trades(conn, csv_path):
    return load_csv(conn, csv_path, "trades", TRADE_COLUMNS, check_trade)


def load_settlements(conn, csv_path):
    return load_csv(
        conn, csv_path, "settlements", SETTLEMENT_COLUMNS, check_settlement
    )


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 1
    trades_csv, settlements_csv = argv
    # Start fresh each run, so loading the same files twice
    # doesn't fail on duplicate ids.
    Path(DEFAULT_DB).unlink(missing_ok=True)
    conn = connect()
    try:
        print(f"Loaded {load_trades(conn, trades_csv)} trades")
        print(f"Loaded {load_settlements(conn, settlements_csv)} settlements")
    except LoadError as e:
        print(f"Error: {e}")
        return 1
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
