import type { BoardResponse, CardDetail, ChecklistItem } from "./types";

const API_BASE = "http://127.0.0.1:8000/api";

export async function fetchBoard(): Promise<BoardResponse> {
  const response = await fetch(`${API_BASE}/board`);
  return handleResponse(response);
}

export async function fetchCard(cardId: number): Promise<CardDetail> {
  const response = await fetch(`${API_BASE}/cards/${cardId}`);
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
    headers: { "Content-Type": "application/json" },
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
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleResponse(response);
}

export async function addComment(cardId: number, body: string): Promise<CardDetail> {
  const response = await fetch(`${API_BASE}/cards/${cardId}/comments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleResponse(response);
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}
