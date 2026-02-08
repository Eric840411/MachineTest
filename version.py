"""
版本號管理

格式: v主版.次版.修補
- 主版 (MAJOR): 重大架構變更、不相容更新
- 次版 (MINOR): 新增功能、模組
- 修補 (PATCH): 修復 Bug、微調

更新時修改此檔案，並在 changelogs/ 新增對應的 .md 檔案。
app.py 和 Lark 報告會自動讀取版本號。
"""

__version__ = "1.1.2"
__version_name__ = "README 同步更新"


def get_version_string() -> str:
    """回傳格式化版本字串，例如 'v1.0.0 (正式版)'"""
    return f"v{__version__} ({__version_name__})"


def get_version_info() -> dict:
    """回傳版本資訊字典"""
    return {
        "version": __version__,
        "name": __version_name__,
        "display": get_version_string(),
    }
