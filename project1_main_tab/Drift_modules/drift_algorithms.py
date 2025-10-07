import numpy as np

def detect_ewma(residual, lambda_, L):
    """
    Phát hiện drift bằng phương pháp EWMA.
    :param residual: Chuỗi sai số (observed - baseline)
    :param lambda_: hệ số làm mượt (cấu hình từ drift_config)
    :param L: Hệ số giới hạn kiểm soát (cấu hình từ drift_config)
    :return: EWMA series, UCL, LCL, mask cảnh báo
    """
    S = [residual.iloc[0]]
    for r in residual.iloc[1:]:
        S.append(lambda_ * r + (1 - lambda_) * S[-1])
    S = np.array(S)
    mu, sigma = residual.mean(), residual.std()
    ucl = mu + L * sigma * np.sqrt(lambda_ / (2 - lambda_))
    lcl = mu - L * sigma * np.sqrt(lambda_ / (2 - lambda_))
    anomalies = (S > ucl) | (S < lcl)
    return S, ucl, lcl, anomalies

def detect_cusum(residual, k=0.5, h=5):
    """
    Phát hiện drift bằng thuật toán CUSUM.
    :param residual: Chuỗi sai số (observed - baseline)
    :param k: hệ số bias
    :param h: ngưỡng cảnh báo
    :return: CUSUM+, CUSUM-, mask cảnh báo
    """
    C_plus = [0]; C_minus = [0]
    for r in residual:
        C_plus.append(max(0, C_plus[-1] + r - k))
        C_minus.append(min(0, C_minus[-1] + r + k))
    C_plus, C_minus = np.array(C_plus[1:]), np.array(C_minus[1:])
    anomalies = (C_plus > h) | (abs(C_minus) > h)
    return C_plus, C_minus, anomalies

def filter_continuous_anomalies(anomalies, min_len=5):
    """
    Giữ lại các chuỗi anomaly có ít nhất min_len điểm liên tục.
    :param anomalies: mảng bool chỉ điểm bất thường
    :param min_len: số điểm liên tục tối thiểu
    :return: mảng bool mới
    """
    runs = []
    run = []
    last_idx = -2
    for idx in np.where(anomalies)[0]:
        if idx == last_idx + 1:
            run.append(idx)
        else:
            if len(run) >= min_len:
                runs.extend(run)
            run = [idx]
        last_idx = idx
    if len(run) >= min_len:
        runs.extend(run)
    mask = np.zeros_like(anomalies, dtype=bool)
    mask[runs] = True
    return mask

def detect_extreme_trend(df, col, baseline, direction='down'):
    """
    Phát hiện xu hướng tăng/giảm cực trị liên tục
    :param df: dataframe chứa dữ liệu
    :param col: tên cột theo dõi
    :param baseline: giá trị tham chiếu ban đầu
    :param direction: 'down' hoặc 'up'
    :return: danh sách (datetime, value) các điểm cực trị mới
    """
    trend_points = []
    last_val = baseline
    for idx, row in df.iterrows():
        current_val = row[col]
        if direction == 'down' and current_val < last_val:
            trend_points.append((row['Datetime'], current_val))
            last_val = current_val
        elif direction == 'up' and current_val > last_val:
            trend_points.append((row['Datetime'], current_val))
            last_val = current_val
    return trend_points