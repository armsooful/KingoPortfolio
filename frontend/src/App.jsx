import { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { getCurrentUser, logout as logoutApi } from './services/api';
import Header from './components/Header';
import Footer from './components/Footer';
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import EmailVerificationPage from './pages/EmailVerificationPage';
import ProfilePage from './pages/ProfilePage';
import SurveyPage from './pages/SurveyPage';
import TerminologyPage from './pages/TerminologyPage';
import DiagnosisResultPage from './pages/DiagnosisResultPage';
import DiagnosisHistoryPage from './pages/DiagnosisHistoryPage';
import AdminPage from './pages/AdminPage';
import AdminConsentPage from './pages/AdminConsentPage';
import DataManagementPage from './pages/DataManagementPage';
import UserManagementPage from './pages/UserManagementPage';
import PortfolioManagementPage from './pages/PortfolioManagementPage';
import PortfolioComparisonPage from './pages/PortfolioComparisonPage';
import BatchJobsPage from './pages/BatchJobsPage';
import StockDetailPage from './pages/StockDetailPage';
import FinancialAnalysisPage from './pages/FinancialAnalysisPage';
import ValuationPage from './pages/ValuationPage';
import QuantAnalysisPage from './pages/QuantAnalysisPage';
import ReportPage from './pages/ReportPage';
import MarketDashboardPage from './pages/MarketDashboardPage';
import PortfolioRecommendationPage from './pages/PortfolioRecommendationPage';
import BacktestPage from './pages/BacktestPage';
import ScenarioSimulationPage from './pages/ScenarioSimulationPage';
import StockScreenerPage from './pages/StockScreenerPage';
import WatchlistPage from './pages/WatchlistPage';
import PortfolioExplanationPage from './pages/PortfolioExplanationPage';
import ReportHistoryPage from './pages/ReportHistoryPage';
import Phase7PortfolioEvaluationPage from './pages/Phase7PortfolioEvaluationPage';
import PortfolioBuilderPage from './pages/PortfolioBuilderPage';
import './styles/App.css';

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

  return (
    <div className="app">
      {isAuthenticated && <Header />}
      <main className="main-content">
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
      </main>
      <Footer />
    </div>
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
