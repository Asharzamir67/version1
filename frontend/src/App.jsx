import { useState } from 'react';
import {
  BrowserRouter,
  HashRouter,
  Routes,
  Route,
  Navigate,
} from 'react-router-dom';
import Welcome from './pages/Welcome';
import Login from './pages/Login';
import Register from './pages/Register';
import WorkerDashboard from './pages/WorkerDashboard';
import AdminDashboard from './pages/AdminDashboard';
import ProcessingResults from './pages/ProcessingResults';
import { isTokenExpired } from './utils/auth';
import './App.css';


export function AppContent() {
  const [user, setUser] = useState(() => {
    try {
      const raw = localStorage.getItem('user');
      if (!raw) return null;
      
      const userData = JSON.parse(raw);
      // Validate token expiration on initialization
      if (isTokenExpired(userData.raw?.access_token)) {
        console.warn('Session expired - clearing local storage');
        localStorage.removeItem('user');
        return null;
      }
      return userData;
    } catch {
      return null;
    }
  });

  const handleLogin = (userData) => {
    const timestamp = new Date().toLocaleString();
    console.log(`\n[${timestamp}] 🟢 FRONTEND: User logged in`);
    console.log(`  Role: ${userData.role}`);
    console.log(`  Username: ${userData.username}`);
    setUser(userData);
    localStorage.setItem('user', JSON.stringify(userData));
  };

  const handleLogout = () => {
    const timestamp = new Date().toLocaleString();
    const username = user?.username || 'Unknown';
    const role = user?.role || 'Unknown';
    console.log(`\n[${timestamp}] 🔴 FRONTEND: User logged out`);
    console.log(`  Role: ${role}`);
    console.log(`  Username: ${username}`);
    setUser(null);
    localStorage.removeItem('user');
  };

  return (
    <Routes>
    <Route path="/register" element={<Register />} />
      <Route
        path="/"
        element={<Welcome />}
      />
      <Route
        path="/login"
        element={
          !user ? (
            <Login onLogin={handleLogin} />
          ) : (
            <Navigate to={`/${user.role}-dashboard`} replace />
          )
        }
      />
      <Route
        path="/worker-dashboard"
        element={
          user?.role === 'worker' ? (
            <WorkerDashboard user={user} onLogout={handleLogout} />
          ) : (
            <Navigate to="/" replace />
          )
        }
      />
      <Route
        path="/admin-dashboard"
        element={
          user?.role === 'admin' ? (
            <AdminDashboard user={user} onLogout={handleLogout} />
          ) : (
            <Navigate to="/" replace />
          )
        }
      />
      <Route
        path="/processing-results"
        element={<ProcessingResults />}
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  const RouterComponent =
    typeof window !== 'undefined' && window.location.protocol === 'file:'
      ? HashRouter
      : BrowserRouter;

  return (
    <RouterComponent>
      <AppContent />
    </RouterComponent>
  );
}

export default App;