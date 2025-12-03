import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { authAPI } from '../services/api'
import logo from '../components/logo.png'
import './AdminDashboard.css'

function AdminDashboard({ user, onLogout }) {
  const navigate = useNavigate()
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false)

  // User Management State
  const [showUserModal, setShowUserModal] = useState(false)
  const [users, setUsers] = useState([])
  const [editingUser, setEditingUser] = useState(null)
  const [editForm, setEditForm] = useState({ username: '', password: '' })
  const [loadingUsers, setLoadingUsers] = useState(false)
  const [actionStatus, setActionStatus] = useState({ message: '', type: '' }) // type: 'success' | 'error'
  const [deleteConfirmId, setDeleteConfirmId] = useState(null)

  // Redirect to home if user is not logged in
  useEffect(() => {
    if (!user || user.role !== 'admin') {
      navigate('/', { replace: true })
    }
  }, [user, navigate])

  const handleLogout = () => {
    setShowLogoutConfirm(true)
  }

  const confirmLogout = () => {
    setShowLogoutConfirm(false)
    onLogout()
  }

  const cancelLogout = () => {
    setShowLogoutConfirm(false)
  }

  const fetchUsers = async () => {
    setLoadingUsers(true);
    setShowUserModal(true);
    try {
      const response = await authAPI.getUsers();
      setUsers(response.data);
    } catch (error) {
      setActionStatus({ message: "Failed to fetch users", type: "error" });
    } finally {
      setLoadingUsers(false);
    }
  };

  // Clear status after 3 seconds
  useEffect(() => {
    if (actionStatus.message) {
      const timer = setTimeout(() => setActionStatus({ message: '', type: '' }), 3000);
      return () => clearTimeout(timer);
    }
  }, [actionStatus]);

  const handleUpdateUser = async () => {
    try {
      const updates = {};
      if (editForm.username && editForm.username !== editingUser.username) updates.username = editForm.username;
      if (editForm.password) updates.password = editForm.password;

      if (Object.keys(updates).length === 0) {
        setEditingUser(null);
        return;
      }

      await authAPI.updateUser(editingUser.id, updates);
      setActionStatus({ message: "User updated successfully", type: "success" });
      setEditingUser(null);
      fetchUsers(); // Refresh list
    } catch (error) {
      setActionStatus({ message: "Failed to update user", type: "error" });
    }
  };

  const handleDeleteUser = async (id) => {
    try {
      await authAPI.deleteUser(id);
      setUsers(users.filter(u => u.id !== id));
      setActionStatus({ message: "User deleted successfully", type: "success" });
      setDeleteConfirmId(null);
    } catch (error) {
      setActionStatus({ message: "Failed to delete user", type: "error" });
    }
  };

  // Don't render if user is not logged in (will redirect)
  if (!user || user.role !== 'admin') {
    return null
  }

  return (
    <div className="admin-dashboard">
      <header className="dashboard-header">
        <div className="header-left">
          <img src={logo} alt="Logo" className="dashboard-logo" />
          <div className="header-content">
            <h1>Admin Dashboard</h1>
            <p className="user-info">Welcome, {user?.username}</p>
          </div>
        </div>
        <button className="logout-button" onClick={handleLogout}>
          Logout
        </button>
      </header>

      <main className="dashboard-content">
        <div className="admin-section">
          <h2>Admin Controls</h2>

          <div className="admin-card">
            <h3>Reports & Analytics</h3>
            <p>View production reports and analytics</p>
            <button className="admin-action">View Reports</button>
          </div>

          <div className="admin-card">
            <h3>Model Retraining</h3>
            <p>Retrain the sealant detection model</p>
            <button className="admin-action">Retrain Model</button>
          </div>

          <div className="admin-card">
            <h3>Manage Team</h3>
            <p>View, edit, or remove team members</p>
            <button className="admin-action" onClick={() => fetchUsers()}>Manage Team</button>
          </div>
        </div>
      </main>

      {showUserModal && (
        <div className="modal-overlay" role="dialog" aria-modal="true">
          <div className="modal-card wide-modal">
            <h3>Team Management</h3>

            {actionStatus.message && (
              <div className={`status-message ${actionStatus.type}`}>
                {actionStatus.message}
              </div>
            )}

            {editingUser ? (
              <div className="edit-user-form">
                <h4>Edit User: {editingUser.username}</h4>
                <div style={{ marginBottom: 10 }}>
                  <label>New Username (optional)</label>
                  <input
                    type="text"
                    value={editForm.username}
                    onChange={(e) => setEditForm({ ...editForm, username: e.target.value })}
                    placeholder="Leave blank to keep current"
                    autoFocus
                  />
                </div>
                <div style={{ marginBottom: 10 }}>
                  <label>New Password (optional)</label>
                  <input
                    type="password"
                    value={editForm.password}
                    onChange={(e) => setEditForm({ ...editForm, password: e.target.value })}
                    placeholder="Leave blank to keep current"
                  />
                </div>
                <div className="modal-actions">
                  <button className="button-secondary" onClick={() => {
                    setEditingUser(null);
                    setEditForm({ username: '', password: '' });
                  }}>Cancel</button>
                  <button className="login-button" onClick={handleUpdateUser}>Save Changes</button>
                </div>
              </div>
            ) : (
              <>
                <div className="user-list">
                  {loadingUsers ? <p>Loading...</p> : (
                    <table className="user-table">
                      <thead>
                        <tr>
                          <th>ID</th>
                          <th>Username</th>
                          <th>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {users.map(u => (
                          <tr key={u.id}>
                            <td>{u.id}</td>
                            <td>{u.username}</td>
                            <td>
                              <button className="small-button" onClick={() => {
                                setEditingUser(u);
                                setEditForm({ username: u.username, password: '' });
                              }}>Edit</button>

                              {deleteConfirmId === u.id ? (
                                <>
                                  <button className="small-button danger" onClick={() => handleDeleteUser(u.id)}>Confirm</button>
                                  <button className="small-button" onClick={() => setDeleteConfirmId(null)}>Cancel</button>
                                </>
                              ) : (
                                <button className="small-button danger" onClick={() => setDeleteConfirmId(u.id)}>Delete</button>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
                <div className="modal-actions" style={{ marginTop: 20 }}>
                  <button className="button-secondary" onClick={() => setShowUserModal(false)}>Close</button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {showLogoutConfirm && (
        <div className="modal-overlay" role="dialog" aria-modal="true">
          <div className="modal-card">
            <h3>Confirm Logout</h3>
            <p>Are you sure you want to end this session?</p>
            <div className="modal-actions">
              <button className="button-secondary" onClick={cancelLogout}>
                Cancel
              </button>
              <button className="button-danger" onClick={confirmLogout}>
                Logout
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default AdminDashboard

