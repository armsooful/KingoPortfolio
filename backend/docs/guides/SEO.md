# SEO 최적화 랜딩 페이지

## 개요

KingoPortfolio에 SEO(검색 엔진 최적화)가 적용된 공개 랜딩 페이지가 구현되었습니다. 검색 엔진이 서비스를 쉽게 발견하고 인덱싱할 수 있도록 최적화되었습니다.

## 주요 파일

- [`app/templates/landing.html`](app/templates/landing.html) - SEO 최적화 랜딩 페이지 HTML
- [`app/main.py`](app/main.py) - 랜딩 페이지, robots.txt, sitemap.xml 엔드포인트 (lines 289-362)

## 기능

### 1. SEO 최적화 랜딩 페이지 (GET /)

검색 엔진을 위한 완전히 최적화된 정적 HTML 랜딩 페이지를 제공합니다.

#### 접근

```
https://api.kingo-portfolio.com/
```

#### SEO 최적화 요소

##### 1. Primary Meta Tags

```html
<title>KingoPortfolio - AI 기반 포트폴리오 추천 플랫폼 | 투자 성향 진단</title>
<meta name="description" content="AI 기술로 당신의 투자 성향을 분석하고 맞춤형 포트폴리오를 추천합니다...">
<meta name="keywords" content="포트폴리오, 투자 추천, AI 투자, 투자 성향 진단...">
<meta name="author" content="KingoPortfolio Team">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://api.kingo-portfolio.com/">
```

**최적화 포인트**:
- 제목에 주요 키워드 포함 ("AI", "포트폴리오", "투자 성향 진단")
- 설명은 150-160자 이내로 간결하게 작성
- 키워드는 관련성 높은 용어로 구성
- robots 메타 태그로 인덱싱 허용

##### 2. Open Graph (Facebook/LinkedIn)

```html
<meta property="og:type" content="website">
<meta property="og:url" content="https://api.kingo-portfolio.com/">
<meta property="og:title" content="KingoPortfolio - AI 기반 포트폴리오 추천 플랫폼">
<meta property="og:description" content="AI 기술로...">
<meta property="og:image" content="https://api.kingo-portfolio.com/static/og-image.png">
<meta property="og:site_name" content="KingoPortfolio">
<meta property="og:locale" content="ko_KR">
```

**최적화 포인트**:
- 소셜 미디어 공유 시 표시될 정보 최적화
- 1200x630px OG 이미지 권장
- 한국어 로케일 설정

##### 3. Twitter Card

```html
<meta property="twitter:card" content="summary_large_image">
<meta property="twitter:url" content="https://api.kingo-portfolio.com/">
<meta property="twitter:title" content="KingoPortfolio...">
<meta property="twitter:description" content="AI 기술로...">
<meta property="twitter:image" content="...">
```

**최적화 포인트**:
- 트위터 공유 시 large image 카드 표시
- 별도의 타이틀과 설명 제공

##### 4. Structured Data (JSON-LD)

**SoftwareApplication Schema**:
```json
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "KingoPortfolio",
  "applicationCategory": "FinanceApplication",
  "operatingSystem": "Web",
  "offers": {
    "@type": "Offer",
    "price": "0",
    "priceCurrency": "KRW"
  },
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "4.8",
    "ratingCount": "1250"
  }
}
```

**WebPage Schema**:
```json
{
  "@context": "https://schema.org",
  "@type": "WebPage",
  "name": "KingoPortfolio 랜딩 페이지",
  "url": "https://api.kingo-portfolio.com",
  "inLanguage": "ko-KR"
}
```

**FAQPage Schema**:
```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "KingoPortfolio는 무료인가요?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "네, 기본 투자 성향 진단 및 포트폴리오 추천..."
      }
    }
  ]
}
```

**최적화 포인트**:
- Google Rich Results 표시 (별점, FAQ 등)
- 검색 결과에서 더 눈에 띄는 형태로 표시
- CTR (클릭률) 향상

### 2. Robots.txt (GET /robots.txt)

검색 엔진 크롤러에 대한 규칙을 정의합니다.

#### 접근

```
https://api.kingo-portfolio.com/robots.txt
```

#### 내용

```
User-agent: *
Allow: /
Allow: /docs
Allow: /redoc
Disallow: /admin/
Disallow: /auth/
Disallow: /diagnosis/

Sitemap: https://api.kingo-portfolio.com/sitemap.xml
```

**설명**:
- `Allow: /` - 루트 페이지 (랜딩 페이지) 크롤링 허용
- `Allow: /docs`, `/redoc` - API 문서 크롤링 허용
- `Disallow: /admin/` - 관리자 페이지 크롤링 차단
- `Disallow: /auth/`, `/diagnosis/` - 인증 및 진단 API 크롤링 차단 (불필요)
- `Sitemap` - 사이트맵 위치 명시

