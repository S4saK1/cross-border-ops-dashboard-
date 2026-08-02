import math
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.models.term import TermDictionary
from app.schemas.term import TermCreate, TermOut, TermListResponse
from app.core.deps import require_viewer, require_editor

router = APIRouter()


@router.get("", response_model=TermListResponse)
def list_terms(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str = Query(None),
    q: str = Query(None),
    is_builtin: bool = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_viewer),
):
    query = db.query(TermDictionary)
    if category:
        query = query.filter(TermDictionary.category == category)
    if q:
        query = query.filter(
            TermDictionary.zh.contains(q) | TermDictionary.en.contains(q)
        )
    if is_builtin is not None:
        query = query.filter(TermDictionary.is_builtin == is_builtin)
    total = query.count()
    items = query.order_by(TermDictionary.category, TermDictionary.zh).offset((page - 1) * page_size).limit(page_size).all()
    return TermListResponse(
        items=[TermOut.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.post("", response_model=TermOut, status_code=201)
def create_term(
    data: TermCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_editor),
):
    # P3: 预检 (zh, en) 唯一索引冲突，返回 409 而非 500
    existing = db.query(TermDictionary).filter(
        TermDictionary.zh == data.zh,
        TermDictionary.en == data.en,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Term already exists")

    term = TermDictionary(
        **data.model_dump(),
        is_builtin=False,
        created_by=current_user.id,
    )
    db.add(term)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Term already exists")
    db.refresh(term)
    return term
