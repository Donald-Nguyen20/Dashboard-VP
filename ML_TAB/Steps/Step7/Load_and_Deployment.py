import os
import pickle
import pandas as pd
import re
def _coerce_numeric_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    return out

def predict_from_model(model_path: str, data_path: str, save_path: str = "predicted_results.csv"):
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"❌ Không tìm thấy file model: {model_path}")
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"❌ Không tìm thấy file dữ liệu: {data_path}")

    # 1) Load bundle
    with open(model_path, "rb") as f:
        bundle = pickle.load(f)

    model = bundle.get("model")
    scaler = bundle.get("scaler")
    x_cols = bundle.get("x_cols")  # <-- CẦN lưu x_cols ở Step 6

    if model is None or scaler is None:
        raise ValueError("Bundle thiếu 'model' hoặc 'scaler'.")
    if not x_cols:
        raise ValueError("Bundle thiếu 'x_cols'. Hãy cập nhật Step 6 để lưu x_cols khi save model.")

    # 2) Read data
    data = pd.read_csv(data_path)


    def normalize_col(col: str) -> str:
        c = col.strip()
        c = re.sub(r"\s+", "_", c)   # space -> _
        c = c.replace("-", "_")      # - -> _
        c = re.sub(r"_+", "_", c)    # __ -> _
        return c

    data = pd.read_csv(data_path)
    data.columns = [normalize_col(c) for c in data.columns]
    # 3) Chọn đúng feature + ép numeric
    missing = [c for c in x_cols if c not in data.columns]
    if missing:
        raise ValueError(f"Dữ liệu deploy thiếu các cột feature: {missing}")

    X = _coerce_numeric_df(data[x_cols])

    # dòng hợp lệ: không NaN trên feature
    ok_mask = ~X.isna().any(axis=1)
    X_ok = X.loc[ok_mask]

    if len(X_ok) == 0:
        raise ValueError("Không còn dòng hợp lệ sau khi ép numeric/drop NaN.")

    # 4) Scale + predict
    X_scaled = scaler.transform(X_ok.values)
    preds = model.predict(X_scaled)

    # 5) Ghép kết quả (giữ nguyên số dòng; dòng invalid -> Prediction = NaN)
    result = data.copy()
    result["Prediction"] = pd.NA
    result.loc[ok_mask, "Prediction"] = preds

    abs_path = os.path.abspath(save_path)
    result.to_csv(abs_path, index=False)
    return abs_path, len(result)