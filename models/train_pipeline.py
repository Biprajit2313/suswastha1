from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier, VotingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

try:
    from xgboost import XGBClassifier
except ImportError:  # The pipeline still works when xgboost is not installed.
    XGBClassifier = None  # type: ignore[assignment]


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = ROOT_DIR / "data"
DEFAULT_OUTPUT_DIR = ROOT_DIR
RANDOM_STATE = 42


@dataclass(frozen=True)
class ModelSpec:
    name: str
    dataset_name: str
    features: list[str]
    target_candidates: list[str]
    task: str
    builders: Callable[[], dict[str, tuple[BaseEstimator, dict[str, list[Any]]]]]
    feature_aliases: dict[str, list[str]]
    target_builder: Callable[[pd.DataFrame], pd.Series] | None = None
    feature_engineer: Callable[[pd.DataFrame], pd.DataFrame] | None = None


def normalize_column_name(name: str) -> str:
    return (
        str(name)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace(".", "_")
        .replace("/", "_")
        .replace("(", "")
        .replace(")", "")
    )


def clean_dataframe(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame.columns = [normalize_column_name(column) for column in frame.columns]
    frame = frame.replace(["?", "NA", "N/A", "na", "n/a", "", " "], np.nan)

    mappings = {
        "yes": 1,
        "no": 0,
        "true": 1,
        "false": 0,
        "male": 1,
        "female": 0,
        "m": 1,
        "f": 0,
        "t": 1,
        "present": 1,
        "notpresent": 0,
        "normal": 0,
        "abnormal": 1,
        "good": 0,
        "poor": 1,
        "ckd": 1,
        "notckd": 0,
        "not_ckd": 0,
        "positive": 1,
        "negative": 0,
    }
    target_like_columns = {"target", "class", "classification", "selector", "outcome", "dataset", "label"}

    for column in frame.columns:
        if frame[column].dtype == object:
            normalized = frame[column].astype(str).str.strip().str.lower().replace({"nan": np.nan})
            normalized = normalized.replace(mappings)
            converted = pd.to_numeric(normalized, errors="coerce")
            if column in target_like_columns:
                frame[column] = normalized
            elif converted.notna().sum() >= normalized.notna().sum() * 0.9:
                frame[column] = converted
            else:
                frame[column] = normalized.astype("category").cat.codes.replace({-1: np.nan})
        else:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def rename_aliases(frame: pd.DataFrame, aliases: dict[str, list[str]]) -> pd.DataFrame:
    frame = frame.copy()
    rename_map: dict[str, str] = {}
    columns = set(frame.columns)
    for canonical, candidates in aliases.items():
        if canonical in columns:
            continue
        for candidate in candidates:
            normalized = normalize_column_name(candidate)
            if normalized in columns:
                rename_map[normalized] = canonical
                break
    return frame.rename(columns=rename_map)


def load_dataset(data_dir: Path, spec: ModelSpec) -> pd.DataFrame:
    candidates = [
        data_dir / spec.dataset_name,
        data_dir / f"{spec.name}.csv",
        data_dir / f"{spec.name}.data",
    ]
    for candidate in candidates:
        if candidate.exists():
            return clean_dataframe(pd.read_csv(candidate, sep=None, engine="python"))
    searched = ", ".join(str(candidate) for candidate in candidates)
    raise FileNotFoundError(f"Dataset for {spec.name} not found. Searched: {searched}")


def resolve_target(frame: pd.DataFrame, spec: ModelSpec) -> pd.Series:
    if spec.target_builder is not None:
        return spec.target_builder(frame)

    for target in spec.target_candidates:
        normalized = normalize_column_name(target)
        if normalized in frame.columns:
            return pd.to_numeric(frame[normalized], errors="coerce")
    raise ValueError(f"No target column found for {spec.name}. Tried: {spec.target_candidates}")


def prepare_training_data(frame: pd.DataFrame, spec: ModelSpec) -> tuple[pd.DataFrame, pd.Series]:
    if spec.feature_engineer is not None:
        frame = spec.feature_engineer(frame)
    frame = rename_aliases(frame, spec.feature_aliases)
    missing_features = [feature for feature in spec.features if feature not in frame.columns]
    if missing_features:
        raise ValueError(f"{spec.name} dataset is missing required features: {missing_features}")

    target = resolve_target(frame, spec)
    data = frame[spec.features].copy()
    combined = pd.concat([data, target.rename("target")], axis=1).dropna(subset=["target"])
    y = combined["target"]
    X = combined[spec.features]

    if spec.task == "binary":
        y = normalize_binary_target(pd.Series(y), spec.name)
    else:
        y = pd.Series(y).astype(int)

    return X, y


def normalize_binary_target(target: pd.Series, test_name: str) -> pd.Series:
    if target.dtype == object:
        text = target.astype(str).str.strip().str.lower().str.replace(r"[\t ]+", "", regex=True)
        if test_name == "kidney":
            return text.map({"ckd": 1, "ckd\t": 1, "notckd": 0, "notckd\t": 0}).astype(int)
        if set(text.dropna().unique()).issubset({"0", "1"}):
            return text.astype(int)
    y = pd.to_numeric(target, errors="coerce")
    unique_values = sorted(pd.Series(y).dropna().unique().tolist())
    if test_name == "heart" and len(unique_values) > 2:
        return (y > 0).astype(int)
    if test_name == "liver" and set(unique_values) == {1, 2}:
        return y.map({1: 1, 2: 0}).astype(int)
    if set(unique_values) == {0, 1}:
        return y.astype(int)
    if len(unique_values) != 2:
        raise ValueError(f"{test_name} needs a binary target, got values: {unique_values}")
    return y.map({unique_values[0]: 0, unique_values[1]: 1}).astype(int)


def numeric_pipeline(scaled: bool) -> ColumnTransformer:
    steps: list[tuple[str, Any]] = [("imputer", SimpleImputer(strategy="median"))]
    if scaled:
        steps.append(("scaler", StandardScaler()))
    return ColumnTransformer([("numeric", Pipeline(steps), slice(0, None))], remainder="drop")


def make_pipeline(estimator: BaseEstimator, *, scaled: bool = False) -> Pipeline:
    return Pipeline(
        steps=[
            ("preprocess", numeric_pipeline(scaled=scaled)),
            ("model", estimator),
        ]
    )


def xgb_classifier(num_classes: int | None = None) -> BaseEstimator | None:
    if XGBClassifier is None:
        return None
    params: dict[str, Any] = {
        "n_estimators": 250,
        "max_depth": 3,
        "learning_rate": 0.04,
        "subsample": 0.85,
        "colsample_bytree": 0.85,
        "tree_method": "hist",
        "device": "cpu",
        "n_jobs": 1,
        "eval_metric": "logloss",
        "random_state": RANDOM_STATE,
    }
    if num_classes and num_classes > 2:
        params.update({"objective": "multi:softprob", "num_class": num_classes, "eval_metric": "mlogloss"})
    return XGBClassifier(**params)


def diabetes_builders() -> dict[str, tuple[BaseEstimator, dict[str, list[Any]]]]:
    estimators: list[tuple[str, BaseEstimator]] = [
        ("lr", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=RANDOM_STATE)),
        ("rf", RandomForestClassifier(class_weight="balanced", random_state=RANDOM_STATE)),
    ]
    xgb = xgb_classifier()
    if xgb is not None:
        estimators.append(("xgb", xgb))
    ensemble = VotingClassifier(estimators=estimators, voting="soft")
    return {
        "diabetes_voting_ensemble": (
            make_pipeline(ensemble, scaled=True),
            {
                "model__rf__n_estimators": [150, 300],
                "model__rf__max_depth": [4, 8, None],
                "model__lr__C": [0.1, 1.0, 3.0],
            },
        )
    }


