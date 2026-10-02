from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.database import get_session
from app.models import Book, Rating, Tag
from app.schemas import RatingCreate, RatingRead, RatingUpdate, TagRead

router = APIRouter(prefix="/ratings", tags=["ratings"])

SessionDep = Annotated[Session, Depends(get_session)]


def to_rating_read(rating: Rating) -> RatingRead:
    """Build the response while the session is still open (tags are lazy)."""
    return RatingRead(
        id=rating.id,
        book_id=rating.book_id,
        pacing=rating.pacing,
        plot_complexity=rating.plot_complexity,
        character_depth=rating.character_depth,
        language_sophistication=rating.language_sophistication,
        overall_rating=rating.overall_rating,
        review_text=rating.review_text,
        created_at=rating.created_at,
        tags=[TagRead.model_validate(tag, from_attributes=True) for tag in rating.tags],
    )


def require_book(session: Session, book_id: int) -> Book:
    book = session.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")
    return book


def resolve_tags(session: Session, tag_ids: list[int]) -> list[Tag]:
    """Look up tags by id, preserving request order and rejecting unknown ids.

    Retired (``active=false``) tags are still attachable — they stay valid on
    ratings, they just don't show up as options for new ones.
    """
    unique_ids = list(dict.fromkeys(tag_ids))
    if not unique_ids:
        return []
    found = {
        tag.id: tag
        for tag in session.exec(select(Tag).where(Tag.id.in_(unique_ids))).all()
    }
    missing = [tag_id for tag_id in unique_ids if tag_id not in found]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown tag_ids: {missing}",
        )
    return [found[tag_id] for tag_id in unique_ids]


@router.post("", response_model=RatingRead, status_code=status.HTTP_201_CREATED)
def create_rating(payload: RatingCreate, session: SessionDep) -> RatingRead:
    require_book(session, payload.book_id)
    tags = resolve_tags(session, payload.tag_ids)

    rating = Rating.model_validate(payload, update={"tags": tags})
    session.add(rating)
    session.commit()
    session.refresh(rating)
    return to_rating_read(rating)


@router.get("", response_model=list[RatingRead])
def list_ratings(
    session: SessionDep,
    book_id: Annotated[Optional[int], Query()] = None,
) -> list[RatingRead]:
    statement = select(Rating).options(selectinload(Rating.tags))
    if book_id is not None:
        statement = statement.where(Rating.book_id == book_id)
    ratings = session.exec(statement.order_by(Rating.id)).all()
    return [to_rating_read(rating) for rating in ratings]


@router.get("/{rating_id}", response_model=RatingRead)
def get_rating(rating_id: int, session: SessionDep) -> RatingRead:
    rating = session.get(Rating, rating_id)
    if rating is None:
        raise HTTPException(status_code=404, detail=f"Rating {rating_id} not found")
    return to_rating_read(rating)


@router.put("/{rating_id}", response_model=RatingRead)
def update_rating(
    rating_id: int, payload: RatingUpdate, session: SessionDep
) -> RatingRead:
    rating = session.get(Rating, rating_id)
    if rating is None:
        raise HTTPException(status_code=404, detail=f"Rating {rating_id} not found")

    data = payload.model_dump(exclude_unset=True)
    tag_ids = data.pop("tag_ids", None)

    if "book_id" in data:
        require_book(session, data["book_id"])
    for field, value in data.items():
        setattr(rating, field, value)
    if tag_ids is not None:
        # Assigning the collection drops the old RatingTag rows and inserts the
        # new ones in one go.
        rating.tags = resolve_tags(session, tag_ids)

    session.add(rating)
    session.commit()
    session.refresh(rating)
    return to_rating_read(rating)


@router.delete("/{rating_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rating(rating_id: int, session: SessionDep) -> None:
    rating = session.get(Rating, rating_id)
    if rating is None:
        raise HTTPException(status_code=404, detail=f"Rating {rating_id} not found")
    # Its RatingTag rows go with it.
    session.delete(rating)
    session.commit()
