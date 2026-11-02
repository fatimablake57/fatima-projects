SELECT
    p.policy_id,
    p.expected_premium_cents,
    COALESCE(pay.actual_premium_cents, 0) AS actual_premium_cents,
    COALESCE(pay.actual_premium_cents, 0) - p.expected_premium_cents AS premium_variance_cents,
    p.expected_commission_cents,
    COALESCE(com.actual_commission_cents, 0) AS actual_commission_cents,
    COALESCE(com.actual_commission_cents, 0) - p.expected_commission_cents AS commission_variance_cents
FROM policies AS p
LEFT JOIN (
    SELECT policy_id, SUM(amount_cents) AS actual_premium_cents
    FROM payments
    GROUP BY policy_id
) AS pay ON pay.policy_id = p.policy_id
LEFT JOIN (
    SELECT policy_id, SUM(amount_cents) AS actual_commission_cents
    FROM commissions
    GROUP BY policy_id
) AS com ON com.policy_id = p.policy_id
ORDER BY p.policy_id;
