
import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000/api",
  headers: {
    "Content-Type": "application/json",
  },
});

// Attach the JWT token to every protected API request.
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");

    if (token) {
      config.headers = config.headers || {};
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

export const phase3Api = {
  getShifts: () => api.get("/shifts").then((r) => r.data),
  getLeaves: () => api.get("/leaves").then((r) => r.data),
  getDocuments: () => api.get("/documents").then((r) => r.data),
  getPerformance: () => api.get("/performance").then((r) => r.data),
  getAnalytics: () => api.get("/analytics").then((r) => r.data),
  getNotifications: () => api.get("/notifications").then((r) => r.data),
  getEmployees: () => api.get("/employees").then((r) => r.data),
};

export default api;
