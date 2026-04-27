import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.core.logging import get_logger
from app.models.prediction import Prediction
from app.services.encryption_service import EncryptionService
from app.services.storage_service import StorageService

logger = get_logger(__name__)


class ReportService:
    def __init__(self, storage_service: StorageService | None = None) -> None:
        self.storage_service = storage_service or StorageService()

    def generate_pdf(
        self,
        *,
        user_email: str,
        test_type: str,
        inputs: dict[str, Any],
        label: str,
        risk_score: float,
        recommendations: dict[str, list[str]] | None = None,
    ) -> Path:
        fd, tmp_name = tempfile.mkstemp(prefix=f"suswastha_{test_type}_", suffix=".pdf")
        os.close(fd)
        path = Path(tmp_name)

        document = canvas.Canvas(str(path), pagesize=A4)
        width, height = A4
        y = height - 50

        document.setFont("Helvetica-Bold", 18)
        document.drawString(50, y, f"SuSwastha {test_type.replace('_', ' ').title()} Report")

        y -= 40
        document.setFont("Helvetica", 12)
        document.drawString(50, y, f"User: {user_email}")
        y -= 20
        document.drawString(50, y, f"Generated: {datetime.now(timezone.utc).isoformat()}")

        y -= 40
        document.setFont("Helvetica-Bold", 14)
        document.drawString(50, y, "Prediction Summary")

        y -= 22
        document.setFont("Helvetica", 12)
        document.drawString(50, y, f"Label: {label}")
        y -= 20
        document.drawString(50, y, f"Risk Score: {risk_score:.1f}%")

        y -= 40
        document.setFont("Helvetica-Bold", 14)
        document.drawString(50, y, "Submitted Health Data")
        y -= 22
        document.setFont("Helvetica", 11)

        for key, value in inputs.items():
            if key == "email":
                continue
            if y < 80:
                document.showPage()
                y = height - 50
                document.setFont("Helvetica", 11)
            document.drawString(60, y, f"- {key.replace('_', ' ').title()}: {value}")
            y -= 18

        if recommendations:
            if y < 140:
                document.showPage()
                y = height - 50
            document.setFont("Helvetica-Bold", 14)
            document.drawString(50, y, "Personalized Recommendations")
            y -= 22
            document.setFont("Helvetica", 11)
            for category, items in recommendations.items():
                if y < 80:
                    document.showPage()
                    y = height - 50
                document.setFont("Helvetica-Bold", 11)
                document.drawString(60, y, category.title())
                y -= 16
                document.setFont("Helvetica", 10)
                for item in items:
                    if y < 80:
                        document.showPage()
                        y = height - 50
                    document.drawString(75, y, f"- {item[:95]}")
                    y -= 15

        if y < 100:
            document.showPage()
            y = height - 50

        document.setFont("Helvetica", 10)
        document.drawString(
            50,
            y,
            "Educational risk estimate only. Not a diagnosis. Please consult a clinician.",
        )
        document.showPage()
        document.save()
        return path

    def generate_and_upload(self, prediction: Prediction) -> str:
        crypto = EncryptionService()
        try:
            inputs = crypto.decrypt_json(prediction.raw_input)
        except (json.JSONDecodeError, ValueError):
            inputs = json.loads(prediction.raw_input)
        recommendations = {}
        if prediction.recommendations:
            try:
                recommendations = crypto.decrypt_json(prediction.recommendations)
            except (json.JSONDecodeError, ValueError):
                recommendations = json.loads(prediction.recommendations)
        pdf_path = self.generate_pdf(
            user_email=prediction.user_email,
            test_type=prediction.test_type,
            inputs=inputs,
            label=prediction.label,
            risk_score=prediction.risk_score,
            recommendations=recommendations,
        )
        # StorageService is responsible for deleting the local file after upload.
        return self.storage_service.upload_file(pdf_path)
