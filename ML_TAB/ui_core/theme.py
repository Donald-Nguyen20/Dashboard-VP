# ui_core/theme.py
from __future__ import annotations
import os, re

class ThemeManager:
    """
    Quản lý theme: nạp base.qss + dark.qss, thay token {{...}}, áp dụng cho toàn app.
    """
    def __init__(self, app, base_dir: str):
        self.app = app
        self.base_dir = base_dir
        self.tokens = {
            # font
            "font.family": "Inter, Segoe UI, Arial",
            "font.size": "13px",
            # palette
            "bg": "#0b1220",         # nền app
            "bg.elev": "#111827",    # nền thẻ/card
            "bg.alt": "#0f172a",     # vùng container/viewport
            "text": "#e5e7eb",
            "text.muted": "#9ca3af",
            "border": "#253046",
            # accents
            "accent": "#22c55e",     # màu chủ đạo (đổi 1 chỗ)
            "accent.text": "#0b1a0f",
            # semantic
            "ok": "#16a34a",
            "warn": "#f59e0b",
            "err": "#ef4444",
            "info": "#38bdf8",
        }

    def set_accent(self, hex_color: str):
        self.tokens["accent"] = hex_color

    def _load_qss(self, rel_path: str) -> str:
        path = os.path.join(self.base_dir, rel_path)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def apply(self, theme: str = "dark"):
        css = []
        css.append(self._load_qss("assets/qss/base.qss"))
        css.append(self._load_qss(f"assets/qss/{theme}.qss"))

        merged = "\n".join(css)

        # thay {{token}} trong QSS bằng giá trị thực
        def repl(m): 
            key = m.group(1)
            return self.tokens.get(key, m.group(0))
        merged = re.sub(r"\{\{([a-zA-Z0-9\.\-_]+)\}\}", repl, merged)

        self.app.setStyleSheet(merged)
