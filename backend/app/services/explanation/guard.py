"""
Phase A 규제 가드 모듈 (Regulatory Guard)

API 응답/리포트 생성 전에 텍스트를 검사한다.
위반 시 처리 정책:
- (권장) 템플릿 fallback + 경고 로그
- (금지) 사용자에게 "위반" 메시지 노출(UX 악화)

버전: v1
생성일: 2026-01-17
"""

import re
import os
import logging
from dataclasses import dataclass
from typing import List, Set, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


# =============================================================================
# 금지어 로드
# =============================================================================

def load_banned_words(file_path: Optional[str] = None) -> Set[str]:
    """
    금지어 목록 로드

    Args:
        file_path: 금지어 파일 경로 (None이면 기본 경로 사용)

    Returns:
        금지어 집합
    """
    if file_path is None:
        # 기본 경로: 같은 디렉토리의 banned_words_v1.txt
        base_dir = Path(__file__).parent
        file_path = str(base_dir / "banned_words_v1.txt")

    banned_words = set()

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 주석과 빈 줄 무시
                if not line or line.startswith('#'):
                    continue
                banned_words.add(line)
    except FileNotFoundError:
        logger.warning(f"Banned words file not found: {file_path}")
    except Exception as e:
        logger.error(f"Error loading banned words: {e}")

    return banned_words


# =============================================================================
# 정규식 패턴
# =============================================================================

# 금지 패턴 (정규식)
BANNED_PATTERNS: List[Tuple[str, str]] = [
    (r'~해야$', '행동 유도 표현'),
    (r'~하세요$', '행동 유도 표현'),
    (r'반드시', '강제 표현'),
    (r'꼭\s', '강제 표현'),
    (r'추천합니다', '추천 표현'),
    (r'권유합니다', '권유 표현'),
    (r'투자하세요', '투자 권유'),
    (r'매수|매도', '매매 지시'),
    (r'사세요|파세요', '매매 지시'),
    (r'보장', '보장 표현'),
    (r'확실한\s*수익', '수익 보장'),
    (r'무위험', '무위험 표현'),
    (r'안전한\s*투자', '안전 보장'),
    (r'최적', '최적 표현'),
    (r'최고', '최고 표현'),
    (r'최선', '최선 표현'),
    (r'가장\s*좋은', '최상위 표현'),
    (r'예상됩니다', '미래 예측'),
    (r'전망됩니다', '미래 예측'),
    (r'될\s*것입니다', '미래 예측'),
    (r'오를\s*것', '상승 예측'),
    (r'내릴\s*것', '하락 예측'),
]

# 예외 패턴 (화이트리스트) - 이 패턴이 포함되면 위반으로 처리하지 않음
EXCEPTION_PATTERNS: List[str] = [
    r'추천이\s*아닙니다',
    r'권유가\s*아닙니다',
    r'보장하지\s*않습니다',
    r'보장되지\s*않습니다',
    r'예측이\s*아닙니다',
    r'자문이\s*아닙니다',
    r'투자\s*권유나\s*추천이\s*아닙니다',
]


# =============================================================================
# 위반 결과 클래스
# =============================================================================

@dataclass
class ViolationResult:
    """위반 검사 결과"""
    has_violation: bool
    violations: List[str]  # 발견된 위반 목록
    original_text: str
    sanitized_text: Optional[str] = None  # 치환된 텍스트 (fallback 적용 시)

    def to_log_dict(self) -> dict:
        """로그용 dict"""
        return {
            "has_violation": self.has_violation,
            "violation_count": len(self.violations),
            "violations": self.violations[:5]  # 최대 5개만 로그
        }


# =============================================================================
# 규제 가드 클래스
# =============================================================================

