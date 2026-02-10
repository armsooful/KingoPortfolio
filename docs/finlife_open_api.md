# 금융감독원 OPEN API 목록

## 권역코드
- `020000` 은행
- `030200` 여신전문금융
- `030300` 저축은행
- `050000` 보험
- `060000` 금융투자

## 금융회사 API
- `http://finlife.fss.or.kr/finlifeapi/companySearch.json?auth=177bac3760aabb417642c45ad8bc8b31&topFinGrpNo=020000&pageNo=1`

## 정기예금 API
- `http://finlife.fss.or.kr/finlifeapi/depositProductsSearch.json?auth=177bac3760aabb417642c45ad8bc8b31&topFinGrpNo=020000&pageNo=1`

## 적금 API
- `http://finlife.fss.or.kr/finlifeapi/savingProductsSearch.json?auth=177bac3760aabb417642c45ad8bc8b31&topFinGrpNo=020000&pageNo=1`

## 연금저축 API
- `http://finlife.fss.or.kr/finlifeapi/annuitySavingProductsSearch.json?auth=177bac3760aabb417642c45ad8bc8b31&topFinGrpNo=060000&pageNo=1`

## 주택담보대출 API
- `http://finlife.fss.or.kr/finlifeapi/mortgageLoanProductsSearch.json?auth=177bac3760aabb417642c45ad8bc8b31&topFinGrpNo=050000&pageNo=1`

## 전세자금대출 API
- `http://finlife.fss.or.kr/finlifeapi/rentHouseLoanProductsSearch.json?auth=177bac3760aabb417642c45ad8bc8b31&topFinGrpNo=050000&pageNo=1`

## 개인신용대출 API
- `http://finlife.fss.or.kr/finlifeapi/creditLoanProductsSearch.json?auth=177bac3760aabb417642c45ad8bc8b31&topFinGrpNo=050000&pageNo=1`

## 공통 요청 파라미터 예시
- `auth`: 인증키
- `topFinGrpNo`: 권역코드
- `pageNo`: 페이지 번호 (1부터 시작)

## 응답 구조 확인 방법 (권장)
- 응답 스키마는 API별로 다를 수 있으니 실제 호출 결과로 확인한다.

```bash
curl -s "http://finlife.fss.or.kr/finlifeapi/depositProductsSearch.json?auth=YOUR_KEY&topFinGrpNo=020000&pageNo=1" \
  | head -n 20
```

```bash
curl -s "http://finlife.fss.or.kr/finlifeapi/depositProductsSearch.json?auth=YOUR_KEY&topFinGrpNo=020000&pageNo=1" \
  | head -n 1
```

```bash
curl -s "http://finlife.fss.or.kr/finlifeapi/depositProductsSearch.json?auth=YOUR_KEY&topFinGrpNo=020000&pageNo=1" \
  | jq '. | length'
```

## 응답 필드 정리 (실제 응답으로 보완)
- 실제 JSON 응답을 확보한 뒤 주요 필드(예: 결과코드/메시지, 목록 배열)를 표로 정리하는 것을 권장.

## 공통 필드 설명
| 필드 | 의미 |
| --- | --- |
| `dcls_month` | 공시 기준 월 (YYYYMM) |
| `dcls_strt_day` | 공시 시작일 (YYYYMMDD) |
| `dcls_end_day` | 공시 종료일 (YYYYMMDD, 미정이면 `null`) |
| `fin_co_no` | 금융회사 코드 |
| `fin_prdt_cd` | 금융상품 코드 |
| `kor_co_nm` | 금융회사명 |
| `fin_prdt_nm` | 금융상품명 |
| `join_way` | 가입방법 |
| `err_cd` | 결과 코드 |
| `err_msg` | 결과 메시지 |
| `total_count` | 전체 결과 건수 |
| `max_page_no` | 최대 페이지 |
| `now_page_no` | 현재 페이지 |
| `fin_co_subm_day` | 제출일시 (YYYYMMDDHHmm) |

## 공통 코드값 (관측)
아래 값들은 제공된 응답 예시에서 확인된 코드만 정리했다.

### `join_deny`
| 코드 | 의미 |
| --- | --- |
| `1` | 가입제한 있음 |
| `3` | 가입대상 제한(특정 조건) |

### `intr_rate_type`
| 코드 | 의미 |
| --- | --- |
| `S` | 단리 |
| `M` | 복리 |

