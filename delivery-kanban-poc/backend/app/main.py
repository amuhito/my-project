from __future__ import annotations

import os
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .auth import AuthUser, authenticate_user, create_session, create_user, ensure_default_user, list_users, resolve_user_by_token
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
    AuthUserResponse,
    BoardResponse,
    CardDetail,
    CreateUserRequest,
    CreateCardRequest,
    LoginRequest,
    LoginResponse,
    MoveCardRequest,
    SaveCardRequest,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"


def get_allowed_origins() -> list[str]:
    configured = os.getenv("KANBAN_CORS_ORIGINS", "").strip()
    if not configured:
        return ["http://localhost:5173", "http://127.0.0.1:5173"]
    if configured == "*":
        return ["*"]
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


def get_frontend_dist() -> Path:
    configured = os.getenv("KANBAN_FRONTEND_DIST", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return DEFAULT_FRONTEND_DIST


app = FastAPI(title="Kanban POC API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    initialize_database()
    ensure_default_user()


@app.get("/api/health")
def get_health() -> dict[str, str]:
    return {"status": "ok"}


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        return ""
    prefix = "bearer "
    if authorization.lower().startswith(prefix):
        return authorization[len(prefix) :].strip()
    return ""


def require_auth_user(authorization: str | None = Header(default=None)) -> AuthUser:
    token = _extract_bearer_token(authorization)
    user = resolve_user_by_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="ログインが必要です。")
    return user


def require_admin_user(current_user: AuthUser = Depends(require_auth_user)) -> AuthUser:
    if current_user.username != "admin":
        raise HTTPException(status_code=403, detail="管理者のみ実行できます。")
    return current_user


@app.post("/api/auth/login", response_model=LoginResponse)
def post_login(payload: LoginRequest) -> LoginResponse:
    user = authenticate_user(payload.username, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="ユーザー名またはパスワードが正しくありません。")

    token = create_session(user.id)
    return LoginResponse(
        token=token,
        user=AuthUserResponse(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
        ),
    )


@app.get("/api/auth/me", response_model=AuthUserResponse)
def get_me(current_user: AuthUser = Depends(require_auth_user)) -> AuthUserResponse:
    return AuthUserResponse(
        id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
    )


@app.get("/api/auth/users", response_model=list[AuthUserResponse])
def get_users(_: AuthUser = Depends(require_admin_user)) -> list[AuthUserResponse]:
    return [
        AuthUserResponse(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
        )
        for user in list_users()
    ]


@app.post("/api/auth/users", response_model=AuthUserResponse)
def post_user(
    payload: CreateUserRequest,
    _: AuthUser = Depends(require_admin_user),
) -> AuthUserResponse:
    try:
        user = create_user(payload.username, payload.display_name, payload.password)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return AuthUserResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
    )


@app.get("/api/board", response_model=BoardResponse)
def get_board(
    include_archived: bool = Query(default=False),
    _: AuthUser = Depends(require_auth_user),
) -> BoardResponse:
    return fetch_board(include_archived=include_archived)


@app.get("/api/cards/{card_id}", response_model=CardDetail)
def get_card(card_id: int, _: AuthUser = Depends(require_auth_user)) -> CardDetail:
    card = fetch_card_detail(card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return card


@app.post("/api/cards/move", response_model=BoardResponse)
def post_move_card(payload: MoveCardRequest, current_user: AuthUser = Depends(require_auth_user)) -> BoardResponse:
    try:
        move_card(payload, current_user)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return fetch_board()


@app.put("/api/cards/{card_id}", response_model=CardDetail)
def put_card(
    card_id: int,
    payload: SaveCardRequest,
    current_user: AuthUser = Depends(require_auth_user),
) -> CardDetail:
    if not (payload.title.strip() or payload.project_no.strip() or payload.customer_name.strip()):
        raise HTTPException(status_code=400, detail="Card title or business fields are required")
    try:
        card = save_card(card_id, payload, current_user)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return card


@app.post("/api/cards/{card_id}/comments", response_model=CardDetail)
def post_comment(
    card_id: int,
    payload: AddCommentRequest,
    current_user: AuthUser = Depends(require_auth_user),
) -> CardDetail:
    if not payload.body.strip():
        raise HTTPException(status_code=400, detail="Comment body is required")
    card = add_comment(card_id, payload, current_user)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return card


@app.post("/api/lists/{list_id}/cards", response_model=CardDetail)
def post_card(
    list_id: int,
    payload: CreateCardRequest,
    current_user: AuthUser = Depends(require_auth_user),
) -> CardDetail:
    if not (payload.title.strip() or payload.project_no.strip() or payload.customer_name.strip()):
        raise HTTPException(status_code=400, detail="Card title or business fields are required")
    try:
        card = create_card(list_id, payload, current_user)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if card is None:
        raise HTTPException(status_code=404, detail="List not found")
    return card


@app.post("/api/cards/{card_id}/archive", response_model=CardDetail)
def post_archive_card(card_id: int, current_user: AuthUser = Depends(require_auth_user)) -> CardDetail:
    try:
        card = set_card_archived(card_id, True, current_user)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return card


@app.post("/api/cards/{card_id}/unarchive", response_model=CardDetail)
def post_unarchive_card(card_id: int, current_user: AuthUser = Depends(require_auth_user)) -> CardDetail:
    try:
        card = set_card_archived(card_id, False, current_user)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return card


frontend_dist = get_frontend_dist()
frontend_assets = frontend_dist / "assets"
frontend_index = frontend_dist / "index.html"

if frontend_assets.exists():
    app.mount("/assets", StaticFiles(directory=frontend_assets), name="assets")


if frontend_index.exists():

    @app.get("/", include_in_schema=False)
    def serve_index() -> FileResponse:
        return FileResponse(frontend_index)


    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str) -> FileResponse:
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = frontend_dist / full_path
        if candidate.exists() and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(frontend_index)
