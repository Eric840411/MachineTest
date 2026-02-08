"""機器類型配置模組 - 從文件夾結構載入不同機器類型的測試流程"""
import json
import logging
from pathlib import Path
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field


@dataclass
class MachineTestFlow:
    """單一測試流程步驟"""
    name: str
    description: str
    enabled: bool = True
    timeout: float = 10.0
    retry_count: int = 3
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MachineProfile:
    """機器類型配置檔案"""
    name: str
    description: str
    enabled: bool = True
    
    # 識別規則（用於自動匹配）
    match_rules: Dict[str, Any] = field(default_factory=dict)
    # 例如: {"gameid": ["osmbwjl"], "game_title_code_pattern": ["DFDC", "JJBX"]}
    
    # 測試流程步驟
    test_flows: List[MachineTestFlow] = field(default_factory=list)
    
    # 按鈕配置
    button_selectors: Dict[str, str] = field(default_factory=dict)
    # 例如: {"spin": "button.spin", "bet": "button.bet"}
    
    # 按鈕測試配置（支持高亮檢測）
    button_test_config: Dict[str, Any] = field(default_factory=dict)
    # 例如: {"highlight_detection": {...}, "buttons": [...]}
    
    # 視頻檢測配置
    video_detection: Dict[str, Any] = field(default_factory=dict)
    
    # 特殊配置
    special_config: Dict[str, Any] = field(default_factory=dict)
    
    # 文件夾路徑
    folder_path: Optional[Path] = None


@dataclass
class MachineProfiles:
    """所有機器類型配置"""
    profiles: Dict[str, MachineProfile] = field(default_factory=dict)
    default_profile: Optional[str] = None
    profiles_dir: Optional[Path] = None


def load_machine_profile_from_folder(profile_dir: Path) -> Optional[MachineProfile]:
    """
    從文件夾載入單個機器類型配置
    
    Args:
        profile_dir: 機器類型配置文件夾路徑
        
    Returns:
        機器類型配置，如果載入失敗則返回 None
    """
    config_file = profile_dir / "config.json"
    
    if not config_file.exists():
        logging.warning(f"[MachineProfiles] 配置文件不存在: {config_file}")
        return None
    
    try:
        with config_file.open("r", encoding="utf-8") as f:
            profile_data = json.load(f)
        
        # 解析測試流程
        test_flows = []
        flows_file = profile_dir / "test_flows.json"
        if flows_file.exists():
            with flows_file.open("r", encoding="utf-8") as f:
                flows_data = json.load(f)
                for flow_data in flows_data.get("test_flows", flows_data.get("flows", [])):
                    # 取得 config，若不存在則建立空 dict
                    flow_config = flow_data.get("config", {})
                    
                    # 如果 image_comparison 在頂層（不在 config 內），合併進 config
                    if "image_comparison" in flow_data and "image_comparison" not in flow_config:
                        flow_config["image_comparison"] = flow_data["image_comparison"]
                    
                    flow = MachineTestFlow(
                        name=flow_data.get("name", ""),
                        description=flow_data.get("description", ""),
                        enabled=flow_data.get("enabled", True),
                        timeout=flow_data.get("timeout", 10.0),
                        retry_count=flow_data.get("retry_count", 3),
                        config=flow_config
                    )
                    test_flows.append(flow)
        else:
            # 如果沒有 test_flows.json，從 config.json 讀取
            for flow_data in profile_data.get("test_flows", []):
                flow_config = flow_data.get("config", {})
                if "image_comparison" in flow_data and "image_comparison" not in flow_config:
                    flow_config["image_comparison"] = flow_data["image_comparison"]
                
                flow = MachineTestFlow(
                    name=flow_data.get("name", ""),
                    description=flow_data.get("description", ""),
                    enabled=flow_data.get("enabled", True),
                    timeout=flow_data.get("timeout", 10.0),
                    retry_count=flow_data.get("retry_count", 3),
                    config=flow_config
                )
                test_flows.append(flow)
        
        profile = MachineProfile(
            name=profile_data.get("name", profile_dir.name),
            description=profile_data.get("description", ""),
            enabled=profile_data.get("enabled", True),
            match_rules=profile_data.get("match_rules", {}),
            test_flows=test_flows,
            button_selectors=profile_data.get("button_selectors", {}),
            button_test_config=profile_data.get("button_test_config", {}),
            video_detection=profile_data.get("video_detection", {}),
            special_config=profile_data.get("special_config", {}),
            folder_path=profile_dir
        )
        
        logging.info(f"[MachineProfiles] 載入機器類型配置: {profile.name} (來自 {profile_dir.name})")
        return profile
        
    except Exception as e:
        logging.error(f"[MachineProfiles] 載入配置失敗 {profile_dir.name}: {e}")
        return None


