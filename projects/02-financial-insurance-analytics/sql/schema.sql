CREATE TABLE IF NOT EXISTS policies (
    policy_id TEXT PRIMARY KEY,
    expected_premium_cents INTEGER NOT NULL CHECK (expected_premium_cents >= 0),
    expected_commission_cents INTEGER NOT NULL CHECK (expected_commission_cents >= 0)
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id TEXT PRIMARY KEY,
    policy_id TEXT NOT NULL REFERENCES policies(policy_id),
    amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0),
    paid_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS commissions (
    commission_id TEXT PRIMARY KEY,
    policy_id TEXT NOT NULL REFERENCES policies(policy_id),
    amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0),
    paid_at TEXT NOT NULL
);