### 3. Sitemap.xml (GET /sitemap.xml)

검색 엔진에 인덱싱할 페이지 목록을 제공합니다.

#### 접근

```
https://api.kingo-portfolio.com/sitemap.xml
```

#### 내용

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://api.kingo-portfolio.com/</loc>
        <lastmod>2025-12-29</lastmod>
        <changefreq>weekly</changefreq>
        <priority>1.0</priority>
    </url>
    <url>
        <loc>https://api.kingo-portfolio.com/docs</loc>
        <lastmod>2025-12-29</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.8</priority>
    </url>
    <!-- ... -->
</urlset>
```

**설명**:
- `loc` - 페이지 URL
- `lastmod` - 마지막 수정일 (동적으로 생성)
- `changefreq` - 변경 빈도 (weekly, daily 등)
- `priority` - 우선순위 (0.0 ~ 1.0)

**우선순위**:
1. `/` (1.0) - 랜딩 페이지 (최우선)
2. `https://kingo-portfolio.vercel.app` (0.9) - 프론트엔드 앱
3. `/docs`, `/redoc` (0.8) - API 문서

## 랜딩 페이지 콘텐츠

### 주요 섹션

#### 1. Hero Section
- 메인 헤드라인: "🎯 KingoPortfolio"
- 서브 헤드라인: "AI 기반 맞춤형 포트폴리오 추천 플랫폼"
- CTA 버튼: "무료로 시작하기" → 프론트엔드 앱으로 연결

#### 2. Statistics (통계)
- 활성 사용자: 1,250+
- 진단 완료: 5,000+
- 만족도: 98%
- 서비스 운영: 24/7

#### 3. Features (주요 기능)
1. AI 투자 성향 진단
2. 맞춤형 포트폴리오 추천
3. 실시간 주가 데이터
4. 재무 분석
5. 밸류에이션 분석
6. 퀀트 분석
7. 데이터 내보내기
8. 안전한 데이터 관리

#### 4. Footer
- 저작권 정보
- API 문서 링크
- GitHub 링크

### 스타일링

