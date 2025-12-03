import axios from 'axios';

// Determine API base URL based on environment
const getApiBaseUrl = () => {
  // Check if running in Electron
  const isElectron = typeof window !== 'undefined' &&
    (window.location.protocol === 'file:' || navigator.userAgent.includes('Electron'));

  // Check if running on localhost (dev server)
  const isLocalhost = typeof window !== 'undefined' &&
    (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

  // For localhost dev, use proxy (vite will proxy to backend)
  if (isLocalhost) {
    return ''; // Empty string means use relative URLs (vite proxy will handle it)
  }

  // For Electron or production, use full backend URL
  // Change this to your backend URL
  return 'http://localhost:8000'; // FastAPI default port
};

// Create axios instance
const api = axios.create({
  baseURL: getApiBaseUrl(),
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor to include auth token
api.interceptors.request.use(
  (config) => {
    const user = localStorage.getItem('user');
    if (user) {
      try {
        const userData = JSON.parse(user);
        if (userData.raw?.access_token) {
          config.headers.Authorization = `Bearer ${userData.raw.access_token}`;
        }
      } catch (e) {
        console.error('Error parsing user data:', e);
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Unauthorized - clear user data and redirect to login
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// API methods
export const authAPI = {
  // User APIs
  register: (data) => api.post('/user/register', data),
  login: (data) => api.post('/user/login', data),

  // Admin APIs
  adminRegister: (data) => api.post('/admin/register', data),
  adminLogin: (data) => api.post('/admin/login', data),

  // Admin User Management
  getUsers: () => api.get('/admin/users'),
  updateUser: (id, data) => api.put(`/admin/users/${id}`, data),
  deleteUser: (id) => api.delete(`/admin/users/${id}`),
};

export const imageAPI = {
  // Process 4 images
  processImages: (images, model, metadata = 'default') => {
    const formData = new FormData();
    images.forEach((image) => {
      formData.append('images', image);
    });
    formData.append('model', model);
    formData.append('metadata', metadata);

    return api.post('/images/process', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      responseType: 'blob', // Important for receiving ZIP file
    });
  },
};

export default api;

