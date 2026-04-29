from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from migrations import init_db
from routers.auth import router as auth_router
from routers.cards import router as cards_router
from routers.meta import router as meta_router
from routers.reports import router as reports_router


app = FastAPI(title="機械課 工程見える化PoC")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meta_router)
app.include_router(auth_router)
app.include_router(cards_router)
app.include_router(reports_router)


@app.on_event("startup")
def startup() -> None:
    init_db()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False, app_dir=str(Path(__file__).parent))
