import joblib
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier


MODELS_DIR = Path("models")
MODELS_DIR.mkdir(exist_ok=True)


# ----------------- Helper: safe column picker -----------------


def pick_col(df: pd.DataFrame, logical_name: str, candidates: list[str]) -> str:
    """
    Try to find a column in df whose name matches one of the candidates
    (case-insensitive, ignoring spaces and underscores).
    Raise KeyError if none match.
    """
    normalized = {c.lower().replace(" ", "").replace("_", ""): c for c in df.columns}
    for cand in candidates:
        key = cand.lower().replace(" ", "").replace("_", "")
        if key in normalized:
            return normalized[key]
    raise KeyError(
        f"Could not find a column for '{logical_name}'. Tried {candidates}.\n"
        f"Available columns: {list(df.columns)}"
    )


def clean_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """
    Replace '?' with NaN, convert given cols to numeric, drop rows with NaN.
    """
    df = df.copy()
    df.replace("?", pd.NA, inplace=True)
    for col in cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=cols)
    return df


# ----------------- Core training helper -----------------


def train_best_model(X, y, model_name: str):
    pipe_lr = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000)),
        ]
    )
    pipe_rf = Pipeline(
        [
            ("clf", RandomForestClassifier()),
        ]
    )

    grids = [
        (pipe_lr, {"clf__C": [0.1, 1, 10]}),
        (pipe_rf, {"clf__n_estimators": [100, 200], "clf__max_depth": [None, 5, 10]}),
    ]

    best_auc = -1
    best_model = None

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    for pipe, params in grids:
        try:
            gs = GridSearchCV(pipe, params, cv=5, scoring="roc_auc", n_jobs=-1)
            gs.fit(X_train, y_train)
            preds = gs.predict_proba(X_val)[:, 1]
            auc = roc_auc_score(y_val, preds)
            print(f"{model_name} candidate {pipe.steps[-1][0]} AUC = {auc:.3f}")
            if auc > best_auc:
                best_auc = auc
                best_model = gs.best_estimator_
        except Exception as e:
            print(f"[WARN] GridSearch failed for {model_name} with {pipe}: {e}")

    if best_model is None:
        print(f"[ERROR] Could not train any model for {model_name}. Skipping save.")
        return

    path = MODELS_DIR / f"{model_name}.joblib"
    joblib.dump(best_model, path)
    print(f"[OK] Saved best {model_name} model at {path} (AUC={best_auc:.3f})")


# ----------------- Diabetes -----------------


def train_diabetes():
    """
    Uses diabetes.csv (Pima-style).
    Columns (typical): Glucose, BloodPressure, SkinThickness, Insulin,
                       BMI, DiabetesPedigreeFunction, Age, Outcome
    """
    try:
        df = pd.read_csv("data/diabetes.csv")
    except FileNotFoundError:
        print("[SKIP] diabetes: data/diabetes.csv not found")
        return

    feature_cols = [
        "Glucose",
        "BloodPressure",
        "SkinThickness",
        "Insulin",
        "BMI",
        "DiabetesPedigreeFunction",
        "Age",
    ]

    missing = [c for c in feature_cols + ["Outcome"] if c not in df.columns]
    if missing:
        print(f"[SKIP] diabetes: missing columns {missing}")
        return

    df = clean_numeric(df, feature_cols)

    X = df[feature_cols]
    y = df["Outcome"]  # 0/1
    train_best_model(X, y, "diabetes")


# ----------------- Cholesterol (best-effort / may SKIP) -----------------