### `rsrv_type`
| 코드 | 의미 |
| --- | --- |
| `S` | 정액적립식 |
| `F` | 자유적립식 |

### `rpay_type`
| 코드 | 의미 |
| --- | --- |
| `S` | 만기일시상환방식 |
| `D` | 분할상환방식 |

### `lend_rate_type`
| 코드 | 의미 |
| --- | --- |
| `F` | 고정금리 |
| `C` | 변동금리 |

### `mrtg_type`
| 코드 | 의미 |
| --- | --- |
| `A` | 아파트 |
| `E` | 아파트외 |

### `crdt_lend_rate_type`
| 코드 | 의미 |
| --- | --- |
| `A` | 대출금리 |
| `B` | 기준금리 |
| `C` | 가산금리 |

### `pnsn_recp_trm`
| 코드 | 의미 |
| --- | --- |
| `A` | 10년 확정 |
| `B` | 20년 확정 |

## 금융회사 API 응답 구조 예시 (companySearch.json)
| 경로 | 설명 |
| --- | --- |
| `result.prdt_div` | 상품구분 |
| `result.total_count` | 전체 건수 |
| `result.max_page_no` | 최대 페이지 번호 |
| `result.now_page_no` | 현재 페이지 번호 |
| `result.err_cd` | 결과코드 |
| `result.err_msg` | 결과메시지 |
| `result.baseList[]` | 금융회사 기본 정보 목록 |
| `result.optionList[]` | 금융회사 지역/존재 여부 목록 |

### 샘플 JSON 스니펫
```json
{
  "result": {
    "prdt_div": "F",
    "total_count": 18,
    "max_page_no": 1,
    "now_page_no": 1,
    "err_cd": "000",
    "err_msg": "정상",
    "baseList": [
      {
        "dcls_month": "202601",
        "fin_co_no": "0010001",
        "kor_co_nm": "우리은행",
        "dcls_chrg_man": "개인상품마케팅부, 1588-5000",
        "homp_url": "https://spot.wooribank.com",
        "cal_tel": "15885000"
      }
    ],
    "optionList": [
      {
        "dcls_month": "202601",
        "fin_co_no": "0010001",
        "area_cd": "01",
        "area_nm": "서울",
        "exis_yn": "Y"
      }
    ]
  }
}
```

### `result.baseList[]` 주요 필드
| 필드 | 설명 |
| --- | --- |
| `dcls_month` | 공시월 |
| `fin_co_no` | 금융회사 코드 |
| `kor_co_nm` | 금융회사명 |
| `dcls_chrg_man` | 공시담당자/문의처 |
| `homp_url` | 홈페이지 URL |
| `cal_tel` | 대표 전화번호 |

### `result.optionList[]` 주요 필드
| 필드 | 설명 |
| --- | --- |
| `dcls_month` | 공시월 |
| `fin_co_no` | 금융회사 코드 |
| `area_cd` | 지역 코드 |
| `area_nm` | 지역명 |
| `exis_yn` | 존재 여부 (`Y`/`N`) |

## 정기예금 API 응답 구조 예시 (depositProductsSearch.json)
| 경로 | 설명 |
| --- | --- |
| `result.prdt_div` | 상품구분 |
| `result.total_count` | 전체 건수 |
| `result.max_page_no` | 최대 페이지 번호 |
| `result.now_page_no` | 현재 페이지 번호 |
| `result.err_cd` | 결과코드 |
| `result.err_msg` | 결과메시지 |
| `result.baseList[]` | 정기예금 상품 기본 정보 목록 |
| `result.optionList[]` | 금리 옵션 목록 |

### 샘플 JSON 스니펫
```json
{
  "result": {
    "prdt_div": "D",
    "total_count": 37,
    "max_page_no": 1,
    "now_page_no": 1,
    "err_cd": "000",
    "err_msg": "정상",
    "baseList": [
      {
        "dcls_month": "202601",
        "fin_co_no": "0010001",
        "fin_prdt_cd": "WR0001B",
        "kor_co_nm": "우리은행",
        "fin_prdt_nm": "WON플러스예금",
        "join_way": "인터넷,스마트폰"
      }
    ],
    "optionList": [
      {
        "dcls_month": "202601",
        "fin_co_no": "0010001",
        "fin_prdt_cd": "WR0001B",
        "intr_rate_type": "S",
        "intr_rate_type_nm": "단리",
        "save_trm": "12",
        "intr_rate": 2.8,
        "intr_rate2": 2.8
      }
    ]
  }
}
```

