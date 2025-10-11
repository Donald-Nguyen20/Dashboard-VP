import os
import pickle
import pandas as pd

def predict_from_model(model_path: str, data_path: str, save_path: str = "predicted_results.csv"):
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"❌ Không tìm thấy file model: {model_path}")
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"❌ Không tìm thấy file dữ liệu: {data_path}")

    # 1️⃣ Load model và scaler từ file pickle
    with open(model_path, "rb") as f:
        bundle = pickle.load(f)
    model, scaler = bundle["model"], bundle["scaler"]

    # 2️⃣ Đọc dữ liệu cần dự đoán
    data = pd.read_csv(data_path)

    # 3️⃣ Chuẩn hóa dữ liệu đầu vào
    data_scaled = scaler.transform(data)

    # 4️⃣ Dự đoán
    preds = model.predict(data_scaled)

    # 5️⃣ Ghép kết quả và lưu ra file
    result = data.copy()
    result["Prediction"] = preds
    abs_path = os.path.abspath(save_path)
    result.to_csv(abs_path, index=False)

    return abs_path, len(result)