def train_cholesterol():
    """
    Best-effort cholesterol model.

    It will look for a CSV under data/ named:
      - dataset_2190_cholesterol.csv
      - OR heart.csv (using 'chol' as total_cholesterol)

    If appropriate columns are not found, it will SKIP gracefully.
    """
    import os

    path1 = Path("data/dataset_2190_cholesterol.csv")
    path2 = Path("data/heart.csv")

    if path1.exists():
        df = pd.read_csv(path1)
        print("[INFO] Using dataset_2190_cholesterol.csv for cholesterol model")
    elif path2.exists():
        df = pd.read_csv(path2)
        print("[INFO] Using heart.csv for cholesterol model (chol column only)")
    else:
        print("[SKIP] cholesterol: no suitable CSV found")
        return

    # Try to pick columns smartly
    try:
        total_chol_col = pick_col(
            df,
            "total_cholesterol",
            ["TotalCholesterol", "Total Cholesterol", "chol", "Cholesterol"],
        )
        hdl_col = pick_col(df, "hdl", ["HDL", "hdl"])
        ldl_col = pick_col(df, "ldl", ["LDL", "ldl"])
        trig_col = pick_col(
            df,
            "triglycerides",
            ["Triglycerides", "triglycerides", "Trig", "Triglyceride"],
        )
        age_col = pick_col(df, "age", ["Age", "age"])
    except KeyError as e:
        print(f"[SKIP] cholesterol: {e}")
        return

    # Some CSVs may not have BMI, BloodPressure, etc. We will fill with zeros if missing.
    bmi_col = None
    bp_col = None
    smoke_col = None
    family_col = None

    try:
        bmi_col = pick_col(df, "bmi", ["BMI", "bmi", "BodyMassIndex"])
    except KeyError:
        print("[WARN] cholesterol: BMI column not found, will use zeros")
    try:
        bp_col = pick_col(df, "blood_pressure", ["BloodPressure", "BP", "blood_pressure"])
    except KeyError:
        print("[WARN] cholesterol: BloodPressure column not found, will use zeros")
    try:
        smoke_col = pick_col(
            df,
            "smoking_status",
            ["SmokingStatus", "smoking_status", "Smoker"],
        )
    except KeyError:
        print("[WARN] cholesterol: SmokingStatus column not found, will use zeros")
    try:
        family_col = pick_col(
            df,
            "family_history",
            ["FamilyHistory", "family_history", "FH"],
        )
    except KeyError:
        print("[WARN] cholesterol: FamilyHistory column not found, will use zeros")

    # Target column
    if "Outcome" in df.columns:
        target_col = "Outcome"
    elif "target" in df.columns:
        target_col = "target"
    elif "num" in df.columns:
        # UCI heart dataset: num > 0 = disease
        df["chol_label"] = (df["num"] > 0).astype(int)
        target_col = "chol_label"
    else:
        print("[SKIP] cholesterol: no binary outcome column found")
        return

    # Build numeric feature df
    cols_to_clean = [total_chol_col, hdl_col, ldl_col, trig_col, age_col]
    optional_cols = [bmi_col, bp_col, smoke_col, family_col]
    cols_to_clean.extend([c for c in optional_cols if c is not None])

    df = clean_numeric(df, cols_to_clean + [target_col])

    def get_or_zero(col):
        return df[col] if col is not None else 0.0

    X = pd.DataFrame(
        {
            "total_cholesterol": df[total_chol_col],
            "hdl": df[hdl_col],
            "ldl": df[ldl_col],
            "triglycerides": df[trig_col],
            "age": df[age_col],
            "bmi": get_or_zero(bmi_col),
            "blood_pressure": get_or_zero(bp_col),
            "smoking_status": get_or_zero(smoke_col),
            "family_history": get_or_zero(family_col),
        }
    )
    y = df[target_col].astype(int)

    train_best_model(X, y, "cholesterol")


# ----------------- Kidney -----------------


