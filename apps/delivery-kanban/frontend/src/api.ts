import type {
  AuthUser,
  InquiryDetail,
  InquiryComment,
  InquiryItemDetail,
  InquiryListResponse,
  KanbanResponse,
} from "./types";

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

export async function fetchInquiries(): Promise<InquiryListResponse> {
  const response = await fetch(`${API_BASE}/inquiries`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
}

export async function createInquiry(payload: {
  customer_name: string;
  order_nos: string;
  requested_due_type: "shortest" | "specific";
  requested_due_date: string | null;
  request_kind: "confirm" | "shorten";
  remarks: string;
}): Promise<InquiryDetail> {
  const response = await fetch(`${API_BASE}/inquiries`, {
    method: "POST",
    headers: getAuthHeaders(true),
    body: JSON.stringify(payload),
  });
  return handleResponse(response);
}

export async function fetchInquiry(inquiryId: number): Promise<InquiryDetail> {
  const response = await fetch(`${API_BASE}/inquiries/${inquiryId}`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
}

export async function fetchInquiryComments(inquiryId: number): Promise<InquiryComment[]> {
  const response = await fetch(`${API_BASE}/inquiries/${inquiryId}/comments`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
}

export async function addInquiryComment(
  inquiryId: number,
  payload: {
    comment_type: "normal" | "send_back";
    body: string;
  },
): Promise<InquiryComment> {
  const response = await fetch(`${API_BASE}/inquiries/${inquiryId}/comments`, {
    method: "POST",
    headers: getAuthHeaders(true),
    body: JSON.stringify(payload),
  });
  return handleResponse(response);
}

export async function fetchKanban(): Promise<KanbanResponse> {
  const response = await fetch(`${API_BASE}/kanban/items`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
}

export async function moveInquiryItem(payload: {
  item_id: number;
  destination_process: string;
  destination_index: number;
}): Promise<KanbanResponse> {
  const response = await fetch(`${API_BASE}/inquiry-items/move`, {
    method: "POST",
    headers: getAuthHeaders(true),
    body: JSON.stringify(payload),
  });
  return handleResponse(response);
}

export async function fetchInquiryItem(itemId: number): Promise<InquiryItemDetail> {
  const response = await fetch(`${API_BASE}/inquiry-items/${itemId}`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
}

export async function updateInquiryItem(
  itemId: number,
  payload: {
    process: string;
    owner: string;
    state: "normal" | "waiting" | "done";
    final_arrival_planned_date?: string | null;
    final_handover_date?: string | null;
    assembly_completed_date?: string | null;
    packing_completed_date?: string | null;
    shipping_planned_date?: string | null;
    remarks: string;
  },
): Promise<InquiryItemDetail> {
  const response = await fetch(`${API_BASE}/inquiry-items/${itemId}`, {
    method: "PUT",
    headers: getAuthHeaders(true),
    body: JSON.stringify(payload),
  });
  return handleResponse(response);
}

export async function confirmDrawingReady(itemId: number): Promise<InquiryItemDetail> {
  const response = await fetch(`${API_BASE}/inquiry-items/${itemId}/confirm-drawing`, {
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
      // Ignore JSON parse failures.
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}