def heart_builders() -> dict[str, tuple[BaseEstimator, dict[str, list[Any]]]]:
    ensemble = VotingClassifier(
        estimators=[
            ("rf", RandomForestClassifier(class_weight="balanced", random_state=RANDOM_STATE)),
            ("gb", GradientBoostingClassifier(random_state=RANDOM_STATE)),
        ],
        voting="soft",
    )
    return {
        "heart_rf_gradient_boosting": (
            make_pipeline(ensemble),
            {
                "model__rf__n_estimators": [150, 300],
                "model__rf__max_depth": [4, 8, None],
                "model__gb__learning_rate": [0.03, 0.08],
            },
        )
    }


def blood_pressure_builders() -> dict[str, tuple[BaseEstimator, dict[str, list[Any]]]]:
    return {
        "blood_pressure_random_forest": (
            make_pipeline(RandomForestClassifier(class_weight="balanced", random_state=RANDOM_STATE)),
            {"model__n_estimators": [150, 300], "model__max_depth": [3, 6, None]},
        ),
        "blood_pressure_decision_tree": (
            make_pipeline(DecisionTreeClassifier(class_weight="balanced", random_state=RANDOM_STATE)),
            {"model__max_depth": [3, 5, 8], "model__min_samples_leaf": [2, 5, 10]},
        ),
    }


