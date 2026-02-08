# 채권기본정보 적재 구현 설계

## 1. API 개요
- **API명**: 금융위원회_채권기본정보
- **엔드포인트**: `http://apis.data.go.kr/1160100/service/GetBondIssuInfoService/getBondBasiInfo`
- **인증**: serviceKey 방식
- **응답형식**: XML/JSON 선택 가능
- **데이터 갱신주기**: 일 1회

## 2. 요청 파라미터

### 필수 파라미터
- `serviceKey`: 공공데이터포털 인증키
- `numOfRows`: 한 페이지 결과 수 (최대값 확인 필요)
- `pageNo`: 페이지 번호
- `resultType`: xml 또는 json

### 선택 파라미터
- `basDt`: 기준일자 (YYYYMMDD)
- `crno`: 법인등록번호 (13자리)
- `bondIsurNm`: 채권발행인명

## 3. 응답 데이터 구조 (총 82개 필드)

### 핵심 식별자
- `isinCd`: ISIN코드 (채권 고유번호)
- `crno`: 법인등록번호
- `basDt`: 기준일자

### 주요 필드 그룹
1. **기본정보**: isinCdNm, bondIsurNm, sicNm, scrsItmsKcd
2. **발행정보**: bondIssuDt, bondExprDt, bondIssuAmt, bondPymtAmt, bondBal
3. **금리정보**: bondSrfcInrt, irtChngDcd, bondIntTcd, intPayCyclCtt
4. **등급정보**: kisScrsItmsKcd, kbpScrsItmsKcd, niceScrsItmsKcd, fnScrsItmsKcd
5. **보증/순위**: grnDcd, bondRnknDcd
6. **모집/상장**: bondOffrMcd, lstgDt, txtnDcd

## 4. 적재 아키텍처

```
[공공데이터 API] 
    ↓
[API Client Layer] - 페이징, 재시도, 에러핸들링
    ↓
[Data Validation Layer] - 스키마 검증, 데이터 정합성
    ↓
[Transformation Layer] - 타입 변환, NULL 처리
    ↓
[Database Layer] - MariaDB/MySQL
```

## 5. 데이터베이스 스키마 설계

