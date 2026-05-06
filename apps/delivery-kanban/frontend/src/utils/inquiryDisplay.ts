import type { InquiryItemSummary } from "../types";

const PROCESS_LABEL_MAP: Record<InquiryItemSummary["process"], string> = {
  sales_registered: "営業登録",
  not_drawn: "未出図",
  arranging: "調達中",
  arrival_receiving: "検査・表面処理",
  // Process/date alignment (R2):
  // - assembly -> assembly_completed_date
  // - packing -> packing_completed_date
  assembly: "組付け",
  packing: "梱包",
  shipped: "発送完了",
};

export function getProcessDisplayLabel(process: InquiryItemSummary["process"]): string {
  return PROCESS_LABEL_MAP[process];
}

export const PROCESS_OPTIONS = [
  { value: "not_drawn", label: PROCESS_LABEL_MAP.not_drawn },
  { value: "arranging", label: PROCESS_LABEL_MAP.arranging },
  { value: "arrival_receiving", label: PROCESS_LABEL_MAP.arrival_receiving },
  { value: "assembly", label: PROCESS_LABEL_MAP.assembly },
  { value: "packing", label: PROCESS_LABEL_MAP.packing },
  { value: "shipped", label: PROCESS_LABEL_MAP.shipped },
] as const;

export function formatDisplayItemNo(itemType: InquiryItemSummary["item_type"], itemNo: string): string {
  const normalized = itemNo.trim();
  if (!normalized) {
    return `${itemType}-`;
  }
  if (/^[PES]-/i.test(normalized)) {
    return `${normalized.slice(0, 1).toUpperCase()}${normalized.slice(1)}`;
  }
  return `${itemType}-${normalized}`;
}

export function buildOrderNoSummary(items: InquiryItemSummary[] | undefined): string {
  if (!items || items.length === 0) {
    return "-";
  }

  const uniqueOrderNos = Array.from(
    new Set(items.map((item) => formatDisplayItemNo(item.item_type, item.item_no))),
  ).sort((left, right) => left.localeCompare(right, "ja-JP"));
  if (uniqueOrderNos.length === 0) {
    return "-";
  }

  const shown = uniqueOrderNos.slice(0, 3).join(", ");
  if (uniqueOrderNos.length > 3) {
    return `${shown} ... (${uniqueOrderNos.length}件)`;
  }
  return `${shown} (${uniqueOrderNos.length}件)`;
}
