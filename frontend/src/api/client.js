import axios from 'axios';

const API_BASE_URL = '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor — attach JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor — handle 401 (expired/invalid token)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      // Only redirect if not already on auth pages
      if (!window.location.pathname.startsWith('/login') && 
          !window.location.pathname.startsWith('/signup')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// --- Auth API ---
export const authAPI = {
  signup: (data) => api.post('/auth/signup', data),
  login: (data) => api.post('/auth/login', data),
  getMe: () => api.get('/auth/me'),
};

// --- Chatbots API ---
export const chatbotsAPI = {
  list: () => api.get('/chatbots/'),
  get: (id) => api.get(`/chatbots/${id}`),
  create: (data) => api.post('/chatbots/', data),
  update: (id, data) => api.patch(`/chatbots/${id}`, data),
  delete: (id) => api.delete(`/chatbots/${id}`),
};

// --- Documents API ---
export const documentsAPI = {
  upload: (chatbotId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/chatbots/${chatbotId}/documents/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  list: (chatbotId) => api.get(`/chatbots/${chatbotId}/documents/`),
  get: (chatbotId, docId) => api.get(`/chatbots/${chatbotId}/documents/${docId}`),
  getChunks: (chatbotId, docId) => api.get(`/chatbots/${chatbotId}/documents/${docId}/chunks`),
  delete: (chatbotId, docId) => api.delete(`/chatbots/${chatbotId}/documents/${docId}`),
};

// --- Chat API ---
export const chatAPI = {
  sendMessage: (chatbotId, data) => api.post(`/chatbots/${chatbotId}/chat`, data),
  listConversations: (chatbotId) => api.get(`/chatbots/${chatbotId}/conversations`),
  getConversation: (conversationId) => api.get(`/conversations/${conversationId}`),
  deleteConversation: (conversationId) => api.delete(`/conversations/${conversationId}`),
};

// --- Invitations API ---
export const invitationsAPI = {
  create: (data) => api.post('/invitations/', data),
  list: () => api.get('/invitations/'),
  getByToken: (token) => api.get(`/invitations/${token}`),
  accept: (data) => api.post('/invitations/accept', data),
};

export default api;