```sql
CREATE TABLE bond_basic_info (
    -- 기본키 (복합키)
    isin_cd VARCHAR(12) NOT NULL COMMENT 'ISIN코드',
    bas_dt DATE NOT NULL COMMENT '기준일자',
    
    -- 기본정보
    crno VARCHAR(13) COMMENT '법인등록번호',
    isin_cd_nm VARCHAR(200) COMMENT 'ISIN코드명',
    scrs_itms_kcd VARCHAR(4) COMMENT '유가증권종목종류코드',
    scrs_itms_kcd_nm VARCHAR(100) COMMENT '유가증권종목종류코드명',
    bond_issu_cur_cd VARCHAR(3) COMMENT '채권발행통화코드',
    bond_issu_cur_cd_nm VARCHAR(100) COMMENT '채권발행통화코드명',
    bond_isur_nm VARCHAR(100) COMMENT '채권발행인명',
    sic_nm VARCHAR(1000) COMMENT '표준산업분류명',
    
    -- 발행 정보
    bond_issu_dt DATE COMMENT '채권발행일자',
    bond_expr_dt DATE COMMENT '채권만기일자',
    bond_issu_amt DECIMAL(18,3) COMMENT '채권발행금액',
    bond_pymt_amt DECIMAL(22,3) COMMENT '채권납입금액',
    bond_bal DECIMAL(18,3) COMMENT '채권잔액',
    
    -- 금리 정보
    irt_chng_dcd VARCHAR(1) COMMENT '금리변동구분코드',
    irt_chng_dcd_nm VARCHAR(100) COMMENT '금리변동구분코드명',
    bond_srfc_inrt DECIMAL(15,10) COMMENT '채권표면이율',
    bond_int_tcd VARCHAR(1) COMMENT '채권이자유형코드',
    bond_int_tcd_nm VARCHAR(100) COMMENT '채권이자유형코드명',
    int_pay_cycl_ctt VARCHAR(100) COMMENT '이자지급주기내용',
    nxtm_copn_dt DATE COMMENT '차기이표일자',
    rbf_copn_dt DATE COMMENT '직전이표일자',
    
    -- 보증 및 순위
    grn_dcd VARCHAR(1) COMMENT '보증구분코드',
    grn_dcd_nm VARCHAR(100) COMMENT '보증구분코드명',
    bond_rnkn_dcd VARCHAR(1) COMMENT '채권순위구분코드',
    bond_rnkn_dcd_nm VARCHAR(100) COMMENT '채권순위구분코드명',
    
    -- 신용평가 등급
    kis_scrs_itms_kcd VARCHAR(4) COMMENT '한국신용평가유가증권종목종류코드',
    kis_scrs_itms_kcd_nm VARCHAR(100) COMMENT '한국신용평가유가증권종목종류코드명',
    kbp_scrs_itms_kcd VARCHAR(4) COMMENT '한국자산평가유가증권종목종류코드',
    kbp_scrs_itms_kcd_nm VARCHAR(100) COMMENT '한국자산평가유가증권종목종류코드명',
    nice_scrs_itms_kcd VARCHAR(4) COMMENT 'NICE평가정보유가증권종목종류코드',
    nice_scrs_itms_kcd_nm VARCHAR(100) COMMENT 'NICE평가정보유가증권종목종류코드명',
    fn_scrs_itms_kcd VARCHAR(4) COMMENT 'FN유가증권종목종류코드',
    fn_scrs_itms_kcd_nm VARCHAR(100) COMMENT 'FN유가증권종목종류코드명',
    
    -- 옵션 및 특이사항
    optn_tcd VARCHAR(4) COMMENT '옵션유형코드',
    optn_tcd_nm VARCHAR(100) COMMENT '옵션유형코드명',
    pclr_bond_kcd VARCHAR(1) COMMENT '특이채권종류코드',
    pclr_bond_kcd_nm VARCHAR(100) COMMENT '특이채권종류코드명',
    
    -- 모집 및 상장
    bond_offr_mcd VARCHAR(2) COMMENT '채권모집방법코드',
    bond_offr_mcd_nm VARCHAR(100) COMMENT '채권모집방법코드명',
    lstg_dt DATE COMMENT '상장일자',
    txtn_dcd VARCHAR(1) COMMENT '과세구분코드',
    txtn_dcd_nm VARCHAR(100) COMMENT '과세구분코드명',
    
    -- 상환 정보
    pamt_rdpt_mcd VARCHAR(2) COMMENT '원금상환방법코드',
    pamt_rdpt_mcd_nm VARCHAR(100) COMMENT '원금상환방법코드명',
    
    -- 기타 여부 정보
    strips_psbl_yn CHAR(1) COMMENT '스트립스채권가능여부',
    strips_nm VARCHAR(100) COMMENT '스트립스채권명',
    pris_lnkg_bond_yn CHAR(1) COMMENT '물가연동채권여부',
    crfnd_yn CHAR(1) COMMENT '크라우드펀딩여부',
    prmnc_bond_yn CHAR(1) COMMENT '영구채권여부',
    qib_trgt_scrt_yn CHAR(1) COMMENT 'QIB대상증권여부',
    elps_int_pay_yn CHAR(1) COMMENT '경과이자지급여부',
    
    -- 기관 정보
    piam_pay_inst_nm VARCHAR(100) COMMENT '원리금지급기관명',
    piam_pay_brof_nm VARCHAR(100) COMMENT '원리금지급지점명',
    bond_reg_inst_dcd VARCHAR(2) COMMENT '채권등록기관구분코드',
    bond_reg_inst_dcd_nm VARCHAR(100) COMMENT '채권등록기관구분코드명',
    issu_dpty_nm VARCHAR(1000) COMMENT '발행대리인명',
    bond_undt_inst_nm VARCHAR(1000) COMMENT '채권인수기관명',
    bond_grn_inst_nm VARCHAR(1000) COMMENT '채권보증기관명',
    cpbd_mng_cmpy_nm VARCHAR(1000) COMMENT '사채관리회사명',
    
    -- 자금용도
    cpt_usge_dcd VARCHAR(2) COMMENT '자금용도구분코드',
    cpt_usge_dcd_nm VARCHAR(100) COMMENT '자금용도구분코드명',
    
    -- 이자 지급 관련
    bnk_hldy_int_pydy_dcd VARCHAR(1) COMMENT '은행휴일이자지급일구분코드',
    bnk_hldy_int_pydy_dcd_nm VARCHAR(100) COMMENT '은행휴일이자지급일구분코드명',
    sttr_hldy_int_pydy_dcd VARCHAR(1) COMMENT '법정휴일이자지급일구분코드',
    sttr_hldy_int_pydy_dcd_nm VARCHAR(100) COMMENT '법정휴일이자지급일구분코드명',
    int_pay_mmnt_dcd VARCHAR(2) COMMENT '이자지급시기구분코드',
    int_pay_mmnt_dcd_nm VARCHAR(100) COMMENT '이자지급시기구분코드명',
    
    -- 권리행사 및 산정
    rgt_exert_mnbd_dcd VARCHAR(1) COMMENT '권리행사주체구분코드',
    rgt_exert_mnbd_dcd_nm VARCHAR(100) COMMENT '권리행사주체구분코드명',
    int_cmpu_mcd VARCHAR(1) COMMENT '이자산정방법코드',
    int_cmpu_mcd_nm VARCHAR(100) COMMENT '이자산정방법코드명',
    
    -- 기타 날짜
    prmnc_bond_tmn_dt DATE COMMENT '영구채권해지일자',
    qib_tmn_dt DATE COMMENT 'QIB해지일자',
    
    -- 메타데이터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '생성일시',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일시',
    
    PRIMARY KEY (isin_cd, bas_dt),
    INDEX idx_crno (crno),
    INDEX idx_bond_isur_nm (bond_isur_nm),
    INDEX idx_bond_expr_dt (bond_expr_dt),
    INDEX idx_bas_dt (bas_dt)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='채권기본정보';
```

