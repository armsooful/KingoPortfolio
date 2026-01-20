"""
Golden Test v2 (spec scaffold)

Note: This file is a reference specification for expected assertions.
Integration into the test runner is deferred.
"""

import json
from pathlib import Path


def load_sample() -> dict:
    sample_path = Path(__file__).parent / "golden_output_sample_v2.json"
    return json.loads(sample_path.read_text(encoding="utf-8"))


def test_same_input_same_output():
    sample = load_sample()
    assert sample["period"]["start"] == "2019-01-01"
    assert sample["period"]["end"] == "2024-12-31"


def test_text_has_no_banned_terms():
    sample = load_sample()
    banned = ["추천", "최적", "우수", "효율", "승자", "Top", "랭킹", "더 낫다", "불리하다"]
    text = " ".join(sample.get("notes", []))
    for term in banned:
        assert term not in text
