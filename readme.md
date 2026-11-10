# Settlement Reconciliation Tool

A small Python and SQL tool that checks whether executed trades actually settled, and reports the ones that didn't.

> **Status:** in progress. Sections marked _TODO_ will be filled in as the project is built.

## What it does

1. Loads a CSV of executed trades into a SQLite database.
2. Nets each counterparty's obligations per asset per settlement window, so you can see what each party owes and is owed.
3. Loads a second CSV of what actually settled.
4. Reconciles the two and records every mismatch ("break") in a `breaks` table.
5. Writes a short report summarising the breaks.

Everything runs with one command.

## Why I built it

When a trade is executed, both sides still have to deliver: one side the asset, the other the cash. Settlement is the step where that happens, and reconciliation checks that it happened correctly. Breaks that go unnoticed turn into real losses.

I based this on the post-trade settlement model in the [zerohash API docs](https://docs.zerohash.com). There, `POST /trades` submits a trade for settlement, and `GET /trades/{trade_id}` returns its `trade_state` along with each party's `settlement_state` (for example `obligations_outstanding`, `settled` or `defaulted`). This project is a simplified offline version of that idea. It does not call the zerohash API.

## Break types

| Break | Meaning |
|---|---|
| Missing trade | A settlement arrived, but no trade created an obligation for it |
| Amount mismatch | The settled amount is different from the net amount owed |
| Unsettled past due | Something is owed, nothing has settled, and the settlement date has passed |
| Settled twice | Two or more settlements arrived for the same obligation |
| Settled late | The amount is right, but it settled after the settlement date |

Settlements are matched against netted totals per counterparty, asset and settlement date, not against individual trades.

## Data model

Defined in [`schema.sql`](schema.sql):

- **`trades`**: executed trades, one row each (buyer, seller, asset, quantity, price, currency, settlement date).
- **`obligations`**: what each counterparty owes or is owed, per asset, per settlement date, after netting.
- **`settlements`**: what actually settled.
- **`breaks`**: every problem the reconciliation finds.

Amounts are stored as text and calculated with Python's `Decimal`, so they stay exact. Floating point would introduce rounding errors that show up as fake mismatches.

## How to run

_TODO: setup and run command, e.g._

```bash
python -m pip install -r requirements.txt
python src/reconcile.py data/trades.csv data/settlements.csv
```

## Tests

The test data includes deliberate breaks of every type, so the tests confirm each one is caught.

```bash
pytest
```

## Tech

- Python
- SQLite / SQL
- pytest

## How I built it

I designed the data model and the break rules myself, and built the tool with [Claude Code](https://claude.com/claude-code) as a coding assistant. I reviewed every file it produced. Using an LLM day to day is a normal part of modern development, and I wanted this project to show how I work with one.

## About me

Leon: BSc Software Development, SETU Carlow (2024), based in Vancouver.
_TODO: GitHub / LinkedIn / email._
