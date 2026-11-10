"""Compare obligations with settlements and record breaks.

Both tables are grouped by (counterparty, asset, settlement_date),
then each group is checked:

    settlements but no obligation           -> missing_trade
    2+ settlements for one obligation       -> settled_twice
    1 settlement, wrong amount              -> amount_mismatch
    1 settlement, right amount, too late    -> settled_late
    obligation, no settlement, date passed  -> unsettled_past_due

An obligation of zero needs no settlement. An obligation whose date
hasn't passed yet is pending, not a break.
"""

from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal


def reconcile(conn, as_of=None):
    """Rebuild the breaks table. Returns the number of breaks found.

    as_of is the date to judge "past due" against (default: today).
    """
    as_of = as_of or date.today()
    detected_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    obligations = {
        (cp, asset, day): Decimal(amount)
        for cp, asset, day, amount in conn.execute(
            "SELECT counterparty, asset, settlement_date, net_amount"
            " FROM obligations"
        )
    }

    settlements = defaultdict(list)  # key -> [(id, amount, settled_at), ...]
    for sid, cp, asset, amount, day, settled_at in conn.execute(
        "SELECT settlement_id, counterparty, asset, amount,"
        " settlement_date, settled_at FROM settlements ORDER BY settlement_id"
    ):
        settlements[(cp, asset, day)].append((sid, Decimal(amount), settled_at))

    breaks = []

    def add(break_type, key, expected, actual, settlement_id):
        cp, asset, day = key
        breaks.append((
            break_type, cp, asset, day,
            None if expected is None else str(expected),
            None if actual is None else str(actual),
            settlement_id, detected_at,
        ))

    # Check every settlement group against what was owed.
    for key, rows in sorted(settlements.items()):
        expected = obligations.get(key)

        if expected is None:
            for sid, amount, _ in rows:
                add("missing_trade", key, None, amount, sid)

        elif len(rows) > 1:
            ids = ",".join(sid for sid, _, _ in rows)
            total = sum(amount for _, amount, _ in rows)
            add("settled_twice", key, expected, total, ids)

        else:
            sid, amount, settled_at = rows[0]
            due = date.fromisoformat(key[2])
            if amount != expected:
                add("amount_mismatch", key, expected, amount, sid)
            elif datetime.fromisoformat(settled_at).date() > due:
                add("settled_late", key, expected, amount, sid)

    # Check every obligation that nothing settled.
    for key, expected in sorted(obligations.items()):
        if key in settlements or expected == 0:
            continue
        if date.fromisoformat(key[2]) < as_of:
            add("unsettled_past_due", key, expected, None, None)

    with conn:
        conn.execute("DELETE FROM breaks")
        conn.executemany(
            "INSERT INTO breaks (break_type, counterparty, asset,"
            " settlement_date, expected_amount, actual_amount,"
            " settlement_id, detected_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            breaks,
        )
    return len(breaks)