def cholesterol_builders() -> dict[str, tuple[BaseEstimator, dict[str, list[Any]]]]:
    ensemble = VotingClassifier(
        estimators=[
            ("lr", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=RANDOM_STATE)),
            ("gb", GradientBoostingClassifier(random_state=RANDOM_STATE)),
        ],
        voting="soft",
    )
    return {
        "cholesterol_lr_gradient_boosting": (
            make_pipeline(ensemble, scaled=True),
            {"model__lr__C": [0.1, 1.0, 3.0], "model__gb__learning_rate": [0.03, 0.08]},
        )
    }


def liver_builders() -> dict[str, tuple[BaseEstimator, dict[str, list[Any]]]]:
    estimators: list[tuple[str, BaseEstimator]] = [
        ("rf", RandomForestClassifier(class_weight="balanced", random_state=RANDOM_STATE)),
    ]
    xgb = xgb_classifier()
    if xgb is not None:
        estimators.append(("xgb", xgb))
    ensemble = VotingClassifier(estimators=estimators, voting="soft")
    return {
        "liver_rf_xgboost": (
            make_pipeline(ensemble),
            {"model__rf__n_estimators": [150, 300], "model__rf__max_depth": [4, 8, None]},
        )
    }


def kidney_builders() -> dict[str, tuple[BaseEstimator, dict[str, list[Any]]]]:
    return {
        "kidney_random_forest": (
            make_pipeline(RandomForestClassifier(class_weight="balanced", random_state=RANDOM_STATE)),
            {
                "model__n_estimators": [200, 400],
                "model__max_depth": [4, 8, None],
                "model__min_samples_leaf": [1, 3, 5],
            },
        )
    }


def thyroid_builders() -> dict[str, tuple[BaseEstimator, dict[str, list[Any]]]]:
    ensemble = VotingClassifier(
        estimators=[
            ("svm", SVC(probability=True, class_weight="balanced", random_state=RANDOM_STATE)),
            ("rf", RandomForestClassifier(class_weight="balanced", random_state=RANDOM_STATE)),
        ],
        voting="soft",
    )
    return {
        "thyroid_svm_random_forest": (
            make_pipeline(ensemble, scaled=True),
            {"model__svm__C": [0.5, 1.0, 3.0], "model__rf__n_estimators": [150, 300]},
        )
    }


def blood_pressure_target(frame: pd.DataFrame) -> pd.Series:
    for candidate in ["target", "label", "class", "hypertension_stage"]:
        if candidate in frame.columns:
            return pd.to_numeric(frame[candidate], errors="coerce")
    systolic = pd.to_numeric(frame["systolic"], errors="coerce")
    diastolic = pd.to_numeric(frame["diastolic"], errors="coerce")
    return pd.Series(
        np.select(
            [(systolic >= 140) | (diastolic >= 90), (systolic >= 120) | (diastolic >= 80)],
            [2, 1],
            default=0,
        ),
        index=frame.index,
    )


def cholesterol_target(frame: pd.DataFrame) -> pd.Series:
    for candidate in ["target", "label", "class", "high_cholesterol", "disease"]:
        if candidate in frame.columns:
            return pd.to_numeric(frame[candidate], errors="coerce")
    ldl = pd.to_numeric(frame["ldl"], errors="coerce")
    hdl = pd.to_numeric(frame["hdl"], errors="coerce")
    triglycerides = pd.to_numeric(frame["triglycerides"], errors="coerce")
    total = pd.to_numeric(frame["total_cholesterol"], errors="coerce")
    return (((ldl >= 160) | (hdl < 40) | (triglycerides >= 200) | (total >= 240))).astype(int)


