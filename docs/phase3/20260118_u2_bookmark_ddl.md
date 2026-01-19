# Phase 3-C / U-2 북마크 DDL
최초작성일자: 2026-01-18
최종수정일자: 2026-01-18

## 1. 목적
U-2 북마크 기능을 위한 테이블 스키마를 정의한다.

---

## 2. DDL
```sql
CREATE TABLE IF NOT EXISTS bookmark (
    bookmark_id VARCHAR(36) PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    portfolio_id BIGINT NOT NULL REFERENCES custom_portfolio(portfolio_id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_bookmark_user_portfolio UNIQUE (user_id, portfolio_id)
);

CREATE INDEX IF NOT EXISTS idx_bookmark_user ON bookmark(user_id);
CREATE INDEX IF NOT EXISTS idx_bookmark_portfolio ON bookmark(portfolio_id);
```

