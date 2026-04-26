import json
import pytest
from unittest.mock import patch, MagicMock

SAMPLE_ITEMS = [
    {"title": "OpenAI releases GPT-5", "url": "https://tc.com/1", "summary": "New model", "source": "TechCrunch"},
    {"title": "Massive hospital ransomware", "url": "https://bc.com/2", "summary": "200 hospitals", "source": "BC"},
]

SAMPLE_RESPONSE = {
    "high_alerts": [{"title": "Massive hospital ransomware", "summary": "200 hospitals offline",
                     "url": "https://bc.com/2", "source": "BC"}],
    "ai": [{"title": "OpenAI releases GPT-5", "summary": "New model", "url": "https://tc.com/1", "source": "TC"}],
    "cybersecurity": [], "gaming": [], "tech_startups": [], "scandals": [],
    "quick_insight": "AI model releases are accelerating in 2026",
}


def _mock_lm_response(body: dict) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"choices": [{"message": {"content": json.dumps(body)}}]}
    return resp


def test_categorize_items_returns_all_categories():
    with patch("categorizer.httpx.post", return_value=_mock_lm_response(SAMPLE_RESPONSE)):
        from categorizer import categorize_items
        result = categorize_items(SAMPLE_ITEMS)
    assert "high_alerts" in result and "ai" in result
    assert result["ai"][0]["title"] == "OpenAI releases GPT-5"
    assert result["quick_insight"] == "AI model releases are accelerating in 2026"


def test_categorize_returns_empty_dict_for_no_items():
    from categorizer import categorize_items
    result = categorize_items([])
    assert result["high_alerts"] == []
    assert result["ai"] == []


def test_categorize_raises_on_lm_studio_failure():
    with patch("categorizer.httpx.post", side_effect=Exception("connection refused")):
        from categorizer import categorize_items
        with pytest.raises(Exception, match="connection refused"):
            categorize_items(SAMPLE_ITEMS)


def test_categorize_strips_markdown_fences():
    fenced = "```json\n" + json.dumps(SAMPLE_RESPONSE) + "\n```"
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"choices": [{"message": {"content": fenced}}]}
    with patch("categorizer.httpx.post", return_value=resp):
        from categorizer import categorize_items
        result = categorize_items(SAMPLE_ITEMS)
    assert result["quick_insight"] == "AI model releases are accelerating in 2026"


def test_has_high_alerts_true():
    from categorizer import has_high_alerts
    assert has_high_alerts(SAMPLE_RESPONSE) is True


def test_has_high_alerts_false():
    from categorizer import has_high_alerts
    assert has_high_alerts({**SAMPLE_RESPONSE, "high_alerts": []}) is False
