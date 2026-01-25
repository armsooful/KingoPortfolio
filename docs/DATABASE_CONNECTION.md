# PostgreSQL 데이터베이스 연결 가이드

## 운영 환경 (Render PostgreSQL)

### 연결 정보

| 항목 | 값 |
|------|-----|
| Host | `dpg-d5qt0ushg0os73cjg16g-a.singapore-postgres.render.com` |
| Port | `5432` |
| Database | `kingo` |
| Username | `admin` |
| Password | `NGK3b7FTFEHeyvhBWZwJkEMG4WL8LCFo` |

### Internal URL (Render 서비스 간 통신용)
```
postgresql://admin:NGK3b7FTFEHeyvhBWZwJkEMG4WL8LCFo@dpg-d5qt0ushg0os73cjg16g-a/kingo
```

### External URL (외부 접속용)
```
postgresql://admin:NGK3b7FTFEHeyvhBWZwJkEMG4WL8LCFo@dpg-d5qt0ushg0os73cjg16g-a.singapore-postgres.render.com/kingo
```

---

## DBeaver 연결 방법

1. DBeaver 실행
2. **Database** → **New Database Connection** 클릭
3. **PostgreSQL** 선택 → **Next**
4. 연결 정보 입력:
   - Host: `dpg-d5qt0ushg0os73cjg16g-a.singapore-postgres.render.com`
   - Port: `5432`
   - Database: `kingo`
   - Username: `admin`
   - Password: `NGK3b7FTFEHeyvhBWZwJkEMG4WL8LCFo`
5. **Test Connection** 클릭하여 연결 확인
6. **Finish** 클릭

### 테이블 확인
- 왼쪽 패널: `kingo` → `Schemas` → `public` → `Tables`
- 테이블 더블클릭하면 데이터 확인 가능

---

## CLI (psql) 연결 방법

### macOS에서 psql 설치
```bash
brew install libpq
echo 'export PATH="/opt/homebrew/opt/libpq/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### 접속
```bash
psql postgresql://admin:NGK3b7FTFEHeyvhBWZwJkEMG4WL8LCFo@dpg-d5qt0ushg0os73cjg16g-a.singapore-postgres.render.com/kingo
```

### 유용한 psql 명령어
```sql
-- 모든 테이블 목록
\dt

-- 테이블 구조 확인
\d users

-- 사용자 목록 조회
SELECT id, email, name, role, vip_tier FROM users;

-- psql 종료
\q
```

---

## 로컬 개발 환경 (SQLite)

로컬 개발 시 기본적으로 SQLite를 사용합니다.

### 파일 위치
```
backend/kingo.db
```

### SQLite 접속
```bash
cd backend
sqlite3 kingo.db
```

### SQLite 명령어
```sql
-- 테이블 목록
.tables

-- 테이블 구조
.schema users

-- 종료
.quit
```

---

## 환경별 DATABASE_URL 설정

### 로컬 개발 (기본값)
```
DATABASE_URL=sqlite:///./kingo.db
```

### Render 운영 환경
Render 대시보드 → Backend 서비스 → Environment → `DATABASE_URL` 설정:
```
DATABASE_URL=postgresql://admin:NGK3b7FTFEHeyvhBWZwJkEMG4WL8LCFo@dpg-d5qt0ushg0os73cjg16g-a/kingo
```

---

## 주의사항

1. **비밀번호 보안**: 이 문서에 포함된 비밀번호는 예시입니다. 실제 운영 환경에서는 비밀번호를 안전하게 관리하세요.
2. **External URL**: 외부 접속 시 `.singapore-postgres.render.com` 도메인을 사용합니다.
3. **Internal URL**: Render 서비스 간 통신 시에만 사용 가능합니다.
