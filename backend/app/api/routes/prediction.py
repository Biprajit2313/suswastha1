from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.prediction import DiseaseType
from app.services.prediction_service import (
    PredictionService,
    get_feature_importance,
    get_model_metrics,
)

router = APIRouter(prefix="/api/predict", tags=["predictions"])


def get_prediction_service() -> PredictionService:
    return PredictionService()


@router.post("/{test_type}")
def predict_test(
    test_type: str,
    payload: dict[str, Any],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: PredictionService = Depends(get_prediction_service),
) -> dict[str, Any]:
    try:
        disease = DiseaseType(test_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid test type") from exc
    try:
        print("Prediction request received:", {"test_type": disease.value, "user": current_user.email})
        result = service.predict(
            test_type=disease,
            payload=payload,
            current_user=current_user,
            db=db,
            background_tasks=background_tasks,
        )
        return {
            "label": result.label,
            "risk_score": float(result.risk_score),
            "message": "Prediction completed successfully",
        }
    except HTTPException:
        raise
    except Exception as exc:
        print("Prediction error:", repr(exc))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Prediction failed") from exc


@router.get("/{test_type}/metrics")
def model_metrics(test_type: DiseaseType) -> dict[str, Any]:
    return get_model_metrics(test_type.value)


@router.get("/{test_type}/feature-importance")
def model_feature_importance(test_type: DiseaseType) -> dict[str, Any]:
    return get_feature_importance(test_type.value)
