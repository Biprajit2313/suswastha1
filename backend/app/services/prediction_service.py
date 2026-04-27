from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import joblib
import numpy as np
import pandas as pd
from fastapi import BackgroundTasks, HTTPException, status
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import session_scope
from app.models.user import User
from app.repositories.prediction_repo import PredictionRepository
from app.schemas.prediction import (
    BMIInput,
    BloodPressureInput,
    CholesterolInput,
    DiabetesInput,
    DiseaseType,
    HeartInput,
    KidneyInput,
    LiverInput,
    PredictionResponse,
    ThyroidInput,
)
from app.services.email_service import EmailService
from app.services.recommendation_service import RecommendationService
from app.services.report_service import ReportService

logger = get_logger(__name__)

SCHEMA_BY_TEST: dict[str, type[BaseModel]] = {
    "diabetes": DiabetesInput,
    "heart": HeartInput,
    "blood_pressure": BloodPressureInput,
    "bmi": BMIInput,
    "cholesterol": CholesterolInput,
    "liver": LiverInput,
    "kidney": KidneyInput,
    "thyroid": ThyroidInput,
}

MODEL_FEATURES: dict[str, list[str]] = {
    "diabetes": ["glucose", "blood_pressure", "skin_thickness", "insulin", "bmi", "pedigree", "age"],
    "heart": [
        "age",
        "sex",
        "cp",
        "trestbps",
        "chol",
        "fbs",
        "restecg",
        "thalach",
        "exang",
        "oldpeak",
        "slope",
        "ca",
        "thal",
    ],
    "blood_pressure": ["systolic", "diastolic", "age", "weight", "height", "stress_level", "activity_level"],
    "bmi": ["weight", "height"],
    "cholesterol": [
        "total_cholesterol",
        "hdl",
        "ldl",
        "triglycerides",
        "age",
        "bmi",
        "blood_pressure",
        "smoking_status",
        "family_history",
    ],
    "liver": [
        "age",
        "gender",
        "total_bilirubin",
        "direct_bilirubin",
        "alkaline_phosphatase",
        "alt",
        "ast",
        "total_proteins",
        "albumin",
        "ag_ratio",
    ],
    "kidney": [
        "age",
        "blood_pressure",
        "specific_gravity",
        "albumin",
        "sugar",
        "blood_glucose_random",
        "blood_urea",
        "serum_creatinine",
        "sodium",
        "potassium",
        "hemoglobin",
        "packed_cell_volume",
        "white_blood_cell_count",
        "red_blood_cell_count",
    ],
    "thyroid": [
        "age",
        "sex",
        "tsh",
        "t3",
        "t4",
        "free_t4_index",
        "free_t3_index",
        "medication_status",
        "pregnancy_status",
        "goitre_status",
    ],
}

BINARY_LABELS: dict[str, tuple[str, str]] = {
    "diabetes": ("Low Risk", "High Risk"),
    "heart": ("Low Risk", "High Risk"),
    "cholesterol": ("Normal", "High Risk"),
    "liver": ("Low Risk", "High Risk"),
    "kidney": ("Low Risk", "High Risk"),
}

MULTICLASS_LABELS: dict[str, dict[Any, str]] = {
    "blood_pressure": {
        0: "Normal",
        1: "Prehypertension",
        2: "Hypertension",
        "normal": "Normal",
        "prehypertension": "Prehypertension",
        "hypertension": "Hypertension",
    },
    "thyroid": {
        0: "Normal",
        1: "Hypothyroid",
        2: "Hyperthyroid",
        "normal": "Normal",
        "hypothyroid": "Hypothyroid",
        "hyperthyroid": "Hyperthyroid",
    },
}


def validate_prediction_payload(test_type: str, input_data: Mapping[str, Any]) -> dict[str, Any]:
    schema = SCHEMA_BY_TEST.get(test_type)
    if schema is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unsupported test type: {test_type}")
    try:
        validated = schema.model_validate(dict(input_data))
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc
    return validated.model_dump(exclude_none=True)


