from pathlib import Path
from typing import Any

from fastapi import HTTPException, status

from app.services.ocr_service import OCRService
from app.services.parser_service import ParserService
from app.services.prediction_service import predict
from app.services.recommendation_service import RecommendationService



class MultimodalService:
    def __init__(
        self,
        ocr_service: OCRService | None = None,
        parser_service: ParserService | None = None,
    ) -> None:
        self.ocr_service = ocr_service or OCRService()
        self.parser_service = parser_service or ParserService()

    def extract_from_image(self, *, test_type: str, image_path: Path) -> dict[str, Any]:
        text = self.ocr_service.extract_text(image_path)
        if not text.strip():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "OCR failed to extract any text. If running locally, ensure the "
                    "Tesseract binary is installed/configured or that EasyOCR dependencies are available."
                ),
            )

        extracted = self.parser_service.extract_values(test_type=test_type, text=text)
        missing = self.parser_service.missing_values(test_type=test_type, values=extracted)
        return {"ocr_text": text, "extracted_values": extracted, "missing_values": missing}

    def predict_from_image(self, *, test_type: str, image_path: Path) -> dict[str, Any]:
        extracted_bundle = self.extract_from_image(test_type=test_type, image_path=image_path)
        if extracted_bundle["missing_values"]:
            return {**extracted_bundle, "prediction": None}
        try:
            prediction = predict(test_type, extracted_bundle["extracted_values"])
            prediction["recommendations"] = RecommendationService().generate(
                test_type=test_type,
                risk_score=prediction["risk_score"],
                label=prediction["label"],
                input_data=extracted_bundle["extracted_values"],
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        return {**extracted_bundle, "missing_values": [], "prediction": prediction}
