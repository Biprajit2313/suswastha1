from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.prediction_repo import PredictionRepository
from app.schemas.prediction import UserReportOut
from app.services.prediction_service import process_prediction_report

router = APIRouter(prefix="/api", tags=["reports"])


@router.post("/user/reports/sync")
def sync_user_reports(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """
    Finds reports with missing PDF URLs and re-queues them for generation.
    """
    repo = PredictionRepository(db)
    rows = repo.get_user_reports(current_user.email, limit=50)
    
    count = 0
    for row in rows:
        if not row.pdf_url:
            background_tasks.add_task(process_prediction_report, row.id)
            count += 1
            
    return {"message": f"Successfully queued {count} reports for regeneration"}


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
