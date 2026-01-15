# Foresto 도메인 포워딩 설정 매뉴얼

(가비아 + Cloudflare 기준)

## 1. 목적

본 문서는 foresto.co.kr 도메인을 기준으로 다음 포워딩 구조를 구축하고,
향후 재사용할 수 있도록 설정 절차를 정리한 매뉴얼입니다.

-   www.foresto.co.kr → Vercel 서비스
-   blog.foresto.co.kr → 네이버 블로그
-   foresto.co.kr → www.foresto.co.kr

모든 포워딩은 301 리다이렉트 기반으로 구성됩니다.

------------------------------------------------------------------------

## 2. 전체 아키텍처 개요

1.  도메인 등록기관: 가비아
2.  DNS / 포워딩 관리: Cloudflare
3.  실제 서비스:
    -   메인 사이트: Vercel
    -   블로그: Naver Blog

------------------------------------------------------------------------

## 3. 사전 준비 사항

-   가비아에서 도메인 소유 중일 것
-   Cloudflare 계정 보유
-   이메일 서비스 미사용 (MX 레코드 없음 기준)

------------------------------------------------------------------------

## 4. Cloudflare로 네임서버 이전

### 4.1 Cloudflare 사이트 추가

1.  Cloudflare 로그인
2.  Add a site
3.  도메인 입력: foresto.co.kr
4.  Free 플랜 선택

### 4.2 네임서버 확인

Cloudflare에서 제공하는 네임서버 2개를 확인합니다. 예: -
xxxx.ns.cloudflare.com - yyyy.ns.cloudflare.com

### 4.3 가비아 네임서버 변경

1.  My가비아 → 서비스 관리 → 도메인
2.  foresto.co.kr 선택
3.  네임서버 설정 → 사용자 지정 네임서버
4.  Cloudflare 네임서버 2개 입력 후 저장

------------------------------------------------------------------------

## 5. Cloudflare DNS 레코드 설정

Cloudflare → DNS → Records 에서 아래 레코드를 추가합니다.

  Type   Name   Value       Proxy
  ------ ------ ----------- -------
  A      @      192.0.2.1   ON
  A      www    192.0.2.1   ON
  A      blog   192.0.2.1   ON

※ 192.0.2.1은 리다이렉트 전용 더미 IP입니다.

------------------------------------------------------------------------

## 6. Redirect Rules 설정

Cloudflare → Rules → Redirect Rules → Create rule

### 6.1 blog → naver

-   Request URL: https://blog.foresto.co.kr/\*
-   Target URL: https://blog.naver.com/foresto_compass
-   Status code: 301

### 6.2 www → vercel

-   Request URL: https://www.foresto.co.kr/\*
-   Target URL: https://kingo-portfolio.vercel.app
-   Status code: 301

### 6.3 root → www

-   Request URL: https://foresto.co.kr/\*
-   Target URL: https://www.foresto.co.kr
-   Status code: 301

### 6.4 규칙 순서

1.  blog → naver
2.  www → vercel
3.  root → www

모든 규칙은 Enabled 상태여야 합니다.

------------------------------------------------------------------------

## 7. 테스트 방법

시크릿 모드 또는 모바일 브라우저에서 테스트합니다.

-   https://blog.foresto.co.kr → 네이버 블로그
-   https://www.foresto.co.kr → Vercel
-   https://foresto.co.kr → www → Vercel

------------------------------------------------------------------------

## 8. 유지보수 가이드

-   DNS 및 포워딩 수정은 Cloudflare에서만 수행
-   가비아 DNS / 포워딩 설정은 사용하지 않음
-   서비스 주소 변경 시 Redirect Rule의 Target URL만 수정

------------------------------------------------------------------------

## 9. 확장 시나리오

-   블로그 이전 시 blog Redirect Rule만 수정
-   자체 서버 도입 시 DNS A/CNAME 확장 가능
-   SEO 유지하며 무중단 이전 가능

------------------------------------------------------------------------

## 10. 결론

본 구조는 다음을 만족합니다. - HTTPS 기본 적용 - SEO 안전한 301
리다이렉트 - 서브도메인별 유연한 확장 - 가비아 포워딩 한계 극복

본 매뉴얼을 기준으로 동일한 구조를 재구성할 수 있습니다.