def train_kidney():
    """
    Uses kidney_disease.csv (CKD dataset).
    Tries common column names, cleans '?' and NaN.
    """
    path = Path("data/kidney_disease.csv")
    if not path.exists():
        print("[SKIP] kidney: data/kidney_disease.csv not found")
        return

    df = pd.read_csv(path)

    try:
        age_col = pick_col(df, "age", ["age", "Age"])
        bp_col = pick_col(df, "blood_pressure", ["bp", "BloodPressure", "blood_pressure"])
        sg_col = pick_col(df, "specific_gravity", ["sg", "SpecificGravity"])
        al_col = pick_col(df, "albumin", ["al", "Albumin"])
        su_col = pick_col(df, "sugar", ["su", "Sugar"])
        bgr_col = pick_col(
            df,
            "blood_glucose_random",
            ["bgr", "BloodGlucoseRandom", "random_blood_glucose"],
        )
        bu_col = pick_col(df, "blood_urea", ["bu", "BloodUrea"])
        sc_col = pick_col(df, "serum_creatinine", ["sc", "SerumCreatinine"])
        sod_col = pick_col(df, "sodium", ["sod", "Sodium"])
        pot_col = pick_col(df, "potassium", ["pot", "Potassium"])
        hemo_col = pick_col(df, "hemoglobin", ["hemo", "Hemoglobin"])
        pcv_col = pick_col(df, "packed_cell_volume", ["pcv", "PackedCellVolume"])
        wc_col = pick_col(
            df,
            "white_blood_cell_count",
            ["wc", "WhiteBloodCellCount"],
        )
        rc_col = pick_col(
            df,
            "red_blood_cell_count",
            ["rc", "RedBloodCellCount"],
        )
    except KeyError as e:
        print(f"[SKIP] kidney: {e}")
        return

    # target
    if "classification" in df.columns:
        y_raw = df["classification"]
    elif "Outcome" in df.columns:
        y_raw = df["Outcome"]
    else:
        print("[SKIP] kidney: no 'classification' or 'Outcome' column")
        return

    # map strings to 0/1 if needed
    if y_raw.dtype == object:
        y = y_raw.map(lambda v: 1 if str(v).lower().startswith("ckd") else 0)
    else:
        y = y_raw

    feature_cols = [
        age_col,
        bp_col,
        sg_col,
        al_col,
        su_col,
        bgr_col,
        bu_col,
        sc_col,
        sod_col,
        pot_col,
        hemo_col,
        pcv_col,
        wc_col,
        rc_col,
    ]

    df = clean_numeric(df, feature_cols)
    X = df[feature_cols]
    train_best_model(X, y.loc[X.index], "kidney")


# ----------------- Liver -----------------


def train_liver():
    """
    Uses Liver Patient Dataset (LPD)_train.csv.
    """
    path = Path("data/Liver Patient Dataset (LPD)_train.csv")
    if not path.exists():
        print("[SKIP] liver: Liver Patient Dataset (LPD)_train.csv not found")
        return

    df = pd.read_csv(path)

    try:
        age_col = pick_col(df, "age", ["Age", "age"])
        gender_col = pick_col(df, "gender", ["Gender", "gender"])
        tb_col = pick_col(df, "total_bilirubin", ["Total_Bilirubin", "total_bilirubin"])
        db_col = pick_col(df, "direct_bilirubin", ["Direct_Bilirubin", "direct_bilirubin"])
        alp_col = pick_col(
            df,
            "alkaline_phosphatase",
            ["Alkaline_Phosphotase", "Alkaline_Phosphatase"],
        )
        alt_col = pick_col(
            df,
            "alt",
            ["Alamine_Aminotransferase", "ALT", "Alt"],
        )
        ast_col = pick_col(
            df,
            "ast",
            ["Aspartate_Aminotransferase", "AST", "Ast"],
        )
        tp_col = pick_col(df, "total_proteins", ["Total_Proteins", "total_proteins"])
        alb_col = pick_col(df, "albumin", ["Albumin", "albumin"])
        agr_col = pick_col(
            df,
            "ag_ratio",
            ["Albumin_and_Globulin_Ratio", "AG_Ratio", "A/G Ratio"],
        )
    except KeyError as e:
        print(f"[SKIP] liver: {e}")
        return

    # target
    if "Dataset" in df.columns:
        y_raw = df["Dataset"]
        y = (y_raw == 1).astype(int)
    elif "Outcome" in df.columns:
        y = df["Outcome"]
    else:
        print("[SKIP] liver: no 'Dataset' or 'Outcome' column")
        return

    feature_cols = [
        age_col,
        gender_col,
        tb_col,
        db_col,
        alp_col,
        alt_col,
        ast_col,
        tp_col,
        alb_col,
        agr_col,
    ]

    df = clean_numeric(df, feature_cols)
    X = df[feature_cols]
    train_best_model(X, y.loc[X.index], "liver")


