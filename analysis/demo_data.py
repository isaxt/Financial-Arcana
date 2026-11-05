"""PLACEHOLDER data so the app runs before the real datasets are processed.

Everything here is invented and is flagged is_demo=True in the database and
labelled DEMO in the UI. Running analysis/process_aml.py and
analysis/process_transactions.py followed by `python seed_db.py` replaces it
with real calculated values.
"""

DEMO_METRIC_VALUES = {
    "aml_flagged_rate": 0.10,
    "aml_flagged_median_amount": 1234.56,
    "aml_amount_cv": 95.0,
    "aml_flagged_account_count": 1500,
    "aml_top_format_share": 38.0,
    "consumer_txns_per_user_mean": 6500.0,
    "consumer_top_category_share": 12.0,
    "consumer_median_amount": 28.0,
    "consumer_amount_cv": 1.8,
    "consumer_fraud_rate": 0.15,
}

DEMO_SAMPLE_SIZE = 0

DEMO_CHARTS = {
    "aml_by_payment_format": [
        {"payment_format": "Cheque", "count": 1000, "flagged": 1, "flagged_rate": 0.1},
        {"payment_format": "Credit Card", "count": 3000, "flagged": 3, "flagged_rate": 0.1},
        {"payment_format": "ACH", "count": 2500, "flagged": 12, "flagged_rate": 0.48},
        {"payment_format": "Wire", "count": 600, "flagged": 2, "flagged_rate": 0.33},
        {"payment_format": "Cash", "count": 800, "flagged": 1, "flagged_rate": 0.13},
        {"payment_format": "Bitcoin", "count": 300, "flagged": 2, "flagged_rate": 0.67},
    ],
    "aml_amount_histogram": [
        {"bin_start": b, "nonflagged": n, "flagged": f}
        for b, n, f in [(0, 40, 0), (1, 220, 1), (2, 900, 2), (3, 2100, 4),
                        (4, 2600, 6), (5, 1500, 5), (6, 500, 3), (7, 120, 1),
                        (8, 30, 0)]
    ],
    "consumer_by_category": [
        {"category": "Grocery Stores", "count": 1200, "share_pct": 12.0, "fraud_rate_pct": 0.1},
        {"category": "Eating Places", "count": 1100, "share_pct": 11.0, "fraud_rate_pct": 0.2},
        {"category": "Service Stations", "count": 900, "share_pct": 9.0, "fraud_rate_pct": 0.1},
        {"category": "Drug Stores", "count": 700, "share_pct": 7.0, "fraud_rate_pct": 0.1},
        {"category": "Department Stores", "count": 600, "share_pct": 6.0, "fraud_rate_pct": 0.3},
        {"category": "Online Retail", "count": 500, "share_pct": 5.0, "fraud_rate_pct": 0.9},
    ],
}
