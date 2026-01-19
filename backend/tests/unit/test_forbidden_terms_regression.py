"""
금지 키워드/문구 회귀 테스트 자동화
"""

from pathlib import Path
import subprocess

import pytest

pytestmark = pytest.mark.guard


def test_forbidden_terms_check_script():
    repo_root = Path(__file__).resolve().parents[3]
    script_path = repo_root / "scripts" / "forbidden_terms_check.sh"
    assert script_path.exists(), f"스크립트를 찾을 수 없습니다: {script_path}"

    result = subprocess.run(
        ["bash", str(script_path)],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
        raise AssertionError(f"금지어 검사 실패:\n{output}")


def test_recommendation_endpoint_blocked(client):
    response = client.get("/api/v1/recommendations")
    assert response.status_code == 404
