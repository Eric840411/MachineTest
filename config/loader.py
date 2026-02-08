"""配置讀取模組"""
import json
import csv
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any

from .models import GameConfig


def load_games(base_dir: Path) -> List[GameConfig]:
    """
    讀取 game_config.json 和 game_title_codes.csv，配對後返回 GameConfig 列表
    """
    # 讀取遊戲清單
    try:
        with (base_dir / "game_config.json").open("r", encoding="utf-8") as f:
            cfg_list = json.load(f)
        logging.info(f"[Config] 讀取 game_config.json 成功，筆數={len(cfg_list)}")
    except Exception as e:
        logging.error(f"[Config] 讀取 game_config.json 失敗: {e}")
        raise

    # 讀取 game_title_codes.csv
    game_title_codes: List[str] = []
    csv_path = base_dir / "game_title_codes.csv"
    if csv_path.exists():
        try:
            with csv_path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    code = row.get("game_title_code", "").strip()
                    if code:  # 只添加非空值
                        game_title_codes.append(code)
            logging.info(f"[Config] 讀取 game_title_codes.csv 成功，共 {len(game_title_codes)} 個代碼")
        except Exception as e:
            logging.warning(f"[Config] 讀取 game_title_codes.csv 失敗: {e}")
    else:
        logging.warning(f"[Config] game_title_codes.csv 不存在，將使用空值")

    # 配對 game_config.json 和 game_title_codes.csv
    games: List[GameConfig] = []
    code_index = 0  # CSV 索引計數器
    for raw in cfg_list:
        if raw.get("enabled", True):
            # 從 CSV 中按順序取得 game_title_code
            game_title_code = None
            if code_index < len(game_title_codes):
                game_title_code = game_title_codes[code_index]
                code_index += 1
                logging.info(f"[Config] 配對 game_title_code: {game_title_code} -> URL: {raw.get('url', '')[:50]}...")
            else:
                logging.warning(f"[Config] CSV 中的 game_title_code 數量不足，第 {code_index + 1} 個配置將使用空值")
            
            games.append(
                GameConfig(
                    url=raw.get("url"),
                    game_title_code=game_title_code,
                    machine_type=raw.get("machine_type"),  # 可選的機器類型
                    enabled=True,
                )
            )
    
    return games


def load_csv_codes(base_dir: Path) -> List[str]:
    """
    讀取 game_title_codes.csv，返回所有機器號列表
    
    Returns:
        機器號列表，例如 ["873-JJBX-0004", "873-JJBX-0005", ...]
    """
    csv_path = base_dir / "game_title_codes.csv"
    codes: List[str] = []
    
    if not csv_path.exists():
        logging.warning(f"[Config] game_title_codes.csv 不存在")
        return codes
    
    try:
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row.get("game_title_code", "").strip()
                if code:
                    codes.append(code)
        logging.info(f"[Config] 讀取 game_title_codes.csv 成功，共 {len(codes)} 個機器號")
    except Exception as e:
        logging.warning(f"[Config] 讀取 game_title_codes.csv 失敗: {e}")
    
    return codes


def load_actions(base_dir: Path) -> Tuple[Dict[str, List[str]], Dict[str, Tuple[List[str], bool]]]:
    """
    讀取 actions.json，返回 keyword_actions 和 machine_actions
    """
    with (base_dir / "actions.json").open("r", encoding="utf-8") as f:
        actions = json.load(f)
    
    keyword_actions: Dict[str, List[str]] = actions.get("keyword_actions", {})
    # 將 {"kw": {"positions":[...], "click_take":true}} 轉成 {"kw": ([...], True)}
    machine_actions: Dict[str, Tuple[List[str], bool]] = {
        kw: (info.get("positions", []), bool(info.get("click_take", False)))
        for kw, info in actions.get("machine_actions", {}).items()
    }
    
    return keyword_actions, machine_actions


def load_test_service_config(base_dir: Path) -> Dict[str, Any]:
    """讀取測試服務配置"""
    test_config_path = base_dir / "test_config.json"
    
    if not test_config_path.exists():
        return {}
    
    try:
        with test_config_path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        return raw.get("test_service", {})
    except Exception as e:
        logging.warning(f"[Config] 讀取測試服務配置失敗: {e}")
        return {}
