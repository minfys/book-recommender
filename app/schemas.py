"""Request/response models for the API boundary.

Validation that the spec deliberately keeps out of SQLite (1-10 rating ranges,
the polarity/status enums) is enforced here, so loosening it later is a one-line
change with no migration.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel

RATING_FIELD_DESCRIPTION = "1-10 scale"


class Polarity(str, Enum):
    worked = "worked"
    didnt_work = "didnt_work"


class TBRStatus(str, Enum):
    want_to_read = "want_to_read"
    read = "read"


# --------------------------------------------------------------------------- #
# Books
# --------------------------------------------------------------------------- #


class BookCreate(SQLModel):
    title: str
    author: str
    genre: Optional[str] = None
    page_count: Optional[int] = Field(default=None, ge=0)
    description: Optional[str] = None


class BookUpdate(SQLModel):
    """All fields optional — only what's sent gets written."""

    title: Optional[str] = None
    author: Optional[str] = None
    genre: Optional[str] = None
    page_count: Optional[int] = Field(default=None, ge=0)
    description: Optional[str] = None


class BookRead(SQLModel):
    id: int
    title: str
    author: str
    genre: Optional[str]
    page_count: Optional[int]
    description: Optional[str]
    source_id: Optional[str]
    created_at: datetime


# --------------------------------------------------------------------------- #
# Tags
# --------------------------------------------------------------------------- #


class TagCreate(SQLModel):
    label: str = Field(min_length=1)
    polarity_hint: Polarity


class TagUpdate(SQLModel):
    label: Optional[str] = Field(default=None, min_length=1)
    polarity_hint: Optional[Polarity] = None
    active: Optional[bool] = None


class TagRead(SQLModel):
    id: int
    label: str
    polarity_hint: str
    active: bool


# --------------------------------------------------------------------------- #
# Ratings
# --------------------------------------------------------------------------- #


class RatingCreate(SQLModel):
    book_id: int
    pacing: int = Field(ge=1, le=10, description=RATING_FIELD_DESCRIPTION)
    plot_complexity: int = Field(ge=1, le=10, description=RATING_FIELD_DESCRIPTION)
    character_depth: int = Field(ge=1, le=10, description=RATING_FIELD_DESCRIPTION)
    language_sophistication: int = Field(
        ge=1, le=10, description=RATING_FIELD_DESCRIPTION
    )
    overall_rating: int = Field(ge=1, le=10, description=RATING_FIELD_DESCRIPTION)
    review_text: Optional[str] = None
    tag_ids: list[int] = Field(default_factory=list)


class RatingUpdate(SQLModel):
    """Omitted fields are left alone; a supplied ``tag_ids`` replaces the set."""

    book_id: Optional[int] = None
    pacing: Optional[int] = Field(default=None, ge=1, le=10)
    plot_complexity: Optional[int] = Field(default=None, ge=1, le=10)
    character_depth: Optional[int] = Field(default=None, ge=1, le=10)
    language_sophistication: Optional[int] = Field(default=None, ge=1, le=10)
    overall_rating: Optional[int] = Field(default=None, ge=1, le=10)
    review_text: Optional[str] = None
    tag_ids: Optional[list[int]] = None


class RatingRead(SQLModel):
    id: int
    book_id: int
    pacing: int
    plot_complexity: int
    character_depth: int
    language_sophistication: int
    overall_rating: int
    review_text: Optional[str]
    created_at: datetime
    tags: list[TagRead] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# TBR
# --------------------------------------------------------------------------- #


class TBRCreate(SQLModel):
    book_id: int
    status: TBRStatus = TBRStatus.want_to_read


class TBRUpdate(SQLModel):
    status: Optional[TBRStatus] = None


class TBRRead(SQLModel):
    id: int
    book_id: int
    status: str
    predicted_score: Optional[float]
    created_at: datetime
    book_title: Optional[str] = None
    book_author: Optional[str] = None


# --------------------------------------------------------------------------- #
# Libraries
# --------------------------------------------------------------------------- #


class LibraryCreate(SQLModel):
    name: str = Field(min_length=1)
    catalog_url_template: str = Field(min_length=1)


class LibraryUpdate(SQLModel):
    name: Optional[str] = Field(default=None, min_length=1)
    catalog_url_template: Optional[str] = Field(default=None, min_length=1)
    active: Optional[bool] = None


class LibraryRead(SQLModel):
    id: int
    name: str
    catalog_url_template: str
    active: bool


class LibraryLink(SQLModel):
    library_id: int
    library_name: str
    url: str
