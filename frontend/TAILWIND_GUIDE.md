# Tailwind CSS 사용 가이드

## 설치 완료 ✅

Tailwind CSS가 KingoPortfolio 프론트엔드에 성공적으로 설치되었습니다.

## 설치된 패키지

```json
{
  "devDependencies": {
    "tailwindcss": "^3.x",
    "postcss": "^8.x",
    "autoprefixer": "^10.x"
  }
}
```

## 설정 파일

### 1. `tailwind.config.js`
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          500: '#667eea', // KingoPortfolio 메인 브랜드 컬러
          // ... 기타 색상
        },
        success: { ... },
        warning: { ... },
        danger: { ... },
      },
    },
  },
  plugins: [],
}
```

### 2. `postcss.config.js`
```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

### 3. `src/index.css`
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

## 기본 사용법

### 유틸리티 클래스 사용
```jsx
// 기존 방식 (커스텀 CSS)
<div className="result-card" style={{ padding: '32px', background: 'white' }}>

// Tailwind 방식
<div className="p-8 bg-white rounded-lg shadow-card">
```

### 반응형 디자인
```jsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  {/* 모바일: 1열, 태블릿: 2열, 데스크톱: 3열 */}
</div>
```

### 호버 & 상태
```jsx
<button className="bg-primary-500 hover:bg-primary-600 active:bg-primary-700
                   text-white px-6 py-3 rounded-md transition-colors">
  클릭하세요
</button>
```

## 마이그레이션 전략

### Phase 1: 신규 컴포넌트에만 적용
새로 만드는 컴포넌트는 Tailwind만 사용합니다.

```jsx
// frontend/src/components/NewComponent.jsx
const NewComponent = () => {
  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold text-gray-900 mb-4">
        Tailwind 사용 예제
      </h1>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg shadow-card hover:shadow-card-hover transition-shadow">
          <h2 className="text-xl font-semibold mb-2">카드 1</h2>
          <p className="text-gray-600">Tailwind로 스타일링</p>
        </div>
      </div>
    </div>
  );
};
```

### Phase 2: 기존 컴포넌트 점진적 마이그레이션
인라인 스타일과 커스텀 CSS를 Tailwind로 교체합니다.

**Before (기존 방식)**:
```jsx
<div style={{
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
  gap: '24px',
  marginTop: '40px'
}}>
  <div style={{
    background: 'white',
    borderRadius: '16px',
    padding: '32px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
  }}>
    Content
  </div>
</div>
```

**After (Tailwind)**:
```jsx
<div className="grid grid-cols-[repeat(auto-fit,minmax(280px,1fr))] gap-6 mt-10">
  <div className="bg-white rounded-2xl p-8 shadow-card">
    Content
  </div>
</div>
```

### Phase 3: 커스텀 CSS 클래스 정리
자주 사용하는 패턴은 `@apply`로 재사용 가능한 클래스 생성합니다.

```css
/* src/index.css */
@layer components {
  .btn-primary {
    @apply bg-primary-500 hover:bg-primary-600 text-white font-semibold
           py-3 px-6 rounded-lg transition-colors shadow-md hover:shadow-lg;
  }

  .card {
    @apply bg-white rounded-lg shadow-card p-6 hover:shadow-card-hover
           transition-shadow;
  }

  .input-field {
    @apply w-full px-4 py-2 border border-gray-300 rounded-md
           focus:ring-2 focus:ring-primary-500 focus:border-transparent;
  }
}
```

사용:
```jsx
<button className="btn-primary">제출</button>
<div className="card">카드 내용</div>
<input type="text" className="input-field" />
```

## 커스텀 브랜드 컬러 활용

KingoPortfolio 브랜드 컬러가 이미 설정되어 있습니다:

```jsx
// Primary 컬러 (브랜드 컬러)
<div className="bg-primary-500 text-white">메인 컬러</div>
<div className="bg-primary-600">호버 시 컬러</div>

// Success (성공/긍정)
<div className="bg-success text-white">성공 메시지</div>

// Warning (경고)
<div className="bg-warning text-white">주의 메시지</div>

// Danger (위험/오류)
<div className="bg-danger text-white">오류 메시지</div>
```

## 실제 사용 예제

### 1. 카드 컴포넌트
```jsx
const AnalysisCard = ({ title, value, change }) => {
  return (
    <div className="bg-white rounded-lg shadow-card p-6 hover:shadow-card-hover transition-shadow">
      <h3 className="text-gray-600 text-sm font-medium mb-2">{title}</h3>
      <div className="flex items-end justify-between">
        <span className="text-3xl font-bold text-gray-900">{value}</span>
        <span className={`text-sm font-semibold ${
          change >= 0 ? 'text-success' : 'text-danger'
        }`}>
          {change >= 0 ? '+' : ''}{change}%
        </span>
      </div>
    </div>
  );
};
```

