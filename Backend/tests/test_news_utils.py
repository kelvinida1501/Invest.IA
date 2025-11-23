from datetime import datetime, timezone

from app.services import news


def test_extract_datetime_handles_seconds_and_millis():
    ts_seconds = datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp()
    ts_millis = ts_seconds * 1000

    dt_seconds = news._extract_datetime(ts_seconds)
    dt_millis = news._extract_datetime(ts_millis)

    assert dt_seconds.year == 2024
    assert dt_millis.year == 2024


def test_analyse_sentiment_detects_positive_and_negative():
    label_pos, score_pos, _ = news._analyse_sentiment("Alta forte anima mercado", None)
    label_neg, score_neg, _ = news._analyse_sentiment(
        "Queda pressiona mercado e crise", None
    )
    assert label_pos == "positivo" and score_pos > 0
    assert label_neg == "negativo"
