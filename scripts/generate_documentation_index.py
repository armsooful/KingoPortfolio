#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
from datetime import date


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
INDEX = DOCS_DIR / "documentation_index.md"


SECTION_ORDER = [
    "phase3",
    "phase4",
    "phase5",
    "phase8",
    "phase2",
    "phase1",
    "architecture",
    "compliance",
    "deployment",
    "development",
    "changelogs",
    "phase6",
    "phase7",
    "phase9",
    "phase10",
    "phase11",
    "manuals",
    "reports",
    "alpha_test",
    "legacy",
    "project",
]

SECTION_TITLES = {
    "phase3": "Phase 3 (설명·안심 중심 해석 서비스) - 현재",
    "phase4": "Phase 4 (운영 전환)",
    "phase5": "Phase 5 (외부 노출·운영 단계)",
    "phase8": "Phase 8 (분석 깊이/입력 다양성 확장)",
    "phase2": "Phase 2 (고급 시뮬레이션)",
    "phase1": "Phase 1 (시뮬레이션 인프라)",
    "architecture": "Architecture (설계)",
    "compliance": "Compliance (법적 준수)",
    "deployment": "Deployment (배포)",
    "development": "Development (개발)",
    "changelogs": "Changelogs (변경 이력)",
    "phase6": "Phase 6",
    "phase7": "Phase 7",
    "phase9": "Phase 9",
    "phase10": "Phase 10",
    "phase11": "Phase 11",
    "manuals": "Manuals (운영 매뉴얼)",
    "reports": "Reports (보고서)",
    "alpha_test": "Alpha Test",
    "legacy": "Legacy (과거 문서)",
    "project": "Project (프로젝트 개요)",
}

PHASE_SECTION_PREFIX = "## Phase "

PHASE_RE = re.compile(r"phase(\d+)([a-z])?")

EXCEPTIONS = {
    "documentation_index.md": "문서 인덱스",
    "DOCUMENT_NAMING_CONVENTION.md": "네이밍 규칙",
    "DATABASE_CONNECTION.md": "DB 연결 가이드",
    "database_connection.md": "DB 연결 가이드",
    "feature_overview.md": "기능 개요",
    "table_catalog.md": "테이블 카탈로그",
    "manuals_index.md": "매뉴얼 인덱스",
    "link_fix_report.md": "링크 점검 리포트",
}

TYPE_MAP = [
    ("completion_report", "완료 보고서"),
    ("completion_statement", "완료 진술서"),
    ("implementation_tickets", "구현 티켓"),
    ("implementation_plan", "구현 계획"),
    ("implementation_summary", "구현 요약"),
    ("backlog_tickets", "백로그 티켓"),
    ("backlog", "백로그"),
    ("objectives", "목표"),
    ("overview", "개요"),
    ("specification", "명세서"),
    ("spec", "명세서"),
    ("detailed_design", "상세 설계"),
    ("design", "설계"),
    ("execution_plan", "실행 계획"),
    ("execution_guide", "실행 가이드"),
    ("revalidation", "재검증"),
    ("validation", "검증"),
    ("verification_report", "검증 보고서"),
    ("verification", "검증"),
    ("checklist", "체크리스트"),
    ("runbook", "운영 Runbook"),
    ("operator_guide", "운영자 가이드"),
    ("guide", "가이드"),
    ("manual", "매뉴얼"),
    ("report", "보고서"),
    ("release_notes", "릴리즈 노트"),
    ("roadmap", "로드맵"),
    ("policy", "정책"),
    ("rules", "규칙"),
    ("alert", "알림"),
    ("metrics", "메트릭"),
    ("schema", "스키마"),
    ("ddl", "DDL"),
    ("api", "API"),
    ("ui", "UI"),
    ("ux", "UX"),
    ("architecture", "아키텍처"),
    ("status", "상태"),
    ("log", "로그"),
    ("template", "템플릿"),
]

EXT_LABEL = {
    ".json": "JSON",
    ".sql": "SQL",
    ".yaml": "YAML",
    ".yml": "YAML",
}


def section_title(key: str) -> str:
    return SECTION_TITLES.get(key, key.replace("_", " ").title())