### 2. 버튼 컴포넌트
```jsx
const Button = ({ children, variant = 'primary', disabled, onClick }) => {
  const baseClasses = "px-6 py-3 rounded-lg font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed";

  const variants = {
    primary: "bg-primary-500 hover:bg-primary-600 text-white shadow-md hover:shadow-lg",
    success: "bg-success hover:bg-success-dark text-white",
    outline: "border-2 border-primary-500 text-primary-500 hover:bg-primary-50",
  };

  return (
    <button
      className={`${baseClasses} ${variants[variant]}`}
      disabled={disabled}
      onClick={onClick}
    >
      {children}
    </button>
  );
};
```

### 3. 그리드 레이아웃
```jsx
const StockGrid = ({ stocks }) => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {stocks.map(stock => (
        <div key={stock.id} className="bg-white rounded-lg shadow-card p-4">
          <h3 className="text-lg font-semibold mb-2">{stock.name}</h3>
          <p className="text-gray-600">{stock.ticker}</p>
        </div>
      ))}
    </div>
  );
};
```

### 4. 폼
```jsx
const LoginForm = () => {
  return (
    <form className="max-w-md mx-auto space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          이메일
        </label>
        <input
          type="email"
          className="w-full px-4 py-2 border border-gray-300 rounded-lg
                     focus:ring-2 focus:ring-primary-500 focus:border-transparent"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          비밀번호
        </label>
        <input
          type="password"
          className="w-full px-4 py-2 border border-gray-300 rounded-lg
                     focus:ring-2 focus:ring-primary-500 focus:border-transparent"
        />
      </div>
      <button className="w-full bg-primary-500 hover:bg-primary-600 text-white
                         py-3 rounded-lg font-semibold transition-colors">
        로그인
      </button>
    </form>
  );
};
```

## 일반적인 Tailwind 클래스 조합

### 레이아웃
```jsx
// Flexbox
<div className="flex items-center justify-between">
<div className="flex flex-col gap-4">

// Grid
<div className="grid grid-cols-3 gap-6">
<div className="grid grid-cols-[repeat(auto-fit,minmax(280px,1fr))] gap-4">

// Container
<div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
```

### 타이포그래피
```jsx
<h1 className="text-4xl font-bold text-gray-900">
<h2 className="text-2xl font-semibold text-gray-800">
<p className="text-base text-gray-600 leading-relaxed">
```

### 간격
```jsx
// Padding
className="p-4"     // 전체 1rem
className="px-6"    // 좌우 1.5rem
className="py-3"    // 상하 0.75rem

// Margin
className="m-4"     // 전체 1rem
className="mt-8"    // 위 2rem
className="mb-4"    // 아래 1rem
className="mx-auto" // 좌우 auto (중앙 정렬)
```

### 색상
```jsx
// 배경
className="bg-white bg-gray-100 bg-primary-500"

// 텍스트
className="text-gray-900 text-white text-primary-500"

// 테두리
className="border border-gray-300 border-primary-500"
```

## 반응형 디자인

```jsx
// Mobile First 접근
<div className="
  p-4              // 모바일: padding 1rem
  sm:p-6           // 640px+: padding 1.5rem
  md:p-8           // 768px+: padding 2rem
  lg:p-12          // 1024px+: padding 3rem
  xl:p-16          // 1280px+: padding 4rem
">
  <div className="
    grid
    grid-cols-1      // 모바일: 1열
    sm:grid-cols-2   // 640px+: 2열
    lg:grid-cols-3   // 1024px+: 3열
    gap-4            // 간격 1rem
  ">
    {/* 카드들 */}
  </div>
</div>
```

## 다크 모드 (추후 구현 시)

```jsx
<div className="bg-white dark:bg-gray-900 text-gray-900 dark:text-white">
  다크 모드 지원
</div>
```

## 성능 최적화

Tailwind는 사용되지 않는 CSS를 자동으로 제거합니다 (PurgeCSS):

```javascript
// tailwind.config.js
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",  // 이 경로의 파일들만 스캔
  ],
  // ...
}
```

## 디버깅 팁

### 1. 클래스 적용 확인
브라우저 개발자 도구에서 `Computed` 탭을 확인하세요.

### 2. JIT 모드 활성화 (기본값)
Tailwind는 Just-In-Time 모드로 실행되어 빌드 속도가 빠릅니다.

### 3. VS Code 확장
**Tailwind CSS IntelliSense** 설치 권장:
- 자동완성
- 클래스 미리보기
- 린팅

## 참고 자료

- 공식 문서: https://tailwindcss.com/docs
- Cheat Sheet: https://nerdcave.com/tailwind-cheat-sheet
- 컴포넌트 예제: https://tailwindui.com (유료/무료)

## 다음 단계

1. ✅ Tailwind CSS 설치 완료
2. 신규 컴포넌트에 Tailwind 적용
3. 기존 AdminPage.jsx 리팩토링
4. 공통 컴포넌트 라이브러리 구축
5. 디자인 시스템 문서화
