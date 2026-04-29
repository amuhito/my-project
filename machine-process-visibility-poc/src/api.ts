export const API = "http://127.0.0.1:8000/api";
export const TOKEN_KEY = "machine_poc_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
  });
  if (res.status === 401) {
    clearToken();
  }
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "APIエラー" }));
    throw new Error(error.detail ?? "APIエラー");
  }
  return res.json();
}
