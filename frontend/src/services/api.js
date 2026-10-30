const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";
let historyCache = null;
let historyCacheTime = 0;

async function request(path, options = {}) {
  const token = localStorage.getItem("relife-token");
  const headers = new Headers(options.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 20000);
  try {
    const response = await fetch(`${API_URL}${path}`, { ...options, headers, signal: controller.signal });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
    return data;
  } catch (error) {
    if (error.name === "AbortError") throw new Error("The request took too long. Check your connection and try again.");
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

export const api = {
  register: async (body) => { const result = await request("/auth/register", { method: "POST", body: JSON.stringify(body) }); historyCache = null; return result; },
  login: async (body) => { const result = await request("/auth/login", { method: "POST", body: JSON.stringify(body) }); historyCache = null; return result; },
  me: () => request("/auth/me"),
  history: async () => {
    if (historyCache && Date.now() - historyCacheTime < 5000) return historyCache;
    historyCache = request("/history").catch((error) => { historyCache = null; throw error; });
    historyCacheTime = Date.now();
    return historyCache;
  },
  analyze: async (body) => {
    const result = await request("/analyses", { method: "POST", body });
    historyCache = null;
    return result;
  },
  passport: (id) => request(`/passports/${id}`),
  passportByPublicId: (publicId) => request(`/passports/lookup/${encodeURIComponent(publicId)}`),
  passportUpdate: (id, body) => request(`/passports/${id}/updates`, { method: "POST", body: JSON.stringify(body) }),
  transfer: (id, body) => request(`/passports/${id}/transfer`, { method: "POST", body: JSON.stringify(body) }),
  matches: (id) => request(`/matches/${id}`),
  matchUpdate: (productId, requestId, status) => request(`/matches/${productId}/${requestId}`, { method: "PATCH", body: JSON.stringify({ status }) }),
  salvage: (id, body) => request(`/salvage/${id}`, { method: "POST", body: JSON.stringify(body) }),
  getSalvage: (id) => request(`/salvage/${id}`),
  simulate: (body) => request("/simulations", { method: "POST", body: JSON.stringify(body) }),
  getSimulation: (id) => request(`/simulations/${id}`),
  centers: (params = {}) => request(`/centers?${new URLSearchParams(params)}`),
  liveCenters: (params) => request(`/centers/live?${new URLSearchParams(params)}`),
  createPlan: (id) => request(`/plans/${id}`, { method: "POST" }),
  getPlan: (id) => request(`/plans/${id}`),
  findPlanAlternative: (productId, stepId) => request(`/plans/${productId}/steps/${stepId}/alternative`, { method: "POST" }),
  updateStep: (id, status) => request(`/plans/steps/${id}`, { method: "PATCH", body: JSON.stringify({ status }) }),
  impact: () => request("/impact"),
};
