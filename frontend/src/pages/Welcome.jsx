import { useNavigate } from 'react-router-dom'
import './Welcome.css'

function Welcome() {
  const navigate = useNavigate()

  const selectRole = (role) => {
    navigate(`/login?role=${role}`)
  }

  return (
    <div className="welcome-container">
      <div className="welcome-content">
        <h1 className="welcome-title">Welcome to Sealant Detection System</h1>
        <p className="welcome-subtitle">Choose your role to continue</p>
        
        <div className="role-buttons">
          <button className="role-button worker-button" onClick={() => selectRole('worker')}>
            <div className="button-icon">👷</div>
            <h2>Team Member</h2>
            <p>Access camera feeds and monitor production status</p>
          </button>

          <button className="role-button admin-button" onClick={() => selectRole('admin')}>
            <div className="button-icon">👔</div>
            <h2>Admin</h2>
            <p>View reports, analytics and manage system settings</p>
          </button>
        </div>
      </div>
    </div>
  )
}

export default Welcome

