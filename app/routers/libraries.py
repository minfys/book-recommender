from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.database import get_session
from app.models import Library
from app.schemas import LibraryCreate, LibraryRead, LibraryUpdate

router = APIRouter(prefix="/libraries", tags=["libraries"])

SessionDep = Annotated[Session, Depends(get_session)]

ACTIVE_QUERY_DESCRIPTION = (
    "true (default) lists only active libraries; false lists every library, "
    "hidden ones included."
)


@router.post("", response_model=LibraryRead, status_code=status.HTTP_201_CREATED)
def create_library(payload: LibraryCreate, session: SessionDep) -> Library:
    """Register a library catalog.

    ``catalog_url_template`` should contain ``{title}`` and/or ``{author}``,
    e.g. ``https://bpl.bibliocommons.com/v2/search?query={title}+{author}``.
    """
    library = Library.model_validate(payload)
    session.add(library)
    session.commit()
    session.refresh(library)
    return library


@router.get("", response_model=list[LibraryRead])
def list_libraries(
    session: SessionDep,
    active: Annotated[bool, Query(description=ACTIVE_QUERY_DESCRIPTION)] = True,
) -> list[Library]:
    statement = select(Library)
    if active:
        statement = statement.where(Library.active == True)  # noqa: E712
    return list(session.exec(statement.order_by(Library.id)).all())


@router.get("/{library_id}", response_model=LibraryRead)
def get_library(library_id: int, session: SessionDep) -> Library:
    library = session.get(Library, library_id)
    if library is None:
        raise HTTPException(status_code=404, detail=f"Library {library_id} not found")
    return library


@router.put("/{library_id}", response_model=LibraryRead)
def update_library(
    library_id: int, payload: LibraryUpdate, session: SessionDep
) -> Library:
    """Edit a library, or hide/restore it by toggling ``active``.

    No DELETE, same hide-don't-delete pattern as Tag.
    """
    library = session.get(Library, library_id)
    if library is None:
        raise HTTPException(status_code=404, detail=f"Library {library_id} not found")

    # Every Library column is non-nullable, so an explicit null is a no-op.
    data = {
        field: value
        for field, value in payload.model_dump(exclude_unset=True).items()
        if value is not None
    }
    for field, value in data.items():
        setattr(library, field, value)
    session.add(library)
    session.commit()
    session.refresh(library)
    return library
