"""
集成測試腳本 - 測試組件之間的協作

測試 GameRunner 與各個測試組件的整合
"""
import sys
import asyncio
import logging
from pathlib import Path

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


async def test_game_runner_integration():
    """測試 GameRunner 與測試組件的整合"""
    print("\n" + "="*60)
    print("測試 GameRunner 整合")
    print("="*60)
    
    try:
        from config.models import GameConfig
        from notification.lark import LarkClient
        from qa.test_manager import TestTaskManager
        from qa.test_service import TestServiceClient
        from game.game_runner import GameRunner
        
        print("[OK] 所有模組導入成功")
        
        # 創建測試配置
        test_config = GameConfig(
            url="https://example.com/test",
            game_title_code="TEST_CODE",
            enabled=True
        )
        
        # 創建測試組件
        lark = LarkClient(None)  # 不使用實際webhook
        test_service = TestServiceClient(None)  # 不使用實際服務
        task_manager = TestTaskManager(
            ["https://example.com/test"],
            ["CSV_1", "CSV_2"]
        )
        
        # 創建 GameRunner
        runner = GameRunner(
            test_config,
            lark,
            {},  # keyword_actions
            {},  # machine_actions
            None,  # bet_random_map
            None,  # test_scenario
            test_service=test_service,
            task_manager=task_manager
        )
        
        print("[OK] GameRunner 創建成功")
        
        # 檢查屬性
        assert hasattr(runner, 'test_service'), "應有 test_service 屬性"
        assert hasattr(runner, 'task_manager'), "應有 task_manager 屬性"
        assert hasattr(runner, 'console_logs'), "應有 console_logs 屬性"
        assert hasattr(runner, 'test_report'), "應有 test_report 屬性"
        print("[OK] 所有測試相關屬性存在")
        
        # 檢查測試報告結構
        report = runner.test_report
        required_keys = ["url", "csv_data", "entry_status", "console_errors",
                        "video_status", "video_message", "button_tests", "bet_results"]
        for key in required_keys:
            assert key in report, f"測試報告應包含 {key}"
        print("[OK] 測試報告結構正確")
        
        # 檢查方法
        assert hasattr(runner, 'run_full_test'), "應有 run_full_test 方法"
        assert hasattr(runner, '_test_buttons'), "應有 _test_buttons 方法"
        print("[OK] 所有測試方法存在")
        
        print("[OK] GameRunner 整合測試通過")
        return True
        
    except Exception as e:
        print(f"[FAIL] GameRunner 整合測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_app_integration():
    """測試 app.py 的整合"""
    print("\n" + "="*60)
    print("測試 app.py 整合")
    print("="*60)
    
    try:
        from config.loader import load_test_service_config
        from qa.test_manager import TestTaskManager
        from qa.test_service import TestServiceClient
        
        # 測試配置加載
        print("\n測試配置加載:")
        service_config = load_test_service_config(BASE_DIR)
        print(f"  服務配置: {service_config}")
        
        # 測試服務創建
        if service_config.get("enabled"):
            test_service = TestServiceClient(
                service_config.get("url"),
                service_config.get("api_key")
            )
            print(f"  [OK] 測試服務已創建: {test_service.enabled}")
        else:
            print("  [WARN] 測試服務未啟用（配置中 enabled=false）")
        
        # 測試任務管理器創建
        print("\n測試任務管理器創建:")
        urls = ["URL1", "URL2"]
        csv_data = ["CSV1", "CSV2", "CSV3"]
        task_manager = TestTaskManager(urls, csv_data)
        print(f"  [OK] 任務管理器已創建: {len(urls)} 個URL, {len(csv_data)} 筆CSV")
        
        print("[OK] app.py 整合測試通過")
        return True
        
    except Exception as e:
        print(f"[FAIL] app.py 整合測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函數"""
    print("\n" + "="*60)
    print("開始集成測試")
    print("="*60)
    
    results = {}
    
    results['game_runner'] = await test_game_runner_integration()
    results['app'] = await test_app_integration()
    
    # 總結
    print("\n" + "="*60)
    print("集成測試總結")
    print("="*60)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    for name, result in results.items():
        status = "[OK] 通過" if result else "[FAIL] 失敗"
        print(f"{name:15} - {status}")
    
    print(f"\n總計: {passed}/{total} 通過, {failed} 失敗")
    
    if failed == 0:
        print("\n[SUCCESS] 所有集成測試通過！")
        return True
    else:
        print(f"\n[WARN] 有 {failed} 個測試失敗")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

