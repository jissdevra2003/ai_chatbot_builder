import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import LoginPage from './pages/Auth/LoginPage';
import SignupPage from './pages/Auth/SignupPage';
import DashboardPage from './pages/Dashboard/DashboardPage';
import ChatbotsPage from './pages/Chatbots/ChatbotsPage';
import ChatbotDetailPage from './pages/Chatbots/ChatbotDetailPage';
import TeamPage from './pages/Team/TeamPage';
import SettingsPage from './pages/Settings/SettingsPage';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />

          {/* Protected routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />

          {/* Chatbot routes */}
          <Route
            path="/chatbots"
            element={
              <ProtectedRoute>
                <ChatbotsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/chatbots/:chatbotId"
            element={
              <ProtectedRoute>
                <ChatbotDetailPage />
              </ProtectedRoute>
            }
          />

          {/* Team & Settings routes */}
          <Route
            path="/team"
            element={
              <ProtectedRoute>
                <TeamPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/settings"
            element={
              <ProtectedRoute>
                <SettingsPage />
              </ProtectedRoute>
            }
          />

          {/* Default redirect */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
