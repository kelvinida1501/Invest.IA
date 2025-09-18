import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

// instancia global
const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

// helper para setar token
export function setAuthToken(token: string | null) {
  if (token) {
    api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    localStorage.setItem("token", token);
  } else {
    delete api.defaults.headers.common["Authorization"];
    localStorage.removeItem("token");
  }
}

// tipos de resposta
export interface LoginResponse {
  access_token: string;
  token_type?: string;
}

export interface RegisterResponse {
  ok: boolean;
  access_token?: string;
}

// métodos auth
export const AuthApi = {
  login: async (email: string, password: string): Promise<LoginResponse> => {
    const res = await api.post<LoginResponse>("/auth/login", { email, password });
    if (res.data.access_token) {
      setAuthToken(res.data.access_token);
    }
    return res.data;
  },

  register: async (name: string, email: string, password: string): Promise<RegisterResponse> => {
    const res = await api.post<RegisterResponse>("/auth/register", {
      name,
      email,
      password,
    });
    if ((res.data as any).access_token) {
      setAuthToken((res.data as any).access_token);
    }
    return res.data;
  },

  me: async () => {
    const res = await api.get("/auth/me");
    return res.data;
  },
};

// outros módulos (exemplo)
export const NewsApi = {
  list: async () => {
    const res = await api.get("/news");
    return res.data;
  },
};

export const AssetsApi = {
  list: async () => {
    const res = await api.get("/assets");
    return res.data;
  },
  add: async (symbol: string, name: string, cls: string) => {
    const res = await api.post("/assets", { symbol, name, class: cls });
    return res.data;
  },
};

export default api;
