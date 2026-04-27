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
        
        # Header Background (Gradient-like split or solid teal)
        document.setFillColorRGB(0, 0.658, 0.658) # #00A8A8 (Teal)
        document.rect(0, height - 120, width, 120, fill=True, stroke=False)
        
        # Draw Simplified Logo in Header
        logo_x = width - 100
        logo_y = height - 60
        logo_scale = 0.15
        
        # Circle
        document.setStrokeColorRGB(1, 1, 1) # White
        document.setLineWidth(2)
        document.circle(logo_x, logo_y, 30, fill=False, stroke=True)
        
        # H letter
        document.setFillColorRGB(1, 1, 1) # White
        document.rect(logo_x - 12, logo_y - 15, 6, 30, fill=True, stroke=False) # Left pillar
        document.rect(logo_x + 6, logo_y - 15, 6, 30, fill=True, stroke=False)  # Right pillar
        document.rect(logo_x - 12, logo_y - 3, 24, 6, fill=True, stroke=False)  # Middle bar
        
        # Heartbeat
        document.setStrokeColorRGB(1, 1, 1)
        document.setLineWidth(1.5)
        path_points = [
            (logo_x - 15, logo_y - 5),
            (logo_x - 10, logo_y - 5),
            (logo_x - 5, logo_y + 10),
            (logo_x, logo_y - 15),
            (logo_x + 5, logo_y + 5),
            (logo_x + 10, logo_y - 5),
            (logo_x + 15, logo_y - 5)
        ]
        document.polyline(path_points)
        
        # Header Text
        document.setFillColorRGB(1, 1, 1) # White
        document.setFont("Helvetica-Bold", 26)
        document.drawString(50, height - 65, "SuSwastha")
        
        document.setFont("Helvetica", 14)
        document.drawString(50, height - 90, f"{test_type.replace('_', ' ').title()} Screening Report")
        
        y = height - 150
        document.setFillColorRGB(0, 0, 0) # Black
        document.setFont("Helvetica", 12)
        document.drawString(50, y, f"User: {user_email}")
        
        y -= 20
        # Format date as DD/MM/YYYY, HH:MM AM/PM
        now = datetime.now(timezone.utc)
        formatted_date = now.strftime("%d/%m/%Y, %I:%M %p")
        document.drawString(50, y, f"Generated: {formatted_date}")
        
        y -= 40
        document.setFont("Helvetica-Bold", 16)
        document.setFillColorRGB(0.039, 0.4, 0.76) # #0A66C2 (Blue)
        document.drawString(50, y, "Prediction Summary")
        
        y -= 25
        document.setFont("Helvetica", 12)
        document.setFillColorRGB(0, 0, 0) # Black
        document.drawString(50, y, f"Condition: {label}")
        y -= 20
        document.drawString(50, y, f"Risk Score: {risk_score:.1f}%")
        
        y -= 40
        document.setFont("Helvetica-Bold", 16)
        document.setFillColorRGB(0.039, 0.4, 0.76) # #0A66C2 (Blue)
        document.drawString(50, y, "Submitted Health Data")
        y -= 25
        document.setFont("Helvetica", 11)
        document.setFillColorRGB(0, 0, 0) # Black
        
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
            document.setFont("Helvetica-Bold", 16)
            document.setFillColorRGB(0.039, 0.4, 0.76) # #0A66C2 (Blue)
            document.drawString(50, y, "Personalized Recommendations")
            y -= 25
            document.setFont("Helvetica", 11)
            document.setFillColorRGB(0, 0, 0) # Black
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
        
        # Footer
        if y < 60:
            document.showPage()
            y = height - 50
            
        document.setFont("Helvetica-Oblique", 9)
        document.setFillColorRGB(0.5, 0.5, 0.5) # Grey
        document.drawString(50, 30, "DIAGNOSTICS. INSIGHTS. BETTER HEALTH")
        document.drawRightString(width - 50, 30, "SuSwastha - Powered by AI")
        
        document.setFont("Helvetica", 10)
        document.setFillColorRGB(0, 0, 0) # Black
        document.drawString(
            50,
            y - 20 if y > 60 else 60,
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
