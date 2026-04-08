from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .database import initialize_database
from .repository import (
    add_comment,
    create_card,
    fetch_board,
    fetch_card_detail,
    move_card,
    save_card,
    set_card_archived,
)
from .schemas import (
    AddCommentRequest,
    BoardResponse,
    CardDetail,
    CreateCardRequest,
    MoveCardRequest,
    SaveCardRequest,
)

app = FastAPI(title="Kanban POC API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    initialize_database()


@app.get("/api/board", response_model=BoardResponse)
def get_board(include_archived: bool = Query(default=False)) -> BoardResponse:
    return fetch_board(include_archived=include_archived)


@app.get("/api/cards/{card_id}", response_model=CardDetail)
def get_card(card_id: int) -> CardDetail:
    card = fetch_card_detail(card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return card


@app.post("/api/cards/move", response_model=BoardResponse)
def post_move_card(payload: MoveCardRequest) -> BoardResponse:
    try:
        move_card(payload)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return fetch_board()


@app.put("/api/cards/{card_id}", response_model=CardDetail)
def put_card(card_id: int, payload: SaveCardRequest) -> CardDetail:
    if not (payload.title.strip() or payload.project_no.strip() or payload.customer_name.strip()):
        raise HTTPException(status_code=400, detail="Card title or business fields are required")
    card = save_card(card_id, payload)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return card


@app.post("/api/cards/{card_id}/comments", response_model=CardDetail)
def post_comment(card_id: int, payload: AddCommentRequest) -> CardDetail:
    if not payload.body.strip():
        raise HTTPException(status_code=400, detail="Comment body is required")
    card = add_comment(card_id, payload)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return card


@app.post("/api/lists/{list_id}/cards", response_model=CardDetail)
def post_card(list_id: int, payload: CreateCardRequest) -> CardDetail:
    if not (payload.title.strip() or payload.project_no.strip() or payload.customer_name.strip()):
        raise HTTPException(status_code=400, detail="Card title or business fields are required")
    card = create_card(list_id, payload)
    if card is None:
        raise HTTPException(status_code=404, detail="List not found")
    return card


@app.post("/api/cards/{card_id}/archive", response_model=CardDetail)
def post_archive_card(card_id: int) -> CardDetail:
    try:
        card = set_card_archived(card_id, True)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return card


@app.post("/api/cards/{card_id}/unarchive", response_model=CardDetail)
def post_unarchive_card(card_id: int) -> CardDetail:
    try:
        card = set_card_archived(card_id, False)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return card
