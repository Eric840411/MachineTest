"""
主執行程序 - 協調所有模組的執行順序

這個文件負責：
- 初始化環境和日誌
- 啟動熱鍵監聽器
- 讀取配置（game_config.json, actions.json 等）
- 為每個遊戲創建 GameRunner 實例（來自 game/game_runner.py）
- 啟動所有遊戲執行器並等待完成ㄋ
"""
import sys
import signal
import logging
import threading
import numpy as np
from pathlib import Path

from version import get_version_string
from config import load_games, load_csv_codes, load_actions, load_test_config, load_test_service_config
from config.machine_profiles import load_machine_profiles, match_machine_profile
from notification import LarkClient
from hotkey import start_hotkey_listener, stop_event
from game import GameRunner

# 測試相關導入
try:
    from qa.test_manager import TestTaskManager
    from qa.test_service import TestServiceClient
except ImportError:
    TestTaskManager = None
    TestServiceClient = None

# BASE_DIR: 若是打包成 .exe，取可執行檔所在資料夾；否則取 .py 檔案所在資料夾
BASE_DIR = Path(getattr(sys, "frozen", False) and Path(sys.executable).parent or Path(__file__).resolve().parent)

# 載入 .env（LARK Webhook 等）
from dotenv import load_dotenv
import os
load_dotenv(BASE_DIR / "dotenv.env")
LARK_WEBHOOK = os.getenv("LARK_WEBHOOK_URL")

# 設定 logging 到終端
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def handle_interrupt(sig, frame):
    """Ctrl+C 時將 stop_event 設為 True，讓各執行緒優雅退出"""
    print("\n🛑 收到 Ctrl+C，中止中…")
    stop_event.set()

signal.signal(signal.SIGINT, handle_interrupt)


def main():
    """
    主執行程序：
    1. 初始化日誌和環境變量
    2. 啟動熱鍵監聽器
    3. 讀取配置（config/loader.py）
    4. 初始化通知客戶端（notification/lark.py）
    5. 為每個遊戲創建 GameRunner（game/game_runner.py）
    6. 啟動所有遊戲執行器
    7. 等待所有執行完成
    """
    # 0. 顯示版本資訊
    ver = get_version_string()
    logging.info(f"========================================")
    logging.info(f"  Machine Test  {ver}")
    logging.info(f"========================================")
    
    # 1. 啟動熱鍵監聯器
    start_hotkey_listener()
    
    # 2. 讀取配置
    logging.info("[Runner] 開始讀取設定檔")
    games = load_games(BASE_DIR)
    keyword_actions, machine_actions = load_actions(BASE_DIR)
    test_config = load_test_config(BASE_DIR)
    
    # 2.5. 讀取機器類型配置
    machine_profiles = load_machine_profiles(BASE_DIR)
    logging.info(f"[Runner] 載入 {len(machine_profiles.profiles)} 個機器類型配置")
    
    if not games:
        logging.warning("[Runner] 沒有 enabled 的機台，程式結束")
        return
    
    # 2.5. 檢查測試模式
    test_scenario = None
    if test_config.test_mode and test_config.active_scenario:
        if test_config.active_scenario in test_config.scenarios:
            test_scenario = test_config.scenarios[test_config.active_scenario]
            logging.info(f"[Runner] 🧪 測試模式已啟用: {test_scenario.name}")
        else:
            logging.warning(f"[Runner] 測試場景 '{test_config.active_scenario}' 不存在，使用正常模式")
    
    # 3. 初始化通知客戶端
    lark = LarkClient(LARK_WEBHOOK)
    
    # 3.5. 讀取測試服務配置
    test_service_config = load_test_service_config(BASE_DIR)
    test_service = None
    if test_service_config.get("enabled") and TestServiceClient:
        test_service = TestServiceClient(
            service_url=test_service_config.get("url"),
            api_key=test_service_config.get("api_key")
        )
        logging.info(f"[Runner] 測試服務已啟用: {test_service_config.get('url')}")
    else:
        logging.info("[Runner] 測試服務未啟用")
    
    # 3.6. 讀取 CSV 機器號，創建共享佇列
    csv_codes = load_csv_codes(BASE_DIR)
    task_manager = None
    if csv_codes and TestTaskManager:
        task_manager = TestTaskManager(csv_codes)
        logging.info(f"[Runner] 共享佇列已建立: {len(csv_codes)} 個機器號, {len(games)} 個 URL (Worker)")
    else:
        logging.info("[Runner] 沒有 CSV 機器號，將使用單機模式")
    
    # 4. 為每個 URL 創建 GameRunner 並啟動
    #    每個 URL 是一個 Worker，從共享佇列中依次取機器號測試
    threads: list[threading.Thread] = []
    logging.info(f"[Runner] 準備啟動 {len(games)} 個執行緒 (Worker)")
    
    for idx, conf in enumerate(games):
        # 如果有共享佇列，初始 game_title_code 由佇列分配（不用 load_games 配對的）
        if task_manager:
            # 清空 load_games 配對的 game_title_code，由 GameRunner 的循環控制
            conf.game_title_code = None
        else:
            # 無佇列（單機模式）：保留原始配對，但需要匹配 profile
            if conf.game_title_code:
                machine_profile = match_machine_profile(
                    machine_profiles,
                    conf.url,
                    conf.game_title_code,
                    require_game_title_code=True
                )
                if not machine_profile:
                    logging.warning(f"[Runner] 機器 {idx+1} 未匹配到任何類型配置，跳過執行")
                    continue
            else:
                logging.warning(f"[Runner] 機器 {idx+1} 無 game_title_code，跳過執行")
                continue
        
        runner = GameRunner(
            conf, 
            lark, 
            keyword_actions, 
            machine_actions, 
            test_scenario,
            test_service=test_service,
            task_manager=task_manager,
            machine_profile=None,  # 由 GameRunner 內部動態匹配
            machine_profiles=machine_profiles,  # 傳入所有 profiles 供動態匹配
        )
        
        worker_name = f"Worker-{idx+1}"
        logging.info(f"[Runner] 啟動 {worker_name} (URL: ...{conf.url[-30:]})")
        
        t = threading.Thread(
            target=runner.run,
            name=worker_name,
            daemon=True,
        )
        t.start()
        threads.append(t)
        # 錯開啟動時間，避免同時啟動造成資源競爭
        if idx < len(games) - 1:
            delay = 1.0 + np.random.random()
            logging.info(f"[Runner] 等待 {delay:.2f} 秒後啟動下一個執行緒")
            import time
            time.sleep(delay)
    
    # 5. 等待所有 Worker 完成
    if task_manager:
        logging.info(f"[Runner] 所有 Worker 已啟動，等待佇列處理完畢...")
    for t in threads:
        t.join()
    
    if task_manager:
        logging.info(f"[Runner] 所有機器測試完成! 進度: {task_manager.get_progress()}")
        history = task_manager.get_worker_history()
        for worker_id, codes in history.items():
            logging.info(f"[Runner]   {worker_id}: 完成 {len(codes)} 台 - {codes}")


if __name__ == "__main__":
    main()

