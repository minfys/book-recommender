from typing import Annotated, Optional
from urllib.parse import quote_plus

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlmodel import Session, select

from app.database import get_session
from app.models import Book, Library
from app.schemas import BookCreate, BookRead, BookUpdate, LibraryLink

router = APIRouter(prefix="/books", tags=["books"])

SessionDep = Annotated[Session, Depends(get_session)]


def get_book_or_404(session: Session, book_id: int) -> Book:
    book = session.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")
    return book


@router.post("", response_model=BookRead, status_code=status.HTTP_201_CREATED)
def create_book(payload: BookCreate, session: SessionDep) -> Book:
    book = Book.model_validate(payload)
    session.add(book)
    session.commit()
    session.refresh(book)
    return book


@router.get("", response_model=list[BookRead])
def list_books(
    session: SessionDep,
    genre: Annotated[
        Optional[str], Query(description="Case-insensitive exact match on genre")
    ] = None,
) -> list[Book]:
    statement = select(Book)
    if genre is not None:
        statement = statement.where(func.lower(Book.genre) == genre.strip().lower())
    return list(session.exec(statement.order_by(Book.id)).all())


@router.get("/{book_id}", response_model=BookRead)
def get_book(book_id: int, session: SessionDep) -> Book:
    return get_book_or_404(session, book_id)


@router.put("/{book_id}", response_model=BookRead)
def update_book(book_id: int, payload: BookUpdate, session: SessionDep) -> Book:
    book = get_book_or_404(session, book_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(book, field, value)
    session.add(book)
    session.commit()
    session.refresh(book)
    return book


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: int, session: SessionDep) -> None:
    book = get_book_or_404(session, book_id)
    # Cascades to the book's ratings (and their RatingTag links) and TBR entry.
    session.delete(book)
    session.commit()


@router.get("/{book_id}/library-links", response_model=list[LibraryLink])
def get_library_links(book_id: int, session: SessionDep) -> list[LibraryLink]:
    """Deep links into each active library's catalog search page.

    Pure string templating against rows already in the DB — no network calls, no
    availability lookup.
    """
    book = get_book_or_404(session, book_id)
    libraries = session.exec(
        select(Library).where(Library.active == True).order_by(Library.id)  # noqa: E712
    ).all()

    title = quote_plus(book.title)
    author = quote_plus(book.author)
    return [
        LibraryLink(
            library_id=library.id,
            library_name=library.name,
            # str.replace rather than str.format, so a template containing other
            # braces (or a typo'd placeholder) can't raise.
            url=library.catalog_url_template.replace("{title}", title).replace(
                "{author}", author
            ),
        )
        for library in libraries
    ]