def load_machine_profiles(base_dir: Path) -> MachineProfiles:
    """
    從文件夾結構載入所有機器類型配置
    
    預期文件夾結構:
    machine_profiles/
        DFDC/
            config.json
            test_flows.json (可選)
        JJBX/
            config.json
            test_flows.json (可選)
        JJBXGRAND/
            config.json
            test_flows.json (可選)
        default/
            config.json
            test_flows.json (可選)
    """
    profiles_dir = base_dir / "machine_profiles"
    
    if not profiles_dir.exists():
        logging.warning(f"[MachineProfiles] 機器類型配置文件夾不存在: {profiles_dir}")
        return MachineProfiles(profiles_dir=profiles_dir)
    
    profiles = {}
    default_profile = None
    
    # 遍歷所有子文件夾
    for profile_dir in profiles_dir.iterdir():
        if not profile_dir.is_dir():
            continue
        
        # 跳過隱藏文件夾
        if profile_dir.name.startswith("."):
            continue
        
        profile = load_machine_profile_from_folder(profile_dir)
        if profile:
            profiles[profile_dir.name.upper()] = profile
            
            # 檢查是否為默認配置
            if profile_dir.name.lower() == "default":
                default_profile = profile_dir.name.upper()
    
    # 如果沒有找到 default，使用第一個配置作為默認
    if not default_profile and profiles:
        default_profile = list(profiles.keys())[0]
        logging.info(f"[MachineProfiles] 未找到 default 配置，使用 {default_profile} 作為默認")
    
    result = MachineProfiles(
        profiles=profiles,
        default_profile=default_profile,
        profiles_dir=profiles_dir
    )
    
    logging.info(f"[MachineProfiles] 載入 {len(profiles)} 個機器類型配置")
    return result


def extract_keyword_from_game_title_code(game_title_code: str) -> Optional[str]:
    """
    從 game_title_code 中提取關鍵字
    
    例如: "873-RISINGROCKETS-0140" -> "RISINGROCKETS"
          "873-DFDC-0140" -> "DFDC"
    
    Args:
        game_title_code: 遊戲標題代碼
        
    Returns:
        提取的關鍵字，如果無法提取則返回 None
    """
    if not game_title_code:
        return None
    
    # 嘗試用 "-" 分割，通常格式為 "數字-關鍵字-數字"
    parts = game_title_code.split("-")
    if len(parts) >= 2:
        # 取中間部分（通常是關鍵字）
        keyword = parts[1].strip().upper()
        if keyword:
            return keyword
    
    # 如果分割失敗，嘗試直接使用整個字符串（去除數字）
    import re
    # 移除開頭和結尾的數字
    keyword = re.sub(r'^\d+-?', '', game_title_code)
    keyword = re.sub(r'-?\d+$', '', keyword)
    keyword = keyword.strip('-').strip().upper()
    
    if keyword:
        return keyword
    
    return None


