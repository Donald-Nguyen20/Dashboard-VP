# ML_APP/ML_TAB/Steps/Step3/pipelines.py
from __future__ import annotations
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import RobustScaler, StandardScaler
#from feature_engine.outliers import Winsorizer

# dùng NumericCleaner anh đã có sẵn ở utils/transformers.py
from ML_APP.ML_TAB.utils.transformers import NumericCleaner

def build_numeric_pipeline(
    *,
    impute_strategy: str = "median",
    outlier_capping: bool = True,
    scaler: str = "robust"          # "robust" | "standard" | None
) -> Pipeline:
    steps = [
        ("cleaner", NumericCleaner()),
        ("imputer", SimpleImputer(strategy=impute_strategy)),
    ]
    if outlier_capping:
        steps.append(("outlier", Winsorizer(capping_method="iqr", tail="both", fold=iqr_fold)))
    if scaler == "robust":
        steps.append(("scaler", RobustScaler()))
    elif scaler == "standard":
        steps.append(("scaler", StandardScaler()))
    return Pipeline(steps=steps)