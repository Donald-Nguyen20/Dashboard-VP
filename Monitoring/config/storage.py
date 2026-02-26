"""
Config storage cho Monitoring System.
Tất cả config lưu vào folder "Monitoring storage" tại project root.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Any
from dataclasses import dataclass, asdict


def get_storage_dir() -> Path:
    """Trả về thư mục Monitoring storage (cạnh master_window.py)."""
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).resolve().parent.parent.parent

    storage = base / "Monitoring storage"
    storage.mkdir(parents=True, exist_ok=True)

    # ✅ ẨN folder trên Windows (giống các folder ẩn khác)
    try:
        if sys.platform.startswith("win"):
            import ctypes
            FILE_ATTRIBUTE_HIDDEN = 0x02
            FILE_ATTRIBUTE_SYSTEM = 0x04
            ctypes.windll.kernel32.SetFileAttributesW(str(storage), FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM)
    except Exception:
        pass

    return storage


CONFIG_FILE = "monitoring_systems.json"


@dataclass
class SystemConfig:
    """Cấu hình một hệ thống giám sát."""
    id: str
    name: str
    created_at: str = ""
    config: dict[str, Any] | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> SystemConfig:
        return cls(
            id=d.get("id", ""),
            name=d.get("name", ""),
            created_at=d.get("created_at", ""),
            config=d.get("config") or {},
        )


def load_all_systems() -> list[SystemConfig]:
    """Load danh sách hệ thống từ Monitoring storage."""
    path = get_storage_dir() / CONFIG_FILE
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [SystemConfig.from_dict(item) for item in data.get("systems", [])]
    except (json.JSONDecodeError, IOError):
        return []


def save_all_systems(systems: list[SystemConfig]) -> bool:
    """Lưu danh sách hệ thống vào Monitoring storage."""
    path = get_storage_dir() / CONFIG_FILE
    try:
        data = {"systems": [s.to_dict() for s in systems]}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except IOError:
        return False


def save_system_config(system: SystemConfig) -> bool:
    """Lưu config của một hệ thống (thêm hoặc cập nhật)."""
    systems = load_all_systems()
    new_list = [s for s in systems if s.id != system.id]
    new_list.append(system)
    return save_all_systems(new_list)
