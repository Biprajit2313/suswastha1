from typing import Any


class RecommendationService:
    def _risk_tier(self, *, risk_score: float, label: str) -> str:
        normalized = (label or "").strip().lower()
        if risk_score >= 70 or "high" in normalized or normalized in {"hypertension", "obese"}:
            return "high"
        if risk_score >= 40 or normalized in {"prehypertension", "overweight"}:
            return "medium"
        return "low"

    def generate(self, *, test_type: str, risk_score: float, label: str, input_data: dict[str, Any]) -> dict[str, list[str]]:
        tier = self._risk_tier(risk_score=risk_score, label=label)
        suggestions: dict[str, list[str]] = {
            "exercise": [],
            "diet": [],
            "lifestyle": [],
        }

        if test_type == "diabetes":
            suggestions["exercise"].append("Walk briskly for 30 minutes at least 5 days per week.")
            suggestions["diet"].append("Prefer high-fiber meals and reduce added sugar and refined carbohydrates.")
            suggestions["lifestyle"].append("Track fasting glucose and body weight consistently.")
        elif test_type == "heart":
            suggestions["exercise"].append("Choose moderate cardio such as walking, cycling, or swimming after clinician clearance.")
            suggestions["diet"].append("Reduce saturated fat, fried foods, and excess salt.")
            suggestions["lifestyle"].append("Prioritize sleep, blood pressure monitoring, and stress management.")
        elif test_type == "blood_pressure":
            suggestions["exercise"].append("Do low-impact aerobic activity for 150 minutes weekly.")
            suggestions["diet"].append("Follow a DASH-style pattern with lower sodium and more potassium-rich foods.")
            suggestions["lifestyle"].append("Measure blood pressure at the same time daily and limit alcohol/tobacco.")
        elif test_type == "bmi":
            suggestions["exercise"].append("Combine daily walking with 2-3 weekly strength sessions.")
            suggestions["diet"].append("Use portion control and prioritize protein, vegetables, and whole grains.")
            suggestions["lifestyle"].append("Track waist, weight, and energy levels weekly instead of daily swings.")
        elif test_type == "cholesterol":
            suggestions["exercise"].append("Add regular aerobic exercise and resistance training twice weekly.")
            suggestions["diet"].append("Increase soluble fiber and reduce trans fats, processed foods, and excess sugar.")
            suggestions["lifestyle"].append("Recheck lipid profile as advised and avoid smoking.")
        elif test_type == "liver":
            suggestions["exercise"].append("Maintain gentle regular activity to support metabolic health.")
            suggestions["diet"].append("Avoid alcohol and reduce fatty, highly processed foods.")
            suggestions["lifestyle"].append("Discuss abnormal bilirubin/enzyme markers with a clinician.")
        elif test_type == "kidney":
            suggestions["exercise"].append("Use light-to-moderate exercise while avoiding dehydration.")
            suggestions["diet"].append("Limit excess salt and discuss protein/potassium targets with a clinician.")
            suggestions["lifestyle"].append("Monitor blood pressure, glucose, creatinine, and urine findings.")
        elif test_type == "thyroid":
            suggestions["exercise"].append("Use steady low-to-moderate activity adjusted to fatigue and heart rate.")
            suggestions["diet"].append("Maintain balanced iodine intake and avoid unsupervised thyroid supplements.")
            suggestions["lifestyle"].append("Repeat thyroid labs and medication review with a clinician if symptoms persist.")

        if tier == "high":
            suggestions["lifestyle"].append("Book a clinician review; this screening result is not a diagnosis.")
        elif tier == "medium":
            suggestions["lifestyle"].append("Consider a clinician review if symptoms exist and repeat screening sooner.")
        else:
            suggestions["lifestyle"].append("Keep healthy routines and repeat screening periodically.")
        return suggestions
