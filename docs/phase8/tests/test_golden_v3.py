"""
Golden Test v3 (spec scaffold)

확장 지표(extensions) 포함, 금지어 유입 여부 확인.
"""

import json
from pathlib import Path


def load_sample() -> dict:
    sample_path = Path(__file__).parent / "golden_output_sample_v3.json"
    return json.loads(sample_path.read_text(encoding="utf-8"))


def test_same_input_same_output():
    sample = load_sample()
    assert sample["period"]["start"] == "2019-01-01"
    assert sample["period"]["end"] == "2024-12-31"


def test_extensions_present():
    sample = load_sample()
    extensions = sample.get("extensions", {})
    assert "rolling_returns" in extensions
    assert "rolling_volatility" in extensions
    assert "yearly_returns" in extensions
    assert "contributions" in extensions
    assert "drawdown_segments" in extensions


def test_text_has_no_banned_terms():
    sample = load_sample()
    banned = [
        "추천",
        "최적",
        "우수",
        "효율",
        "승자",
        "Top",
        "랭킹",
        "더 낫다",
        "불리하다",
        "안정적",
        "공격적",
    ]
    text = json.dumps(sample, ensure_ascii=False)
    for term in banned:
        assert term not in text
