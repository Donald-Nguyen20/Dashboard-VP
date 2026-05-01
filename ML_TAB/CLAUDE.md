# [M03] Machine Learning

- **Mục đích**: Tiền xử lý dữ liệu, huấn luyện và deploy mô hình ML.
- **Key Files**: ⚠️ `(Các file cấu hình và logic train model)`.
- **Input/Output**: Nhận DataFrame qua `df_provider` -> Xuất model / predict results.
- **Dependencies**: Pandas, Scikit-learn/TensorFlow ⚠️.

## ⛔ KHÔNG làm
- KHÔNG viết lại các hàm xử lý/làm sạch dữ liệu đã tồn tại ở [M02]/[M05].
- KHÔNG hardcode các tham số mô hình vào UI layer.
