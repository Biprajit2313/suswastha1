from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.prediction import DiseaseType
from app.services.image_service import ImageService
from app.services.multimodal_service import MultimodalService
from app.services.prediction_service import PredictionService

router = APIRouter(prefix="/api", tags=["image-predictions"])


@router.post("/predict-from-image/{test_type}")
async def predict_from_image(
    test_type: DiseaseType,
    background_tasks: BackgroundTasks,
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    image_service = ImageService()
    path = await image_service.save_upload(image)
    try:
        extracted = MultimodalService().extract_from_image(test_type=test_type.value, image_path=path)
        extracted_values = extracted["extracted_values"]
        missing = extracted["missing_values"]

        # Required response shape
        response: dict[str, Any] = {
            "extracted_data": extracted_values,
            "prediction": None,
        }

        # Backward-compatible fields (existing clients)
        response["ocr_text"] = extracted["ocr_text"]
        response["missing_values"] = missing

        if missing:
            return response

        # Persist + background report generation using the same pipeline as JSON predictions
        service = PredictionService()
        prediction_row = service.predict(
            test_type=test_type,
            payload=extracted_values,
            current_user=current_user,
            db=db,
            background_tasks=background_tasks,
        )

        response["prediction"] = prediction_row.model_dump()
        response["missing_values"] = []
        return response
    finally:
        image_service.cleanup(path)
