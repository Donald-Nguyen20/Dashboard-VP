import pandas as pd
from .base import BaseHandler

def _coerce_numeric_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    return out

class RegressionMultiHandler(BaseHandler):
    bundle_type = "regression_multi"

    def predict(self, bundle: dict, data: pd.DataFrame) -> pd.DataFrame:
        x_cols = bundle["x_cols"]
        scaler = bundle["scaler"]

        X = _coerce_numeric_df(data[x_cols])
        ok = ~X.isna().any(axis=1)
        X_ok = X.loc[ok]
        X_scaled = scaler.transform(X_ok.values)

        result = data.copy()

        # Option 1: models_by_target
        mbt = bundle.get("models_by_target")
        if isinstance(mbt, dict) and mbt:
            for t, m in mbt.items():
                col = f"Prediction_{t}"
                result[col] = pd.NA
                result.loc[ok, col] = m.predict(X_scaled)
            return result

        # Option 2: one model returns 2D
        model = bundle["model"]
        preds = model.predict(X_scaled)   # shape (n, k)
        target_names = bundle.get("target_names") or [f"T{i+1}" for i in range(preds.shape[1])]

        for j, t in enumerate(target_names):
            col = f"Prediction_{t}"
            result[col] = pd.NA
            result.loc[ok, col] = preds[:, j]
        return result