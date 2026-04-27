from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr


class DiseaseType(str, Enum):
    diabetes = "diabetes"
    heart = "heart"
    blood_pressure = "blood_pressure"
    bmi = "bmi"
    cholesterol = "cholesterol"
    liver = "liver"
    kidney = "kidney"
    thyroid = "thyroid"


class PredictionBase(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: EmailStr | None = None


class DiabetesInput(PredictionBase):
    glucose: float
    blood_pressure: float
    skin_thickness: float
    bmi: float
    age: float
    insulin: float
    pedigree: float


class CholesterolInput(PredictionBase):
    total_cholesterol: float
    hdl: float
    ldl: float
    triglycerides: float
    age: float
    bmi: float
    blood_pressure: float
    smoking_status: int
    family_history: int


class KidneyInput(PredictionBase):
    age: float
    blood_pressure: float
    specific_gravity: float
    albumin: float
    sugar: float
    blood_glucose_random: float
    blood_urea: float
    serum_creatinine: float
    sodium: float
    potassium: float
    hemoglobin: float
    packed_cell_volume: float
    white_blood_cell_count: float
    red_blood_cell_count: float


class LiverInput(PredictionBase):
    age: float
    gender: int
    total_bilirubin: float
    direct_bilirubin: float
    alkaline_phosphatase: float
    alt: float
    ast: float
    total_proteins: float
    albumin: float
    ag_ratio: float


class HeartInput(PredictionBase):
    age: float
    sex: int
    cp: int
    trestbps: float
    chol: float
    fbs: int
    restecg: int
    thalach: float
    exang: int
    oldpeak: float
    slope: int
    ca: float
    thal: int


class BloodPressureInput(PredictionBase):
    systolic: float
    diastolic: float
    age: float
    weight: float
    height: float
    stress_level: int
    activity_level: int


class BMIInput(PredictionBase):
    weight: float
    height: float
    age: float | None = None
    sex: int | None = None
    waist_circumference: float | None = None
    body_fat_percentage: float | None = None


class ThyroidInput(PredictionBase):
    age: float
    sex: int
    tsh: float
    t3: float
    t4: float
    free_t4_index: float
    free_t3_index: float
    medication_status: int
    pregnancy_status: int
    goitre_status: int


class PredictionResponse(BaseModel):
    id: int
    test_type: DiseaseType
    label: str
    risk_score: float
    confidence: float
    recommendations: dict[str, list[str]]
    pdf_url: str | None = None
    report_status: str
    created_at: datetime


class UserReportOut(BaseModel):
    id: int
    test_type: str
    label: str
    risk_score: float
    created_at: datetime
    pdf_url: str | None = None

    class Config:
        from_attributes = True