@lru_cache(maxsize=32)
def load_model_package(test_type: str) -> dict[str, Any]:
    model_path = get_settings().normalized_ml_models_dir / f"{test_type}.joblib"
    if not model_path.exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"ML model artifact is not deployed for '{test_type}'",
        )

    artifact = joblib.load(model_path)
    if isinstance(artifact, dict) and ("model" in artifact or artifact.get("type") == "bmi_rule"):
        package = artifact
    else:
        package = {
            "model": artifact,
            "features": MODEL_FEATURES[test_type],
            "task": "binary",
            "metrics": {},
            "feature_importance": {},
        }

    package.setdefault("features", MODEL_FEATURES[test_type])
    package.setdefault("task", "binary")
    package.setdefault("metrics", {})
    package.setdefault("feature_importance", {})
    logger.info("ml_model_loaded", extra={"test_type": test_type, "path": str(model_path)})
    return package


def _as_feature_frame(test_type: str, input_data: dict[str, Any], features: list[str]) -> pd.DataFrame:
    missing = [feature for feature in features if feature not in input_data]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Missing required feature(s): {', '.join(missing)}",
        )
    return pd.DataFrame([{feature: input_data[feature] for feature in features}], columns=features)


def _class_probability(model: Any, features: pd.DataFrame) -> tuple[Any, float, dict[Any, float]]:
    prediction = model.predict(features)[0]
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(features)[0]
        classes = list(getattr(model, "classes_", range(len(probabilities))))
        probability_map = {classes[index]: float(probabilities[index]) for index in range(len(probabilities))}
        return prediction, float(max(probabilities)), probability_map

    if hasattr(model, "decision_function"):
        scores = np.atleast_1d(model.decision_function(features))[0]
        if np.ndim(scores) == 0:
            probability = float(1.0 / (1.0 + np.exp(-scores)))
            return prediction, max(probability, 1.0 - probability), {prediction: probability}
    return prediction, 1.0, {prediction: 1.0}


def _binary_result(test_type: str, prediction: Any, confidence: float, probabilities: dict[Any, float]) -> dict[str, Any]:
    negative_label, positive_label = BINARY_LABELS.get(test_type, ("Low Risk", "High Risk"))
    positive_probability = probabilities.get(1)
    if positive_probability is None:
        positive_probability = probabilities.get("1")
    if positive_probability is None:
        positive_probability = confidence if int(prediction) == 1 else 1.0 - confidence
    label = positive_label if float(positive_probability) >= 0.5 else negative_label
    return {
        "label": label,
        "risk_score": round(float(positive_probability) * 100.0, 2),
        "confidence": round(float(confidence), 4),
    }


def _multiclass_result(test_type: str, prediction: Any, confidence: float, probabilities: dict[Any, float]) -> dict[str, Any]:
    labels = MULTICLASS_LABELS.get(test_type, {})
    label = labels.get(prediction, labels.get(str(prediction).lower(), str(prediction)))
    ordinal_risk = {"Normal": 0.1, "Prehypertension": 0.55, "Hypertension": 0.95, "Hypothyroid": 0.75, "Hyperthyroid": 0.75}
    risk_score = ordinal_risk.get(label, confidence) * 100.0
    return {
        "label": label,
        "risk_score": round(float(risk_score), 2),
        "confidence": round(float(confidence), 4),
    }


def _bmi_result(input_data: dict[str, Any]) -> dict[str, Any]:
    height_m = float(input_data["height"])
    if height_m > 3:
        height_m = height_m / 100.0
    if height_m <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Height must be positive")

    bmi = float(input_data["weight"]) / (height_m**2)
    if bmi < 18.5:
        label = "Underweight"
    elif bmi < 25:
        label = "Normal"
    elif bmi < 30:
        label = "Overweight"
    else:
        label = "Obese"

    distance_to_normal = 0.0 if 18.5 <= bmi < 25 else min(abs(bmi - 21.75) / 21.75, 1.0)
    confidence = min(0.99, 0.65 + distance_to_normal * 0.34)
    return {
        "label": label,
        "risk_score": round(distance_to_normal * 100.0, 2),
        "confidence": round(confidence, 4),
        "bmi": round(bmi, 2),
    }


