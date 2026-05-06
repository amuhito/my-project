from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException

from auth import require_ready_user
from card_create_service import create_card_for_user
from card_query_service import get_card_detail, list_cards_for_user
from card_update_service import update_card_for_user
from schemas import CardPayload, CommentPayload, WorkResultPayload
from work_result_service import register_work_result_for_card


router = APIRouter(prefix="/api/cards")


@router.get("")
def list_cards(
    process_id: Optional[int] = None,
    assignee_id: Optional[int] = None,
    tag: Optional[str] = None,
    user: dict[str, Any] = Depends(require_ready_user),
) -> list[dict[str, Any]]:
    return list_cards_for_user(process_id=process_id, assignee_id=assignee_id, tag=tag)


@router.post("")
def create_card(payload: CardPayload, user: dict[str, Any] = Depends(require_ready_user)) -> dict[str, Any]:
    return create_card_for_user(payload, user)


@router.get("/{card_id}")
def card_detail(card_id: int, user: dict[str, Any] = Depends(require_ready_user)) -> dict[str, Any]:
    return get_card_detail(card_id)


@router.put("/{card_id}")
def update_card(card_id: int, payload: CardPayload, user: dict[str, Any] = Depends(require_ready_user)) -> dict[str, Any]:
    return update_card_for_user(card_id, payload, user)


@router.post("/{card_id}/comments")
def add_comment(card_id: int, payload: CommentPayload, user: dict[str, Any] = Depends(require_ready_user)) -> dict[str, Any]:
    raise HTTPException(status_code=400, detail="コメントは作業実績から登録してください")


@router.post("/{card_id}/work-results")
def register_work_result(card_id: int, payload: WorkResultPayload, user: dict[str, Any] = Depends(require_ready_user)) -> dict[str, Any]:
    return register_work_result_for_card(card_id, payload, user)
