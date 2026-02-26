import pickle
import pandas as pd

from .handlers.reg_single import RegressionSingleHandler
from .handlers.reg_multi import RegressionMultiHandler

HANDLERS = {
    RegressionSingleHandler.bundle_type: RegressionSingleHandler(),
    RegressionMultiHandler.bundle_type: RegressionMultiHandler(),
}

def load_bundle(model_path: str) -> dict:
    with open(model_path, "rb") as f:
        b = pickle.load(f)
    if not isinstance(b, dict) or "bundle_type" not in b:
        raise ValueError("Bundle không hợp lệ hoặc thiếu bundle_type.")
    return b

def run_inference(model_path: str, data_path: str) -> pd.DataFrame:
    bundle = load_bundle(model_path)
    data = pd.read_csv(data_path)
    

    bt = bundle["bundle_type"]
    if bt not in HANDLERS:
        raise ValueError(f"Chưa hỗ trợ bundle_type='{bt}'.")
    handler = HANDLERS[bt]

    # validate columns
    x_cols = bundle.get("x_cols", [])
    missing = [c for c in x_cols if c not in data.columns]
    if missing:
        raise ValueError(f"Dữ liệu thiếu feature: {missing}")

    return handler.predict(bundle, data)