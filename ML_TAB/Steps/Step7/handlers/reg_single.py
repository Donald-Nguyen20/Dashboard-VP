import pandas as pd
from .base import BaseHandler

def _coerce_numeric_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    return out

class RegressionSingleHandler(BaseHandler):
    bundle_type = "regression_single"

    def predict(self, bundle: dict, data: pd.DataFrame) -> pd.DataFrame:
        x_cols = bundle["x_cols"]
        scaler = bundle["scaler"]
        model = bundle["model"]
        target = bundle.get("target_name", "Target")

        X = _coerce_numeric_df(data[x_cols])
        ok = ~X.isna().any(axis=1)
        X_ok = X.loc[ok]
        X_scaled = scaler.transform(X_ok.values)

        preds = model.predict(X_scaled)

        result = data.copy()
        col = f"Prediction_{target}"
        result[col] = pd.NA
        result.loc[ok, col] = preds
        return result