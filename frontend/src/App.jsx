import { useState, useEffect, createContext, useContext, lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { getCurrentUser, logout as logoutApi } from './services/api';
import { ThemeContext, useThemeInit } from './hooks/useTheme';
import Header from './components/Header';
import Footer from './components/Footer';
import ErrorBoundary from './components/ErrorBoundary';
import './styles/App.css';

// Public — 정적 import (첫 화면/인증)
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import EmailVerificationPage from './pages/EmailVerificationPage';

// Protected — lazy import (온디맨드 로딩)
const MarketDashboardPage = lazy(() => import('./pages/MarketDashboardPage'));
const ProfilePage = lazy(() => import('./pages/ProfilePage'));
const SurveyPage = lazy(() => import('./pages/SurveyPage'));
const TerminologyPage = lazy(() => import('./pages/TerminologyPage'));
const DiagnosisResultPage = lazy(() => import('./pages/DiagnosisResultPage'));
const DiagnosisHistoryPage = lazy(() => import('./pages/DiagnosisHistoryPage'));
const PortfolioRecommendationPage = lazy(() => import('./pages/PortfolioRecommendationPage'));
const BacktestPage = lazy(() => import('./pages/BacktestPage'));
const ScenarioSimulationPage = lazy(() => import('./pages/ScenarioSimulationPage'));
const StockScreenerPage = lazy(() => import('./pages/StockScreenerPage'));
const WatchlistPage = lazy(() => import('./pages/WatchlistPage'));
const PortfolioExplanationPage = lazy(() => import('./pages/PortfolioExplanationPage'));
const ReportHistoryPage = lazy(() => import('./pages/ReportHistoryPage'));
const Phase7PortfolioEvaluationPage = lazy(() => import('./pages/Phase7PortfolioEvaluationPage'));
const PortfolioBuilderPage = lazy(() => import('./pages/PortfolioBuilderPage'));
const AdminPage = lazy(() => import('./pages/AdminPage'));
const AdminConsentPage = lazy(() => import('./pages/AdminConsentPage'));
const DataManagementPage = lazy(() => import('./pages/DataManagementPage'));
const UserManagementPage = lazy(() => import('./pages/UserManagementPage'));
const PortfolioManagementPage = lazy(() => import('./pages/PortfolioManagementPage'));
const PortfolioComparisonPage = lazy(() => import('./pages/PortfolioComparisonPage'));
const BatchJobsPage = lazy(() => import('./pages/BatchJobsPage'));
const StockDetailPage = lazy(() => import('./pages/StockDetailPage'));
const FinancialAnalysisPage = lazy(() => import('./pages/FinancialAnalysisPage'));
const ValuationPage = lazy(() => import('./pages/ValuationPage'));
const QuantAnalysisPage = lazy(() => import('./pages/QuantAnalysisPage'));
const ReportPage = lazy(() => import('./pages/ReportPage'));
const StockComparisonPage = lazy(() => import('./pages/StockComparisonPage'));

// ============================================================
// Auth Context
// ============================================================

export const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

// ============================================================
// Auth Provider
// ============================================================

function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // 초기 사용자 정보 로드
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const token = localStorage.getItem('access_token');

        if (token) {
          const response = await getCurrentUser();
          setUser(response.data);
          setIsAuthenticated(true);
        }
      } catch (error) {
        console.error('Auth check failed:', error);
        localStorage.removeItem('access_token');
        setIsAuthenticated(false);
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  const login = (user, token) => {
    localStorage.setItem('access_token', token);
    localStorage.setItem('user', JSON.stringify(user));
    setUser(user);
    setIsAuthenticated(true);
  };

  const logout = () => {
    logoutApi();
    setUser(null);
    setIsAuthenticated(false);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        setUser,
        isAuthenticated,
        isLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// ============================================================
// Protected Route
// ============================================================

function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p>로딩 중...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

// ============================================================
// App Component
// ============================================================

function AppContent() {
  const { isAuthenticated } = useAuth();
  const themeValue = useThemeInit();

  return (
    <ThemeContext.Provider value={themeValue}>
    <div className="app">
      {isAuthenticated && <Header />}
      <main className="main-content">
        <ErrorBoundary>
        <Suspense fallback={<div className="loading-container"><div className="spinner"></div><p>로딩 중...</p></div>}>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="/verify-email" element={<EmailVerificationPage />} />

          {/* Protected Routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <MarketDashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <ProfilePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/survey"
            element={
              <ProtectedRoute>
                <SurveyPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/terminology"
            element={
              <ProtectedRoute>
                <TerminologyPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/result"
            element={
              <ProtectedRoute>
                <DiagnosisResultPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/history"
            element={
              <ProtectedRoute>
                <DiagnosisHistoryPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/portfolio"
            element={
              <ProtectedRoute>
                <PortfolioRecommendationPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/backtest"
            element={
              <ProtectedRoute>
                <BacktestPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/scenarios"
            element={
              <ProtectedRoute>
                <ScenarioSimulationPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/screener"
            element={
              <ProtectedRoute>
                <StockScreenerPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/watchlist"
            element={
              <ProtectedRoute>
                <WatchlistPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/stock-comparison"
            element={
              <ProtectedRoute>
                <StockComparisonPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/analysis"
            element={
              <ProtectedRoute>
                <PortfolioExplanationPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/report-history"
            element={
              <ProtectedRoute>
                <ReportHistoryPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/phase7-evaluation"
            element={
              <ProtectedRoute>
                <Phase7PortfolioEvaluationPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/portfolio-evaluation"
            element={
              <ProtectedRoute>
                <Phase7PortfolioEvaluationPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/portfolio-builder"
            element={
              <ProtectedRoute>
                <PortfolioBuilderPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <ProtectedRoute>
                <AdminPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/data"
            element={
              <ProtectedRoute>
                <DataManagementPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/users"
            element={
              <ProtectedRoute>
                <UserManagementPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/consents"
            element={
              <ProtectedRoute>
                <AdminConsentPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/portfolio"
            element={
              <ProtectedRoute>
                <PortfolioManagementPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/portfolio-comparison"
            element={
              <ProtectedRoute>
                <PortfolioComparisonPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/batch"
            element={
              <ProtectedRoute>
                <BatchJobsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/stock-detail"
            element={
              <ProtectedRoute>
                <StockDetailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/financial-analysis"
            element={
              <ProtectedRoute>
                <FinancialAnalysisPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/valuation"
            element={
              <ProtectedRoute>
                <ValuationPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/quant"
            element={
              <ProtectedRoute>
                <QuantAnalysisPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/report"
            element={
              <ProtectedRoute>
                <ReportPage />
              </ProtectedRoute>
            }
          />

          {/* Default Route */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        </Suspense>
        </ErrorBoundary>
      </main>
      <Footer />
    </div>
    </ThemeContext.Provider>
  );
}

function App() {
  return (
    <Router
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </Router>
  );
}

export default App;
