from app.copilot import tools
from app.ingest.seed import seed_if_empty

seed_if_empty()  # standalone runs start with an empty emulator


def test_spending_breakdown_matches_ledger():
    r = tools.get_spending_breakdown("demo-priya", days=365)
    assert "error" not in r
    assert abs(sum(c["amount"] for c in r["by_category"]) - r["total_spend"]) < 1
    assert abs(sum(m["amount"] for m in r["by_month"]) - r["total_spend"]) < 1
    assert not {c["category"] for c in r["by_category"]} & tools.NON_SPEND


def test_query_transactions_total_is_spend():
    r = tools.query_transactions("demo-priya", category="", merchant="", days=365)
    assert r["count"] > 0 and r["total"] > 0


def test_unconnected_sources_report_data_gap():
    assert "data_gap" in tools.get_invoices("demo-priya")
    assert "data_gap" in tools.get_investments("demo-priya")