class RegulatoryGuard:
    """
    규제 가드

    텍스트에서 금지 표현을 검사하고 필요시 fallback 적용
    """

    def __init__(
        self,
        banned_words_file: Optional[str] = None,
        fallback_text: str = "해당 지표에 대한 정보입니다."
    ):
        """
        Args:
            banned_words_file: 금지어 파일 경로
            fallback_text: 위반 시 대체할 기본 텍스트
        """
        self.banned_words = load_banned_words(banned_words_file)
        self.fallback_text = fallback_text

        # 정규식 패턴 컴파일
        self.banned_patterns = [
            (re.compile(pattern, re.IGNORECASE), reason)
            for pattern, reason in BANNED_PATTERNS
        ]
        self.exception_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in EXCEPTION_PATTERNS
        ]

    def check_text(self, text: str) -> ViolationResult:
        """
        텍스트 위반 검사

        Args:
            text: 검사할 텍스트

        Returns:
            ViolationResult
        """
        violations = []

        # 예외 패턴 확인 - 예외에 해당하면 위반 검사 건너뜀
        for exception_pattern in self.exception_patterns:
            if exception_pattern.search(text):
                # 예외 패턴이 있으면 해당 문장은 위반이 아님
                return ViolationResult(
                    has_violation=False,
                    violations=[],
                    original_text=text
                )

        # 금지어 검사
        for banned_word in self.banned_words:
            if banned_word in text:
                violations.append(f"금지어 '{banned_word}' 발견")

        # 정규식 패턴 검사
        for pattern, reason in self.banned_patterns:
            if pattern.search(text):
                violations.append(f"금지 패턴 '{reason}' 발견")

        has_violation = len(violations) > 0

        if has_violation:
            logger.warning(f"Regulatory violation detected: {violations[:3]}")

        return ViolationResult(
            has_violation=has_violation,
            violations=violations,
            original_text=text
        )

    def sanitize(self, text: str) -> Tuple[str, ViolationResult]:
        """
        텍스트 검사 및 필요시 fallback 적용

        Args:
            text: 검사할 텍스트

        Returns:
            (정화된 텍스트, 위반 결과)
        """
        result = self.check_text(text)

        if result.has_violation:
            # 위반 시 fallback 적용
            result.sanitized_text = self.fallback_text
            logger.warning(
                f"Text sanitized due to {len(result.violations)} violations. "
                f"Original length: {len(text)}"
            )
            return self.fallback_text, result
        else:
            return text, result

    def validate_template_output(self, output: dict) -> dict:
        """
        전체 템플릿 출력 검증

        Args:
            output: 템플릿 출력 dict

        Returns:
            검증/정화된 output dict
        """
        validated = output.copy()
        total_violations = []

        # summary 검사
        if "summary" in validated:
            sanitized, result = self.sanitize(validated["summary"])
            validated["summary"] = sanitized
            total_violations.extend(result.violations)

        # performance_explanations 검사
        if "performance_explanations" in validated:
            for exp in validated["performance_explanations"]:
                if "description" in exp:
                    sanitized, result = self.sanitize(exp["description"])
                    exp["description"] = sanitized
                    total_violations.extend(result.violations)
                if "context" in exp and exp["context"]:
                    sanitized, result = self.sanitize(exp["context"])
                    exp["context"] = sanitized
                    total_violations.extend(result.violations)

        # risk_explanation 검사
        if "risk_explanation" in validated:
            sanitized, result = self.sanitize(validated["risk_explanation"])
            validated["risk_explanation"] = sanitized
            total_violations.extend(result.violations)

        # comparison 검사
        if "comparison" in validated and validated["comparison"]:
            if "relative_performance" in validated["comparison"]:
                sanitized, result = self.sanitize(validated["comparison"]["relative_performance"])
                validated["comparison"]["relative_performance"] = sanitized
                total_violations.extend(result.violations)

        # 위반 통계 로그
        if total_violations:
            logger.info(f"Total violations found and sanitized: {len(total_violations)}")

        return validated


# =============================================================================
# 모듈 레벨 인스턴스
# =============================================================================

# 기본 가드 인스턴스 (lazy initialization)
_default_guard: Optional[RegulatoryGuard] = None


def get_default_guard() -> RegulatoryGuard:
    """기본 가드 인스턴스 반환"""
    global _default_guard
    if _default_guard is None:
        _default_guard = RegulatoryGuard()
    return _default_guard


def check_text(text: str) -> ViolationResult:
    """텍스트 위반 검사 (편의 함수)"""
    return get_default_guard().check_text(text)


def sanitize(text: str) -> Tuple[str, ViolationResult]:
    """텍스트 정화 (편의 함수)"""
    return get_default_guard().sanitize(text)