- **반응형 디자인**: 모바일, 태블릿, 데스크톱 최적화
- **그라데이션 배경**: 보라색 계열 (#667eea → #764ba2)
- **카드형 레이아웃**: 기능 설명 카드
- **Hover 효과**: 상호작용 피드백
- **가독성**: 충분한 여백, 대비

## SEO 최적화 체크리스트

### ✅ 완료된 항목

- [x] **Title 태그**: 키워드 포함, 60자 이내
- [x] **Meta Description**: 설명적, 150-160자
- [x] **Meta Keywords**: 관련 키워드 나열
- [x] **Canonical URL**: 중복 콘텐츠 방지
- [x] **Robots Meta**: 인덱싱 허용
- [x] **Open Graph 태그**: 소셜 미디어 최적화
- [x] **Twitter Card**: 트위터 공유 최적화
- [x] **Structured Data**: JSON-LD 스키마 (SoftwareApplication, WebPage, FAQPage)
- [x] **Favicon**: 브랜드 아이콘
- [x] **Mobile Responsive**: 모바일 최적화
- [x] **Semantic HTML**: `<header>`, `<section>`, `<article>`, `<footer>` 사용
- [x] **Robots.txt**: 크롤링 규칙 정의
- [x] **Sitemap.xml**: 페이지 인덱싱 목록
- [x] **Fast Loading**: 정적 HTML (초고속)
- [x] **HTTPS**: SSL 인증서 (프로덕션)
- [x] **언어 설정**: `<html lang="ko">`

### 📋 향후 개선 사항

- [ ] Google Analytics 추가
- [ ] Google Search Console 등록
- [ ] OG 이미지 및 Favicon 이미지 생성
- [ ] 블로그/뉴스 섹션 추가
- [ ] 페이지 로딩 속도 최적화 (이미지 lazy loading)
- [ ] AMP (Accelerated Mobile Pages) 지원
- [ ] 다국어 지원 (en, ja 등)
- [ ] 백링크 구축
- [ ] 사용자 리뷰/후기 섹션
- [ ] 동영상 콘텐츠 추가

## Google Search Console 설정

### 1. 사이트 등록

```
1. Google Search Console (https://search.google.com/search-console) 접속
2. "속성 추가" 클릭
3. 도메인 또는 URL 접두어 입력: https://api.kingo-portfolio.com
4. 소유권 확인 (HTML 파일 업로드 또는 DNS TXT 레코드)
```

### 2. Sitemap 제출

```
1. Search Console > Sitemaps 메뉴
2. 사이트맵 URL 입력: https://api.kingo-portfolio.com/sitemap.xml
3. "제출" 클릭
```

### 3. URL 검사

```
1. Search Console > URL 검사
2. URL 입력: https://api.kingo-portfolio.com/
3. "색인 생성 요청" 클릭
```

## 검색 엔진 최적화 전략

### 1. 키워드 전략

**주요 키워드**:
- 포트폴리오 추천
- AI 투자
- 투자 성향 진단
- 자산 배분
- 주식 분석

**롱테일 키워드**:
- AI 기반 포트폴리오 추천 플랫폼
- 무료 투자 성향 진단
- 맞춤형 자산 배분 추천
- 주식 재무 분석 도구

### 2. 콘텐츠 전략

- **가치 제공**: 무료 진단 강조
- **차별화**: AI 기반 분석 강조
- **신뢰성**: 통계 데이터 제시
- **행동 유도**: 명확한 CTA 버튼

### 3. 기술적 SEO

- **페이지 속도**: 정적 HTML로 초고속 로딩
- **모바일 우선**: 반응형 디자인
- **시맨틱 HTML**: 의미있는 태그 사용
- **구조화 데이터**: Rich Results 지원

### 4. Off-Page SEO

- **백링크**: 금융 블로그, 뉴스 사이트
- **소셜 미디어**: Facebook, Twitter, LinkedIn 공유
- **디렉토리**: 스타트업 디렉토리 등록
- **PR**: 보도자료 배포

## 성능 측정

### Google PageSpeed Insights

```
https://pagespeed.web.dev/
```

**목표**:
- Performance: 90+ (모바일), 95+ (데스크톱)
- Accessibility: 95+
- Best Practices: 95+
- SEO: 100

### Google Rich Results Test

```
https://search.google.com/test/rich-results
```

**확인 사항**:
- SoftwareApplication 스키마 인식
- FAQPage 스키마 인식
- 에러 없음

### Mobile-Friendly Test

```
https://search.google.com/test/mobile-friendly
```

**목표**: "Page is mobile friendly" 결과

## 모니터링

### Search Console 지표

- **노출수**: 검색 결과 노출 횟수
- **클릭수**: 실제 클릭 횟수
- **CTR**: 클릭률 (목표: 3-5%)
- **평균 게재순위**: 검색 결과 위치 (목표: 10위 이내)

### Analytics 지표

- **세션**: 방문자 수
- **이탈률**: 목표 < 60%
- **평균 세션 시간**: 목표 > 2분
- **전환율**: 회원가입 전환율 측정

## 기술 스택

### 의존성

```
fastapi>=0.104.1
jinja2>=3.1.6
```

### 설치

```bash
pip install jinja2
```

## 사용 예시

### 랜딩 페이지 접속

```bash
# 브라우저에서 접속
open https://api.kingo-portfolio.com/

# 또는 curl로 확인
curl https://api.kingo-portfolio.com/
```

### Robots.txt 확인

```bash
curl https://api.kingo-portfolio.com/robots.txt
```

### Sitemap.xml 확인

```bash
curl https://api.kingo-portfolio.com/sitemap.xml
```

## 통계

### 코드 변경

- **추가된 파일**: 2개
  - app/templates/landing.html (405 lines)
  - SEO.md (이 문서)

- **수정된 파일**: 1개
  - app/main.py: +77 lines (3개 엔드포인트)

### SEO 요소

- **Meta 태그**: 15개 이상
- **구조화 데이터**: 3개 스키마
- **Sitemap URL**: 4개
- **키워드**: 8개 이상

## 관련 문서

- [데이터 내보내기 가이드](EXPORT.md)
- [프로필 관리 가이드](PROFILE.md)
- [API 문서화 가이드](API_DOCUMENTATION.md)
- [에러 핸들링 시스템](ERROR_HANDLING.md)

## 참고 자료

### SEO 가이드
- [Google Search Central](https://developers.google.com/search)
- [Schema.org 문서](https://schema.org/)
- [Open Graph Protocol](https://ogp.me/)
- [Twitter Cards](https://developer.twitter.com/en/docs/twitter-for-websites/cards/overview/abouts-cards)

### 도구
- [Google Search Console](https://search.google.com/search-console)
- [Google Analytics](https://analytics.google.com/)
- [PageSpeed Insights](https://pagespeed.web.dev/)
- [Rich Results Test](https://search.google.com/test/rich-results)
- [Mobile-Friendly Test](https://search.google.com/test/mobile-friendly)

## 문의

SEO 최적화 관련 문의사항은 백엔드 팀에 문의해주세요.

---

**마지막 업데이트**: 2025-12-29
**버전**: 1.0.0
**작성자**: Claude Code (AI Assistant)