def predict_with_extras(test_type: str, input_data: dict[str, Any]) -> dict[str, Any]:
    test_type = test_type.lower()
    validated = validate_prediction_payload(test_type, input_data)
    validated.pop("email", None)

    if test_type == "bmi":
        return _bmi_result(validated)

    package = load_model_package(test_type)
    features = list(package["features"])
    frame = _as_feature_frame(test_type, validated, features)
    prediction, confidence, probabilities = _class_probability(package["model"], frame)

    if package.get("task") == "multiclass" or test_type in MULTICLASS_LABELS:
        return _multiclass_result(test_type, prediction, confidence, probabilities)
    return _binary_result(test_type, prediction, confidence, probabilities)


def predict(test_type: str, input_data: dict) -> dict:
    """
    Standard prediction contract used across the backend.

    Returns exactly:
      { "label": str, "risk_score": float, "confidence": float }
    """
    result = predict_with_extras(str(test_type), dict(input_data))
    return {
        "label": result["label"],
        "risk_score": float(result["risk_score"]),
        "confidence": float(result["confidence"]),
    }


def get_model_metrics(test_type: str) -> dict[str, Any]:
    if test_type == "bmi":
        return {"task": "rule_regression_hybrid", "metrics": {"source": "WHO BMI thresholds"}}
    package = load_model_package(test_type)
    return {
        "test_type": test_type,
        "task": package.get("task"),
        "features": package.get("features", []),
        "metrics": package.get("metrics", {}),
    }


def get_feature_importance(test_type: str) -> dict[str, Any]:
    if test_type == "bmi":
        return {"test_type": "bmi", "feature_importance": {"weight": 0.5, "height": 0.5}}
    package = load_model_package(test_type)
    return {"test_type": test_type, "feature_importance": package.get("feature_importance", {})}


def process_prediction_report(prediction_id: int) -> None:
    try:
        with session_scope() as db:
            repo = PredictionRepository(db)
            prediction_row = repo.get_prediction_by_id(prediction_id)
            if prediction_row is None:
                logger.warning("prediction_missing_for_report", extra={"prediction_id": prediction_id})
                return
            pdf_url = ReportService().generate_and_upload(prediction_row)
            repo.update_report_url(prediction_id, pdf_url)
            try:
                EmailService().send_report_email(
                    to_email=prediction_row.user_email,
                    test_type=prediction_row.test_type,
                    pdf_url=pdf_url,
                )
            except Exception:
                logger.exception("report_email_failed", extra={"prediction_id": prediction_id})
    except Exception:
        logger.exception("report_background_task_failed", extra={"prediction_id": prediction_id})


class PredictionService:
    def predict(
        self,
        *,
        test_type: DiseaseType,
        payload: dict[str, Any],
        current_user: User,
        db: Session,
        background_tasks: BackgroundTasks,
    ) -> PredictionResponse:
        data = validate_prediction_payload(test_type.value, payload)
        supplied_email = data.pop("email", None)
        if supplied_email and str(supplied_email).lower() != current_user.email.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payload email does not match authenticated user",
            )

        # Use extended result internally (e.g. includes computed BMI)
        result = predict_with_extras(test_type.value, data)
        recommendations = RecommendationService().generate(
            test_type=test_type.value,
            risk_score=result["risk_score"],
            label=result["label"],
            input_data=data,
        )
        raw_input = data | {"confidence": result["confidence"]}
        if "bmi" in result:
            raw_input["computed_bmi"] = result["bmi"]

        prediction_row = PredictionRepository(db).save_prediction(
            user_email=current_user.email,
            test_type=test_type.value,
            raw_input=raw_input,
            label=result["label"],
            risk_score=result["risk_score"],
            recommendations=recommendations,
        )
        background_tasks.add_task(process_prediction_report, prediction_row.id)

        return PredictionResponse(
            id=prediction_row.id,
            test_type=test_type,
            label=prediction_row.label,
            risk_score=prediction_row.risk_score,
            confidence=result["confidence"],
            recommendations=recommendations,
            pdf_url=prediction_row.pdf_url,
            report_status="processing",
            created_at=prediction_row.created_at,
        )