### `result.baseList[]` 주요 필드
| 필드 | 설명 |
| --- | --- |
| `dcls_month` | 공시월 |
| `fin_co_no` | 금융회사 코드 |
| `fin_prdt_cd` | 금융상품 코드 |
| `kor_co_nm` | 금융회사명 |
| `fin_prdt_nm` | 금융상품명 |
| `join_way` | 가입방법 |
| `mtrt_int` | 만기 후 이자율 |
| `spcl_cnd` | 우대조건 |
| `join_deny` | 가입제한 |
| `join_member` | 가입대상 |
| `etc_note` | 기타 유의사항 |
| `max_limit` | 최고한도 |
| `dcls_strt_day` | 공시 시작일 |
| `dcls_end_day` | 공시 종료일 |
| `fin_co_subm_day` | 제출일시 |

### `result.optionList[]` 주요 필드
| 필드 | 설명 |
| --- | --- |
| `dcls_month` | 공시월 |
| `fin_co_no` | 금융회사 코드 |
| `fin_prdt_cd` | 금융상품 코드 |
| `intr_rate_type` | 금리유형 코드 |
| `intr_rate_type_nm` | 금리유형명 |
| `save_trm` | 저축기간(개월) |
| `intr_rate` | 저축금리 |
| `intr_rate2` | 최고우대금리 |

## 적금 API 응답 구조 예시 (savingProductsSearch.json)
| 경로 | 설명 |
| --- | --- |
| `result.prdt_div` | 상품구분 |
| `result.total_count` | 전체 건수 |
| `result.max_page_no` | 최대 페이지 번호 |
| `result.now_page_no` | 현재 페이지 번호 |
| `result.err_cd` | 결과코드 |
| `result.err_msg` | 결과메시지 |
| `result.baseList[]` | 적금 상품 기본 정보 목록 |
| `result.optionList[]` | 금리 옵션 목록 |

### 샘플 JSON 스니펫
```json
{
  "result": {
    "prdt_div": "S",
    "total_count": 54,
    "max_page_no": 1,
    "now_page_no": 1,
    "err_cd": "000",
    "err_msg": "정상",
    "baseList": [
      {
        "dcls_month": "202601",
        "fin_co_no": "0010001",
        "fin_prdt_cd": "WR0001F",
        "kor_co_nm": "우리은행",
        "fin_prdt_nm": "우리SUPER주거래적금",
        "join_way": "영업점,인터넷,스마트폰"
      }
    ],
    "optionList": [
      {
        "dcls_month": "202601",
        "fin_co_no": "0010001",
        "fin_prdt_cd": "WR0001F",
        "intr_rate_type": "S",
        "intr_rate_type_nm": "단리",
        "rsrv_type": "S",
        "rsrv_type_nm": "정액적립식",
        "save_trm": "12",
        "intr_rate": 2.15,
        "intr_rate2": 3.55
      }
    ]
  }
}
```

### `result.baseList[]` 주요 필드
| 필드 | 설명 |
| --- | --- |
| `dcls_month` | 공시월 |
| `fin_co_no` | 금융회사 코드 |
| `fin_prdt_cd` | 금융상품 코드 |
| `kor_co_nm` | 금융회사명 |
| `fin_prdt_nm` | 금융상품명 |
| `join_way` | 가입방법 |
| `mtrt_int` | 만기 후 이자율 |
| `spcl_cnd` | 우대조건 |
| `join_deny` | 가입제한 |
| `join_member` | 가입대상 |
| `etc_note` | 기타 유의사항 |
| `max_limit` | 최고한도 |
| `dcls_strt_day` | 공시 시작일 |
| `dcls_end_day` | 공시 종료일 |
| `fin_co_subm_day` | 제출일시 |

### `result.optionList[]` 주요 필드
| 필드 | 설명 |
| --- | --- |
| `dcls_month` | 공시월 |
| `fin_co_no` | 금융회사 코드 |
| `fin_prdt_cd` | 금융상품 코드 |
| `intr_rate_type` | 금리유형 코드 |
| `intr_rate_type_nm` | 금리유형명 |
| `rsrv_type` | 적립유형 코드 |
| `rsrv_type_nm` | 적립유형명 |
| `save_trm` | 저축기간(개월) |
| `intr_rate` | 저축금리 |
| `intr_rate2` | 최고우대금리 |

