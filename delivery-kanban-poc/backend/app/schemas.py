from __future__ import annotations

from pydantic import BaseModel, Field


class Comment(BaseModel):
    id: int
    author: str
    body: str
    created_at: str


class ChecklistItem(BaseModel):
    id: int
    text: str
    completed: bool
    position: int


class Activity(BaseModel):
    id: int
    message: str
    created_at: str


class CardSummary(BaseModel):
    id: int
    title: str
    project_no: str
    customer_name: str
    status: str
    received_date: str | None
    latest_activity_at: str | None
    labels: list[str]
    requested_due_date: str | None
    assignee_name: str
    response_due_date: str | None
    earliest_ship_date: str | None
    notes: str
    checklist_progress: str
    comment_count: int
    archived: bool


class CardDetail(BaseModel):
    id: int
    list_id: int
    title: str
    project_no: str
    customer_name: str
    status: str
    received_date: str | None
    latest_activity_at: str | None
    requested_due_date: str | None
    assignee_name: str
    response_due_date: str | None
    earliest_ship_date: str | None
    description: str
    notes: str
    history_text: str
    labels: list[str]
    comments: list[Comment]
    checklist: list[ChecklistItem]
    activities: list[Activity]
    archived: bool


class BoardList(BaseModel):
    id: int
    title: str
    position: int
    cards: list[CardSummary]


class BoardResponse(BaseModel):
    id: int
    title: str
    lists: list[BoardList]


class MoveCardRequest(BaseModel):
    card_id: int
    source_list_id: int
    destination_list_id: int
    destination_index: int = Field(ge=0)


class SaveChecklistItem(BaseModel):
    id: int | None = None
    text: str
    completed: bool = False
    position: int


class SaveCardRequest(BaseModel):
    title: str = ""
    project_no: str = ""
    customer_name: str = ""
    status: str
    received_date: str | None = None
    requested_due_date: str | None = None
    assignee_name: str = ""
    response_due_date: str | None = None
    earliest_ship_date: str | None = None
    description: str = ""
    notes: str = ""
    history_text: str = ""
    labels: list[str]
    checklist: list[SaveChecklistItem]


class AddCommentRequest(BaseModel):
    author: str = "あなた"
    body: str


class CreateCardRequest(BaseModel):
    title: str = ""
    project_no: str = ""
    customer_name: str = ""
    description: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthUserResponse(BaseModel):
    id: int
    username: str
    display_name: str


class LoginResponse(BaseModel):
    token: str
    user: AuthUserResponse


class CreateUserRequest(BaseModel):
    username: str
    display_name: str
    password: str


class InquirySummary(BaseModel):
    id: int
    display_id: str
    customer_name: str
    requested_due_type: str
    requested_due_date: str | None
    requested_due_display: str
    request_kind: str
    request_kind_label: str
    overall_status: str
    overall_status_label: str
    remarks: str | None
    item_count: int
    created_at: str
    updated_at: str


class InquiryListResponse(BaseModel):
    inquiries: list[InquirySummary]


class InquiryItemSummary(BaseModel):
    id: int
    inquiry_id: int
    inquiry_display_id: str
    item_type: str
    item_no: str
    process: str
    process_label: str
    owner: str
    state: str
    state_label: str
    # Canonical domain date fields (public API contract).
    final_arrival_planned_date: str | None
    final_handover_date: str | None
    assembly_completed_date: str | None
    packing_completed_date: str | None
    shipping_planned_date: str | None
    drawing_ready_confirmed: bool
    drawing_ready_confirmed_at: str | None
    updated_at: str
    remarks: str | None
    customer_name: str
    request_kind: str
    request_kind_label: str
    requested_due_type: str
    requested_due_date: str | None
    requested_due_display: str


class InquiryComment(BaseModel):
    id: int
    inquiry_id: int
    comment_type: str
    comment_type_label: str
    body: str
    created_at: str
    created_by: str


class InquiryDetail(BaseModel):
    id: int
    display_id: str
    customer_name: str
    requested_due_type: str
    requested_due_date: str | None
    requested_due_display: str
    request_kind: str
    request_kind_label: str
    remarks: str | None
    created_at: str
    updated_at: str
    items: list[InquiryItemSummary]
    comments: list[InquiryComment]


class CreateInquiryRequest(BaseModel):
    customer_name: str
    order_nos: str
    requested_due_type: str = "shortest"
    requested_due_date: str | None = None
    request_kind: str = "confirm"
    remarks: str | None = None


class AddInquiryCommentRequest(BaseModel):
    comment_type: str = "normal"
    body: str


class UpdateInquiryItemRequest(BaseModel):
    process: str
    owner: str = ""
    state: str
    final_arrival_planned_date: str | None = None
    final_handover_date: str | None = None
    assembly_completed_date: str | None = None
    packing_completed_date: str | None = None
    shipping_planned_date: str | None = None
    remarks: str | None = None


class InquiryItemDetail(InquiryItemSummary):
    pass


class InquiryMoveRequest(BaseModel):
    item_id: int
    destination_process: str
    destination_index: int = Field(ge=0)


class KanbanColumn(BaseModel):
    process: str
    label: str
    items: list[InquiryItemSummary]


class KanbanResponse(BaseModel):
    columns: list[KanbanColumn]
