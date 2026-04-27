# SuSwastha Training Datasets

Place real CSV datasets in this directory before running `train_pipeline.py`.

Expected filenames:

- `diabetes.csv` - Pima Indians Diabetes style data.
- `heart.csv` - UCI Heart style data.
- `blood_pressure.csv` - Systolic/diastolic records; target can be omitted and derived from BP stage.
- `cholesterol.csv` - Lipid panel records; target can be omitted and derived from clinical lipid thresholds.
- `liver.csv` - ILPD style data.
- `kidney.csv` - CKD style data.
- `thyroid.csv` - Thyroid status data.

Canonical prediction features:

- Diabetes: `glucose`, `blood_pressure`, `skin_thickness`, `insulin`, `bmi`, `pedigree`, `age`
- Heart: `age`, `sex`, `cp`, `trestbps`, `chol`, `fbs`, `restecg`, `thalach`, `exang`, `oldpeak`, `slope`, `ca`, `thal`
- Blood pressure: `systolic`, `diastolic`, `age`, `weight`, `height`, `stress_level`, `activity_level`
- BMI: `weight`, `height`
- Cholesterol: `total_cholesterol`, `hdl`, `ldl`, `triglycerides`, `age`, `bmi`, `blood_pressure`, `smoking_status`, `family_history`
- Liver: `age`, `gender`, `total_bilirubin`, `direct_bilirubin`, `alkaline_phosphatase`, `alt`, `ast`, `total_proteins`, `albumin`, `ag_ratio`
- Kidney: `age`, `blood_pressure`, `specific_gravity`, `albumin`, `sugar`, `blood_glucose_random`, `blood_urea`, `serum_creatinine`, `sodium`, `potassium`, `hemoglobin`, `packed_cell_volume`, `white_blood_cell_count`, `red_blood_cell_count`
- Thyroid: `age`, `sex`, `tsh`, `t3`, `t4`, `free_t4_index`, `free_t3_index`, `medication_status`, `pregnancy_status`, `goitre_status`

Train all models:

```powershell
cd C:\Users\itsbi\Downloads\SuSwastha-main
python backend\models\train_pipeline.py --data-dir backend\models\data --output-dir backend\models
```
