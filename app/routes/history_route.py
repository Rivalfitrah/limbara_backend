import math
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel import Session, col, func, select

from app.database import get_session
from app.models import ScanHistory
from app.schemas.history import ScanHistoryCreate
from app.services.auth_service import get_current_user

router = APIRouter()


@router.post("", response_model=ScanHistory)
def create_history(request: Request, payload: ScanHistoryCreate, session: Session = Depends(get_session)):
    user = get_current_user(request, session)
    history = ScanHistory(user_id=user.id, **payload.model_dump(mode="json"))
    session.add(history)
    session.commit()
    session.refresh(history)
    return history


@router.get("")
def list_histories(
    request: Request,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 9,
    session: Session = Depends(get_session),
):
    user = get_current_user(request, session)
    statement = select(ScanHistory).where(ScanHistory.user_id == user.id)
    total = session.exec(select(func.count()).select_from(ScanHistory).where(ScanHistory.user_id == user.id)).one()
    histories = session.exec(statement.order_by(col(ScanHistory.created_at).desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return {
        "data": histories,
        "total": total,
        "page": page,
        "pageSize": page_size,
        "totalPages": math.ceil(total / page_size) if total else 0,
    }


@router.get("/{history_id}", response_model=ScanHistory)
def get_history(history_id: str, request: Request, session: Session = Depends(get_session)):
    user = get_current_user(request, session)
    history = session.get(ScanHistory, history_id)
    if history is None or history.user_id != user.id:
        raise HTTPException(status_code=404, detail="Riwayat scan tidak ditemukan.")
    return history
