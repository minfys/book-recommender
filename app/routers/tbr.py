from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.database import get_session
from app.models import TBR, Book
from app.schemas import TBRCreate, TBRRead, TBRStatus, TBRUpdate

router = APIRouter(prefix="/tbr", tags=["tbr"])

SessionDep = Annotated[Session, Depends(get_session)]


def to_tbr_read(entry: TBR, book: Optional[Book]) -> TBRRead:
    return TBRRead(
        id=entry.id,
        book_id=entry.book_id,
        status=entry.status,
        predicted_score=entry.predicted_score,
        created_at=entry.created_at,
        book_title=book.title if book else None,
        book_author=book.author if book else None,
    )


@router.post("", response_model=TBRRead, status_code=status.HTTP_201_CREATED)
def create_tbr_entry(payload: TBRCreate, session: SessionDep) -> TBRRead:
    book = session.get(Book, payload.book_id)
    if book is None:
        raise HTTPException(
            status_code=404, detail=f"Book {payload.book_id} not found"
        )

    existing = session.exec(
        select(TBR).where(TBR.book_id == payload.book_id)
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Book {payload.book_id} already has a TBR entry ({existing.id})",
        )

    # predicted_score stays null until the Phase 4+ regression exists.
    entry = TBR(book_id=payload.book_id, status=payload.status.value)
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return to_tbr_read(entry, book)


@router.get("", response_model=list[TBRRead])
def list_tbr_entries(
    session: SessionDep,
    status_filter: Annotated[Optional[TBRStatus], Query(alias="status")] = None,
) -> list[TBRRead]:
    statement = select(TBR, Book).join(Book, TBR.book_id == Book.id)
    if status_filter is not None:
        statement = statement.where(TBR.status == status_filter.value)
    rows = session.exec(statement.order_by(TBR.id)).all()
    return [to_tbr_read(entry, book) for entry, book in rows]


@router.get("/{tbr_id}", response_model=TBRRead)
def get_tbr_entry(tbr_id: int, session: SessionDep) -> TBRRead:
    entry = session.get(TBR, tbr_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"TBR entry {tbr_id} not found")
    return to_tbr_read(entry, session.get(Book, entry.book_id))


@router.put("/{tbr_id}", response_model=TBRRead)
def update_tbr_entry(tbr_id: int, payload: TBRUpdate, session: SessionDep) -> TBRRead:
    entry = session.get(TBR, tbr_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"TBR entry {tbr_id} not found")

    if payload.status is not None:
        entry.status = payload.status.value
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return to_tbr_read(entry, session.get(Book, entry.book_id))


@router.delete("/{tbr_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tbr_entry(tbr_id: int, session: SessionDep) -> None:
    entry = session.get(TBR, tbr_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"TBR entry {tbr_id} not found")
    session.delete(entry)
    session.commit()
