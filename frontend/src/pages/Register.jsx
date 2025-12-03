import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import './Login.css'
import { authAPI } from '../services/api'

function Register() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const roleFromUrl = searchParams.get('role') || 'worker'
  
  const [form, setForm] = useState({ username: '', password: '', role: roleFromUrl })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Update role when URL param changes
  useEffect(() => {
    setForm(prev => ({ ...prev, role: roleFromUrl }))
  }, [roleFromUrl])

  const handleChange = (e) => setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      // Use appropriate API based on role
      const response = form.role === 'admin'
        ? await authAPI.adminRegister({
            username: form.username,
            password: form.password
          })
        : await authAPI.register({
            username: form.username,
            password: form.password
          })
      
      // Success - redirect to login with role parameter
      const timestamp = new Date().toLocaleString();
      console.log(`\n[${timestamp}] ✅ FRONTEND: Registration successful`);
      console.log(`  Role: ${form.role}`);
      console.log(`  Username: ${form.username}`);
      navigate(`/login?role=${form.role}`)
    } catch (err) {
      const timestamp = new Date().toLocaleString();
      console.error(`\n[${timestamp}] ❌ FRONTEND: Registration failed`);
      console.error(`  Error: ${err.message}`);
      console.error(`  Response:`, err.response?.data);
      const errorMessage = err.response?.data?.detail || err.response?.data?.error || err.message || 'Registration failed'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <h1>Create {form.role === 'admin' ? 'Admin' : 'User'} Account</h1>
          <p>Register as {form.role === 'admin' ? 'Admin' : 'Team Member'}</p>
        </div>
        <form onSubmit={handleSubmit} className="login-form">
          <div className={`role-badge role-badge-${form.role}`} style={{ marginBottom: '16px' }}>
            <span className="role-icon">
              {form.role === 'worker' ? '👷' : '👔'}
            </span>
            <div className="role-info">
              <span className="role-label">Registering as</span>
              <span className="role-value">
                {form.role === 'worker' ? 'Team Member' : (form.role.charAt(0).toUpperCase() + form.role.slice(1))}
              </span>
            </div>
          </div>

          <div className="form-group">
            <label>Username</label>
            <input name="username" value={form.username} onChange={handleChange} required />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input name="password" type="password" value={form.password} onChange={handleChange} required />
          </div>
          <button className="login-button" disabled={loading}>{loading ? 'Creating…' : 'Register'}</button>
          {error && <div className="login-error" role="alert">{error}</div>}
          
          <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: '8px', alignItems: 'center' }}>
            <small>
              Already have an account? <Link to={`/login?role=${form.role}`}>Login</Link>
            </small>
            <small>
              <Link 
                to="/" 
                style={{ 
                  color: 'var(--text-secondary, #64748b)', 
                  textDecoration: 'none',
                  transition: 'color 0.2s'
                }}
                onMouseEnter={(e) => e.target.style.color = 'var(--danger-color, #ef4444)'}
                onMouseLeave={(e) => e.target.style.color = 'var(--text-secondary, #64748b)'}
              >
                ← Back to Welcome
              </Link>
            </small>
          </div>
        </form>
      </div>
    </div>
  )
}

export default Register
