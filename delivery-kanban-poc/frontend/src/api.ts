import type { AuthUser, BoardResponse, CardDetail, ChecklistItem } from "./types";

const apiRoot = (
  import.meta.env.VITE_API_BASE_URL ??
  (import.meta.env.DEV ? "http://127.0.0.1:8000" : "")
).replace(/\/$/, "");
const API_BASE = apiRoot ? `${apiRoot}/api` : "/api";
const AUTH_TOKEN_KEY = "kanban_auth_token";

export function getStoredAuthToken(): string {
  return localStorage.getItem(AUTH_TOKEN_KEY) ?? "";
}

function setStoredAuthToken(token: string) {
  localStorage.setItem(AUTH_TOKEN_KEY, token);
}

export function clearStoredAuthToken() {
  localStorage.removeItem(AUTH_TOKEN_KEY);
}

function getAuthHeaders(contentTypeJson = false): Record<string, string> {
  const headers: Record<string, string> = {};
  if (contentTypeJson) {
    headers["Content-Type"] = "application/json";
  }

  const token = getStoredAuthToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

export async function login(username: string, password: string): Promise<AuthUser> {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: getAuthHeaders(true),
    body: JSON.stringify({ username, password }),
  });
  const payload = await handleResponse<{ token: string; user: AuthUser }>(response);
  setStoredAuthToken(payload.token);
  return payload.user;
}

export async function fetchCurrentUser(): Promise<AuthUser> {
  const response = await fetch(`${API_BASE}/auth/me`, {
    headers: getAuthHeaders(),
  });
  return handleResponse<AuthUser>(response);
}

export async function fetchUsers(): Promise<AuthUser[]> {
  const response = await fetch(`${API_BASE}/auth/users`, {
    headers: getAuthHeaders(),
  });
  return handleResponse<AuthUser[]>(response);
}

export async function createUser(payload: {
  username: string;
  display_name: string;
  password: string;
}): Promise<AuthUser> {
  const response = await fetch(`${API_BASE}/auth/users`, {
    method: "POST",
    headers: getAuthHeaders(true),
    body: JSON.stringify(payload),
  });
  return handleResponse<AuthUser>(response);
}

export async function fetchBoard(includeArchived = false): Promise<BoardResponse> {
  const response = await fetch(`${API_BASE}/board?include_archived=${includeArchived}`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
}

export async function fetchCard(cardId: number): Promise<CardDetail> {
  const response = await fetch(`${API_BASE}/cards/${cardId}`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
}

export async function moveCard(params: {
  card_id: number;
  source_list_id: number;
  destination_list_id: number;
  destination_index: number;
}): Promise<BoardResponse> {
  const response = await fetch(`${API_BASE}/cards/move`, {
    method: "POST",
    headers: getAuthHeaders(true),
    body: JSON.stringify(params),
  });
  return handleResponse(response);
}

export async function saveCard(
  cardId: number,
  payload: {
    title: string;
    project_no: string;
    customer_name: string;
    status: string;
    received_date: string | null;
    requested_due_date: string | null;
    assignee_name: string;
    response_due_date: string | null;
    earliest_ship_date: string | null;
    description: string;
    notes: string;
    history_text: string;
    labels: string[];
    checklist: Array<Omit<ChecklistItem, "id"> & { id: number | null }>;
  },
): Promise<CardDetail> {
  const response = await fetch(`${API_BASE}/cards/${cardId}`, {
    method: "PUT",
    headers: getAuthHeaders(true),
    body: JSON.stringify(payload),
  });
  return handleResponse(response);
}

export async function addComment(cardId: number, body: string): Promise<CardDetail> {
  const response = await fetch(`${API_BASE}/cards/${cardId}/comments`, {
    method: "POST",
    headers: getAuthHeaders(true),
    body: JSON.stringify({ body }),
  });
  return handleResponse(response);
}

export async function createCard(
  listId: number,
  payload: {
    title: string;
    project_no?: string;
    customer_name?: string;
    description?: string;
  },
): Promise<CardDetail> {
  const response = await fetch(`${API_BASE}/lists/${listId}/cards`, {
    method: "POST",
    headers: getAuthHeaders(true),
    body: JSON.stringify(payload),
  });
  return handleResponse(response);
}

export async function archiveCard(cardId: number): Promise<CardDetail> {
  const response = await fetch(`${API_BASE}/cards/${cardId}/archive`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
}

export async function unarchiveCard(cardId: number): Promise<CardDetail> {
  const response = await fetch(`${API_BASE}/cards/${cardId}/unarchive`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    if (response.status === 401) {
      throw new Error("UNAUTHORIZED");
    }
    let message = `Request failed: ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        message = payload.detail;
      }
    } catch {
      // Ignore JSON parse failures and keep the default message.
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}
