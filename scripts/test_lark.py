"""
測試 Lark 通知功能

這個腳本會測試：
1. 環境變數是否正確載入
2. LarkClient 是否正常初始化
3. 是否可以成功發送測試訊息
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 設定 BASE_DIR
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# 載入環境變數
load_dotenv(BASE_DIR / "dotenv.env")
LARK_WEBHOOK = os.getenv("LARK_WEBHOOK_URL")

print("="*60)
print("Lark 通知功能測試")
print("="*60)

# 1. 檢查環境變數
print("\n1. 檢查環境變數")
if LARK_WEBHOOK:
    print(f"[OK] LARK_WEBHOOK_URL 已載入")
    print(f"    長度: {len(LARK_WEBHOOK)} 字元")
    print(f"    前50字元: {LARK_WEBHOOK[:50]}...")
else:
    print("[FAIL] LARK_WEBHOOK_URL 未設定")
    print("請確認 dotenv.env 檔案中有設定 LARK_WEBHOOK_URL")
    sys.exit(1)

# 2. 測試 LarkClient 初始化
print("\n2. 測試 LarkClient 初始化")
try:
    from notification.lark import LarkClient
    lark = LarkClient(LARK_WEBHOOK)
    
    if lark.enabled:
        print("[OK] LarkClient 已啟用")
    else:
        print("[FAIL] LarkClient 未啟用")
        sys.exit(1)
except Exception as e:
    print(f"[FAIL] LarkClient 初始化失敗: {e}")
    sys.exit(1)

# 3. 測試發送簡單訊息
print("\n3. 測試發送簡單訊息")
try:
    test_message = "[測試] Lark 通知功能測試成功！"
    print(f"發送訊息: {test_message}")
    result = lark.send_text(test_message)
    
    if result:
        print("[OK] 訊息發送成功")
    else:
        print("[WARN] 訊息發送失敗（可能是網路問題或 Webhook 無效）")
except Exception as e:
    print(f"[FAIL] 發送訊息時發生錯誤: {e}")
    import traceback
    traceback.print_exc()

# 4. 測試發送測試報告
print("\n4. 測試發送測試報告")
try:
    test_report = {
        "url": "https://example.com/test",
        "csv_data": "873-RISINGROCKETS-0140",
        "machine_type": "RISINGROCKETS 機器類型",
        "entry_status": "success",
        "console_errors": [],
        "video_status": "normal",
        "video_message": "",
        "button_tests": [
            {"button": "SPIN", "status": "success"},
            {"button": "BET", "status": "success"}
        ],
        "bet_results": [
            {"success": True, "bet_amount": 100}
        ],
        "image_comparisons": [
            {
                "stage": "entry",
                "match": True,
                "result": {
                    "status": "success",
                    "total_images": 1,
                    "matched_images": 1
                }
            }
        ]
    }
    
    print("發送測試報告...")
    result = lark.send_test_report(test_report)
    
    if result:
        print("[OK] 測試報告發送成功")
    else:
        print("[WARN] 測試報告發送失敗（可能是網路問題或 Webhook 無效）")
except Exception as e:
    print(f"[FAIL] 發送測試報告時發生錯誤: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("測試完成")
print("="*60)
print("\n請檢查您的 Lark 群組，確認是否收到測試訊息。")
print("如果沒有收到訊息，請檢查：")
print("1. Webhook URL 是否正確")
print("2. 網路連線是否正常")
print("3. Lark Bot 是否已加入群組")

