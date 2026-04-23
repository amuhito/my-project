export type AuthUser = {
  id: number;
  username: string;
  display_name: string;
};

// Legacy utility compatibility type.
export type CardSummary = {
  archived: boolean;
  status: string;
  requested_due_date: string | null;
  received_date: string | null;
  latest_activity_at: string | null;
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
  overall_status:
    | "unstarted"
    | "in_progress"
    | "partially_confirmed"
    | "fully_confirmed"
    | "completed";
  overall_status_label: string;
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
    | "assembly"
    | "packing"
    | "shipped";
  process_label: string;
  owner: string;
  state: "normal" | "waiting" | "done";
  state_label: string;
  final_arrival_planned_date: string | null;
  final_handover_date: string | null;
  assembly_completed_date: string | null;
  packing_completed_date: string | null;
  shipping_planned_date: string | null;
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

export type InquiryComment = {
  id: number;
  inquiry_id: number;
  comment_type: "normal" | "send_back";
  comment_type_label: string;
  body: string;
  created_at: string;
  created_by: string;
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
  comments: InquiryComment[];
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