## 6. Python 구현 구조 (FastAPI 기반)

### 6.1 프로젝트 구조
```
bond_data_loader/
├── app/
│   ├── main.py                 # FastAPI 앱
│   ├── config.py               # 설정 관리
│   ├── models/
│   │   ├── bond.py            # SQLAlchemy 모델
│   │   └── schemas.py         # Pydantic 스키마
│   ├── services/
│   │   ├── api_client.py      # API 호출 로직
│   │   ├── data_loader.py     # 데이터 적재 로직
│   │   └── transformer.py     # 데이터 변환 로직
│   ├── repositories/
│   │   └── bond_repository.py # DB 접근 로직
│   └── utils/
│       ├── logger.py          # 로깅
│       └── validator.py       # 데이터 검증
├── tests/
│   └── test_data_loader.py
├── requirements.txt
└── .env
```

### 6.2 핵심 컴포넌트

#### config.py
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API 설정
    API_BASE_URL: str = "http://apis.data.go.kr/1160100/service/GetBondIssuInfoService"
    API_SERVICE_KEY: str
    API_TIMEOUT: int = 30
    API_RETRY_COUNT: int = 3
    
    # DB 설정
    DATABASE_URL: str
    
    # 배치 설정
    BATCH_SIZE: int = 1000
    MAX_WORKERS: int = 5
    
    class Config:
        env_file = ".env"

settings = Settings()
```

#### api_client.py
```python
import requests
from typing import Dict, List, Optional
from xml.etree import ElementTree as ET
import time
import logging

logger = logging.getLogger(__name__)

