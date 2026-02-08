"""
模擬測試腳本 - 模擬完整的測試流程並檢查結果

這個腳本會模擬：
1. 配置加載
2. 機器類型匹配
3. 測試流程執行
4. 圖片比對功能
5. 報告生成
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

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


def simulate_config_loading():
    """模擬配置加載"""
    print("\n" + "="*60)
    print("1. 模擬配置加載")
    print("="*60)
    
    try:
        from config.loader import load_games, load_actions, load_bet_random, load_test_service_config
        from config.machine_profiles import load_machine_profiles, match_machine_profile
        
        # 加載遊戲配置
        games = load_games(BASE_DIR)
        print(f"[OK] 加載遊戲配置: {len(games)} 個")
        for i, game in enumerate(games[:3], 1):  # 只顯示前3個
            print(f"  {i}. URL: {game.url[:50]}...")
            print(f"     game_title_code: {game.game_title_code}")
        
        # 加載機器類型配置
        machine_profiles = load_machine_profiles(BASE_DIR)
        print(f"\n[OK] 加載機器類型配置: {len(machine_profiles.profiles)} 個")
        for name, profile in machine_profiles.profiles.items():
            print(f"  - {name}: {profile.name} ({len(profile.test_flows)} 個測試流程)")
        
        # 加載其他配置
        keyword_actions, machine_actions = load_actions(BASE_DIR)
        print(f"\n[OK] 加載動作配置: {len(keyword_actions)} 個 keyword_actions")
        
        bet_random_map = load_bet_random(BASE_DIR)
        print(f"[OK] 加載下注配置: {len(bet_random_map)} 個")
        
        test_service_config = load_test_service_config(BASE_DIR)
        print(f"[OK] 加載測試服務配置: 啟用={test_service_config.get('enabled', False)}")
        
        return games, machine_profiles, keyword_actions, machine_actions, bet_random_map, test_service_config
        
    except Exception as e:
        print(f"[FAIL] 配置加載失敗: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None, None, None, None


def simulate_machine_matching(games, machine_profiles):
    """模擬機器類型匹配"""
    print("\n" + "="*60)
    print("2. 模擬機器類型匹配")
    print("="*60)
    
    if not games or not machine_profiles:
        print("[SKIP] 跳過匹配測試（配置未加載）")
        return []
    
    matched_results = []
    
    for game in games[:3]:  # 只測試前3個
        print(f"\n測試遊戲: {game.game_title_code or 'N/A'}")
        print(f"  URL: {game.url[:60]}...")
        
        # 從 URL 提取 gameid
        gameid = None
        if "gameid=" in game.url:
            try:
                gameid = game.url.split("gameid=")[1].split("&")[0]
                print(f"  提取 gameid: {gameid}")
            except:
                pass
        
        # 匹配機器類型
        from config.machine_profiles import match_machine_profile
        profile = match_machine_profile(
            machine_profiles,
            game.url,
            game.game_title_code,
            gameid,
            game.machine_type
        )
        
        if profile:
            print(f"  [OK] 匹配到機器類型: {profile.name}")
            print(f"      測試流程數: {len(profile.test_flows)}")
            print(f"      按鈕選擇器: {len(profile.button_selectors)} 個")
            if profile.folder_path:
                print(f"      配置文件夾: {profile.folder_path.name}")
            matched_results.append((game, profile))
        else:
            print(f"  [WARN] 未匹配到機器類型")
            matched_results.append((game, None))
    
    return matched_results


def simulate_test_flows(matched_results):
    """模擬測試流程執行"""
    print("\n" + "="*60)
    print("3. 模擬測試流程執行")
    print("="*60)
    
    if not matched_results:
        print("[SKIP] 跳過測試流程模擬（無匹配結果）")
        return
    
    for game, profile in matched_results:
        if not profile:
            continue
        
        print(f"\n機器類型: {profile.name}")
        print(f"  測試流程:")
        
        for i, flow in enumerate(profile.test_flows, 1):
            if not flow.enabled:
                print(f"    {i}. {flow.name} - [已禁用]")
                continue
            
            print(f"    {i}. {flow.name}")
            print(f"       描述: {flow.description}")
            print(f"       超時: {flow.timeout}s, 重試: {flow.retry_count}次")
            
            # 檢查圖片比對配置
            image_comp = flow.config.get("image_comparison", {})
            if image_comp.get("enabled", False):
                print(f"       圖片比對: 啟用 (閾值: {image_comp.get('similarity_threshold', 0.8)})")
                
                # 檢查參考圖片目錄
                if profile.folder_path:
                    ref_dir = profile.folder_path / "reference_images"
                    stage_name = flow.name.lower().replace(" ", "_")
                    if stage_name == "進入機器":
                        stage_name = "entry"
                    elif stage_name == "視頻檢測":
                        stage_name = "video"
                    elif stage_name == "按鈕測試":
                        stage_name = "buttons"
                    
                    stage_dir = ref_dir / stage_name
                    if stage_dir.exists():
                        images = list(stage_dir.glob("*.png")) + list(stage_dir.glob("*.jpg")) + list(stage_dir.glob("*.jpeg"))
                        print(f"       參考圖片: {len(images)} 張")
                        for img in images[:3]:  # 只顯示前3張
                            print(f"         - {img.name}")
                    else:
                        print(f"       參考圖片: 目錄不存在 ({stage_dir.name})")
            else:
                print(f"       圖片比對: 未啟用")


def simulate_image_comparison():
    """模擬圖片比對功能"""
    print("\n" + "="*60)
    print("4. 模擬圖片比對功能")
    print("="*60)
    
    try:
        from qa.image_comparator import ImageComparator
        import numpy as np
        from PIL import Image
        
        print("[OK] ImageComparator 導入成功")
        
        # 測試相似度計算
        print("\n測試相似度計算:")
        
        # 創建兩張相同的圖片
        img1 = Image.new('RGB', (100, 100), color=(100, 150, 200))
        img2 = Image.new('RGB', (100, 100), color=(100, 150, 200))
        arr1 = np.array(img1)
        arr2 = np.array(img2)
        
        similarity, info = ImageComparator.calculate_similarity(arr1, arr2)
        print(f"  相同圖片相似度: {similarity:.2%} (方法: {info.get('method', 'unknown')})")
        assert similarity >= 0.99, "相同圖片應有極高相似度"
        print("  [OK] 相同圖片比對正確")
        
        # 創建兩張不同的圖片
        img3 = Image.new('RGB', (100, 100), color=(200, 100, 50))
        arr3 = np.array(img3)
        
        similarity2, info2 = ImageComparator.calculate_similarity(arr1, arr3)
        print(f"  不同圖片相似度: {similarity2:.2%} (方法: {info2.get('method', 'unknown')})")
        assert similarity2 < similarity, "不同圖片應有較低相似度"
        print("  [OK] 不同圖片比對正確")
        
        # 檢查參考圖片目錄
        print("\n檢查參考圖片目錄:")
        profiles_dir = BASE_DIR / "machine_profiles"
        if profiles_dir.exists():
            for profile_dir in profiles_dir.iterdir():
                if not profile_dir.is_dir() or profile_dir.name.startswith("."):
                    continue
                
                ref_dir = profile_dir / "reference_images"
                if ref_dir.exists():
                    print(f"  {profile_dir.name}:")
                    for stage_dir in ref_dir.iterdir():
                        if stage_dir.is_dir():
                            images = list(stage_dir.glob("*.png")) + list(stage_dir.glob("*.jpg")) + list(stage_dir.glob("*.jpeg"))
                            if images:
                                print(f"    {stage_dir.name}/: {len(images)} 張圖片")
                            else:
                                print(f"    {stage_dir.name}/: 無圖片（目錄已創建）")
                else:
                    print(f"  {profile_dir.name}: reference_images/ 不存在")
        else:
            print("  [WARN] machine_profiles/ 目錄不存在")
        
        print("[OK] 圖片比對功能測試通過")
        return True
        
    except Exception as e:
        print(f"[FAIL] 圖片比對功能測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def simulate_test_report():
    """模擬測試報告生成"""
    print("\n" + "="*60)
    print("5. 模擬測試報告生成")
    print("="*60)
    
    try:
        from notification.lark import LarkClient
        
        # 創建模擬測試報告
        test_report = {
            "url": "https://example.com/test",
            "csv_data": "873-RISINGROCKETS-0140",
            "machine_type": "RISINGROCKETS 機器類型",
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
            ],
            "image_comparisons": [
                {
                    "stage": "entry",
                    "match": True,
                    "result": {
                        "status": "success",
                        "total_images": 2,
                        "matched_images": 2,
                        "results": [
                            {
                                "reference_image": "entry_1.png",
                                "match": True,
                                "similarity": 0.85,
                                "message": "相似度: 85.00% (匹配, 閾值: 80.00%)"
                            }
                        ]
                    }
                },
                {
                    "stage": "video",
                    "match": True,
                    "result": {
                        "status": "success",
                        "total_images": 1,
                        "matched_images": 1
                    }
                },
                {
                    "stage": "buttons",
                    "match": False,
                    "result": {
                        "status": "failed",
                        "total_images": 1,
                        "matched_images": 0
                    }
                }
            ]
        }
        
        # 創建 LarkClient（不實際發送）
        lark = LarkClient(None)
        
        # 測試報告格式化（不實際發送）
        print("模擬測試報告內容:")
        print("-" * 60)
        
        # 手動格式化報告（模擬 send_test_report 的邏輯，使用 ASCII 字符避免編碼問題）
        lines = [
            "[測試報告]",
            "",
            f"URL: {test_report.get('url', 'N/A')}",
            f"CSV資料: {test_report.get('csv_data', 'N/A')}",
            f"機器類型: {test_report.get('machine_type', 'N/A')}",
            "",
            "---",
            ""
        ]
        
        # 進入狀態
        entry_status = test_report.get('entry_status', 'unknown')
        status_mark = "[OK]" if entry_status == "success" else "[FAIL]"
        lines.append(f"{status_mark} 進入機器: {entry_status}")
        
        # Console錯誤
        console_errors = test_report.get('console_errors', [])
        if console_errors:
            lines.append(f"")
            lines.append(f"[WARN] Console錯誤: {len(console_errors)} 個")
            for i, error in enumerate(console_errors[:3], 1):
                error_text = error.get('text', str(error))[:80]
                error_type = error.get('type', 'unknown')
                lines.append(f"  {i}. [{error_type}] {error_text}")
        
        # 視頻狀態
        video_status = test_report.get('video_status', 'unknown')
        if video_status == "normal":
            lines.append(f"[OK] 視頻顯示: 正常")
        else:
            lines.append(f"[FAIL] 視頻顯示: {video_status}")
        
        # 按鈕測試
        button_tests = test_report.get('button_tests', [])
        if button_tests:
            lines.append(f"")
            lines.append(f"[按鈕測試]")
            for test in button_tests:
                button_name = test.get('button', 'Unknown')
                status = test.get('status', 'unknown')
                mark = "[OK]" if status == "success" else "[FAIL]"
                lines.append(f"  {mark} {button_name}: {status}")
        
        # 圖片比對結果
        image_comparisons = test_report.get('image_comparisons', [])
        if image_comparisons:
            lines.append(f"")
            lines.append(f"[圖片比對結果]")
            for comp in image_comparisons:
                stage = comp.get('stage', 'unknown')
                match = comp.get('match', False)
                mark = "[OK]" if match else "[FAIL]"
                result_info = comp.get('result', {})
                if isinstance(result_info, dict):
                    matched = result_info.get('matched_images', 0)
                    total = result_info.get('total_images', 0)
                    lines.append(f"  {mark} {stage}: {matched}/{total} 匹配")
                else:
                    lines.append(f"  {mark} {stage}: {'匹配' if match else '不匹配'}")
        
        report_text = "\n".join(lines)
        print(report_text)
        print("-" * 60)
        
        print("[OK] 測試報告格式化成功")
        return True
        
    except Exception as e:
        print(f"[FAIL] 測試報告生成失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def simulate_full_flow():
    """模擬完整流程"""
    print("\n" + "="*60)
    print("6. 模擬完整測試流程")
    print("="*60)
    
    try:
        from config.models import GameConfig
        from notification.lark import LarkClient
        from config.machine_profiles import load_machine_profiles, match_machine_profile
        
        # 創建模擬配置
        test_game = GameConfig(
            url="https://osm-redirect.osmslot.org/?token=test&gameid=osmbwjl",
            game_title_code="873-RISINGROCKETS-0140",
            enabled=True
        )
        
        print(f"模擬遊戲配置:")
        print(f"  URL: {test_game.url[:60]}...")
        print(f"  game_title_code: {test_game.game_title_code}")
        
        # 加載機器類型配置
        machine_profiles = load_machine_profiles(BASE_DIR)
        
        # 匹配機器類型
        gameid = "osmbwjl"
        profile = match_machine_profile(
            machine_profiles,
            test_game.url,
            test_game.game_title_code,
            gameid
        )
        
        if profile:
            print(f"\n[OK] 匹配到機器類型: {profile.name}")
            print(f"  測試流程數: {len(profile.test_flows)}")
            
            # 模擬執行測試流程
            print(f"\n模擬執行測試流程:")
            for flow in profile.test_flows:
                if not flow.enabled:
                    continue
                
                print(f"  - {flow.name}: {flow.description}")
                
                # 檢查圖片比對
                img_comp = flow.config.get("image_comparison", {})
                if img_comp.get("enabled", False):
                    print(f"    圖片比對: 啟用")
                    if profile.folder_path:
                        ref_dir = profile.folder_path / "reference_images"
                        stage_map = {
                            "進入機器": "entry",
                            "視頻檢測": "video",
                            "按鈕測試": "buttons"
                        }
                        stage_name = stage_map.get(flow.name, flow.name.lower().replace(" ", "_"))
                        stage_dir = ref_dir / stage_name
                        if stage_dir.exists():
                            images = list(stage_dir.glob("*.png")) + list(stage_dir.glob("*.jpg"))
                            print(f"    參考圖片: {len(images)} 張")
                        else:
                            print(f"    參考圖片: 目錄不存在（將跳過比對）")
                else:
                    print(f"    圖片比對: 未啟用")
        else:
            print(f"\n[WARN] 未匹配到機器類型")
        
        print("[OK] 完整流程模擬成功")
        return True
        
    except Exception as e:
        print(f"[FAIL] 完整流程模擬失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函數"""
    print("\n" + "="*60)
    print("開始模擬測試")
    print("="*60)
    
    results = {}
    
    # 1. 配置加載
    config_result = simulate_config_loading()
    games, machine_profiles, keyword_actions, machine_actions, bet_random_map, test_config = config_result
    results['config'] = config_result[0] is not None
    
    # 2. 機器類型匹配
    if games and machine_profiles:
        matched_results = simulate_machine_matching(games, machine_profiles)
        results['matching'] = len(matched_results) > 0
    else:
        matched_results = []
        results['matching'] = False
    
    # 3. 測試流程模擬
    if matched_results:
        simulate_test_flows(matched_results)
        results['test_flows'] = True
    else:
        results['test_flows'] = False
    
    # 4. 圖片比對功能
    results['image_comparison'] = simulate_image_comparison()
    
    # 5. 測試報告生成
    results['test_report'] = simulate_test_report()
    
    # 6. 完整流程模擬
    results['full_flow'] = simulate_full_flow()
    
    # 總結
    print("\n" + "="*60)
    print("模擬測試總結")
    print("="*60)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    for name, result in results.items():
        status = "[OK] 通過" if result else "[FAIL] 失敗"
        print(f"{name:20} - {status}")
    
    print(f"\n總計: {passed}/{total} 通過, {failed} 失敗")
    
    if failed == 0:
        print("\n[SUCCESS] 所有模擬測試通過！")
        print("\n建議:")
        print("1. 確保參考圖片已準備好（放在 reference_images/ 目錄下）")
        print("2. 根據實際情況調整相似度閾值")
        print("3. 運行實際測試驗證功能")
        return True
    else:
        print(f"\n[WARN] 有 {failed} 個測試失敗，請檢查上述錯誤")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

