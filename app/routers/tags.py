from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlmodel import Session, select

from app.database import get_session
from app.models import Tag
from app.schemas import TagCreate, TagRead, TagUpdate

router = APIRouter(prefix="/tags", tags=["tags"])

SessionDep = Annotated[Session, Depends(get_session)]

ACTIVE_QUERY_DESCRIPTION = (
    "true (default) lists only active tags; false lists every tag, retired ones "
    "included."
)


def label_taken(session: Session, label: str, exclude_id: int | None = None) -> bool:
    statement = select(Tag).where(func.lower(Tag.label) == label.strip().lower())
    if exclude_id is not None:
        statement = statement.where(Tag.id != exclude_id)
    return session.exec(statement).first() is not None


@router.post("", response_model=TagRead, status_code=status.HTTP_201_CREATED)
def create_tag(payload: TagCreate, session: SessionDep) -> Tag:
    label = payload.label.strip()
    if label_taken(session, label):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A tag labelled '{label}' already exists",
        )
    tag = Tag(label=label, polarity_hint=payload.polarity_hint.value)
    session.add(tag)
    session.commit()
    session.refresh(tag)
    return tag


@router.get("", response_model=list[TagRead])
def list_tags(
    session: SessionDep,
    active: Annotated[bool, Query(description=ACTIVE_QUERY_DESCRIPTION)] = True,
) -> list[Tag]:
    statement = select(Tag)
    if active:
        statement = statement.where(Tag.active == True)  # noqa: E712
    return list(session.exec(statement.order_by(Tag.id)).all())


@router.get("/{tag_id}", response_model=TagRead)
def get_tag(tag_id: int, session: SessionDep) -> Tag:
    tag = session.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail=f"Tag {tag_id} not found")
    return tag


@router.put("/{tag_id}", response_model=TagRead)
def update_tag(tag_id: int, payload: TagUpdate, session: SessionDep) -> Tag:
    """Edit a tag, or retire/restore it by toggling ``active``.

    There is no DELETE: retiring keeps the tag attached to past ratings while
    removing it from the options offered for new ones.
    """
    tag = session.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail=f"Tag {tag_id} not found")

    # Every Tag column is non-nullable, so an explicit null is a no-op, not a clear.
    data = {
        field: value
        for field, value in payload.model_dump(exclude_unset=True).items()
        if value is not None
    }
    if "label" in data:
        label = data["label"].strip()
        if label_taken(session, label, exclude_id=tag_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A tag labelled '{label}' already exists",
            )
        data["label"] = label
    if "polarity_hint" in data:
        data["polarity_hint"] = payload.polarity_hint.value

    for field, value in data.items():
        setattr(tag, field, value)
    session.add(tag)
    session.commit()
    session.refresh(tag)
    return tag
