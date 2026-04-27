from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.prediction_repo import PredictionRepository
from app.schemas.prediction import UserReportOut

router = APIRouter(prefix="/api", tags=["reports"])


@router.get("/user/reports", response_model=list[UserReportOut])
def user_reports(
    email: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UserReportOut]:
    if email and email.lower() != current_user.email.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access reports for another user",
        )
    rows = PredictionRepository(db).get_user_reports(current_user.email)
    return [UserReportOut.model_validate(row) for row in rows]


@router.get("/reports/me", response_model=list[UserReportOut])
def my_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UserReportOut]:
    rows = PredictionRepository(db).get_user_reports(current_user.email)
    return [UserReportOut.model_validate(row) for row in rows]
