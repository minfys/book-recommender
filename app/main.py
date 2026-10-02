from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.database import create_db_and_tables, seed_tags
from app.routers import books, libraries, ratings, tags, tbr

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    seed_tags()
    yield


app = FastAPI(
    title="Book Recommender",
    description=(
        "Phase 1: schema + CRUD + library catalog deep links. No external "
        "metadata lookups, no predictions yet."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(books.router)
app.include_router(ratings.router)
app.include_router(tags.router)
app.include_router(tbr.router)
app.include_router(libraries.router)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    """The single-page UI. It talks to the same routers as /docs does."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok", "docs": "/docs"}