def match_machine_profile(
    profiles: MachineProfiles,
    url: str,
    game_title_code: Optional[str] = None,
    gameid: Optional[str] = None,
    machine_type: Optional[str] = None,
    require_game_title_code: bool = True
) -> Optional[MachineProfile]:
    """
    根據 URL、game_title_code、gameid 或 machine_type 匹配機器類型配置
    
    匹配優先級：
    1. 手動指定的 machine_type（最高優先級）
    2. 從 game_title_code 提取關鍵字匹配文件夾名稱
    3. match_rules 中的 game_title_code_pattern 匹配（需要 game_title_code）
    4. match_rules 中的 gameid 匹配（僅當 require_game_title_code=False 時）
    5. match_rules 中的 url_pattern 匹配（僅當 require_game_title_code=False 時）
    
    Args:
        profiles: 機器類型配置
        url: 遊戲 URL
        game_title_code: 遊戲標題代碼（例如 "873-RISINGROCKETS-0140"）
        gameid: 遊戲 ID（從 URL 中提取）
        machine_type: 手動指定的機器類型（優先級最高）
        require_game_title_code: 是否要求必須有 game_title_code 才能匹配（預設 True）
        
    Returns:
        匹配的機器類型配置，如果沒有匹配則返回 None
    """
    # 優先級 1: 使用手動指定的機器類型
    if machine_type:
        machine_type_upper = machine_type.upper()
        if machine_type_upper in profiles.profiles:
            logging.info(f"[MachineProfiles] 使用手動指定的機器類型: {machine_type_upper}")
            return profiles.profiles[machine_type_upper]
        else:
            logging.warning(f"[MachineProfiles] 手動指定的機器類型不存在: {machine_type_upper}")
    
    # 如果要求必須有 game_title_code 但沒有提供，直接返回 None
    if require_game_title_code and not game_title_code:
        logging.warning(f"[MachineProfiles] 要求必須有 game_title_code 才能匹配，但未提供 game_title_code")
        return None
    
    # 優先級 2: 從 game_title_code 提取關鍵字匹配文件夾名稱
    if game_title_code:
        keyword = extract_keyword_from_game_title_code(game_title_code)
        if keyword:
            # 直接匹配文件夾名稱（不區分大小寫）
            for key, profile in profiles.profiles.items():
                if key.upper() == keyword.upper() and profile.enabled:
                    logging.info(f"[MachineProfiles] 從 game_title_code 匹配到機器類型: {key} (關鍵字: {keyword})")
                    return profile
        
        # 優先級 3: 檢查 game_title_code 模式匹配
        for key, profile in profiles.profiles.items():
            if not profile.enabled:
                continue
            
            match_rules = profile.match_rules
            if "game_title_code_pattern" in match_rules:
                patterns = match_rules["game_title_code_pattern"]
                if isinstance(patterns, list):
                    for pattern in patterns:
                        if pattern in game_title_code:
                            logging.info(f"[MachineProfiles] 匹配到機器類型: {key} (pattern: {pattern})")
                            return profile
    
    # 如果要求必須有 game_title_code，則不進行後續匹配
    if require_game_title_code:
        logging.warning(f"[MachineProfiles] 未找到匹配的機器類型配置（要求必須有 game_title_code）")
        return None
    
    # 從 URL 提取 gameid（如果未提供）
    if not gameid and url:
        try:
            # 嘗試從 URL 參數中提取 gameid
            if "gameid=" in url:
                gameid = url.split("gameid=")[1].split("&")[0]
        except:
            pass
    
    # 優先級 4: 檢查 gameid 匹配（僅當不要求 game_title_code 時）
    if gameid:
        for key, profile in profiles.profiles.items():
            if not profile.enabled:
                continue
            
            match_rules = profile.match_rules
            if "gameid" in match_rules:
                gameid_list = match_rules["gameid"]
                if isinstance(gameid_list, list) and gameid in gameid_list:
                    logging.info(f"[MachineProfiles] 匹配到機器類型: {key} (gameid: {gameid})")
                    return profile
    
    # 優先級 5: 檢查 URL 模式匹配（僅當不要求 game_title_code 時）
    for key, profile in profiles.profiles.items():
        if not profile.enabled:
            continue
        
        match_rules = profile.match_rules
        if "url_pattern" in match_rules:
            patterns = match_rules["url_pattern"]
            if isinstance(patterns, list):
                for pattern in patterns:
                    if pattern in url:
                        logging.info(f"[MachineProfiles] 匹配到機器類型: {key} (url_pattern: {pattern})")
                        return profile
    
    # 如果沒有匹配，返回 None
    logging.warning(f"[MachineProfiles] 未找到匹配的機器類型配置")
    return None
