export type AuthUser = {
  id: number;
  username: string;
  display_name: string;
};

export type InquirySummary = {
  id: number;
  display_id: string;
  customer_name: string;
  requested_due_type: "shortest" | "specific";
  requested_due_date: string | null;
  requested_due_display: string;
  request_kind: "confirm" | "shorten";
  request_kind_label: string;
  remarks: string | null;
  item_count: number;
  created_at: string;
  updated_at: string;
};

export type InquiryItemSummary = {
  id: number;
  inquiry_id: number;
  inquiry_display_id: string;
  item_type: "P" | "E" | "S";
  item_no: string;
  process:
    | "sales_registered"
    | "not_drawn"
    | "arranging"
    | "arrival_receiving"
    | "internal_processing"
    | "shipped";
  process_label: string;
  owner: string;
  state: "normal" | "waiting" | "done";
  state_label: string;
  planned_arrival_date: string | null;
  actual_arrival_date: string | null;
  packing_due_date: string | null;
  confirmed_shipping_date: string | null;
  drawing_ready_confirmed: boolean;
  drawing_ready_confirmed_at: string | null;
  updated_at: string;
  remarks: string | null;
  customer_name: string;
  request_kind: "confirm" | "shorten";
  request_kind_label: string;
  requested_due_type: "shortest" | "specific";
  requested_due_date: string | null;
  requested_due_display: string;
};

export type InquiryDetail = {
  id: number;
  display_id: string;
  customer_name: string;
  requested_due_type: "shortest" | "specific";
  requested_due_date: string | null;
  requested_due_display: string;
  request_kind: "confirm" | "shorten";
  request_kind_label: string;
  remarks: string | null;
  created_at: string;
  updated_at: string;
  items: InquiryItemSummary[];
};

export type InquiryListResponse = {
  inquiries: InquirySummary[];
};

export type KanbanColumn = {
  process: InquiryItemSummary["process"];
  label: string;
  items: InquiryItemSummary[];
};

export type KanbanResponse = {
  columns: KanbanColumn[];
};

export type InquiryItemDetail = InquiryItemSummary;
