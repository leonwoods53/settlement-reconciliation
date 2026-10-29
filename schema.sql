-- Settlement reconciliation schema (SQLite)
--
-- Amounts are stored as TEXT, not REAL, so they stay exact.
-- Maths on them is done in Python with decimal.Decimal.
-- Timestamps are ISO 8601 text, e.g. 2026-10-29T14:30:00Z.

-- One row per executed trade.
-- The seller delivers `quantity` of `asset`;
-- the buyer pays `quantity * price` in `currency`.
CREATE TABLE IF NOT EXISTS trades (
    client_trade_id TEXT PRIMARY KEY,   -- named after zerohash's field
    buyer           TEXT NOT NULL,
    seller          TEXT NOT NULL,
    asset           TEXT NOT NULL,      -- e.g. BTC
    quantity        TEXT NOT NULL,      -- exact decimal, e.g. '0.5'
    price           TEXT NOT NULL,      -- per unit, in `currency`
    currency        TEXT NOT NULL,      -- e.g. USD
    traded_at       TEXT NOT NULL,      -- when the trade executed
    settlement_date TEXT NOT NULL,      -- date it must settle by, e.g. 2026-10-30
    CHECK (buyer <> seller)
);
