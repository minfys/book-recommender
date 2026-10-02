"""SQLModel table definitions.

These classes are the DB layer only. Request/response shapes live in
``app/schemas.py`` — keeping them separate means the 1-10 range checks and the
"worked"/"didnt_work" style enums can be enforced at the API boundary without
baking constraints into the SQLite file, which is what the spec asks for.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RatingTag(SQLModel, table=True):
    """Many-to-many join between a Rating and the Tags attached to it."""

    __tablename__ = "ratingtag"

    rating_id: int = Field(foreign_key="rating.id", primary_key=True)
    tag_id: int = Field(foreign_key="tag.id", primary_key=True)


class Book(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    author: str
    genre: Optional[str] = None
    page_count: Optional[int] = None
    description: Optional[str] = None
    # Populated in Phase 2 from Open Library / Google Books.
    source_id: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)

    ratings: list["Rating"] = Relationship(
        back_populates="book",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    tbr: Optional["TBR"] = Relationship(
        back_populates="book",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "uselist": False},
    )


class Rating(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    book_id: int = Field(foreign_key="book.id", index=True)
    pacing: int
    plot_complexity: int
    character_depth: int
    language_sophistication: int
    overall_rating: int
    review_text: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)

    book: Optional[Book] = Relationship(back_populates="ratings")
    tags: list["Tag"] = Relationship(back_populates="ratings", link_model=RatingTag)


class Tag(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    label: str = Field(unique=True, index=True)
    # "worked" | "didnt_work" — which UI section the checkbox sits under. The
    # regression learns the real direction independently of this hint.
    polarity_hint: str
    active: bool = Field(default=True)

    ratings: list[Rating] = Relationship(back_populates="tags", link_model=RatingTag)


class TBR(SQLModel, table=True):
    __tablename__ = "tbr"

    id: Optional[int] = Field(default=None, primary_key=True)
    book_id: int = Field(foreign_key="book.id", unique=True)
    # "want_to_read" | "read"
    status: str = Field(default="want_to_read", index=True)
    # Filled in by the Phase 4+ regression; always null for now.
    predicted_score: Optional[float] = None
    created_at: datetime = Field(default_factory=utcnow)

    book: Optional[Book] = Relationship(back_populates="tbr")


class Library(SQLModel, table=True):
    __tablename__ = "library"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    # URL string containing {title} and/or {author} placeholders.
    catalog_url_template: str
    active: bool = Field(default=True)
