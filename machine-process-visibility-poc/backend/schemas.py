from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from constants import DESCRIPTION_TEMPLATE


class CardPayload(BaseModel):
    order_no: str = ""
    item_type: str = ""
    drawing_no: str
    item_name: str
    remarks: str = ""
    total_qty: int = Field(ge=0)
    completed_qty: int = Field(ge=0)
    current_process_id: int
    status: str
    assignee_id: Optional[int] = None
    planned_work_date: Optional[str] = None
    due_date: Optional[str] = None
    description: str = DESCRIPTION_TEMPLATE
    tag_ids: list[int] = []
    completed_qty_reason: str = ""


class CommentPayload(BaseModel):
    comment_type: str
    body: str
    user_id: Optional[int] = None


class WorkResultPayload(BaseModel):
    completed_qty_delta: int = Field(ge=0)
    work_hours: float = Field(ge=0)
    assignee_id: Optional[int] = None
    work_date: Optional[str] = None
    comment_type: str = "作業"
    comment: str = ""


class LoginPayload(BaseModel):
    username: str
    password: str


class ChangePasswordPayload(BaseModel):
    current_password: str
    new_password: str


class ActivePayload(BaseModel):
    active: bool


class AssigneePayload(BaseModel):
    name: str
    color: str = "#64748b"
    active: bool = True


class TagPayload(BaseModel):
    name: str
    color: str = "#64748b"
