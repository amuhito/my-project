import type { Card, CardDraft, Meta } from "../types";

export const PROCESS_VIEW_NAMES = ["内面研磨", "刃物研磨", "機械加工", "板金加工", "手加工"];

export const emptyCard = (meta: Meta): CardDraft => ({
  order_no: "",
  item_type: "",
  drawing_no: "",
  item_name: "",
  remarks: "",
  total_qty: 1,
  completed_qty: 0,
  current_process_id: meta.processes[0]?.id ?? 1,
  status: "未着手",
  assignee_id: meta.assignees[0]?.id ?? null,
  planned_work_date: "",
  due_date: "",
  description: "【状態】\n\n【注意】\n\n【次工程】\n",
  tag_ids: [],
});

export function labelStyle(color?: string) {
  return { backgroundColor: color ?? "#64748b" };
}

export function percent(card: Card) {
  return `${card.completed_qty}/${card.total_qty} (${card.progress_rate}%)`;
}

export function isRework(card: Card) {
  return card.tags.some((tag) => tag.name === "追加工");
}

export function toPayload(card: Card | CardDraft, tagIds?: number[], completedQtyReason = "") {
  return {
    order_no: card.order_no ?? "",
    item_type: card.item_type ?? "",
    drawing_no: card.drawing_no,
    item_name: card.item_name,
    remarks: card.remarks ?? "",
    total_qty: Number(card.total_qty),
    completed_qty: Number(card.completed_qty),
    current_process_id: Number(card.current_process_id),
    status: card.status,
    assignee_id: card.assignee_id ? Number(card.assignee_id) : null,
    planned_work_date: card.planned_work_date || null,
    due_date: card.due_date || null,
    description: card.description,
    tag_ids: tagIds ?? card.tags?.map((tag) => tag.id) ?? ("tag_ids" in card ? card.tag_ids ?? [] : []),
    completed_qty_reason: completedQtyReason,
  };
}
