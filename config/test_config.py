"""測試配置模型和加載器"""
import json
import logging
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass, field


@dataclass
class TestFeatures:
    """測試功能開關"""
    enable_exit_flow: bool = True
    enable_special_actions: bool = True


@dataclass
class TestScenario:
    """測試場景配置"""
    name: str
    description: str
    enabled: bool = True
    features: TestFeatures = field(default_factory=TestFeatures)
    spin_count: Optional[int] = None  # None 表示無限循環
    spin_interval: float = 1.0
    balance_threshold: int = 20000
    test_exit_after_spins: Optional[int] = None  # 測試退出流程時，在指定次數後退出
    test_flows: Optional[list] = None  # 允許執行的測試流程白名單，None 表示全部執行


@dataclass
class TestConfig:
    """測試配置"""
    test_mode: bool = False
    active_scenario: Optional[str] = None
    scenarios: Dict[str, TestScenario] = field(default_factory=dict)


def load_test_config(base_dir: Path) -> TestConfig:
    """讀取測試配置文件"""
    test_config_path = base_dir / "test_config.json"
    
    if not test_config_path.exists():
        logging.info("[TestConfig] test_config.json 不存在，使用默認配置")
        return TestConfig()
    
    try:
        with test_config_path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        
        test_mode = raw.get("test_mode", False)
        active_scenario = raw.get("active_scenario")
        
        scenarios = {}
        for key, scenario_data in raw.get("test_scenarios", {}).items():
            features_data = scenario_data.get("features", {})
            features = TestFeatures(
                enable_exit_flow=features_data.get("enable_exit_flow", True),
                enable_special_actions=features_data.get("enable_special_actions", True),
            )
            
            scenario = TestScenario(
                name=scenario_data.get("name", key),
                description=scenario_data.get("description", ""),
                enabled=scenario_data.get("enabled", True),
                features=features,
                spin_count=scenario_data.get("spin_count"),
                spin_interval=scenario_data.get("spin_interval", 1.0),
                balance_threshold=scenario_data.get("balance_threshold", 20000),
                test_exit_after_spins=scenario_data.get("test_exit_after_spins"),
                test_flows=scenario_data.get("test_flows"),
            )
            scenarios[key] = scenario
        
        config = TestConfig(
            test_mode=test_mode,
            active_scenario=active_scenario,
            scenarios=scenarios,
        )
        
        if test_mode and active_scenario:
            logging.info(f"[TestConfig] 測試模式已啟用，使用場景: {active_scenario}")
            if active_scenario in scenarios:
                scenario = scenarios[active_scenario]
                logging.info(f"[TestConfig] 場景名稱: {scenario.name}")
                logging.info(f"[TestConfig] 場景描述: {scenario.description}")
                logging.info(f"[TestConfig] 功能開關: {scenario.features}")
            else:
                logging.warning(f"[TestConfig] 場景 '{active_scenario}' 不存在")
        
        return config
        
    except Exception as e:
        logging.error(f"[TestConfig] 讀取測試配置失敗: {e}")
        return TestConfig()

