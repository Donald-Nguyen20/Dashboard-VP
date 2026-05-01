# [M04] Monitoring System (Schematics & Web)

- **Mục đích**: Chứa tài nguyên HTML/SVG/JS tạo nên giao diện mô phỏng thiết bị.
- **Key Files**: `AH_U2.html`, `U2-Main_Turbine.html`, `IDF_A.html`.
- **Input/Output**: Nhận script inject từ Python -> Cập nhật DOM (chỉ số, màu sắc, báo động).
- **Dependencies**: HTML5, JS (Vanilla), SVG.

## ⛔ KHÔNG làm
- KHÔNG thay đổi `id` của các thẻ SVG/HTML (Python phụ thuộc vào ID này để inject data).
- KHÔNG viết logic tính toán cảnh báo phức tạp bằng JS, hãy để Python tính và truyền sang.
