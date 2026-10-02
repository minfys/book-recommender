"""Engine, session dependency, and first-run table creation/seeding.

Tables come straight off ``SQLModel.metadata`` — there's no separate declarative
Base. No Alembic yet; ``create_all()`` is enough until the schema has to evolve
on top of real data.
"""

from collections.abc import Generator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Tag

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "book_recommender.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    # FastAPI serves requests off a threadpool; SQLite's default same-thread
    # guard would reject those connections.
    connect_args={"check_same_thread": False},
)

# Starting point only — tags are user-managed from here on, editable and
# retirable via /tags.
STARTER_TAGS: list[tuple[str, str]] = [
    ("well-paced", "worked"),
    ("complex plot", "worked"),
    ("strong character development", "worked"),
    ("beautiful prose", "worked"),
    ("satisfying ending", "worked"),
    ("well-executed romance", "worked"),
    ("predictable plot", "didnt_work"),
    ("info-dumping", "didnt_work"),
    ("flat characters", "didnt_work"),
    ("slow start", "didnt_work"),
    ("unresolved ending", "didnt_work"),
    ("juvenile romance", "didnt_work"),
    ("overwrought prose", "didnt_work"),
]


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def seed_tags() -> None:
    """Insert the starter tag list, but only into an empty Tag table."""
    with Session(engine) as session:
        if session.exec(select(Tag)).first() is not None:
            return
        session.add_all(
            Tag(label=label, polarity_hint=polarity) for label, polarity in STARTER_TAGS
        )
        session.commit()


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
