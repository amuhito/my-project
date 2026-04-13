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
