import axios from 'axios';

// Se VITE_API_URL não vier, usa "/api" (que o Nginx proxyia).
const API_BASE = (import.meta.env.VITE_API_URL || '/api').replace(/\/+$/, '');

const api = axios.create({ baseURL: API_BASE });

// Header Authorization em toda request (inclusive após F5)
api.interceptors.request.use((cfg) => {
  const t = localStorage.getItem('token');
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

export function setAuthToken(token?: string) {
  if (!token) {
    localStorage.removeItem('token');
    delete (api.defaults.headers as any).Authorization;
  } else {
    localStorage.setItem('token', token);
    (api.defaults.headers as any).Authorization = `Bearer ${token}`;
  }
}

export const AuthApi = {
  async login(email: string, password: string) {
    const { data } = await api.post('/auth/login', { email, password });
    setAuthToken(data.access_token);
    window.dispatchEvent(new Event('auth-changed'));
    return data;
  },

  async register(name: string, email: string, password: string) {
    const { data } = await api.post('/auth/register', { name, email, password });
    return data;
  },

  me() {
    return api.get('/auth/me');
  },

  logout() {
    setAuthToken(undefined);
    window.dispatchEvent(new Event('auth-changed'));
  },
};

export default api;
