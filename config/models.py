"""配置數據模型"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class GameConfig:
    """單一機台／測試目標的設定模型（來自 game_config.json 的一筆）"""

    # 基本設定
    url: str
    game_title_code: Optional[str] = None
    machine_type: Optional[str] = None  # 機器類型（DFDC、JJBX、JJBXGRAND等）

    # 一般開關
    enabled: bool = True

