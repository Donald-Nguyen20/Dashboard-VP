"""
help_dialog.py — Hộp thoại hướng dẫn sử dụng (bấm F1 để mở).
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QTextBrowser, QPushButton, QLabel
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut


# ─────────────────────────────────────────────────────────────
#  Nội dung HTML từng tab
# ─────────────────────────────────────────────────────────────

_STYLE = """
<style>
  body  { font-family: 'Segoe UI', Arial, sans-serif; font-size: 14px;
          color: #1e2a36; margin: 12px 16px; }
  h2    { color: #1a56c4; border-bottom: 2px solid #a9c9ff;
          padding-bottom: 4px; margin-top: 18px; }
  h3    { color: #2f6fe4; margin-top: 14px; margin-bottom: 4px; }
  table { border-collapse: collapse; width: 100%; margin-top: 6px; }
  th    { background: #d0e4ff; color: #1e3c78; padding: 7px 10px;
          text-align: left; border: 1px solid #b6c7d8; }
  td    { padding: 6px 10px; border: 1px solid #dbe8ff;
          vertical-align: top; }
  tr:nth-child(even) td { background: #f0f7ff; }
  code  { background: #e8f2ff; border-radius: 3px;
          padding: 1px 5px; font-size: 13px; color: #1a56c4; }
  ul    { margin: 4px 0 4px 20px; padding: 0; }
  li    { margin-bottom: 3px; }
  .note { background: #fff8e1; border-left: 4px solid #f4b400;
          padding: 8px 12px; border-radius: 4px; margin-top: 8px; }
  .tip  { background: #e8f5e9; border-left: 4px solid #43a047;
          padding: 8px 12px; border-radius: 4px; margin-top: 8px; }
</style>
"""

# ── Tab 1: Tổng quan ────────────────────────────────────────
_HTML_OVERVIEW = _STYLE + """
<h2>Tổng quan ứng dụng</h2>
<p>
  <b>Multi Project Dashboard</b> là công cụ phân tích dữ liệu công nghiệp gồm
  <b>3 module chính</b>, truy cập qua 3 tab ở trên cùng:
</p>
<table>
  <tr><th>Tab</th><th>Tên module</th><th>Mục đích chính</th></tr>
  <tr>
    <td>📊</td>
    <td><b>Data Analyzing</b></td>
    <td>Tải, làm sạch, trực quan hoá và phân tích drift dữ liệu chuỗi thời gian</td>
  </tr>
  <tr>
    <td>🤖</td>
    <td><b>ML Application</b></td>
    <td>Xây dựng và triển khai mô hình hồi quy (7 bước từ thu thập tới deploy)</td>
  </tr>
  <tr>
    <td>📡</td>
    <td><b>Monitoring System</b></td>
    <td>Giám sát theo dõi real-time, lưới ô hiển thị tuỳ chỉnh, xuất báo cáo vận hành</td>
  </tr>
</table>

<h2>Luồng dữ liệu chính</h2>
<p>
  <code>CSV / Excel</code>
  → <b>Xử lý song song (ThreadPool)</b>
  → <code>.parquet (zstd)</code>
  → <b>DuckDB DataManager</b> (query theo khoảng thời gian)
  → <code>final_df</code> (pandas DataFrame) được đẩy tới tất cả các tab
</p>

<h2>Phím tắt toàn cục</h2>
<table>
  <tr><th>Phím</th><th>Chức năng</th></tr>
  <tr><td><code>F1</code></td><td>Mở hướng dẫn này</td></tr>
  <tr><td><code>Esc</code></td><td>Đóng hộp thoại đang mở</td></tr>
</table>

<div class="tip">
  <b>Mẹo:</b> Nhấp vào tên folder ở cột trái của tab <i>Data Analyzing</i>
  để tải nhanh dữ liệu đã xử lý trước đó mà không cần đọc lại CSV.
</div>
"""

# ── Tab 2: Data Analyzing ───────────────────────────────────
_HTML_DATA = _STYLE + """
<h2>Tab — Data Analyzing</h2>

<h3>📂 Load Data</h3>
<ul>
  <li>Nhấn <b>📂 Load Data</b> hoặc bấm vào tên folder ở cột trái để tải dữ liệu.</li>
  <li>Hỗ trợ định dạng: <code>.csv</code>, <code>.xlsx</code>, <code>.xlsm</code>, <code>.xlsb</code>.</li>
  <li>Các subfolder bên trong được xử lý <b>song song</b> (4 luồng), mỗi subfolder tạo 1 file <code>.parquet</code>.</li>
  <li>Subfolder đã xử lý được ghi vào <code>metadata.json</code> — lần sau sẽ bỏ qua để tăng tốc.</li>
  <li>Chọn <b>định dạng ngày</b> trước khi tải: <code>dd/MM/yyyy</code> (mặc định VN)
      hoặc <code>MM/dd/yyyy</code> (US).</li>
</ul>

<h3>🏠 Home — Xem & Quản lý dữ liệu</h3>
<table>
  <tr><th>Nút</th><th>Chức năng</th></tr>
  <tr><td>🔄 Refresh</td><td>Lọc bảng theo khoảng thời gian đã chọn (start/end datetime)</td></tr>
  <tr><td>🧹 Clean Data</td><td>Điền NaN, xử lý ngoại lệ, đổi kiểu dữ liệu</td></tr>
  <tr><td>NaN status</td><td>Thống kê số lượng và % giá trị NaN theo từng cột</td></tr>
  <tr><td>🗑 Delete Features</td><td>Xoá bỏ các cột không cần thiết</td></tr>
  <tr><td>🧠 Formula Module</td><td>
    <b>Build Formula</b>: tạo cột mới bằng biểu thức toán học<br>
    <b>Insert Formula</b>: chèn công thức đã lưu trước đó
  </td></tr>
  <tr><td>💾 Export</td><td>Xuất dữ liệu hiện tại ra CSV hoặc Excel</td></tr>
</table>

<h3>🌐 Plotly — Biểu đồ tương tác</h3>
<p>Chọn loại biểu đồ từ dropdown, chọn biến, thiết lập khoảng thời gian rồi nhấn <b>Plot</b>.</p>
<table>
  <tr><th>Biểu đồ</th><th>Mô tả</th></tr>
  <tr><td>Line Chart</td><td>Xu hướng theo thời gian, hỗ trợ nhiều biến & đa trục Y</td></tr>
  <tr><td>Scatter 2D</td><td>Tương quan giữa 2 biến liên tục</td></tr>
  <tr><td>Bar Max</td><td>Biểu đồ cột giá trị lớn nhất / trung bình theo nhóm thời gian</td></tr>
  <tr><td>Histogram</td><td>Phân phối tần suất của một biến</td></tr>
  <tr><td>Box Plot</td><td>Hộp thống kê (Q1–Q3, median, outlier)</td></tr>
  <tr><td>Violin</td><td>Kết hợp box plot + phân phối mật độ (KDE)</td></tr>
  <tr><td>Heatmap</td><td>Ma trận tương quan giữa nhiều biến</td></tr>
  <tr><td>Z-score Scatter</td><td>Phát hiện ngoại lệ bằng Modified Z-score</td></tr>
  <tr><td>Pairplot</td><td>Ma trận biểu đồ phân tán giữa tất cả cặp biến</td></tr>
  <tr><td>Hist-Box</td><td>Histogram kết hợp Box plot trên cùng trục</td></tr>
  <tr><td>Pie Chart</td><td>Tỷ lệ phần trăm theo danh mục</td></tr>
  <tr><td>Area Chart</td><td>Diện tích dưới đường xu hướng theo thời gian</td></tr>
  <tr><td>Parallel Coords</td><td>So sánh nhiều biến cùng lúc qua trục song song</td></tr>
  <tr><td>SPC Control Chart</td><td>Biểu đồ kiểm soát I-MR (Statistical Process Control)</td></tr>
  <tr><td>Rolling Band</td><td>Đường trung bình động với dải ± độ lệch chuẩn</td></tr>
  <tr><td>MW Binned Scatter</td><td>Scatter phân nhóm theo dải công suất MW</td></tr>
  <tr><td>100% Stacked Bar</td><td>Biểu đồ cột tỷ lệ 100% so sánh cấu trúc theo nhóm</td></tr>
</table>

<h3>🔄 Drift Monitor — Phát hiện lệch chuẩn</h3>
<table>
  <tr><th>Thuật toán</th><th>Mô tả</th></tr>
  <tr><td>EWMA</td><td>Trung bình động có trọng số hàm mũ — nhạy cảm với thay đổi nhỏ, liên tục</td></tr>
  <tr><td>CUSUM</td><td>Tích luỹ sai số — phát hiện drift tích luỹ theo một hướng</td></tr>
  <tr><td>Trendline</td><td>Hồi quy tuyến tính theo khoảng thời gian — xác nhận xu hướng dài hạn</td></tr>
  <tr><td>Min/Max Varying</td><td>Theo dõi biến động biên độ min/max — phát hiện dao động bất thường theo mức tải cố định</td></tr>
  <tr><td>Mann-Kendall Trend</td><td>Kiểm định xu hướng phi tham số — ít nhất 3 tháng dữ liệu</td></tr>
</table>
<div class="note">
  Chức năng <b>Min/Max Varying</b> và <b>Trend</b> tự động phân nhóm tải (<i>low load / high load</i>)
  dựa trên ngưỡng MW trước khi phân tích.
</div>

<h3>🔮 Predict — Dự báo AAKR</h3>
<ul>
  <li><b>AAKR (Auto-Associative Kernel Regression)</b>: mô hình dự báo dựa trên dữ liệu lịch sử, phát hiện sai lệch giữa giá trị thực và dự báo.</li>
  <li>Cho phép chọn biến đầu vào, biến đầu ra, và khoảng thời gian dự báo.</li>
</ul>

<h3>📊 Analysis Report</h3>
<ul>
  <li>Tổng hợp thống kê mô tả (mean, std, min, max, percentile) toàn bộ DataFrame.</li>
  <li>Xuất báo cáo phân tích dạng bảng.</li>
</ul>
"""

# ── Tab 3: ML Application ───────────────────────────────────
_HTML_ML = _STYLE + """
<h2>Tab — ML Application</h2>
<p>Quy trình xây dựng mô hình hồi quy gồm <b>7 bước tuần tự</b>, cuộn ngang để xem tất cả.</p>

<table>
  <tr><th>Bước</th><th>Tên</th><th>Chức năng</th></tr>
  <tr>
    <td><b>Step 1</b></td>
    <td>Data Collection</td>
    <td>Tải dữ liệu thô (<code>Rawdata</code>) từ CSV/Excel hoặc lấy từ Tab Data Analyzing</td>
  </tr>
  <tr>
    <td><b>Step 2</b></td>
    <td>Data Profile</td>
    <td>Thống kê mô tả tổng quan, phân phối và tương quan các biến (<code>raw_df</code>)</td>
  </tr>
  <tr>
    <td><b>Step 3</b></td>
    <td>Outlier Detection</td>
    <td>
      Phát hiện ngoại lệ bằng 5 phương pháp:<br>
      IQR, Z-score, Modified Z-score, Isolation Forest, LOF<br>
      → Kết quả lưu vào <code>cleaned_df</code>
    </td>
  </tr>
  <tr>
    <td><b>Step 4</b></td>
    <td>Feature Visualization</td>
    <td>Vẽ line chart từng biến để kiểm tra chất lượng sau làm sạch</td>
  </tr>
  <tr>
    <td><b>Step 5</b></td>
    <td>Train Model</td>
    <td>
      Huấn luyện mô hình hồi quy:<br>
      <b>Single</b> (1 biến đầu ra) hoặc <b>Multi</b> (nhiều biến đầu ra)<br>
      Tách train/test theo tỉ lệ tuỳ chọn
    </td>
  </tr>
  <tr>
    <td><b>Step 6</b></td>
    <td>Model Compare</td>
    <td>So sánh kết quả các mô hình đã huấn luyện (R², RMSE, MAE)</td>
  </tr>
  <tr>
    <td><b>Step 7</b></td>
    <td>Inference & Deploy</td>
    <td>Tải mô hình đã lưu, dự báo trên dữ liệu mới, xuất kết quả</td>
  </tr>
</table>

<div class="note">
  <b>Lưu ý:</b> Dữ liệu được truyền từ Tab <i>Data Analyzing</i> sang Tab ML qua callback
  <code>get_current_df_for_ml()</code> — phải tải dữ liệu ở Tab 1 trước khi dùng Tab ML.
</div>
"""

# ── Tab 4: Monitoring System ────────────────────────────────
_HTML_MONITORING = _STYLE + """
<h2>Tab — Monitoring System</h2>
<p>
  Lưới ô (<i>grid cells</i>) tuỳ chỉnh để theo dõi thiết bị.
  Mỗi ô có thể chứa biểu đồ, số liệu, chú thích hoặc báo cáo vận hành.
</p>

<h3>Loại ô (Cell Types)</h3>
<table>
  <tr><th>Loại ô</th><th>Chức năng</th></tr>
  <tr><td>Chart Cell</td><td>Nhúng biểu đồ Plotly từ Tab Plotly vào ô giám sát</td></tr>
  <tr><td>Plotly Embed</td><td>Hiển thị biểu đồ Plotly tương tác trực tiếp</td></tr>
  <tr><td>Text Cell</td><td>Ghi chú, nhãn, tiêu đề tự do</td></tr>
  <tr><td>Placeholder</td><td>Ô trống — chỗ trống trong lưới</td></tr>
  <tr><td>Image Cell</td><td>Hiển thị ảnh tĩnh từ biểu đồ đã xuất</td></tr>
</table>

<h3>Báo cáo vận hành (Operating Report)</h3>
<table>
  <tr><th>Module</th><th>Phát hiện</th></tr>
  <tr><td>Oscillation Detector</td><td>Dao động bất thường (biên độ, tần suất)</td></tr>
  <tr><td>Shock Detector</td><td>Xung đột ngột vượt ngưỡng</td></tr>
  <tr><td>Trend Detector</td><td>Xu hướng tăng/giảm kéo dài</td></tr>
  <tr><td>Local Trend Detector</td><td>Xu hướng cục bộ trong khoảng thời gian ngắn</td></tr>
</table>

<h3>Xuất báo cáo</h3>
<ul>
  <li>Xuất PDF hoặc Excel từ nút <b>Export Report</b>.</li>
  <li>Báo cáo bao gồm bảng số liệu, biểu đồ và kết quả phân tích vận hành.</li>
</ul>
"""

# ── Tab 5: DataFrames trong code ───────────────────────────
_HTML_DATAFRAMES = _STYLE + """
<h2>Danh sách DataFrame & đối tượng dữ liệu trong code</h2>
<p>Bảng dưới liệt kê tất cả DataFrame / đối tượng lưu dữ liệu quan trọng,
   vị trí trong code và mục đích sử dụng.</p>

<table>
  <tr>
    <th>Tên</th>
    <th>Nơi khai báo</th>
    <th>Kiểu</th>
    <th>Mô tả</th>
  </tr>
  <tr>
    <td><code>final_df</code></td>
    <td><code>project1_main.py → MainWindow</code></td>
    <td>pandas DataFrame</td>
    <td>
      DataFrame <b>chính</b> của toàn ứng dụng. Được load từ tất cả file
      <code>.parquet</code> trong thư mục <code>parquet_data/</code>,
      sắp xếp theo <code>Datetime</code>. Cột đầu tiên luôn là <code>Datetime</code>.
      Được đẩy tới tất cả các tab khi gọi <code>set_final_df()</code>.
    </td>
  </tr>
  <tr>
    <td><code>data_manager</code></td>
    <td><code>project1_main.py → MainWindow</code></td>
    <td>DataManager (DuckDB)</td>
    <td>
      Query engine <b>không load hết RAM</b>. Đọc trực tiếp các file
      <code>.parquet</code> qua DuckDB với <i>predicate pushdown</i> và
      <i>column pushdown</i>. Dùng khi cần query theo khoảng thời gian hoặc
      chỉ một số cột cụ thể. Lấy bằng <code>main_window.get_data_manager()</code>.
    </td>
  </tr>
  <tr>
    <td><code>dataframes</code></td>
    <td><code>project1_main.py → MainWindow</code></td>
    <td>dict[str, DataFrame]</td>
    <td>
      Từ điển lưu nhiều DataFrame, key là tên folder đã tải
      (<i>VD: "athuy", "duchien"</i>). Truy xuất qua
      <code>get_df_by_name(folder_name)</code>.
    </td>
  </tr>
  <tr>
    <td><code>df_full</code></td>
    <td><code>load_data.py → PreviewWidget</code></td>
    <td>pandas DataFrame</td>
    <td>
      Bản sao của <code>final_df</code> dùng <b>riêng trong widget xem bảng</b>
      (Home tab). Hỗ trợ lọc theo datetime mà không ảnh hưởng dữ liệu gốc.
      Được cập nhật khi người dùng dùng Clean Data, Delete Features, hay Insert Formula.
    </td>
  </tr>
  <tr>
    <td><code>merged_df</code></td>
    <td><code>load_data.py → process_one_subfolder()</code></td>
    <td>pandas DataFrame (tạm thời)</td>
    <td>
      DataFrame trung gian trong quá trình tải. Gộp tất cả file CSV/Excel
      trong một subfolder, thêm cột <code>Datetime</code>, loại bỏ cột
      <code>Date</code>, <code>Time</code>, xử lý trùng cột. Sau khi ghi
      <code>.parquet</code> xong thì giải phóng.
    </td>
  </tr>
  <tr>
    <td><code>Rawdata / raw_df</code></td>
    <td><code>ML_TAB → MLApplicationTab</code></td>
    <td>pandas DataFrame</td>
    <td>
      Dữ liệu thô tải vào ở <b>Step 1</b> của tab ML. Chưa qua xử lý ngoại lệ
      hay làm sạch. <code>Rawdata</code> là đối tượng widget, <code>raw_df</code>
      là DataFrame thực.
    </td>
  </tr>
  <tr>
    <td><code>cleaned_df</code></td>
    <td><code>ML_TAB → MLApplicationTab</code></td>
    <td>pandas DataFrame</td>
    <td>
      DataFrame sau khi qua <b>Step 3</b> (phát hiện và loại bỏ ngoại lệ).
      Được dùng làm đầu vào cho Step 4 (visualization) và Step 5 (train model).
    </td>
  </tr>
  <tr>
    <td><code>df_provider()</code></td>
    <td><code>master_window.py → ML_Tab, Monitoring_Tab</code></td>
    <td>callable → DataFrame</td>
    <td>
      Hàm callback trả về <code>final_df</code> tại thời điểm gọi.
      Được truyền vào Tab ML và Tab Monitoring khi khởi tạo, đảm bảo
      luôn lấy được dữ liệu mới nhất từ Tab 1.
    </td>
  </tr>
  <tr>
    <td>Parquet files</td>
    <td><code>{folder}/parquet_data/*.parquet</code></td>
    <td>file trên disk</td>
    <td>
      Lưu trữ lâu dài trên đĩa. Mỗi subfolder → 1 file <code>.parquet</code>
      nén <code>zstd</code>. Đây là nguồn dữ liệu gốc mà cả
      <code>pd.read_parquet()</code> lẫn <code>DataManager</code> đọc từ đó.
    </td>
  </tr>
</table>

<h3>Sơ đồ quan hệ</h3>
<pre style="background:#f0f7ff;padding:12px;border-radius:6px;font-size:13px;">
CSV/Excel
   │
   ▼ process_one_subfolder()
merged_df  ──────►  parquet_data/*.parquet  ◄── DataManager (DuckDB query)
                          │
                          ▼ pd.read_parquet()
                       final_df  ──► dataframes[folder_name]
                          │
              ┌───────────┼────────────┐
              ▼           ▼            ▼
          df_full    df_provider()  Monitoring
        (PreviewWidget) (ML Tab)    (plot_provider)
</pre>
"""

# ── Tab 6: Mẹo & FAQ ──────────────────────────────────────
_HTML_TIPS = _STYLE + """
<h2>Mẹo sử dụng & Câu hỏi thường gặp</h2>

<h3>Tải dữ liệu nhanh hơn</h3>
<ul>
  <li>Subfolder nào đã được ghi vào <code>metadata.json</code> sẽ <b>bỏ qua</b>
      không đọc lại CSV — chỉ load parquet. Nhanh hơn 10–50× so với đọc CSV.</li>
  <li>Nếu muốn tải lại từ đầu: xoá file <code>metadata.json</code> và
      thư mục <code>parquet_data/</code> trong folder dữ liệu.</li>
</ul>

<h3>Dữ liệu quá lớn (hàng triệu dòng)</h3>
<ul>
  <li>Dùng <code>DataManager.query(start, end, columns)</code> thay vì
      làm việc trực tiếp với <code>final_df</code> — chỉ đọc phần cần thiết.</li>
  <li>Lấy DataManager: <code>main_window.get_data_manager()</code>.</li>
</ul>

<h3>Cột Datetime không nhận dạng được</h3>
<ul>
  <li>Kiểm tra định dạng ngày: chọn đúng <b>dd/MM/yyyy</b> hoặc <b>MM/dd/yyyy</b>
      ở combobox trước khi nhấn Load Data.</li>
  <li>Nếu file CSV đã có cột <code>Datetime</code> sẵn, ứng dụng sẽ dùng luôn
      mà không cần ghép từ <code>Date</code> + <code>Time</code>.</li>
</ul>

<h3>Công thức (Formula Module)</h3>
<ul>
  <li><b>Build Formula</b>: viết biểu thức Python (<code>col_A + col_B * 0.95</code>),
      kết quả được thêm vào <code>df_full</code> và <code>final_df</code>.</li>
  <li><b>Insert Formula</b>: áp dụng lại công thức đã lưu từ thư mục
      <code>formulas/</code>.</li>
</ul>

<h3>Drift Monitor không hiện kết quả</h3>
<ul>
  <li>Đảm bảo đã chọn ít nhất 1 biến và khoảng thời gian hợp lệ.</li>
  <li>Thuật toán <b>Mann-Kendall</b> cần <b>ít nhất 3 tháng</b> dữ liệu.</li>
  <li>Tham số drift được lưu trong <code>drift_params.json</code> ở thư mục gốc.</li>
</ul>

<h3>Tab ML không thấy dữ liệu</h3>
<ul>
  <li>Phải tải dữ liệu ở Tab <b>Data Analyzing</b> trước — Tab ML lấy dữ liệu
      qua callback <code>get_current_df_for_ml()</code>.</li>
</ul>

<h3>Đóng gói ứng dụng (PyInstaller)</h3>
<ul>
  <li>Dùng <code>--onedir</code> (không dùng <code>--onefile</code>) để khởi động nhanh hơn.</li>
  <li>Không exclude <code>pyarrow</code> vì code dùng <code>pd.read_parquet()</code>.</li>
</ul>
"""


# ─────────────────────────────────────────────────────────────
#  Dialog chính
# ─────────────────────────────────────────────────────────────

class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hướng dẫn sử dụng — F1")
        self.setMinimumSize(860, 620)
        self.resize(960, 700)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Tiêu đề
        title = QLabel("📖  Hướng dẫn sử dụng  —  Multi Project Dashboard")
        title.setStyleSheet(
            "font-size: 17px; font-weight: bold; color: #1a56c4; padding: 4px 0;"
        )
        layout.addWidget(title)

        # Tab nội dung
        tabs = QTabWidget()
        layout.addWidget(tabs)

        sections = [
            ("🏠 Tổng quan",         _HTML_OVERVIEW),
            ("📊 Data Analyzing",    _HTML_DATA),
            ("🤖 ML Application",    _HTML_ML),
            ("📡 Monitoring",        _HTML_MONITORING),
            ("🗃 DataFrames",        _HTML_DATAFRAMES),
            ("💡 Mẹo & FAQ",         _HTML_TIPS),
        ]
        for title_tab, html in sections:
            browser = QTextBrowser()
            browser.setOpenExternalLinks(False)
            browser.setHtml(html)
            tabs.addTab(browser, title_tab)

        # Nút đóng
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton("Đóng  (Esc)")
        btn_close.setFixedWidth(120)
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        # Phím Esc đóng dialog
        QShortcut(QKeySequence("Escape"), self, activated=self.accept)
