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

-- Sign convention for obligations and settlements, from the
-- counterparty's point of view:
--   positive = counterparty pays or delivers it
--   negative = counterparty receives it
-- `asset` covers cash too: USD is netted like BTC.

-- Net position per counterparty, per asset, per settlement window.
-- Built from `trades` by the netting step. Example: if Alice sells
-- 1 BTC and buys 0.4 BTC for the same date, she owes a net 0.6 BTC.
CREATE TABLE IF NOT EXISTS obligations (
    counterparty    TEXT NOT NULL,
    asset           TEXT NOT NULL,
    settlement_date TEXT NOT NULL,
    net_amount      TEXT NOT NULL,      -- signed, see convention above
    PRIMARY KEY (counterparty, asset, settlement_date)
);

-- What actually settled, loaded from the second CSV.
-- No foreign key to obligations on purpose: a settlement with no
-- matching obligation is a break we want to catch, not reject.
CREATE TABLE IF NOT EXISTS settlements (
    settlement_id   TEXT PRIMARY KEY,
    counterparty    TEXT NOT NULL,
    asset           TEXT NOT NULL,
    amount          TEXT NOT NULL,      -- signed, see convention above
    settlement_date TEXT NOT NULL,      -- window this settles
    settled_at      TEXT NOT NULL       -- when it actually happened
);

-- Output of reconciliation: one row per problem found.
CREATE TABLE IF NOT EXISTS breaks (
    break_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    break_type      TEXT NOT NULL CHECK (break_type IN (
                        'missing_trade',       -- settlement with no obligation
                        'amount_mismatch',     -- settled amount != net_amount
                        'unsettled_past_due',  -- obligation, no settlement, date passed
                        'settled_twice',       -- 2+ settlements for one obligation
                        'settled_late'         -- right amount, settled_at after settlement_date
                    )),
    counterparty    TEXT NOT NULL,
    asset           TEXT NOT NULL,
    settlement_date TEXT NOT NULL,
    expected_amount TEXT,               -- NULL for missing_trade
    actual_amount   TEXT,               -- NULL for unsettled_past_due
    settlement_id   TEXT,               -- the settlement involved, if any
    detected_at     TEXT NOT NULL       -- when the run found it
);