## 연금저축 API 응답 구조 예시 (annuitySavingProductsSearch.json)
| 경로 | 설명 |
| --- | --- |
| `result.prdt_div` | 상품구분 |
| `result.total_count` | 전체 건수 |
| `result.max_page_no` | 최대 페이지 번호 |
| `result.now_page_no` | 현재 페이지 번호 |
| `result.err_cd` | 결과코드 |
| `result.err_msg` | 결과메시지 |
| `result.baseList[]` | 연금저축 상품 기본 정보 목록 |
| `result.optionList[]` | 연금 수령 옵션 목록 |

### 샘플 JSON 스니펫
```json
{
  "result": {
    "prdt_div": "P",
    "total_count": 297,
    "max_page_no": 60,
    "now_page_no": 1,
    "err_cd": "000",
    "err_msg": "정상",
    "baseList": [
      {
        "dcls_month": "202010",
        "fin_co_no": "0011317",
        "fin_prdt_cd": "K55232C99568",
        "kor_co_nm": "NH-Amundi",
        "fin_prdt_nm": "NH-Amundi 필승 코리아 증권투자신탁",
        "pnsn_kind_nm": "연금저축펀드",
        "prdt_type_nm": "주식형"
      }
    ],
    "optionList": [
      {
        "dcls_month": "202010",
        "fin_co_no": "0011317",
        "fin_prdt_cd": "K55232C99568",
        "pnsn_recp_trm_nm": "10년 확정",
        "pnsn_entr_age_nm": "30세",
        "mon_paym_atm_nm": "100,000원",
        "paym_prd_nm": "10년",
        "pnsn_strt_age_nm": "60세",
        "pnsn_recp_amt": 201304
      }
    ]
  }
}
```

### `result.baseList[]` 주요 필드
| 필드 | 설명 |
| --- | --- |
| `dcls_month` | 공시월 |
| `fin_co_no` | 금융회사 코드 |
| `fin_prdt_cd` | 금융상품 코드 |
| `kor_co_nm` | 금융회사명 |
| `fin_prdt_nm` | 금융상품명 |
| `join_way` | 가입방법 |
| `pnsn_kind` | 연금 유형 코드 |
| `pnsn_kind_nm` | 연금 유형명 |
| `sale_strt_day` | 판매 시작일 |
| `mntn_cnt` | 운용(적립) 금액 |
| `prdt_type` | 상품 유형 코드 |
| `prdt_type_nm` | 상품 유형명 |
| `avg_prft_rate` | 평균 수익률 |
| `dcls_rate` | 공시이율 |
| `guar_rate` | 최저보증이율 |
| `btrm_prft_rate_1` | 과거 수익률 1 |
| `btrm_prft_rate_2` | 과거 수익률 2 |
| `btrm_prft_rate_3` | 과거 수익률 3 |
| `etc` | 기타사항 |
| `sale_co` | 판매사 |
| `dcls_strt_day` | 공시 시작일 |
| `dcls_end_day` | 공시 종료일 |
| `fin_co_subm_day` | 제출일시 |

### `result.optionList[]` 주요 필드
| 필드 | 설명 |
| --- | --- |
| `dcls_month` | 공시월 |
| `fin_co_no` | 금융회사 코드 |
| `fin_prdt_cd` | 금융상품 코드 |
| `pnsn_recp_trm` | 연금수령기간 코드 |
| `pnsn_recp_trm_nm` | 연금수령기간명 |
| `pnsn_entr_age` | 연금가입나이 코드 |
| `pnsn_entr_age_nm` | 연금가입나이명 |
| `mon_paym_atm` | 월 납입금액 코드 |
| `mon_paym_atm_nm` | 월 납입금액명 |
| `paym_prd` | 납입기간 코드 |
| `paym_prd_nm` | 납입기간명 |
| `pnsn_strt_age` | 연금개시나이 코드 |
| `pnsn_strt_age_nm` | 연금개시나이명 |
| `pnsn_recp_amt` | 연금수령액 |

## 주택담보대출 API 응답 구조 예시 (mortgageLoanProductsSearch.json)
| 경로 | 설명 |
| --- | --- |
| `result.prdt_div` | 상품구분 |
| `result.total_count` | 전체 건수 |
| `result.max_page_no` | 최대 페이지 번호 |
| `result.now_page_no` | 현재 페이지 번호 |
| `result.err_cd` | 결과코드 |
| `result.err_msg` | 결과메시지 |
| `result.baseList[]` | 주택담보대출 상품 기본 정보 목록 |
| `result.optionList[]` | 금리 옵션 목록 |

