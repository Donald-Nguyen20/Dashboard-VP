# =============================================================================
# ANTIGRAVITY AUTO-DEBUG — CẤU HÌNH TELEGRAM
# =============================================================================
# Điền thông tin Telegram bot của bạn vào đây trước khi chạy.
#
# Cách lấy thông tin:
#   1. Bot Token : nhắn /newbot cho @BotFather trên Telegram
#   2. Chat ID   : nhắn /start cho @userinfobot, hoặc gọi:
#                  https://api.telegram.org/bot<TOKEN>/getUpdates
#                  sau khi đã nhắn 1 tin cho bot của bạn
# =============================================================================

TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"   # vd: "7123456789:AAFxxxxxx"
TELEGRAM_CHAT_ID   = "YOUR_CHAT_ID_HERE"     # vd: "123456789"

# --- Cài đặt debug ---
DATA_PATH      = "duchien/duchien.csv"        # file CSV mẫu để test
OUTPUT_DIR     = "antigravity_output"         # thư mục lưu ảnh đồ thị

# --- Thuật toán drift (EWMA / CUSUM) ---
EWMA_LAMBDA    = 0.2
EWMA_L         = 3.0
CUSUM_K        = 0.5
CUSUM_H        = 5.0
MIN_ANOMALY_LEN = 3                           # độ dài chuỗi anomaly tối thiểu