# ----------------- Heart -----------------


def train_heart():
    """
    Uses heart.csv, likely UCI heart dataset:

    Columns:
      age, sex, cp, trestbps, chol, fbs, restecg,
      thalach, exang, oldpeak, slope, ca, thal, target
    """
    path = Path("data/heart.csv")
    if not path.exists():
        print("[SKIP] heart: data/heart.csv not found")
        return

    df = pd.read_csv(path)

    required = [
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
        "target",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"[SKIP] heart: missing columns {missing}")
        return

    df = clean_numeric(df, required)

    feature_cols = [
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
    ]
    target_col = "target"

    X = df[feature_cols]
    y = df[target_col]
    train_best_model(X, y, "heart")


# ----------------- Blood Pressure (using blood_samples_dataset_test.csv) -----------------


def train_blood_pressure():
    """
    Uses blood_samples_dataset_test.csv for blood pressure classification.
    We try to detect:

      systolic        -> Systolic, SystolicBP, Ap_hi, etc.
      diastolic       -> Diastolic, DiastolicBP, Ap_lo, etc.
      age             -> Age, age
      weight          -> Weight, weight
      height          -> Height, height
      stress_level    -> StressLevel, stress, Stress
      activity_level  -> ActivityLevel, PhysicalActivity, activity
      label           -> Label, Hypertension, target

    If something is missing, we SKIP gracefully.
    """
    path = Path("data/blood_samples_dataset_test.csv")
    if not path.exists():
        # fallback to old data.csv if available
        path2 = Path("data/data.csv")
        if not path2.exists():
            print("[SKIP] blood_pressure: no blood_samples_dataset_test.csv or data.csv found")
            return
        print("[INFO] blood_pressure: using data.csv instead of blood_samples_dataset_test.csv")
        df = pd.read_csv(path2)
    else:
        print("[INFO] blood_pressure: using blood_samples_dataset_test.csv")
        df = pd.read_csv(path)

    try:
        sys_col = pick_col(
            df,
            "systolic",
            ["Systolic", "SystolicBP", "SysBP", "Ap_hi", "SBP"],
        )
        dia_col = pick_col(
            df,
            "diastolic",
            ["Diastolic", "DiastolicBP", "DiaBP", "Ap_lo", "DBP"],
        )
        age_col = pick_col(df, "age", ["Age", "age"])
    except KeyError as e:
        print(f"[SKIP] blood_pressure: {e}")
        return

    # optional
    try:
        wt_col = pick_col(df, "weight", ["Weight", "weight", "Wt"])
    except KeyError:
        wt_col = None
        print("[WARN] blood_pressure: Weight not found, using zeros")
    try:
        ht_col = pick_col(df, "height", ["Height", "height", "Ht"])
    except KeyError:
        ht_col = None
        print("[WARN] blood_pressure: Height not found, using zeros")
    try:
        stress_col = pick_col(
            df,
            "stress_level",
            ["StressLevel", "stress_level", "Stress"],
        )
    except KeyError:
        stress_col = None
        print("[WARN] blood_pressure: StressLevel not found, using zeros")
    try:
        act_col = pick_col(
            df,
            "activity_level",
            ["ActivityLevel", "activity_level", "PhysicalActivity"],
        )
    except KeyError:
        act_col = None
        print("[WARN] blood_pressure: ActivityLevel not found, using zeros")

    # target
    if "Label" in df.columns:
        target_col = "Label"
    elif "Hypertension" in df.columns:
        target_col = "Hypertension"
    elif "target" in df.columns:
        target_col = "target"
    else:
        print("[SKIP] blood_pressure: no target/Label/Hypertension column")
        return

    cols_to_clean = [sys_col, dia_col, age_col]
    for c in [wt_col, ht_col, stress_col, act_col, target_col]:
        if c is not None:
            cols_to_clean.append(c)

    df = clean_numeric(df, cols_to_clean)

    def get_or_zero(col):
        return df[col] if col is not None else 0.0

    X = pd.DataFrame(
        {
            "systolic": df[sys_col],
            "diastolic": df[dia_col],
            "age": df[age_col],
            "weight": get_or_zero(wt_col),
            "height": get_or_zero(ht_col),
            "stress_level": get_or_zero(stress_col),
            "activity_level": get_or_zero(act_col),
        }
    )
    y = df[target_col].astype(int)

    train_best_model(X, y, "blood_pressure")


