# User Menu Diagram

This document captures the user menu structure as a Mermaid diagram.

```mermaid
flowchart TD
  Home[Foresto Compass 로고] --> Survey[/survey/]

  Menu[헤더 사용자 메뉴] --> Learn[학습]
  Menu --> Diagnose[진단]
  Menu --> Portfolio[포트폴리오]
  Menu --> Account[계정]
  Menu --> Admin[관리 (admin)]

  Learn --> L1[시장현황 /dashboard]
  Learn --> L2[시나리오 /scenarios]
  Learn --> L3[용어학습 /terminology]

  Diagnose --> D1[투자성향진단 /survey]
  Diagnose --> D2[진단결과 /result]
  Diagnose --> D3[진단이력 /history]

  Portfolio --> P1[포트폴리오 /portfolio]
  Portfolio --> P2[백테스팅 /backtest]
  Portfolio --> P3[성과해석 /analysis]
  Portfolio --> P4[포트폴리오 구성 /portfolio-builder]
  Portfolio --> P5[포트폴리오 평가 /portfolio-evaluation]
  Portfolio --> P6[리포트 /report-history]

  Account --> A1[프로필 /profile]

  Admin --> M1[관리자 홈 /admin]
  Admin --> M2[데이터 관리 /admin/data]
  Admin --> M3[사용자 관리 /admin/users]
  Admin --> M4[동의 이력 /admin/consents]
  Admin --> M5[포트폴리오 관리 /admin/portfolio]
  Admin --> M6[포트폴리오 비교 /admin/portfolio-comparison]
  Admin --> M7[배치 작업 /admin/batch]
  Admin --> M8[종목 상세 /admin/stock-detail]
  Admin --> M9[재무 분석 /admin/financial-analysis]
  Admin --> M10[밸류에이션 /admin/valuation]
  Admin --> M11[퀀트 분석 /admin/quant]
  Admin --> M12[리포트 /admin/report]
```
