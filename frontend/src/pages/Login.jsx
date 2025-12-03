// src/pages/Login.jsx
import { useState, useEffect, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import './Login.css';
import { Link } from 'react-router-dom';
import { authAPI } from '../services/api';

function Login({ onLogin }) {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const roleFromUrl = searchParams.get('role') || 'worker';
  const usernameRef = useRef(null);

  const [formData, setFormData] = useState({
    username: '',
    password: '',
    role: roleFromUrl
  });

  // Display label mapping for roles (keep internal role value 'worker')
  const displayRole = formData.role === 'worker'
    ? 'Team Member'
    : (formData.role.charAt(0).toUpperCase() + formData.role.slice(1))

  const [loading, setLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState(null)

  // Reset form when component mounts or when role changes
  useEffect(() => {
    resetForm();

    // Focus the username field on mount
    if (usernameRef.current) {
      usernameRef.current.focus();
    }
  }, [roleFromUrl]);

  const resetForm = () => {
    setFormData({
      username: '',
      password: '',
      role: roleFromUrl
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.username || !formData.password) return;

    setLoading(true);
    setErrorMsg(null);

    try {
      // Use the appropriate API based on role
      const apiCall = formData.role === 'admin'
        ? authAPI.adminLogin({ username: formData.username, password: formData.password })
        : authAPI.login({ username: formData.username, password: formData.password });

      const response = await apiCall;
      const data = response.data;

      // Ensure backend returned an access_token
      if (!data || !data.access_token) {
        const errMsg = data?.error || data?.detail || 'Invalid credentials';
        throw new Error(errMsg);
      }

      const userData = {
        username: formData.username,
        role: formData.role,
        id: data?.id || Math.random().toString(36).substr(2, 9),
        raw: data
      };

      // Store user + token
      const timestamp = new Date().toLocaleString();
      console.log(`\n[${timestamp}] ✅ FRONTEND: Login successful`);
      console.log(`  Role: ${userData.role}`);
      console.log(`  Username: ${userData.username}`);
      console.log(`  Token received: ${data.access_token ? 'Yes' : 'No'}`);

      localStorage.setItem('user', JSON.stringify(userData));
      onLogin(userData);
      navigate(`/${userData.role}-dashboard`);
    } catch (err) {
      const timestamp = new Date().toLocaleString();
      console.error(`\n[${timestamp}] ❌ FRONTEND: Login failed`);
      console.error(`  Error: ${err.message}`);
      console.error(`  Response:`, err.response?.data);
      const errorMessage = err.response?.data?.detail || err.response?.data?.error || err.message || 'Login failed';
      setErrorMsg(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <h1>Sealant Detection System</h1>
          <p>Please login to continue</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <div className={`role-badge role-badge-${formData.role}`}>
            <span className="role-icon">
              {formData.role === 'worker' ? '👷' : '👔'}
            </span>
            <div className="role-info">
              <span className="role-label">Logging in as</span>
              <span className="role-value">
                {displayRole}
              </span>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              ref={usernameRef}
              type="text"
              id="username"
              name="username"
              value={formData.username}
              onChange={handleChange}
              placeholder="Enter your username"
              required
              autoComplete="username"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              placeholder="Enter your password"
              required
              autoComplete="current-password"
            />
          </div>

          <button type="submit" className="login-button" disabled={loading}>
            {loading ? 'Logging in…' : 'Login'}
          </button>

          {errorMsg && (
            <div className="login-error" role="alert" style={{ color: 'var(--danger, #c23)' }}>
              {errorMsg}
            </div>
          )}

          <div style={{ marginTop: 12 }}>
            <small>
              Don't have an account? <Link to={`/register?role=${formData.role}`}>Register</Link>
            </small>
          </div>
        </form>

        <div className="login-footer">
          <Link
            to="/"
            style={{
              color: 'var(--text-secondary, #64748b)',
              textDecoration: 'none',
              transition: 'color 0.2s',
              fontSize: '14px'
            }}
            onMouseEnter={(e) => e.target.style.color = 'var(--danger-color, #ef4444)'}
            onMouseLeave={(e) => e.target.style.color = 'var(--text-secondary, #64748b)'}
          >
            ← Back to Welcome
          </Link>
        </div>
      </div>
    </div>
  );
}

export default Login;