# ----------------- Thyroid -----------------


def train_thyroid():
    """
    Uses cleaned_dataset_Thyroid1.csv.

    Tries to map:
      Age, Sex, TSH, T3, T4, FreeT4Index, FreeT3Index,
      MedicationStatus, PregnancyStatus, GoitreStatus, Class/Outcome/Target
    """
    path = Path("data/cleaned_dataset_Thyroid1.csv")
    if not path.exists():
        print("[SKIP] thyroid: cleaned_dataset_Thyroid1.csv not found")
        return

    df = pd.read_csv(path)

    try:
        age_col = pick_col(df, "age", ["Age", "age"])
        sex_col = pick_col(df, "sex", ["Sex", "sex"])
        tsh_col = pick_col(df, "tsh", ["TSH", "tsh"])
        t3_col = pick_col(df, "t3", ["T3", "t3"])
        t4_col = pick_col(df, "t4", ["T4", "t4"])
        ft4i_col = pick_col(
            df,
            "free_t4_index",
            ["FreeT4Index", "FTI", "free_t4_index"],
        )
        ft3i_col = pick_col(
            df,
            "free_t3_index",
            ["FreeT3Index", "free_t3_index"],
        )
        med_col = pick_col(
            df,
            "medication_status",
            ["MedicationStatus", "on_thyroxine", "Medication"],
        )
        preg_col = pick_col(
            df,
            "pregnancy_status",
            ["PregnancyStatus", "pregnant"],
        )
        goitre_col = pick_col(
            df,
            "goitre_status",
            ["GoitreStatus", "goitre"],
        )
    except KeyError as e:
        print(f"[SKIP] thyroid: {e}")
        return

    if "Class" in df.columns:
        target_col = "Class"
    elif "Outcome" in df.columns:
        target_col = "Outcome"
    else:
        target_col = "Target" if "Target" in df.columns else None

    if target_col is None:
        print("[SKIP] thyroid: no Class/Outcome/Target column")
        return

    feature_cols = [
        age_col,
        sex_col,
        tsh_col,
        t3_col,
        t4_col,
        ft4i_col,
        ft3i_col,
        med_col,
        preg_col,
        goitre_col,
    ]

    df = clean_numeric(df, feature_cols + [target_col])
    X = df[feature_cols]
    y = df[target_col].astype(int)

    train_best_model(X, y, "thyroid")


# ----------------- Main -----------------


if __name__ == "__main__":
    # Make sure all these files are under a ./data/ folder:
    #   data/diabetes.csv
    #   data/dataset_2190_cholesterol.csv (optional)
    #   data/kidney_disease.csv (optional)
    #   data/Liver Patient Dataset (LPD)_train.csv (optional)
    #   data/heart.csv
    #   data/blood_samples_dataset_test.csv  (or data/data.csv)
    #   data/cleaned_dataset_Thyroid1.csv (optional)

    print("=== Training models ===")

    try:
        train_diabetes()
    except Exception as e:
        print(f"[FATAL] diabetes training crashed: {e}")

    try:
        train_cholesterol()
    except Exception as e:
        print(f"[FATAL] cholesterol training crashed: {e}")

    try:
        train_kidney()
    except Exception as e:
        print(f"[FATAL] kidney training crashed: {e}")

    try:
        train_liver()
    except Exception as e:
        print(f"[FATAL] liver training crashed: {e}")

    try:
        train_heart()
    except Exception as e:
        print(f"[FATAL] heart training crashed: {e}")

    try:
        train_blood_pressure()
    except Exception as e:
        print(f"[FATAL] blood_pressure training crashed: {e}")

    try:
        train_thyroid()
    except Exception as e:
        print(f"[FATAL] thyroid training crashed: {e}")

    print("=== Done ===")
