export type CardSummary = {
  id: number;
  title: string;
  project_no: string;
  customer_name: string;
  status: string;
  received_date: string | null;
  labels: string[];
  requested_due_date: string | null;
  assignee_name: string;
  response_due_date: string | null;
  earliest_ship_date: string | null;
  notes: string;
  checklist_progress: string;
  comment_count: number;
};

export type BoardList = {
  id: number;
  title: string;
  position: number;
  cards: CardSummary[];
};

export type BoardResponse = {
  id: number;
  title: string;
  lists: BoardList[];
};

export type Comment = {
  id: number;
  author: string;
  body: string;
  created_at: string;
};

export type ChecklistItem = {
  id: number;
  text: string;
  completed: boolean;
  position: number;
};

export type Activity = {
  id: number;
  message: string;
  created_at: string;
};

export type CardDetail = {
  id: number;
  list_id: number;
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
  comments: Comment[];
  checklist: ChecklistItem[];
  activities: Activity[];
};
