import re
from typing import Any

from app.services.prediction_service import MODEL_FEATURES, load_model_package


ALIASES: dict[str, list[str]] = {
    "blood_pressure": ["bp", "blood pressure", "resting bp"],
    "skin_thickness": ["skin thickness", "skinthickness"],
    "pedigree": ["pedigree", "diabetes pedigree", "diabetes pedigree function"],
    "trestbps": ["resting bp", "resting blood pressure", "trestbps"],
    "chol": ["cholesterol", "chol"],
    "thalach": ["max heart rate", "maximum heart rate", "thalach"],
    "total_cholesterol": ["total cholesterol", "cholesterol total"],
    "specific_gravity": ["specific gravity", "sg"],
    "blood_glucose_random": ["blood glucose random", "bgr"],
    "blood_urea": ["blood urea", "bu"],
    "serum_creatinine": ["serum creatinine", "creatinine", "sc"],
    "packed_cell_volume": ["packed cell volume", "pcv"],
    "white_blood_cell_count": ["white blood cell count", "wbc", "wc"],
    "red_blood_cell_count": ["red blood cell count", "rbc", "rc"],
    "total_bilirubin": ["total bilirubin", "tb"],
    "direct_bilirubin": ["direct bilirubin", "db"],
    "alkaline_phosphatase": ["alkaline phosphatase", "alkphos"],
    "alt": ["alt", "sgpt"],
    "ast": ["ast", "sgot"],
    "ag_ratio": ["a/g ratio", "ag ratio", "albumin globulin ratio"],
    "free_t4_index": ["free t4 index", "fti"],
    "free_t3_index": ["free t3 index"],
}


class ParserService:
    def extract_values(self, *, test_type: str, text: str) -> dict[str, Any]:
        normalized = text.lower().replace("_", " ")
        values: dict[str, Any] = {}
        for feature in self._features(test_type):
            candidates = [feature.replace("_", " ")] + ALIASES.get(feature, [])
            found = self._find_numeric_value(normalized, candidates)
            if found is not None:
                values[feature] = found
        return values

    def missing_values(self, *, test_type: str, values: dict[str, Any]) -> list[str]:
        return [feature for feature in self._features(test_type) if feature not in values]

    def _features(self, test_type: str) -> list[str]:
        if test_type == "bmi":
            return ["weight", "height"]
        try:
            return list(load_model_package(test_type)["features"])
        except Exception:
            return MODEL_FEATURES[test_type]

    def _find_numeric_value(self, text: str, labels: list[str]) -> float | None:
        for label in labels:
            pattern = rf"{re.escape(label.lower())}\s*[:=\-]?\s*(-?\d+(?:\.\d+)?)"
            match = re.search(pattern, text)
            if match:
                return float(match.group(1))
        return None