def infer_desc(filename: str, section_title_line: str) -> str:
    if filename in EXCEPTIONS:
        return EXCEPTIONS[filename]

    name = Path(filename).stem.lower()

    # Phase-specific handling
    if section_title_line.startswith(PHASE_SECTION_PREFIX):
        for key, label in [
            ("completion_report", "완료 보고서"),
            ("completion_statement", "완료 진술서"),
            ("implementation_tickets", "구현 티켓"),
            ("implementation_plan", "구현 계획"),
            ("implementation_summary", "구현 요약"),
            ("backlog_tickets", "백로그 티켓"),
            ("backlog", "백로그"),
            ("objectives", "목표"),
        ]:
            if key in name:
                return label
        if "specification" in name or name.endswith("_spec"):
            return "명세서"
        if "design" in name:
            return "설계"
        if "checklist" in name:
            return "체크리스트"
        if "runbook" in name:
            return "운영 Runbook"
        if "guide" in name:
            return "가이드"
        if "schema" in name:
            return "스키마"
        if "ddl" in name:
            return "DDL"
        if "api" in name:
            return "API"
        if "ux" in name:
            return "UX"
        if "ui" in name:
            return "UI"
        if "report" in name:
            return "보고서"
        return "Phase 문서"

    # Section-specific handling
    if section_title_line == "## Architecture (설계)":
        if "spec" in name:
            return "명세서"
        if "design" in name or "architecture" in name:
            return "설계"
        return "아키텍처"

    if section_title_line == "## Development (개발)":
        if "guide" in name or "manual" in name:
            return "가이드"
        if "setup" in name:
            return "설정"
        if "snapshot" in name:
            return "스냅샷"
        return "개발 문서"

    if section_title_line == "## Compliance (법적 준수)":
        if "policy" in name:
            return "정책"
        if "terminology" in name or "terms" in name:
            return "용어"
        if "disclaimer" in name:
            return "면책"
        return "준수 문서"

    if section_title_line == "## Deployment (배포)":
        if "migration" in name:
            return "마이그레이션"
        if "setup" in name or "environment" in name:
            return "환경 설정"
        if "forwarding" in name:
            return "포워딩"
        return "배포 문서"

    if section_title_line == "## Changelogs (변경 이력)":
        if "release_notes" in name:
            return "릴리즈 노트"
        if "changelog" in name:
            return "변경 이력"
        if "progress" in name:
            return "진행 상황"
        if "summary" in name:
            return "요약"
        return "변경 기록"

    if section_title_line == "## Alpha Test":
        if "plan" in name:
            return "계획"
        if "log" in name:
            return "로그"
        if "issue" in name:
            return "이슈 목록"
        return "테스트 문서"

    if section_title_line == "## Manuals (운영 매뉴얼)":
        return "매뉴얼"

    if section_title_line == "## Reports (보고서)":
        if "evidence" in name:
            return "증적"
        if "baseline" in name:
            return "기준선"
        return "보고서"

    # Generic fallback
    parts = []
    m = PHASE_RE.search(name)
    if m:
        phase_num = m.group(1)
        sub = m.group(2)
        parts.append(f"Phase {phase_num}-{sub.upper()}" if sub else f"Phase {phase_num}")
    if "epic_" in name:
        m2 = re.search(r"epic_(c\d+|u\d+)", name)
        if m2:
            epic = m2.group(1).upper().replace("U", "U-").replace("C", "C-")
            parts.append(f"Epic {epic}")
    else:
        if re.match(r"^c\d+_", name):
            epic = re.match(r"^(c\d+)_", name).group(1).upper().replace("C", "C-")
            parts.append(f"Epic {epic}")
        elif re.match(r"^u\d+_", name):
            epic = re.match(r"^(u\d+)_", name).group(1).upper().replace("U", "U-")
            parts.append(f"Epic {epic}")

    type_label = None
    for key, label in TYPE_MAP:
        if key in name:
            type_label = label
            break
    if not type_label:
        ext = Path(filename).suffix.lower()
        type_label = EXT_LABEL.get(ext)

    if type_label:
        return " / ".join(parts) + f" {type_label}" if parts else type_label
    return "-"


def build_index() -> None:
    files = [p for p in DOCS_DIR.rglob("*") if p.is_file()]
    files = [p for p in files if p != INDEX]

    sections = {}
    for path in files:
        rel = path.relative_to(DOCS_DIR)
        key = rel.parts[0] if len(rel.parts) > 1 else "project"
        sections.setdefault(key, []).append(rel)

    for key in sections:
        sections[key].sort()

    lines = []
    lines.append("# Foresto Compass 문서 목록")
    lines.append("최초작성일자: 2026-01-17")
    lines.append(f"최종수정일자: {date.today().isoformat()}")
    lines.append("")
    lines.append(f"**최종 업데이트**: {date.today().isoformat()} (자동 정리)")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("<!--")
    lines.append("이 문서는 자동 생성 규칙에 따라 정리되었습니다.")
    lines.append("- 파일명 기반으로 설명을 자동 추론합니다.")
    lines.append("- 예외 매핑은 문서 하단의 \"설명 예외 매핑\" 섹션을 참고하세요.")
    lines.append("-->")
    lines.append("")

    used = set()
    for key in SECTION_ORDER:
        items = sections.get(key)
        if not items:
            continue
        used.add(key)
        title = section_title(key)
        lines.append(f"## {title}")
        lines.append("")
        lines.append("| 파일명 | 설명 |")
        lines.append("|--------|------|")
        for rel in items:
            link = str(rel).replace("\\", "/")
            filename = rel.name
            desc = infer_desc(filename, f"## {title}")
            lines.append(f"| [{filename}]({link}) | {desc} |")
        lines.append("")
        lines.append("---")
        lines.append("")

    for key in sorted(k for k in sections.keys() if k not in used):
        items = sections[key]
        title = section_title(key)
        lines.append(f"## {title}")
        lines.append("")
        lines.append("| 파일명 | 설명 |")
        lines.append("|--------|------|")
        for rel in items:
            link = str(rel).replace("\\", "/")
            filename = rel.name
            desc = infer_desc(filename, f"## {title}")
            lines.append(f"| [{filename}]({link}) | {desc} |")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("## 설명 예외 매핑")
    lines.append("")
    lines.append("| 파일명 | 설명 |")
    lines.append("|--------|------|")
    for filename, desc in sorted(EXCEPTIONS.items()):
        lines.append(f"| `{filename}` | {desc} |")
    lines.append("")

    INDEX.write_text("\n".join(lines))


if __name__ == "__main__":
    build_index()
    print(f"Updated {INDEX}")
