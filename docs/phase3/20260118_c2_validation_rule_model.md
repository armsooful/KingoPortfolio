# C-2 Validation Rule 메타 모델 상세화
최초작성일자: 2026-01-18
최종수정일자: 2026-01-18

- 문서명: Validation Rule 메타 모델 상세화
- 범위: 룰 등록 · 버전 · 적용 범위(스코프)

## 1. 규칙 마스터(ValidationRuleMaster)

### 기본 속성
- `rule_code`: 규칙 식별자 (C2-DQ-XXX)
- `rule_type`: REQ/RNG/UNQ/REF/CST
- `rule_name`, `description`
- `severity`: WARN/FAIL
- `is_active`

### 적용 범위(스코프)
- `scope_type`: GLOBAL/DATASET/JOB/RESULT
- `scope_key`: dataset_type/vendor/job_id 등 스코프 분류 키
- `scope_value`: scope_key에 해당하는 값
- `scope_json`: 복합 조건(예: 다중 데이터셋, 태그 기반)

> 기본값은 GLOBAL이며, 특정 데이터셋/잡/결과 타입에만 적용하고자 하는 경우 스코프를 지정한다.

## 2. 규칙 버전(ValidationRuleVersion)

- `rule_code` + `version_no`로 유일하게 식별
- `rule_params`에 상세 파라미터 저장
  - 범위(RNG): min/max
  - 유일성(UNQ): key_fields 배열
  - 참조(REF): parent_table/field
  - 일관성(CST): sum_fields
- `effective_from` ~ `effective_to`로 유효 기간 관리

## 3. 규칙 적용 흐름

1) 규칙 등록
- 마스터에 rule_code/타입/스코프 저장

2) 규칙 버전 추가
- 파라미터/유효기간 기준으로 버전 관리

3) 실행 시 적용 범위 필터링
- scope_type + (scope_key, scope_value) + scope_json 기준으로 적용 규칙 필터
- 예: DATASET + dataset_type=PRICE

4) Validation Result 기록
- `validation_result`에 PASS/WARN/FAIL 기록

## 4. 스코프 예시

- GLOBAL
  - 모든 데이터셋에 적용
- DATASET
  - `scope_key=dataset_type`, `scope_value=PRICE`
- JOB
  - `scope_key=job_id`, `scope_value=DAILY_SIMULATION`
- RESULT
  - `scope_key=result_type`, `scope_value=SIMULATION`

## 5. 완료 기준
- 룰 등록/버전/스코프 관리 가능
- 실행 시 스코프 필터링 가능
- 룰 버전으로 재현성 확보
