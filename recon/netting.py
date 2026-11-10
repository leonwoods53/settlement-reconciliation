"""Net trades into obligations.

Each trade creates four movements, using the sign convention in schema.sql
(positive = counterparty pays or delivers, negative = receives):

    seller  asset     +quantity
    buyer   asset     -quantity
    buyer   currency  +quantity * price
    seller  currency  -quantity * price

These are summed per (counterparty, asset, settlement_date).
"""

from collections import defaultdict
from decimal import Decimal


def net_trades(conn):
    """Rebuild the obligations table from trades. Returns rows written."""
    totals = defaultdict(Decimal)  # missing keys start at Decimal(0)

    rows = conn.execute(
        "SELECT buyer, seller, asset, quantity, price, currency, settlement_date"
        " FROM trades"
    )
    for buyer, seller, asset, quantity, price, currency, day in rows:
        # The maths happens in Python, not SQL: SQLite's SUM would turn
        # the text amounts into floats and lose exactness.
        quantity = Decimal(quantity)
        cash = quantity * Decimal(price)

        totals[(seller, asset, day)] += quantity
        totals[(buyer, asset, day)] -= quantity
        totals[(buyer, currency, day)] += cash
        totals[(seller, currency, day)] -= cash

    # Rows that net to zero are kept: they show the counterparty traded
    # that asset that day but owes nothing.
    with conn:
        conn.execute("DELETE FROM obligations")
        conn.executemany(
            "INSERT INTO obligations"
            " (counterparty, asset, settlement_date, net_amount)"
            " VALUES (?, ?, ?, ?)",
            [(cp, asset, day, str(amount))
             for (cp, asset, day), amount in sorted(totals.items())],
        )
    return len(totals)
