export type Process = { id: number; name: string; sort_order: number; active: number };
export type Assignee = { id: number; name: string; color: string; active: number };
export type Tag = { id: number; name: string; color: string };

export type Card = {
  id: number;
  order_no: string;
  item_type: string;
  drawing_no: string;
  item_name: string;
  remarks: string;
  total_qty: number;
  completed_qty: number;
  current_process_id: number;
  status: "未着手" | "作業中" | "完了";
  assignee_id: number | null;
  planned_work_date: string | null;
  due_date: string | null;
  description: string;
  progress_rate: number;
  assignee: Assignee | null;
  process: Process;
  tags: Tag[];
  comments?: Comment[];
  work_logs?: WorkLog[];
};

export type Comment = {
  id: number;
  comment_type: string;
  body: string;
  user_name?: string;
  created_at: string;
};

export type WorkLog = {
  id: number;
  work_date: string;
  completed_qty_delta: number;
  work_hours: number;
  assignee_name?: string;
  comment_type?: string;
  comment_body?: string;
  created_at: string;
};

export type ReportRow = {
  work_date: string;
  assignee_name: string;
  registered_by_name: string;
  process_name: string;
  order_no: string;
  item_type: string;
  drawing_no: string;
  item_name: string;
  remarks: string;
  completed_qty_delta: number;
  work_hours: number;
  comment_type: string;
  comment: string;
  finding: string;
};

export type Meta = { processes: Process[]; assignees: Assignee[]; tags: Tag[]; comment_types: string[] };
export type View = "board" | "process" | "assignee" | "calendar" | "report" | "admin";
export type ProcessSortMode = "due" | "assignee";

export type AuthUser = {
  id: number;
  username: string;
  display_name: string;
  assignee_id: number | null;
  assignee: Assignee | null;
  role: string;
  password_must_change: boolean;
};

export type LoginResponse = { token: string; user: AuthUser };

export type AdminUser = {
  id: number;
  username: string;
  display_name: string;
  assignee_id: number | null;
  assignee_name: string | null;
  role: string;
  active: number;
  password_must_change: number;
  password_changed_at: string | null;
  created_at: string;
};

export type WorkFormState = {
  work_date: string;
  completed_qty_delta: number;
  work_hours: number;
  assignee_id: number | null;
  comment_type: string;
  comment: string;
};

export type CardDraft = Omit<Card, "id" | "progress_rate" | "assignee" | "process" | "tags" | "comments" | "work_logs"> & {
  id?: number;
  progress_rate?: number;
  assignee?: Assignee | null;
  process?: Process;
  tags?: Tag[];
  comments?: Comment[];
  work_logs?: WorkLog[];
  tag_ids?: number[];
};
