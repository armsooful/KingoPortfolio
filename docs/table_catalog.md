# 테이블 목록 요약 (현재 구현 기준)
최초작성일자: 2026-01-20
최종수정일자: 2026-01-20

본 문서는 `backend/app/models/` 기준으로 정의된 현재 테이블 목록을 요약한다.

## 사용자/권한
- `users`
- `admin_role`
- `admin_permission`
- `admin_role_permission`
- `admin_user_role`
- `admin_audit_log`
- `admin_approval`
- `admin_adjustment`

## 사용자 설정/이벤트
- `user_preset`
- `user_notification_setting`
- `user_activity_event`
- `user_event_log`
- `bookmark`

## 포트폴리오/시나리오
- `portfolios`
- `portfolio_histories`
- `scenario_definition`
- `portfolio_model`
- `portfolio_allocation`
- `asset_class_master`
- `custom_portfolio`
- `custom_portfolio_weight`

## 시뮬레이션
- `simulation_run`
- `simulation_path`
- `simulation_summary`
- `simulation_cache`

## 분석/성과
- `analysis_result`
- `explanation_history`
- `performance_result`
- `performance_basis`
- `benchmark_result`
- `performance_public_view`

## 리밸런싱
- `rebalancing_rule`
- `rebalancing_event`
- `rebalancing_cost_model`

## 시세/상품/외부 데이터
- `stocks`
- `etfs`
- `bonds`
- `deposit_products`
- `krx_timeseries`
- `stock_financials`
- `product_recommendations`
- `alpha_vantage_stocks`
- `alpha_vantage_financials`
- `alpha_vantage_etfs`
- `alpha_vantage_timeseries`

## 데이터 품질/계보
- `data_snapshot`
- `data_lineage_node`
- `data_lineage_edge`
- `validation_rule_master`
- `validation_rule_version`
- `validation_result`
- `execution_context`
- `data_quality_report`
- `data_quality_report_item`

## 운영/배치/버전
- `batch_job`
- `batch_execution`
- `batch_execution_log`
- `ops_audit_log`
- `result_version`
- `ops_alert`
- `error_code_master`

## 참고
- 소스 위치: `backend/app/models/`