class BondAPIClient:
    def __init__(self, service_key: str, base_url: str):
        self.service_key = service_key
        self.base_url = base_url
        
    def fetch_bond_data(
        self, 
        bas_dt: Optional[str] = None,
        crno: Optional[str] = None,
        bond_isur_nm: Optional[str] = None,
        page_no: int = 1,
        num_of_rows: int = 1000
    ) -> Dict:
        """채권 데이터 조회"""
        
        params = {
            'serviceKey': self.service_key,
            'pageNo': page_no,
            'numOfRows': num_of_rows,
            'resultType': 'json'
        }
        
        if bas_dt:
            params['basDt'] = bas_dt
        if crno:
            params['crno'] = crno
        if bond_isur_nm:
            params['bondIsurNm'] = bond_isur_nm
            
        endpoint = f"{self.base_url}/getBondBasiInfo"
        
        for attempt in range(3):
            try:
                response = requests.get(endpoint, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                
                # 에러 체크
                header = data.get('response', {}).get('header', {})
                if header.get('resultCode') != '00':
                    raise Exception(f"API Error: {header.get('resultMsg')}")
                
                return data['response']['body']
                
            except Exception as e:
                logger.error(f"API 호출 실패 (시도 {attempt + 1}/3): {e}")
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
    
    def fetch_all_pages(
        self,
        bas_dt: Optional[str] = None,
        crno: Optional[str] = None,
        bond_isur_nm: Optional[str] = None,
        num_of_rows: int = 1000
    ) -> List[Dict]:
        """전체 페이지 데이터 조회"""
        
        all_items = []
        page_no = 1
        
        while True:
            body = self.fetch_bond_data(
                bas_dt=bas_dt,
                crno=crno,
                bond_isur_nm=bond_isur_nm,
                page_no=page_no,
                num_of_rows=num_of_rows
            )
            
            items = body.get('items', {}).get('item', [])
            
            # 단일 아이템인 경우 리스트로 변환
            if isinstance(items, dict):
                items = [items]
            
            if not items:
                break
                
            all_items.extend(items)
            
            total_count = body.get('totalCount', 0)
            logger.info(f"페이지 {page_no} 처리 완료: {len(items)}건 (전체: {total_count}건)")
            
            # 모든 데이터를 가져왔으면 종료
            if len(all_items) >= total_count:
                break
                
            page_no += 1
            time.sleep(0.5)  # Rate limiting
        
        return all_items
```

#### transformer.py
```python
from typing import Dict, Optional
from datetime import datetime

class BondDataTransformer:
    @staticmethod
    def transform(raw_data: Dict) -> Dict:
        """API 응답 데이터를 DB 스키마에 맞게 변환"""
        
        return {
            # 기본키
            'isin_cd': raw_data.get('isinCd'),
            'bas_dt': BondDataTransformer._parse_date(raw_data.get('basDt')),
            
            # 기본정보
            'crno': raw_data.get('crno'),
            'isin_cd_nm': raw_data.get('isinCdNm'),
            'scrs_itms_kcd': raw_data.get('scrsItmsKcd'),
            'scrs_itms_kcd_nm': raw_data.get('scrsItmsKcdNm'),
            'bond_issu_cur_cd': raw_data.get('bondIssuCurCd'),
            'bond_issu_cur_cd_nm': raw_data.get('bondIssuCurCdNm'),
            'bond_isur_nm': raw_data.get('bondIsurNm'),
            'sic_nm': raw_data.get('sicNm'),
            
            # 발행 정보
            'bond_issu_dt': BondDataTransformer._parse_date(raw_data.get('bondIssuDt')),
            'bond_expr_dt': BondDataTransformer._parse_date(raw_data.get('bondExprDt')),
            'bond_issu_amt': BondDataTransformer._parse_decimal(raw_data.get('bondIssuAmt')),
            'bond_pymt_amt': BondDataTransformer._parse_decimal(raw_data.get('bondPymtAmt')),
            'bond_bal': BondDataTransformer._parse_decimal(raw_data.get('bondBal')),
            
            # 금리 정보
            'irt_chng_dcd': raw_data.get('irtChngDcd'),
            'irt_chng_dcd_nm': raw_data.get('irtChngDcdNm'),
            'bond_srfc_inrt': BondDataTransformer._parse_decimal(raw_data.get('bondSrfcInrt')),
            'bond_int_tcd': raw_data.get('bondIntTcd'),
            'bond_int_tcd_nm': raw_data.get('bondIntTcdNm'),
            'int_pay_cycl_ctt': raw_data.get('intPayCyclCtt'),
            'nxtm_copn_dt': BondDataTransformer._parse_date(raw_data.get('nxtmCopnDt')),
            'rbf_copn_dt': BondDataTransformer._parse_date(raw_data.get('rbfCopnDt')),
            
            # 보증 및 순위
            'grn_dcd': raw_data.get('grnDcd'),
            'grn_dcd_nm': raw_data.get('grnDcdNm'),
            'bond_rnkn_dcd': raw_data.get('bondRnknDcd'),
            'bond_rnkn_dcd_nm': raw_data.get('bondRnknDcdNm'),
            
            # 신용평가
            'kis_scrs_itms_kcd': raw_data.get('kisScrsItmsKcd'),
            'kis_scrs_itms_kcd_nm': raw_data.get('kisScrsItmsKcdNm'),
            'kbp_scrs_itms_kcd': raw_data.get('kbpScrsItmsKcd'),
            'kbp_scrs_itms_kcd_nm': raw_data.get('kbpScrsItmsKcdNm'),
            'nice_scrs_itms_kcd': raw_data.get('niceScrsItmsKcd'),
            'nice_scrs_itms_kcd_nm': raw_data.get('niceScrsItmsKcdNm'),
            'fn_scrs_itms_kcd': raw_data.get('fnScrsItmsKcd'),
            'fn_scrs_itms_kcd_nm': raw_data.get('fnScrsItmsKcdNm'),
            
            # 옵션 및 특이사항
            'optn_tcd': raw_data.get('optnTcd'),
            'optn_tcd_nm': raw_data.get('optnTcdNm'),
            'pclr_bond_kcd': raw_data.get('pclrBondKcd'),
            'pclr_bond_kcd_nm': raw_data.get('pclrBondKcdNm'),
            
            # 모집 및 상장
            'bond_offr_mcd': raw_data.get('bondOffrMcd'),
            'bond_offr_mcd_nm': raw_data.get('bondOffrMcdNm'),
            'lstg_dt': BondDataTransformer._parse_date(raw_data.get('lstgDt')),
            'txtn_dcd': raw_data.get('txtnDcd'),
            'txtn_dcd_nm': raw_data.get('txtnDcdNm'),
            
            # 상환 정보
            'pamt_rdpt_mcd': raw_data.get('pamtRdptMcd'),
            'pamt_rdpt_mcd_nm': raw_data.get('pamtRdptMcdNm'),
            
            # 여부 정보
            'strips_psbl_yn': raw_data.get('stripsPsblYn'),
            'strips_nm': raw_data.get('stripsNm'),
            'pris_lnkg_bond_yn': raw_data.get('prisLnkgBondYn'),
            'crfnd_yn': raw_data.get('crfndYn'),
            'prmnc_bond_yn': raw_data.get('prmncBondYn'),
            'qib_trgt_scrt_yn': raw_data.get('qibTrgtScrtYn'),
            'elps_int_pay_yn': raw_data.get('elpsIntPayYn'),
            
            # 기관 정보
            'piam_pay_inst_nm': raw_data.get('piamPayInstNm'),
            'piam_pay_brof_nm': raw_data.get('piamPayBrofNm'),
            'bond_reg_inst_dcd': raw_data.get('bondRegInstDcd'),
            'bond_reg_inst_dcd_nm': raw_data.get('bondRegInstDcdNm'),
            'issu_dpty_nm': raw_data.get('issuDptyNm'),
            'bond_undt_inst_nm': raw_data.get('bondUndtInstNm'),
            'bond_grn_inst_nm': raw_data.get('bondGrnInstNm'),
            'cpbd_mng_cmpy_nm': raw_data.get('cpbdMngCmpyNm'),
            
            # 자금용도
            'cpt_usge_dcd': raw_data.get('cptUsgeDcd'),
            'cpt_usge_dcd_nm': raw_data.get('cptUsgeDcdNm'),
            
            # 이자 지급
            'bnk_hldy_int_pydy_dcd': raw_data.get('bnkHldyIntPydyDcd'),
            'bnk_hldy_int_pydy_dcd_nm': raw_data.get('bnkHldyIntPydyDcdNm'),
            'sttr_hldy_int_pydy_dcd': raw_data.get('sttrHldyIntPydyDcd'),
            'sttr_hldy_int_pydy_dcd_nm': raw_data.get('sttrHldyIntPydyDcdNm'),
            'int_pay_mmnt_dcd': raw_data.get('intPayMmntDcd'),
            'int_pay_mmnt_dcd_nm': raw_data.get('intPayMmntDcdNm'),
            
            # 권리행사 및 산정
            'rgt_exert_mnbd_dcd': raw_data.get('rgtExertMnbdDcd'),
            'rgt_exert_mnbd_dcd_nm': raw_data.get('rgtExertMnbdDcdNm'),
            'int_cmpu_mcd': raw_data.get('intCmpuMcd'),
            'int_cmpu_mcd_nm': raw_data.get('intCmpuMcdNm'),
            
            # 기타 날짜
            'prmnc_bond_tmn_dt': BondDataTransformer._parse_date(raw_data.get('prmncBondTmnDt')),
            'qib_tmn_dt': BondDataTransformer._parse_date(raw_data.get('qibTmnDt')),
        }
    
    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
        """YYYYMMDD 형식을 date 객체로 변환"""
        if not date_str or date_str in ['', 'NULL']:
            return None
        try:
            return datetime.strptime(date_str, '%Y%m%d').date()
        except:
            return None
    
    @staticmethod
    def _parse_decimal(value: Optional[str]) -> Optional[float]:
        """문자열을 Decimal로 변환"""
        if not value or value in ['', 'NULL']:
            return None
        try:
            return float(value)
        except:
            return None
```

## 7. 적재 전략

### 7.1 전체 적재 (Full Load)
```python
# 특정 기준일자의 모든 데이터 적재
loader.load_by_date('20240101')
```

### 7.2 증분 적재 (Incremental Load)
```python
# 최근 N일간의 데이터만 적재
loader.load_recent_days(days=7)
```

### 7.3 특정 조건 적재
```python
# 특정 발행인의 데이터만 적재
loader.load_by_issuer('한국전력공사')

# 특정 법인의 데이터만 적재
loader.load_by_crno('1146710001456')
```

## 8. 에러 처리 전략

### API 에러코드 대응
```python
ERROR_CODES = {
    '1': 'APPLICATION_ERROR',
    '10': 'INVALID_REQUEST_PARAMETER_ERROR',
    '12': 'NO_OPENAPI_SERVICE_ERROR',
    '20': 'SERVICE_ACCESS_DENIED_ERROR',
    '22': 'LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR',
    '30': 'SERVICE_KEY_IS_NOT_REGISTERED_ERROR',
    '31': 'DEADLINE_HAS_EXPIRED_ERROR',
    '32': 'UNREGISTERED_IP_ERROR',
    '99': 'UNKNOWN_ERROR'
}
```

### 재시도 로직
- 네트워크 오류: 3회 재시도 (exponential backoff)
- Rate limit 초과: 대기 후 재시도
- 데이터 검증 실패: 로깅 후 스킵

## 9. 배치 스케줄링

### 9.1 일일 배치
```bash
# crontab 설정
0 2 * * * /path/to/venv/bin/python /path/to/bond_loader.py --mode daily
```

### 9.2 주간 전체 동기화
```bash
# 매주 일요일 새벽 3시
0 3 * * 0 /path/to/venv/bin/python /path/to/bond_loader.py --mode full
```

## 10. 모니터링 및 로깅

### 로그 레벨
- INFO: 정상 처리 현황
- WARNING: 데이터 품질 이슈
- ERROR: API 오류, DB 오류
- CRITICAL: 배치 실패

### 지표 수집
- 처리 건수
- 처리 시간
- 에러 발생 횟수
- API 응답 시간

## 11. 데이터 품질 검증

### 필수 필드 체크
- isinCd, basDt는 반드시 존재
- crno는 13자리 숫자
- 날짜 필드는 YYYYMMDD 형식

### 비즈니스 룰 검증
- 만기일자 >= 발행일자
- 채권잔액 <= 발행금액
- 이율은 0 이상

## 12. 성능 최적화

### Bulk Insert 사용
```python
# 1000건씩 배치 처리
session.bulk_insert_mappings(BondBasicInfo, transformed_data)
```

### 인덱스 최적화
- 조회가 많은 컬럼에 인덱스 생성
- 복합 인덱스 활용

### 병렬 처리
- 여러 날짜를 동시에 처리
- ThreadPoolExecutor 활용

## 13. 구현 우선순위

1. **Phase 1**: API 클라이언트 + 기본 적재
2. **Phase 2**: 데이터 검증 + 에러 처리
3. **Phase 3**: 배치 스케줄링 + 모니터링
4. **Phase 4**: 성능 최적화 + 병렬 처리