### 샘플 JSON 스니펫
```json
{
  "result": {
    "prdt_div": "M",
    "total_count": 20,
    "max_page_no": 1,
    "now_page_no": 1,
    "err_cd": "000",
    "err_msg": "정상",
    "baseList": [
      {
        "dcls_month": "202601",
        "fin_co_no": "0010593",
        "fin_prdt_cd": "302301",
        "kor_co_nm": "한화생명보험주식회사",
        "fin_prdt_nm": "홈드림모기지론",
        "join_way": "영업점,모집인"
      }
    ],
    "optionList": [
      {
        "dcls_month": "202601",
        "fin_co_no": "0010593",
        "fin_prdt_cd": "302301",
        "mrtg_type_nm": "아파트",
        "rpay_type_nm": "분할상환방식",
        "lend_rate_type_nm": "고정금리",
        "lend_rate_min": 4.68,
        "lend_rate_max": 6.38,
        "lend_rate_avg": 4.79
      }
    ]
  }
}
```

### `result.baseList[]` 주요 필드
| 필드 | 설명 |
| --- | --- |
| `dcls_month` | 공시월 |
| `fin_co_no` | 금융회사 코드 |
| `fin_prdt_cd` | 금융상품 코드 |
| `kor_co_nm` | 금융회사명 |
| `fin_prdt_nm` | 금융상품명 |
| `join_way` | 가입방법 |
| `loan_inci_expn` | 대출 부대비용 |
| `erly_rpay_fee` | 중도상환수수료 |
| `dly_rate` | 연체이자율 |
| `loan_lmt` | 대출한도 |
| `dcls_strt_day` | 공시 시작일 |
| `dcls_end_day` | 공시 종료일 |
| `fin_co_subm_day` | 제출일시 |

### `result.optionList[]` 주요 필드
| 필드 | 설명 |
| --- | --- |
| `dcls_month` | 공시월 |
| `fin_co_no` | 금융회사 코드 |
| `fin_prdt_cd` | 금융상품 코드 |
| `mrtg_type` | 담보유형 코드 |
| `mrtg_type_nm` | 담보유형명 |
| `rpay_type` | 상환방식 코드 |
| `rpay_type_nm` | 상환방식명 |
| `lend_rate_type` | 금리유형 코드 |
| `lend_rate_type_nm` | 금리유형명 |
| `lend_rate_min` | 최저금리 |
| `lend_rate_max` | 최고금리 |
| `lend_rate_avg` | 평균금리 |

## 전세자금대출 API 응답 구조 예시 (rentHouseLoanProductsSearch.json)
| 경로 | 설명 |
| --- | --- |
| `result.prdt_div` | 상품구분 |
| `result.total_count` | 전체 건수 |
| `result.max_page_no` | 최대 페이지 번호 |
| `result.now_page_no` | 현재 페이지 번호 |
| `result.err_cd` | 결과코드 |
| `result.err_msg` | 결과메시지 |
| `result.baseList[]` | 전세자금대출 상품 기본 정보 목록 |
| `result.optionList[]` | 금리 옵션 목록 |

### 샘플 JSON 스니펫
```json
{
  "result": {
    "prdt_div": "R",
    "total_count": 9,
    "max_page_no": 1,
    "now_page_no": 1,
    "err_cd": "000",
    "err_msg": "정상",
    "baseList": [
      {
        "dcls_month": "202601",
        "fin_co_no": "0010594",
        "fin_prdt_cd": "ABLKeymoney1",
        "kor_co_nm": "에이비엘생명보험주식회사",
        "fin_prdt_nm": "ABL전세자금대출",
        "join_way": "영업점,모집인"
      }
    ],
    "optionList": [
      {
        "dcls_month": "202601",
        "fin_co_no": "0010594",
        "fin_prdt_cd": "ABLKeymoney1",
        "rpay_type_nm": "만기일시상환방식",
        "lend_rate_type_nm": "고정금리",
        "lend_rate_min": 4.25,
        "lend_rate_max": 4.35,
        "lend_rate_avg": 4.18
      }
    ]
  }
}
```

