from datetime import datetime

from app.services import news


def test_parse_iso_dt_parses_basic():
    dt = news._parse_iso_dt("2024-01-01T12:00:00Z")
    assert isinstance(dt, datetime)
    assert dt.year == 2024


def test_pick_image_prefers_original_url():
    payload = {"thumbnail": {"originalUrl": "http://img/original.png"}}
    assert news._pick_image(payload) == "http://img/original.png"

    payload2 = {
        "thumbnail": {
            "resolutions": [{"url": "a", "height": 1}, {"url": "b", "height": 2}]
        }
    }
    assert news._pick_image(payload2) == "b"