def cardio_feature_engineer(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    if {"ap_hi", "ap_lo"}.issubset(frame.columns):
        frame = frame[
            frame["ap_hi"].between(80, 250)
            & frame["ap_lo"].between(40, 150)
            & frame["height"].between(120, 220)
            & frame["weight"].between(30, 250)
        ].copy()
        frame["systolic"] = frame["ap_hi"]
        frame["diastolic"] = frame["ap_lo"]
        frame["blood_pressure"] = frame["ap_hi"]
        frame["age"] = frame["age"] / 365.25
        frame["bmi"] = frame["weight"] / ((frame["height"] / 100.0) ** 2)
        frame["stress_level"] = np.select(
            [frame["ap_hi"] >= 140, frame["ap_hi"] >= 120],
            [2, 1],
            default=0,
        )
        frame["activity_level"] = frame.get("active", 0)
        frame["smoking_status"] = frame.get("smoke", 0)
        frame["family_history"] = (frame.get("gluc", 1) > 1).astype(int)
        frame["total_cholesterol"] = frame["cholesterol"].map({1: 180, 2: 220, 3: 260})
        frame["hdl"] = frame["cholesterol"].map({1: 55, 2: 45, 3: 35})
        frame["ldl"] = frame["cholesterol"].map({1: 100, 2: 145, 3: 190})
        frame["triglycerides"] = frame["cholesterol"].map({1: 120, 2: 180, 3: 240})
        frame["high_cholesterol"] = (frame["cholesterol"] >= 2).astype(int)
    return frame


def thyroid_feature_engineer(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    if "tt4" in frame.columns:
        frame["t4"] = frame["tt4"]
    if "fti" in frame.columns:
        frame["free_t4_index"] = frame["fti"]
    if "t3" in frame.columns:
        frame["free_t3_index"] = frame["t3"]
    if "on_thyroxine" in frame.columns and "on_antithyroid_meds" in frame.columns:
        frame["medication_status"] = (
            pd.to_numeric(frame["on_thyroxine"], errors="coerce").fillna(0)
            + pd.to_numeric(frame["on_antithyroid_meds"], errors="coerce").fillna(0)
        ).clip(0, 1)
    if "pregnant" in frame.columns:
        frame["pregnancy_status"] = frame["pregnant"]
    if "goitre" in frame.columns:
        frame["goitre_status"] = frame["goitre"]
    return frame


def thyroid_target(frame: pd.DataFrame) -> pd.Series:
    raw = frame["target"].astype(str).str.strip().str.upper()
    hyper_codes = tuple("ABCDNOPQ")
    hypo_codes = tuple("EFGHLM")

    def classify(value: str) -> int:
        if value == "-":
            return 0
        codes = value.replace("|", "")
        if any(code in codes for code in hyper_codes):
            return 2
        if any(code in codes for code in hypo_codes):
            return 1
        return 0

    return raw.map(classify).astype(int)


def save_bmi_artifact(output_dir: Path) -> None:
    artifact = {
        "type": "bmi_rule",
        "task": "rule_regression_hybrid",
        "features": ["weight", "height"],
        "metrics": {"source": "WHO BMI thresholds", "requires_training": False},
        "feature_importance": {"weight": 0.5, "height": 0.5},
    }
    joblib.dump(artifact, output_dir / "bmi.joblib")


def best_score_name(task: str) -> str:
    return "roc_auc" if task == "binary" else "roc_auc_ovr_weighted"


def evaluate_model(model: BaseEstimator, X_test: pd.DataFrame, y_test: pd.Series, task: str) -> dict[str, Any]:
    predictions = model.predict(X_test)
    metrics: dict[str, Any] = {
        "accuracy": round(float(accuracy_score(y_test, predictions)), 4),
        "classification_report": classification_report(y_test, predictions, output_dict=True, zero_division=0),
    }
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(X_test)
        try:
            if task == "binary":
                metrics["roc_auc"] = round(float(roc_auc_score(y_test, probabilities[:, 1])), 4)
            else:
                metrics["roc_auc"] = round(float(roc_auc_score(y_test, probabilities, multi_class="ovr", average="weighted")), 4)
        except ValueError:
            metrics["roc_auc"] = None
    return metrics


def extract_feature_importance(model: BaseEstimator, features: list[str]) -> dict[str, float]:
    estimator = model.named_steps.get("model") if isinstance(model, Pipeline) else model
    importance: np.ndarray | None = None
    if hasattr(estimator, "feature_importances_"):
        importance = np.asarray(estimator.feature_importances_)
    elif hasattr(estimator, "coef_"):
        importance = np.mean(np.abs(np.asarray(estimator.coef_)), axis=0)
    elif hasattr(estimator, "estimators_"):
        collected = []
        for _, fitted in getattr(estimator, "named_estimators_", {}).items():
            if hasattr(fitted, "feature_importances_"):
                collected.append(np.asarray(fitted.feature_importances_))
            elif hasattr(fitted, "coef_"):
                collected.append(np.mean(np.abs(np.asarray(fitted.coef_)), axis=0))
        if collected:
            importance = np.mean(collected, axis=0)
    if importance is None or len(importance) != len(features):
        return {}
    total = float(np.sum(np.abs(importance))) or 1.0
    return {feature: round(float(value) / total, 4) for feature, value in zip(features, importance)}


def train_one(spec: ModelSpec, data_dir: Path, output_dir: Path) -> dict[str, Any]:
    frame = load_dataset(data_dir, spec)
    X, y = prepare_training_data(frame, spec)
    stratify = y if y.nunique() > 1 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=stratify,
    )

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    scoring = best_score_name(spec.task)
    best_name = ""
    best_estimator: BaseEstimator | None = None
    best_cv_score = -np.inf

    for candidate_name, (pipeline, grid) in spec.builders().items():
        search = GridSearchCV(
            pipeline,
            grid,
            scoring=scoring,
            cv=cv,
            n_jobs=1,
            refit=True,
            error_score="raise",
        )
        search.fit(X_train, y_train)
        if float(search.best_score_) > best_cv_score:
            best_name = candidate_name
            best_cv_score = float(search.best_score_)
            best_estimator = search.best_estimator_

    if best_estimator is None:
        raise RuntimeError(f"No model was trained for {spec.name}")

    metrics = evaluate_model(best_estimator, X_test, y_test, spec.task)
    metrics["best_model"] = best_name
    metrics["cv_score"] = round(best_cv_score, 4)
    artifact = {
        "model": best_estimator,
        "features": spec.features,
        "task": spec.task,
        "metrics": metrics,
        "feature_importance": extract_feature_importance(best_estimator, spec.features),
    }
    output_path = output_dir / f"{spec.name}.joblib"
    joblib.dump(artifact, output_path)
    return {"test_type": spec.name, "output_path": str(output_path), "metrics": metrics}


COMMON_ALIASES = {
    "blood_pressure": ["bp", "bloodpressure", "trestbps", "resting_blood_pressure"],
    "bmi": ["body_mass_index"],
    "pedigree": ["diabetespedigreefunction", "diabetes_pedigree_function"],
}


SPECS: dict[str, ModelSpec] = {
    "diabetes": ModelSpec(
        name="diabetes",
        dataset_name="diabetes (1).csv",
        features=["glucose", "blood_pressure", "skin_thickness", "insulin", "bmi", "pedigree", "age"],
        target_candidates=["outcome", "target", "diabetes"],
        task="binary",
        builders=diabetes_builders,
        feature_aliases=COMMON_ALIASES | {"skin_thickness": ["skinthickness"]},
    ),
    "heart": ModelSpec(
        name="heart",
        dataset_name="heart_statlog_cleveland_hungary_final.csv",
        features=["age", "sex", "cp", "trestbps", "chol", "fbs", "restecg", "thalach", "exang", "oldpeak", "slope"],
        target_candidates=["target", "condition", "heart_disease"],
        task="binary",
        builders=heart_builders,
        feature_aliases={
            "cp": ["chest_pain_type"],
            "trestbps": ["resting_bp_s", "resting_blood_pressure"],
            "chol": ["cholesterol"],
            "fbs": ["fasting_blood_sugar"],
            "restecg": ["resting_ecg"],
            "thalach": ["max_heart_rate"],
            "exang": ["exercise_angina"],
            "slope": ["st_slope"],
        },
    ),
    "blood_pressure": ModelSpec(
        name="blood_pressure",
        dataset_name="cardio_train.csv",
        features=["systolic", "diastolic", "age", "weight", "height", "stress_level", "activity_level"],
        target_candidates=["target", "label", "class", "hypertension_stage"],
        task="multiclass",
        builders=blood_pressure_builders,
        target_builder=blood_pressure_target,
        feature_engineer=cardio_feature_engineer,
        feature_aliases={"systolic": ["systolic_bp"], "diastolic": ["diastolic_bp"]},
    ),
    "cholesterol": ModelSpec(
        name="cholesterol",
        dataset_name="cardio_train.csv",
        features=["total_cholesterol", "hdl", "ldl", "triglycerides", "age", "bmi", "blood_pressure", "smoking_status", "family_history"],
        target_candidates=["target", "label", "class", "high_cholesterol"],
        task="binary",
        builders=cholesterol_builders,
        target_builder=cholesterol_target,
        feature_engineer=cardio_feature_engineer,
        feature_aliases=COMMON_ALIASES | {"total_cholesterol": ["cholesterol", "total_chol"]},
    ),
    "liver": ModelSpec(
        name="liver",
        dataset_name="Indian Liver Patient Dataset (ILPD).csv",
        features=["age", "gender", "total_bilirubin", "direct_bilirubin", "alkaline_phosphatase", "alt", "ast", "total_proteins", "albumin", "ag_ratio"],
        target_candidates=["dataset", "target", "selector", "liver_disease"],
        task="binary",
        builders=liver_builders,
        feature_aliases={
            "gender": ["sex"],
            "total_bilirubin": ["tb", "tot_bilirubin"],
            "direct_bilirubin": ["db"],
            "alkaline_phosphatase": ["alkphos", "alkaline_phosphotase", "alkaline_phosphatase"],
            "alt": ["sgpt", "alamine_aminotransferase"],
            "ast": ["sgot", "aspartate_aminotransferase"],
            "total_proteins": ["tp", "total_protein"],
            "albumin": ["alb"],
            "ag_ratio": ["albumin_and_globulin_ratio", "a_g_ratio"],
        },
    ),
    "kidney": ModelSpec(
        name="kidney",
        dataset_name="kidney_disease.csv",
        features=[
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
        target_candidates=["class", "classification", "target", "ckd"],
        task="binary",
        builders=kidney_builders,
        feature_aliases=COMMON_ALIASES
        | {
            "specific_gravity": ["sg"],
            "albumin": ["al"],
            "sugar": ["su"],
            "blood_glucose_random": ["bgr"],
            "blood_urea": ["bu"],
            "serum_creatinine": ["sc"],
            "sodium": ["sod"],
            "potassium": ["pot"],
            "hemoglobin": ["hemo"],
            "packed_cell_volume": ["pcv"],
            "white_blood_cell_count": ["wc"],
            "red_blood_cell_count": ["rc"],
        },
    ),
    "thyroid": ModelSpec(
        name="thyroid",
        dataset_name="thyroidDF.csv",
        features=["age", "sex", "tsh", "t3", "t4", "free_t4_index", "free_t3_index", "medication_status", "pregnancy_status", "goitre_status"],
        target_candidates=["target", "class", "label", "thyroid_status"],
        task="multiclass",
        builders=thyroid_builders,
        target_builder=thyroid_target,
        feature_engineer=thyroid_feature_engineer,
        feature_aliases={"sex": ["gender"], "free_t4_index": ["fti"], "goitre_status": ["goitre"]},
    ),
}


def train_all(data_dir: Path, output_dir: Path, tests: list[str]) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for test in tests:
        if test == "bmi":
            save_bmi_artifact(output_dir)
            results.append({"test_type": "bmi", "output_path": str(output_dir / "bmi.joblib")})
            continue
        results.append(train_one(SPECS[test], data_dir, output_dir))
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train SuSwastha ML model packages.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--tests",
        nargs="+",
        default=["diabetes", "heart", "blood_pressure", "bmi", "cholesterol", "liver", "kidney", "thyroid"],
        choices=["diabetes", "heart", "blood_pressure", "bmi", "cholesterol", "liver", "kidney", "thyroid"],
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = train_all(args.data_dir, args.output_dir, args.tests)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
