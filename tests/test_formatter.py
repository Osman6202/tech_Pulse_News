from formatter import format_full_briefing, format_alert_message, split_message

SAMPLE = {
    "high_alerts": [
        {"title": "Ransomware Attack", "summary": "200 hospitals hit", "url": "https://bc.com/1", "source": "BC"}
    ],
    "ai": [{"title": "GPT-5 Released", "summary": "Beats benchmarks", "url": "https://tc.com/2", "source": "TC"}],
    "cybersecurity": [],
    "gaming": [{"title": "GTA VI Delayed", "summary": "Q1 2027", "url": "https://ign.com/3", "source": "IGN"}],
    "tech_startups": [], "scandals": [],
    "quick_insight": "AI inference costs dropped 40% YoY",
}


def test_format_full_briefing_returns_list():
    parts = format_full_briefing(SAMPLE, mode="morning")
    assert isinstance(parts, list) and all(isinstance(p, str) for p in parts)


def test_format_full_briefing_contains_header():
    full = "".join(format_full_briefing(SAMPLE, mode="morning"))
    assert "TECH PULSE" in full and "Morning Briefing" in full


def test_format_full_briefing_contains_high_alert():
    full = "".join(format_full_briefing(SAMPLE))
    assert "HIGH ALERT" in full and "Ransomware Attack" in full


def test_format_full_briefing_contains_gaming():
    full = "".join(format_full_briefing(SAMPLE))
    assert "GTA VI Delayed" in full


def test_format_alert_message_contains_headline():
    alert = {"title": "Critical Zero-Day", "summary": "Affects 500M", "url": "https://ex.com", "source": "Ars"}
    msg = format_alert_message(alert)
    assert "Critical Zero-Day" in msg and "HIGH ALERT" in msg


def test_split_message_respects_limit():
    long_text = "A" * 10000
    parts = split_message(long_text, limit=4096)
    assert all(len(p) <= 4096 for p in parts)
    assert "".join(parts) == long_text
