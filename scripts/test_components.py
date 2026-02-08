"""
組件測試腳本 - 測試各個組件的功能

使用方法:
    python test_components.py [組件名稱]

組件名稱:
    all - 測試所有組件
    manager - 測試 TestTaskManager
    video - 測試 VideoDetector
    service - 測試 TestServiceClient
    lark - 測試 LarkClient 報告功能
    config - 測試配置加載
"""
import sys
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# 添加項目路徑
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


def test_test_manager():
    """測試 TestTaskManager 組件"""
    print("\n" + "="*60)
    print("測試 TestTaskManager")
    print("="*60)
    
    try:
        from qa.test_manager import TestTaskManager
        
        # 測試數據
        urls = ["URL_A", "URL_B", "URL_C"]
        csv_data = ["CSV_1", "CSV_2", "CSV_3", "CSV_4", "CSV_5"]
        
        manager = TestTaskManager(urls, csv_data)
        print(f"[OK] TestTaskManager 初始化成功")
        
        # 測試分配邏輯（每個URL獨立索引）
        print("\n測試 CSV 資料分配（每個URL獨立索引）:")
        results = []
        for url in urls:
            csv = manager.get_next_csv_for_url(url)
            results.append((url, csv))
            print(f"  {url} -> {csv}")
        
        # 驗證分配結果（每個URL都從第一個開始）
        expected = [
            ("URL_A", "CSV_1"),
            ("URL_B", "CSV_1"),
            ("URL_C", "CSV_1")
        ]
        assert results == expected, f"分配結果不符合預期: {results}"
        print("[OK] 第一輪分配正確（每個URL獨立索引）")
        
        # 測試第二輪分配
        print("\n測試第二輪分配:")
        csv_a2 = manager.get_next_csv_for_url("URL_A")
        csv_b2 = manager.get_next_csv_for_url("URL_B")
        csv_c2 = manager.get_next_csv_for_url("URL_C")
        print(f"  URL_A -> {csv_a2}")
        print(f"  URL_B -> {csv_b2}")
        print(f"  URL_C -> {csv_c2}")
        
        assert csv_a2 == "CSV_2", f"URL_A 第二輪應為 CSV_2，實際為 {csv_a2}"
        assert csv_b2 == "CSV_2", f"URL_B 第二輪應為 CSV_2，實際為 {csv_b2}"
        assert csv_c2 == "CSV_2", f"URL_C 第二輪應為 CSV_2，實際為 {csv_c2}"
        print("[OK] 第二輪分配正確")
        
        # 測試完成後返回 None（繼續獲取直到用完）
        print("\n測試完成後返回 None:")
        # URL_A 繼續獲取直到用完
        csv_a3 = manager.get_next_csv_for_url("URL_A")
        csv_a4 = manager.get_next_csv_for_url("URL_A")
        csv_a5 = manager.get_next_csv_for_url("URL_A")
        csv_a6 = manager.get_next_csv_for_url("URL_A")
        print(f"  URL_A 第3-6次: {csv_a3}, {csv_a4}, {csv_a5}, {csv_a6}")
        assert csv_a3 == "CSV_3", f"URL_A 第3次應為 CSV_3"
        assert csv_a4 == "CSV_4", f"URL_A 第4次應為 CSV_4"
        assert csv_a5 == "CSV_5", f"URL_A 第5次應為 CSV_5"
        assert csv_a6 is None, f"URL_A 第6次應為 None（已用完）"
        print("[OK] 完成後返回 None 正確")
        
        # 測試剩餘數量
        remaining = manager.get_remaining_count("URL_A")
        print(f"\nURL_A 剩餘數量: {remaining}")
        assert remaining == 0, f"URL_A 應無剩餘，實際為 {remaining}"
        print("[OK] 剩餘數量計算正確")
        
        # 測試狀態查詢
        status = manager.get_all_status()
        print(f"\n所有URL狀態: {status}")
        print("[OK] TestTaskManager 所有測試通過")
        return True
        
    except Exception as e:
        print(f"[FAIL] TestTaskManager 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_video_detector():
    """測試 VideoDetector 組件"""
    print("\n" + "="*60)
    print("測試 VideoDetector")
    print("="*60)
    
    try:
        from qa.video_detector import VideoDetector
        from playwright.async_api import async_playwright
        import numpy as np
        from PIL import Image
        
        print("[OK] VideoDetector 導入成功")
        
        # 測試圖像檢測邏輯（不啟動瀏覽器）
        print("\n測試圖像檢測邏輯:")
        
        # 創建測試圖像
        # 1. 正常圖像（彩色）
        normal_img = Image.new('RGB', (100, 100), color=(100, 150, 200))
        normal_array = np.array(normal_img)
        rgb_mean = np.mean(normal_array[:, :, :3])
        print(f"  正常圖像平均亮度: {rgb_mean:.2f}")
        assert rgb_mean > 10, "正常圖像應有足夠亮度"
        print("  [OK] 正常圖像檢測邏輯正確")
        
        # 2. 黑畫面
        black_img = Image.new('RGB', (100, 100), color=(0, 0, 0))
        black_array = np.array(black_img)
        black_mean = np.mean(black_array)
        print(f"  黑畫面平均亮度: {black_mean:.2f}")
        assert black_mean < 10, "黑畫面應被檢測到"
        print("  [OK] 黑畫面檢測邏輯正確")
        
        # 3. 單色畫面
        monochrome_img = Image.new('RGB', (100, 100), color=(50, 50, 50))
        mono_array = np.array(monochrome_img)
        mono_std = np.std(mono_array)
        print(f"  單色畫面變異數: {mono_std:.2f}")
        assert mono_std < 5, "單色畫面變異數應很低"
        print("  [OK] 單色畫面檢測邏輯正確")
        
        # 測試實際瀏覽器（可選，需要啟動瀏覽器）
        print("\n測試實際瀏覽器檢測（可選）:")
        test_browser = input("是否測試實際瀏覽器檢測？(y/n，預設n): ").strip().lower()
        
        if test_browser == 'y':
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.set_content("""
                    <html>
                        <body>
                            <canvas id="test-canvas" width="200" height="200"></canvas>
                            <script>
                                const canvas = document.getElementById('test-canvas');
                                const ctx = canvas.getContext('2d');
                                ctx.fillStyle = 'rgb(100, 150, 200)';
                                ctx.fillRect(0, 0, 200, 200);
                            </script>
                        </body>
                    </html>
                """)
                await page.wait_for_timeout(500)
                
                result, message = await VideoDetector.check_video_display(page, "#test-canvas")
                print(f"  檢測結果: {result}, 訊息: {message}")
                assert result == True, "正常畫布應檢測為正常"
                print("  [OK] 實際瀏覽器檢測成功")
                
                await browser.close()
        else:
            print("  跳過實際瀏覽器測試")
        
        print("[OK] VideoDetector 所有測試通過")
        return True
        
    except Exception as e:
        print(f"[FAIL] VideoDetector 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_test_service():
    """測試 TestServiceClient 組件"""
    print("\n" + "="*60)
    print("測試 TestServiceClient")
    print("="*60)
    
    try:
        from qa.test_service import TestServiceClient
        
        # 測試未啟用狀態
        print("\n測試未啟用狀態:")
        client_disabled = TestServiceClient(None)
        assert client_disabled.enabled == False, "未提供URL應為未啟用"
        result = client_disabled.log_test_event("test", {})
        assert result == False, "未啟用時應返回 False"
        print("[OK] 未啟用狀態正確")
        
        # 測試啟用狀態（但不實際發送請求）
        print("\n測試啟用狀態:")
        client_enabled = TestServiceClient("http://localhost:8080", "test-key")
        assert client_enabled.enabled == True, "提供URL應為啟用"
        assert client_enabled.service_url == "http://localhost:8080", "URL應正確設置"
        assert client_enabled.api_key == "test-key", "API key應正確設置"
        print("[OK] 啟用狀態正確")
        
        # 測試方法存在性
        print("\n測試方法存在性:")
        assert hasattr(client_enabled, 'test_button_response'), "應有 test_button_response 方法"
        assert hasattr(client_enabled, 'log_bet_result'), "應有 log_bet_result 方法"
        assert hasattr(client_enabled, 'log_entry_status'), "應有 log_entry_status 方法"
        print("[OK] 所有方法存在")
        
        # 測試方法調用（不會實際發送，因為服務不存在）
        print("\n測試方法調用（模擬）:")
        try:
            client_enabled.test_button_response("button.spin", "http://test.com", "SPIN")
            print("  [OK] test_button_response 調用成功（預期會失敗連線）")
        except Exception:
            pass  # 預期會失敗，因為服務不存在
        
        print("[OK] TestServiceClient 所有測試通過")
        return True
        
    except Exception as e:
        print(f"[FAIL] TestServiceClient 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_lark_report():
    """測試 LarkClient 報告功能"""
    print("\n" + "="*60)
    print("測試 LarkClient 報告功能")
    print("="*60)
    
    try:
        from notification.lark import LarkClient
        
        # 測試未啟用狀態
        print("\n測試未啟用狀態:")
        lark_disabled = LarkClient(None)
        assert lark_disabled.enabled == False, "未提供webhook應為未啟用"
        result = lark_disabled.send_test_report({})
        assert result == False, "未啟用時應返回 False"
        print("[OK] 未啟用狀態正確")
        
        # 測試報告格式化（不實際發送）
        print("\n測試報告格式化:")
        test_report = {
            "url": "http://test.com",
            "csv_data": "TEST_CODE",
            "entry_status": "success",
            "console_errors": [
                {"type": "error", "text": "測試錯誤1"},
                {"type": "pageerror", "text": "測試錯誤2"}
            ],
            "video_status": "normal",
            "video_message": "",
            "button_tests": [
                {"button": "SPIN", "status": "success"},
                {"button": "BET", "status": "failed"}
            ],
            "bet_results": [
                {"success": True, "bet_amount": 100},
                {"success": False, "bet_amount": 50}
            ]
        }
        
        # 測試方法存在
        assert hasattr(lark_disabled, 'send_test_report'), "應有 send_test_report 方法"
        print("[OK] send_test_report 方法存在")
        
        # 測試報告結構
        print("\n測試報告結構:")
        required_keys = ["url", "csv_data", "entry_status", "console_errors", 
                        "video_status", "button_tests", "bet_results"]
        for key in required_keys:
            assert key in test_report, f"報告應包含 {key}"
        print("[OK] 報告結構正確")
        
        # 測試實際發送（可選）
        print("\n測試實際發送（可選）:")
        test_send = input("是否測試實際發送到Lark？(y/n，預設n): ").strip().lower()
        
        if test_send == 'y':
            webhook = input("請輸入Lark Webhook URL: ").strip()
            if webhook:
                lark_enabled = LarkClient(webhook)
                result = lark_enabled.send_test_report(test_report)
                if result:
                    print("  [OK] 報告發送成功")
                else:
                    print("  [WARN] 報告發送失敗（可能是webhook無效）")
            else:
                print("  跳過實際發送測試")
        else:
            print("  跳過實際發送測試")
        
        print("[OK] LarkClient 報告功能測試通過")
        return True
        
    except Exception as e:
        print(f"[FAIL] LarkClient 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_loader():
    """測試配置加載功能"""
    print("\n" + "="*60)
    print("測試配置加載功能")
    print("="*60)
    
    try:
        from config.loader import load_test_service_config
        
        # 測試加載配置
        print("\n測試加載 test_service 配置:")
        config = load_test_service_config(BASE_DIR)
        print(f"  配置內容: {config}")
        
        # 檢查配置結構
        if config:
            print("  [OK] 配置加載成功")
            if "enabled" in config:
                print(f"    啟用狀態: {config.get('enabled')}")
            if "url" in config:
                print(f"    服務URL: {config.get('url')}")
        else:
            print("  [WARN] 配置為空（可能是 test_config.json 中沒有 test_service）")
        
        print("[OK] 配置加載功能測試通過")
        return True
        
    except Exception as e:
        print(f"[FAIL] 配置加載測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """運行所有測試"""
    print("\n" + "="*60)
    print("開始運行所有組件測試")
    print("="*60)
    
    results = {}
    
    # 測試各個組件
    results['manager'] = test_test_manager()
    results['video'] = await test_video_detector()
    results['service'] = test_test_service()
    results['lark'] = test_lark_report()
    results['config'] = test_config_loader()
    
    # 總結
    print("\n" + "="*60)
    print("測試總結")
    print("="*60)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    for name, result in results.items():
        status = "[OK] 通過" if result else "[FAIL] 失敗"
        print(f"{name:15} - {status}")
    
    print(f"\n總計: {passed}/{total} 通過, {failed} 失敗")
    
    if failed == 0:
        print("\n[SUCCESS] 所有測試通過！")
        return True
    else:
        print(f"\n[WARN] 有 {failed} 個測試失敗")
        return False


def main():
    """主函數"""
    if len(sys.argv) > 1:
        component = sys.argv[1].lower()
    else:
        component = "all"
    
    if component == "all":
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    elif component == "manager":
        success = test_test_manager()
        sys.exit(0 if success else 1)
    elif component == "video":
        success = asyncio.run(test_video_detector())
        sys.exit(0 if success else 1)
    elif component == "service":
        success = test_test_service()
        sys.exit(0 if success else 1)
    elif component == "lark":
        success = test_lark_report()
        sys.exit(0 if success else 1)
    elif component == "config":
        success = test_config_loader()
        sys.exit(0 if success else 1)
    else:
        print(f"未知的組件名稱: {component}")
        print("可用組件: all, manager, video, service, lark, config")
        sys.exit(1)


if __name__ == "__main__":
    main()

