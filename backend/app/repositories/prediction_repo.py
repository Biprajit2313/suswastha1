import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.prediction import Prediction
from app.services.encryption_service import EncryptionService


class PredictionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.crypto = EncryptionService()

    def save_prediction(
        self,
        *,
        user_email: str,
        test_type: str,
        raw_input: dict[str, Any],
        label: str,
        risk_score: float,
        recommendations: dict[str, Any] | None = None,
    ) -> Prediction:
        prediction = Prediction(
            user_email=user_email,
            test_type=test_type,
            raw_input=self.crypto.encrypt_json(raw_input),
            label=label,
            risk_score=risk_score,
            recommendations=self.crypto.encrypt_json(recommendations or {}),
        )
        self.db.add(prediction)
        self.db.commit()
        self.db.refresh(prediction)
        return prediction

    def decoded_input(self, prediction: Prediction) -> dict[str, Any]:
        try:
            return self.crypto.decrypt_json(prediction.raw_input)
        except (json.JSONDecodeError, ValueError):
            return json.loads(prediction.raw_input)

    def decoded_recommendations(self, prediction: Prediction) -> dict[str, Any]:
        if not prediction.recommendations:
            return {}
        try:
            return self.crypto.decrypt_json(prediction.recommendations)
        except (json.JSONDecodeError, ValueError):
            return json.loads(prediction.recommendations)

    def get_prediction_by_id(self, prediction_id: int) -> Prediction | None:
        return self.db.query(Prediction).filter(Prediction.id == prediction_id).first()

    def update_report_url(self, prediction_id: int, pdf_url: str) -> Prediction | None:
        prediction = self.get_prediction_by_id(prediction_id)
        if prediction is None:
            return None
        prediction.pdf_url = pdf_url
        self.db.add(prediction)
        self.db.commit()
        self.db.refresh(prediction)
        return prediction

    def get_user_reports(self, user_email: str, limit: int = 20) -> list[Prediction]:
        return (
            self.db.query(Prediction)
            .filter(Prediction.user_email == user_email)
            .order_by(Prediction.created_at.desc())
            .limit(limit)
            .all()
        )