### `result.baseList[]` 주요 필드
| 필드 | 설명 |
| --- | --- |
| `dcls_month` | 공시월 |
| `fin_co_no` | 금융회사 코드 |
| `fin_prdt_cd` | 금융상품 코드 |
| `kor_co_nm` | 금융회사명 |
| `fin_prdt_nm` | 금융상품명 |
| `join_way` | 가입방법 |
| `loan_inci_expn` | 대출 부대비용 |
| `erly_rpay_fee` | 중도상환수수료 |
| `dly_rate` | 연체이자율 |
| `loan_lmt` | 대출한도 |
| `dcls_strt_day` | 공시 시작일 |
| `dcls_end_day` | 공시 종료일 |
| `fin_co_subm_day` | 제출일시 |

### `result.optionList[]` 주요 필드
| 필드 | 설명 |
| --- | --- |
| `dcls_month` | 공시월 |
| `fin_co_no` | 금융회사 코드 |
| `fin_prdt_cd` | 금융상품 코드 |
| `rpay_type` | 상환방식 코드 |
| `rpay_type_nm` | 상환방식명 |
| `lend_rate_type` | 금리유형 코드 |
| `lend_rate_type_nm` | 금리유형명 |
| `lend_rate_min` | 최저금리 |
| `lend_rate_max` | 최고금리 |
| `lend_rate_avg` | 평균금리 |

## 개인신용대출 API 응답 구조 예시 (creditLoanProductsSearch.json)
| 경로 | 설명 |
| --- | --- |
| `result.prdt_div` | 상품구분 |
| `result.total_count` | 전체 건수 |
| `result.max_page_no` | 최대 페이지 번호 |
| `result.now_page_no` | 현재 페이지 번호 |
| `result.err_cd` | 결과코드 |
| `result.err_msg` | 결과메시지 |
| `result.baseList[]` | 개인신용대출 상품 기본 정보 목록 |
| `result.optionList[]` | 신용등급별 금리 목록 |

### 샘플 JSON 스니펫
```json
{
  "result": {
    "prdt_div": "C",
    "total_count": 7,
    "max_page_no": 1,
    "now_page_no": 1,
    "err_cd": "000",
    "err_msg": "정상",
    "baseList": [
      {
        "dcls_month": "202601",
        "fin_co_no": "0010593",
        "fin_prdt_cd": "개인신용대출",
        "kor_co_nm": "한화생명보험주식회사",
        "fin_prdt_nm": "개인신용대출",
        "cb_name": "NICE, KCB"
      }
    ],
    "optionList": [
      {
        "dcls_month": "202601",
        "fin_co_no": "0010593",
        "fin_prdt_cd": "개인신용대출",
        "crdt_lend_rate_type_nm": "대출금리",
        "crdt_grad_1": 8.66,
        "crdt_grad_4": 9.57,
        "crdt_grad_avg": 9.09
      }
    ]
  }
}
```

### `result.baseList[]` 주요 필드
| 필드 | 설명 |
| --- | --- |
| `dcls_month` | 공시월 |
| `fin_co_no` | 금융회사 코드 |
| `fin_prdt_cd` | 금융상품 코드 |
| `crdt_prdt_type` | 신용상품 유형 코드 |
| `kor_co_nm` | 금융회사명 |
| `fin_prdt_nm` | 금융상품명 |
| `join_way` | 가입방법 |
| `cb_name` | 신용평가사 |
| `crdt_prdt_type_nm` | 신용상품 유형명 |
| `dcls_strt_day` | 공시 시작일 |
| `dcls_end_day` | 공시 종료일 |
| `fin_co_subm_day` | 제출일시 |

### `result.optionList[]` 주요 필드
| 필드 | 설명 |
| --- | --- |
| `dcls_month` | 공시월 |
| `fin_co_no` | 금융회사 코드 |
| `fin_prdt_cd` | 금융상품 코드 |
| `crdt_prdt_type` | 신용상품 유형 코드 |
| `crdt_lend_rate_type` | 금리구분 코드 |
| `crdt_lend_rate_type_nm` | 금리구분명 |
| `crdt_grad_1` | 신용등급 1 금리 |
| `crdt_grad_4` | 신용등급 4 금리 |
| `crdt_grad_5` | 신용등급 5 금리 |
| `crdt_grad_6` | 신용등급 6 금리 |
| `crdt_grad_10` | 신용등급 10 금리 |
| `crdt_grad_11` | 신용등급 11 금리 |
| `crdt_grad_12` | 신용등급 12 금리 |
| `crdt_grad_13` | 신용등급 13 금리 |
| `crdt_grad_avg` | 평균금리 |
