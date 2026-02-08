"""通用工具函數"""
import hashlib
from pathlib import Path


def file_md5(path: Path) -> str:
    """計算檔案 MD5（逐塊讀取，避免占用過多記憶體）"""
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

