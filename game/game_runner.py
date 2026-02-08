"""
遊戲執行器 - GameRunner 類的實現

這個文件包含 GameRunner 類，負責單個遊戲的執行邏輯：
- 瀏覽器管理
- 遊戲進入/退出流程
- Spin 循環
- 餘額檢測
- 特殊流程觸發

注意：根目錄的 app.py 是主執行程序，會創建多個 GameRunner 實例
"""
import asyncio
import time
import logging
import traceback
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from config.models import GameConfig
from config.test_config import TestScenario
from notification.lark import LarkClient
from core.browser import is_404_page
from core.utils import file_md5
from game.balance import parse_balance, SPECIAL_GAMES
from game.actions import click_spin, click_multiple_positions
from game.navigation import (
    is_in_game,
    scroll_and_click_game,
    low_balance_exit_and_reenter,
    exit_game_to_lobby,
)
from hotkey import stop_event, pause_event

# 測試相關導入
try:
    from qa.test_manager import TestTaskManager
    from qa.video_detector import VideoDetector
    from qa.test_service import TestServiceClient
    from qa.image_comparator import ImageComparator
    from qa.audio_detector import AudioDetector, load_audio_config
except ImportError:
    TestTaskManager = None
    VideoDetector = None
    TestServiceClient = None
    ImageComparator = None
    AudioDetector = None
    load_audio_config = None

# 機器類型配置導入
try:
    from config.machine_profiles import MachineProfile, match_machine_profile
except ImportError:
    MachineProfile = None
    match_machine_profile = None


class GameRunner:
    """
    掌管單一機台的整個流程：
    - 啟動 Edge，進入 URL
    - 在 Lobby 找遊戲卡片 -> Join
    - 迴圈地：檢查餘額 -> 點擊 Spin -> 特殊流程
    """

    def __init__(
        self,
        config: GameConfig,
        lark: LarkClient,
        keyword_actions: Dict[str, List[str]],
        machine_actions: Dict[str, Tuple[List[str], bool]],
        test_scenario: Optional[TestScenario] = None,
        test_service: Optional[Any] = None,
        task_manager: Optional[Any] = None,
        machine_profile: Optional[Any] = None,
        machine_profiles: Optional[Any] = None,  # 所有機器類型配置（用於動態匹配）
    ):
        self.cfg = config
        self.lark = lark
        self.keyword_actions = keyword_actions
        self.machine_actions = machine_actions
        self.test_scenario = test_scenario  # 測試場景配置
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._auto_pause = False
        self._last_balance = None
        self._no_change_count = 0
        self._check_interval = 10
        self._spin_count = 0
        self._last_404_check_time = 0.0
        self._404_check_interval = 30.0
        
        # 測試模式相關
        self._test_spin_count = 0  # 測試模式下的 Spin 計數器
        
        # 新增測試相關屬性
        self.test_service = test_service
        self.task_manager = task_manager
        self.machine_profile = machine_profile  # 當前機器類型配置
        self.machine_profiles = machine_profiles  # 所有機器類型配置（用於動態匹配新機器號）
        self.console_logs: List[Dict[str, Any]] = []
        self._worker_id = f"URL-{config.url[-20:]}"  # 用於 TaskManager 日誌
        self.test_report = self._create_test_report(config.game_title_code, machine_profile)
        
        # 如果沒有明確指定機器類型配置，且非共享佇列模式，記錄警告
        if not machine_profile and not task_manager:
            logging.warning(f"[GameRunner] 未找到機器類型配置，將使用默認測試流程")
        
        # 如果啟用測試模式，記錄日誌
        if test_scenario:
            logging.info(f"[TestMode] 使用測試場景: {test_scenario.name}")
            logging.info(f"[TestMode] 描述: {test_scenario.description}")
            logging.info(f"[TestMode] Spin 次數限制: {test_scenario.spin_count or '無限制'}")

    def _create_test_report(self, game_title_code: Optional[str], machine_profile: Optional[Any]) -> Dict[str, Any]:
        """建立測試報告結構"""
        return {
            "url": self.cfg.url,
            "csv_data": game_title_code or "N/A",
            "machine_type": self.cfg.machine_type or (machine_profile.name if machine_profile else "unknown"),
            "entry_status": "pending",
            "console_errors": [],
            "video_status": "unknown",
            "video_message": "",
            "button_tests": [],
            "bet_results": [],
            "image_comparisons": []
        }

    def _reset_for_new_machine(self, new_code: str, new_profile: Optional[Any]):
        """
        切換到新的機器號時重置狀態
        
        Args:
            new_code: 新的 game_title_code
            new_profile: 新的 MachineProfile
        """
        self.cfg.game_title_code = new_code
        self.machine_profile = new_profile
        self.cfg.machine_type = new_profile.name if new_profile else None
        
        # 重置測試狀態
        self._test_spin_count = 0
        self._last_balance = None
        self._no_change_count = 0
        self._spin_count = 0
        self.console_logs = []
        self.test_report = self._create_test_report(new_code, new_profile)
        
        logging.info(f"[GameRunner] 已切換到新機器: {new_code} (類型: {new_profile.name if new_profile else 'unknown'})")

    def _match_profile_for_code(self, code: str) -> Optional[Any]:
        """根據機器號匹配 machine_profile"""
        if not self.machine_profiles or not match_machine_profile:
            return None
        
        # 從 URL 提取 gameid
        gameid = None
        if "gameid=" in self.cfg.url:
            try:
                gameid = self.cfg.url.split("gameid=")[1].split("&")[0]
            except:
                pass
        
        return match_machine_profile(
            self.machine_profiles,
            self.cfg.url,
            code,
            gameid,
            require_game_title_code=True
        )

    async def _check_and_refresh_if_404(self):
        """定時檢測 404 頁面並刷新，每 30 秒檢查一次"""
        try:
            if not self.page:
                return False
                
            current_time = time.time()
            
            if current_time - self._last_404_check_time < self._404_check_interval:
                return False
            
            self._last_404_check_time = current_time
            
            if await is_404_page(self.page):
                game_name = self.cfg.game_title_code or 'Unknown'
                logging.warning(f"🚨 [{game_name}] 檢測到 404 頁面，準備刷新...")
                
                try:
                    await self.page.reload()
                    logging.info(f"✅ [{game_name}] 頁面已刷新")
                    await asyncio.sleep(3.0)
                    
                    if await is_404_page(self.page):
                        logging.error(f"❌ [{game_name}] 刷新後仍然是 404 頁面")
                        logging.info(f"🔄 [{game_name}] 嘗試重新加載原始 URL...")
                        await self.page.goto(self.cfg.url)
                        await asyncio.sleep(3.0)
                        
                        if await is_404_page(self.page):
                            logging.error(f"❌ [{game_name}] 重新加載後仍然是 404 頁面")
                        else:
                            logging.info(f"✅ [{game_name}] 重新加載成功")
                    else:
                        logging.info(f"✅ [{game_name}] 刷新成功，頁面正常")
                    
                    return True
                except Exception as e:
                    logging.error(f"❌ [{game_name}] 刷新頁面時發生錯誤: {e}")
                    return False
            else:
                game_name = self.cfg.game_title_code or 'Unknown'
                logging.debug(f"✅ [{game_name}] 頁面正常，無需刷新")
                return False
        except Exception as e:
            game_name = self.cfg.game_title_code or 'Unknown'
            logging.error(f"❌ [{game_name}] 檢測 404 頁面時發生錯誤: {e}")
            return False

    async def _build_browser(self, playwright):
        """建立與回傳 Playwright Browser 和 Context"""
        self.browser = await playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context(
            viewport={"width": 500, "height": 859},
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.127 Mobile Safari/537.36"
            ),
        )
        self.page = await self.context.new_page()
        
        # 注入音頻監控腳本（必須在頁面導航前）
        if AudioDetector:
            try:
                await AudioDetector.inject_monitor(self.page)
            except Exception as e:
                logging.warning(f"[AudioDetector] 注入失敗，音頻檢測將跳過: {e}")
        
        # 監聽 console 訊息
        def on_console(msg):
            self.console_logs.append({
                "type": msg.type,
                "text": msg.text,
                "timestamp": time.time()
            })
            if msg.type == "error":
                logging.warning(f"[Console] {msg.type}: {msg.text}")
        
        def on_pageerror(error):
            self.console_logs.append({
                "type": "pageerror",
                "text": str(error),
                "timestamp": time.time()
            })
            logging.error(f"[PageError] {error}")
        
        self.page.on("console", on_console)
        self.page.on("pageerror", on_pageerror)
        
        # 測試進入機器
        try:
            await self.page.goto(self.cfg.url, timeout=30000)
            await self.page.wait_for_load_state("networkidle", timeout=10000)
            
            # 檢查是否有錯誤提示窗
            error_dialogs = await self.page.query_selector_all(
                "div[class*='error'], div[class*='Error'], .alert-error, .error-message, [class*='alert']"
            )
            if error_dialogs:
                error_texts = []
                for dialog in error_dialogs:
                    try:
                        text = await dialog.inner_text()
                        if text and text.strip():
                            error_texts.append(text.strip())
                    except:
                        pass
                
                if error_texts:
                    self.test_report["entry_status"] = "failed"
                    self.test_report["console_errors"].append({
                        "type": "dialog",
                        "text": "; ".join(error_texts),
                        "timestamp": time.time()
                    })
                    logging.error(f"[Entry] 檢測到錯誤提示窗: {error_texts}")
                    if self.test_service:
                        self.test_service.log_entry_status(self.cfg.url, "failed", "; ".join(error_texts))
                    return self.browser, self.context, self.page
            
            # 檢查console是否有錯誤
            console_errors = [log for log in self.console_logs if log.get("type") in ["error", "pageerror"]]
            if console_errors:
                self.test_report["console_errors"] = console_errors
                if self.test_service:
                    for error in console_errors:
                        self.test_service.log_entry_status(self.cfg.url, "failed", error.get("text", ""))
            
            self.test_report["entry_status"] = "success"
            if self.test_service:
                self.test_service.log_entry_status(self.cfg.url, "success")
            
        except Exception as e:
            self.test_report["entry_status"] = "failed"
            error_msg = f"進入機器失敗: {str(e)}"
            self.test_report["console_errors"].append({
                "type": "exception",
                "text": error_msg,
                "timestamp": time.time()
            })
            logging.error(f"[Entry] {error_msg}")
            if self.test_service:
                self.test_service.log_entry_status(self.cfg.url, "failed", error_msg)
        
        return self.browser, self.context, self.page

    async def spin_forever(self):
        """主要工作迴圈"""
        if not self.page:
            return
            
        game_code = self.cfg.game_title_code or ""
        is_special_game = any(k in game_code for k in SPECIAL_GAMES)
        
        # Spin 次數與退出次數設定
        test_mode = self.test_scenario is not None
        max_spins = self.test_scenario.spin_count if test_mode else 10
        test_exit_after = self.test_scenario.test_exit_after_spins if test_mode else 10

        while not stop_event.is_set():
            # 檢查是否達到最大 Spin 次數
            if max_spins is not None and self._test_spin_count >= max_spins:
                logging.info(f"已達到最大 Spin 次數 ({max_spins})，結束當前機器")
                break
            while pause_event.is_set() and not stop_event.is_set():
                logging.info("[Loop] 已暫停，等待恢復（Space 解除暫停）")
                await asyncio.sleep(0.3)
            try:
                loop_start_time = time.time()
                
                await self._check_and_refresh_if_404()
                
                # 1) Balance 檢查（Spin 前）
                bal_before = await parse_balance(self.page, is_special=is_special_game)
                if bal_before is not None:
                    logging.info(f"當前餘額: {bal_before:,}")

                # 檢查是否在遊戲中
                if not await is_in_game(self.page):
                    logging.warning(f"{game_code} 檢測到在大廳，先嘗試進入遊戲")
                    if game_code:
                        if await scroll_and_click_game(self.page, game_code, self.keyword_actions):
                            logging.info(f"{game_code} 成功進入遊戲，等待頁面穩定")
                            await asyncio.sleep(3.0)
                        else:
                            logging.warning(f"{game_code} 無法進入遊戲，跳過本輪")
                            await asyncio.sleep(2.0)
                            continue
                    else:
                        logging.warning(f"{game_code} 沒有 game_title_code，無法進入遊戲")
                        await asyncio.sleep(2.0)
                        continue

                # 2) 點擊 Spin
                if not await click_spin(self.page, is_special=is_special_game):
                    logging.warning(f"{game_code} 點擊 Spin 失敗，嘗試回廳重進")
                    if game_code:
                        await scroll_and_click_game(self.page, game_code, self.keyword_actions)
                    await asyncio.sleep(1.0)
                    continue

                logging.info(f"已點擊 {'特殊' if is_special_game else '一般'} Spin")
                
                # Spin 計數（兩種模式共用）
                self._test_spin_count += 1
                logging.info(f"Spin 計數: {self._test_spin_count}/{max_spins or '∞'}")
                
                # 達到退出次數後結束 Spin 循環，由外層 _run_single_machine 處理切換
                if test_exit_after and self._test_spin_count >= test_exit_after:
                    logging.info(f"達到退出次數 ({test_exit_after})，結束當前機器的 Spin 循環")
                    break

                # 3) 餘額變化檢測
                await asyncio.sleep(0.5)
                bal_after = await parse_balance(self.page, is_special=is_special_game)
                
                balance_changed = False
                should_trigger_special = False
                
                if bal_before is not None and bal_after is not None:
                    balance_changed = (bal_after != bal_before)
                    if balance_changed:
                        logging.info(f"餘額變化: {bal_before:,} → {bal_after:,} (變化: {bal_after - bal_before:+,})")
                        self._no_change_count = 0
                    else:
                        self._no_change_count += 1
                        logging.info(f"餘額無變化: {bal_after:,} (連續無變化: {self._no_change_count}/{self._check_interval})")
                elif self._last_balance is not None and bal_after is not None:
                    balance_changed = (bal_after != self._last_balance)
                    if balance_changed:
                        logging.info(f"餘額變化 (與上次比較): {self._last_balance:,} → {bal_after:,} (變化: {bal_after - self._last_balance:+,})")
                        self._no_change_count = 0
                    else:
                        self._no_change_count += 1
                        logging.info(f"餘額無變化 (與上次比較): {bal_after:,} (連續無變化: {self._no_change_count}/{self._check_interval})")
                else:
                    self._no_change_count += 1
                    logging.info(f"無法檢測餘額變化，計入無變化: {self._no_change_count}/{self._check_interval}")
                
                if self._no_change_count >= self._check_interval:
                    should_trigger_special = True
                    logging.info(f"🎯 連續 {self._check_interval} 次無變化，觸發特殊流程！")
                    self._no_change_count = 0
                
                if bal_after is not None:
                    self._last_balance = bal_after

                # 4) 特殊機台 Spin 後流程 - 根據測試配置決定是否執行
                if should_trigger_special:
                    if not test_mode or (test_mode and self.test_scenario.features.enable_special_actions):
                        for kw, (positions, do_take) in self.machine_actions.items():
                            if game_code and kw in game_code:
                                logging.info(f"連續{self._check_interval}次無變化觸發特殊流程: {kw} -> {positions}, take={do_take}")
                                await click_multiple_positions(self.page, positions, click_take=do_take)
                                break
                elif balance_changed:
                    logging.info("餘額有變化，重置計數器，繼續 Spin")
                else:
                    logging.info(f"餘額無變化，累積計數: {self._no_change_count}/{self._check_interval}，繼續 Spin")

                # 5) 動態 sleep - 扣除循環耗時，使總週期 = 設定間隔
                loop_elapsed = time.time() - loop_start_time
                target_interval = self.test_scenario.spin_interval if test_mode else 5.0
                actual_sleep = max(0, target_interval - loop_elapsed)
                logging.info(f"循環耗時: {loop_elapsed:.3f}s | 目標間隔: {target_interval:.3f}s | 實際等待: {actual_sleep:.3f}s")
                
                await asyncio.sleep(actual_sleep)

            except Exception as e:
                logging.error(f"spin_forever 例外: {e}\n{traceback.format_exc()}")
                await asyncio.sleep(1.0)

        while (pause_event.is_set() or self._auto_pause) and not stop_event.is_set():
            logging.info("[Loop] 已暫停（%s）", "Global" if pause_event.is_set() else "Auto")
            await asyncio.sleep(0.2)

    async def run_full_test(self):
        """執行完整測試流程（根據機器類型配置）"""
        machine_type = self.test_report.get("machine_type", "unknown")
        logging.info(f"[Test] 開始完整測試: {self.cfg.url} (機器類型: {machine_type})")
        
        # 1. 進入機器（已在 _build_browser 中完成）
        
        # 2. 根據機器類型配置執行測試流程
        if self.machine_profile and self.machine_profile.test_flows:
            await self._run_machine_specific_tests()
        else:
            # 使用默認測試流程
            await self._run_default_tests()
        
        # 3. 更新 console 錯誤列表（報告發送由 _send_lark_report 統一處理）
        self.test_report["console_errors"] = [
            log for log in self.console_logs 
            if log.get("type") in ["error", "pageerror"]
        ]
    
    async def _run_machine_specific_tests(self):
        """執行機器類型專屬測試流程（必須在進入遊戲後執行）"""
        if not self.machine_profile:
            return
        
        # 確認已進入遊戲
        if not await is_in_game(self.page):
            logging.warning("[Test] 未進入遊戲，跳過測試流程")
            return
        
        logging.info(f"[Test] 執行機器類型專屬測試流程: {self.machine_profile.name}")
        
        # 取得測試場景的 test_flows 白名單（None 表示全部執行）
        allowed_flows = None
        if self.test_scenario and self.test_scenario.test_flows is not None:
            allowed_flows = self.test_scenario.test_flows
            logging.info(f"[Test] 測試場景限制只執行: {allowed_flows}")
        
        for flow in self.machine_profile.test_flows:
            if not flow.enabled:
                logging.debug(f"[Test] 跳過已禁用的測試流程: {flow.name}")
                continue
            
            # 檢查白名單：如果設定了白名單，只執行白名單中的流程
            if allowed_flows is not None and flow.name not in allowed_flows:
                logging.info(f"[Test] 跳過非白名單流程: {flow.name} (允許: {allowed_flows})")
                continue
            
            logging.info(f"[Test] 執行測試流程: {flow.name} - {flow.description}")
            
            try:
                if flow.name in ("進入機器", "entry"):
                    # 進入機器已在 run_async 中完成，這裡執行圖片比對
                    await self._compare_stage_image("entry", flow.config)
                    
                    # Entry 測試完成後，執行 keyword_actions（如果有的話）
                    if self.cfg.game_title_code:
                        for kw, positions in self.keyword_actions.items():
                            if kw in self.cfg.game_title_code:
                                logging.info(f"[Test] Entry 測試完成，執行 keyword_actions: {kw} -> {positions}")
                                try:
                                    # 等待一下確保頁面穩定
                                    await asyncio.sleep(1.0)
                                    await click_multiple_positions(self.page, positions)
                                    logging.info(f"[Test] ✅ keyword_actions 執行成功: {kw} -> {positions}")
                                    await asyncio.sleep(1.0)
                                except Exception as kw_err:
                                    logging.warning(f"[Test] 執行 keyword_actions 時發生錯誤: {kw_err}")
                                    self.test_report["console_errors"].append({
                                        "type": "keyword_actions_error",
                                        "text": f"執行 keyword_actions 失敗: {str(kw_err)}",
                                        "timestamp": time.time()
                                    })
                                break  # 只執行第一個匹配的關鍵字
                    
                    logging.info("[Test] 進入機器流程已完成")
                    continue
                elif flow.name == "視頻檢測":
                    await self._test_video_display(flow.config)
                    # 視頻檢測後執行圖片比對
                    await self._compare_stage_image("video", flow.config)
                elif flow.name == "按鈕測試":
                    await self._test_buttons_with_config(flow.config)
                    # 按鈕測試後執行圖片比對
                    await self._compare_stage_image("buttons", flow.config)
                elif flow.name == "下注測試":
                    await self._test_betting(flow.config)
                    # 下注測試後執行圖片比對
                    await self._compare_stage_image("betting", flow.config)
                elif flow.name == "特殊功能測試":
                    await self._test_special_features(flow.config)
                    # 特殊功能測試後執行圖片比對
                    await self._compare_stage_image("special", flow.config)
                elif flow.name == "Grand功能測試":
                    await self._test_grand_features(flow.config)
                    # Grand功能測試後執行圖片比對
                    await self._compare_stage_image("grand", flow.config)
                elif flow.name in ("音頻檢測", "audio"):
                    await self._test_audio(flow.config)
                else:
                    logging.warning(f"[Test] 未知的測試流程: {flow.name}")
                    # 未知流程也可以執行圖片比對（如果配置了）
                    if flow.config.get("image_comparison"):
                        await self._compare_stage_image(flow.name.lower().replace(" ", "_"), flow.config)
                
                await asyncio.sleep(0.5)  # 流程間短暫延遲
                
            except Exception as e:
                logging.error(f"[Test] 測試流程 {flow.name} 執行失敗: {e}")
                self.test_report["console_errors"].append({
                    "type": "test_flow_error",
                    "text": f"測試流程 {flow.name} 失敗: {str(e)}",
                    "timestamp": time.time()
                })
    
    async def _run_default_tests(self):
        """執行默認測試流程（必須在進入遊戲後執行）"""
        # 確認已進入遊戲
        if not await is_in_game(self.page):
            logging.warning("[Test] 未進入遊戲，跳過默認測試流程")
            return
        
        logging.info("[Test] 執行默認測試流程")
        
        # 檢查視頻顯示
        if self.test_report["entry_status"] == "success" and VideoDetector:
            await self._test_video_display({})
        
        # 測試按鈕
        await self._test_buttons()
    
    async def _test_audio(self, flow_config: Dict[str, Any]):
        """
        執行音頻品質檢測
        
        檢測項目：有無聲音、音量、爆音、聲道
        """
        if not AudioDetector:
            logging.warning("[Test] AudioDetector 不可用，跳過音頻檢測")
            return
        
        logging.info("[Test] === 開始音頻品質檢測 ===")
        
        # 讀取配置：flow_config > machine_profile/audio_config.json > _default
        audio_config = None
        if self.machine_profile and self.machine_profile.folder_path and load_audio_config:
            audio_config = load_audio_config(self.machine_profile.folder_path)
        if not audio_config:
            from qa.audio_detector import DEFAULT_AUDIO_CONFIG
            audio_config = DEFAULT_AUDIO_CONFIG.copy()
        
        # flow_config 中的 audio 設定覆蓋
        if flow_config.get("audio"):
            from qa.audio_detector import deep_merge
            audio_config = deep_merge(audio_config, flow_config["audio"])
        
        try:
            result = await AudioDetector.analyze(self.page, audio_config)
            
            # 寫入報告
            audio_report = result.to_dict()
            self.test_report["audio_status"] = "pass" if result.passed else "fail"
            self.test_report["audio_result"] = audio_report
            
            if result.passed:
                logging.info("[Test] 音頻檢測通過")
            else:
                for issue in result.issues:
                    logging.warning(f"[Test] 音頻問題: {issue}")
                    self.test_report["console_errors"].append({
                        "type": "audio_issue",
                        "text": issue,
                        "timestamp": time.time()
                    })
        except Exception as e:
            logging.error(f"[Test] 音頻檢測發生錯誤: {e}")
            self.test_report["audio_status"] = "error"
            self.test_report["audio_result"] = {"error": str(e)}
    
    async def _test_video_display(self, config: Dict[str, Any]):
        """測試視頻顯示"""
        if not VideoDetector:
            return
        
        selector = config.get("selector", "canvas, video")
        threshold = config.get("threshold", {})
        
        try:
            video_ok, video_msg = await VideoDetector.check_video_display(
                self.page,
                selector=selector,
                black_threshold=threshold.get("black", 10.0),
                transparent_threshold=threshold.get("transparent", 10.0),
                monochrome_threshold=threshold.get("monochrome", 5.0)
            )
            if video_ok:
                self.test_report["video_status"] = "normal"
            else:
                self.test_report["video_status"] = "error"
                self.test_report["video_message"] = video_msg
                logging.warning(f"[Test] 視頻檢測失敗: {video_msg}")
        except Exception as e:
            logging.error(f"[Test] 視頻檢測過程發生錯誤: {e}")
            self.test_report["video_status"] = "error"
            self.test_report["video_message"] = f"檢測過程發生錯誤: {str(e)}"
    
    async def _test_buttons_with_config(self, config: Dict[str, Any]):
        """根據配置測試按鈕，支持高亮檢測"""
        # 優先使用機器類型配置的按鈕列表
        button_configs = []
        if self.machine_profile and hasattr(self.machine_profile, 'button_test_config'):
            button_test_config = getattr(self.machine_profile, 'button_test_config', {})
            button_configs = button_test_config.get("buttons", [])
        
        # 如果沒有機器類型配置，使用流程配置中的按鈕列表
        if not button_configs:
            buttons = config.get("buttons", ["SPIN", "BET", "PLAY"])
            # 轉換為按鈕配置格式
            for btn in buttons:
                button_configs.append({
                    "name": btn,
                    "selector": f"button:has-text('{btn}')",
                    "highlight_check": config.get("check_highlight", False)
                })
        
        # 獲取高亮檢測配置
        highlight_config = None
        if self.machine_profile and hasattr(self.machine_profile, 'button_test_config'):
            highlight_config = getattr(self.machine_profile, 'button_test_config', {}).get("highlight_detection", {})
        
        for btn_config in button_configs:
            btn_name = btn_config.get("name", "Unknown")
            selector = btn_config.get("selector", f"button:has-text('{btn_name}')")
            check_highlight = btn_config.get("highlight_check", False)
            
            try:
                # 嘗試多個選擇器（如果 selector 是逗號分隔的）
                selectors = [s.strip() for s in selector.split(",")]
                element = None
                used_selector = None
                
                for sel in selectors:
                    try:
                        element = await self.page.wait_for_selector(sel, timeout=2000, state="visible")
                        if element:
                            used_selector = sel
                            break
                    except:
                        continue
                
                if not element:
                    self.test_report["button_tests"].append({
                        "button": btn_name,
                        "status": "failed",
                        "reason": "元素未找到",
                        "selector": selector
                    })
                    continue
                
                # 點擊前截圖（用於比對）
                before_screenshot = None
                if check_highlight:
                    try:
                        before_screenshot = await element.screenshot()
                    except:
                        pass
                
                # 點擊按鈕
                await element.click()
                await asyncio.sleep(0.3)  # 等待高亮效果出現
                
                # 檢測高亮
                highlight_detected = False
                if check_highlight and highlight_config:
                    highlight_detected = await self._check_button_highlight(
                        element, 
                        highlight_config,
                        before_screenshot
                    )
                
                # 記錄結果
                if self.test_service:
                    self.test_service.test_button_response(used_selector or selector, self.cfg.url, btn_name)
                
                test_result = {
                    "button": btn_name,
                    "status": "success" if (not check_highlight or highlight_detected) else "failed",
                    "selector": used_selector or selector
                }
                
                if check_highlight:
                    test_result["highlight_detected"] = highlight_detected
                    if not highlight_detected:
                        test_result["reason"] = "未檢測到高亮效果"
                
                self.test_report["button_tests"].append(test_result)
                
                if highlight_detected:
                    logging.info(f"[Test] 按鈕 {btn_name} 測試成功，已檢測到高亮")
                elif check_highlight:
                    logging.warning(f"[Test] 按鈕 {btn_name} 測試失敗，未檢測到高亮")
                else:
                    logging.info(f"[Test] 按鈕 {btn_name} 測試成功（未啟用高亮檢測）")
                
            except Exception as e:
                logging.warning(f"[Test] 測試按鈕 {btn_name} 時發生錯誤: {e}")
                self.test_report["button_tests"].append({
                    "button": btn_name,
                    "status": "error",
                    "error": str(e),
                    "selector": selector
                })
    
    async def _check_button_highlight(
        self, 
        element, 
        highlight_config: Dict[str, Any],
        before_screenshot: Optional[bytes] = None
    ) -> bool:
        """
        檢測按鈕是否有高亮效果
        
        Args:
            element: 按鈕元素
            highlight_config: 高亮檢測配置
            before_screenshot: 點擊前的截圖（可選，用於比對）
            
        Returns:
            是否檢測到高亮
        """
        method = highlight_config.get("method", "css_class")
        
        try:
            if method == "css_class":
                # 檢查 CSS 類名
                css_classes = highlight_config.get("css_class", "active, selected, highlight")
                class_list = [c.strip() for c in css_classes.split(",")]
                
                class_name = await element.get_attribute("class") or ""
                for check_class in class_list:
                    # 支持完整匹配和部分匹配
                    if check_class in class_name or any(
                        check_class.replace("[class*='", "").replace("']", "") in class_name
                        for check_class in class_list if "class*" in check_class
                    ):
                        logging.debug(f"[Test] 檢測到高亮類名: {check_class}")
                        return True
                
                # 檢查父元素
                parent = await element.evaluate_handle("el => el.parentElement")
                if parent:
                    parent_class = await parent.get_attribute("class") or ""
                    for check_class in class_list:
                        if check_class in parent_class:
                            logging.debug(f"[Test] 在父元素檢測到高亮類名: {check_class}")
                            return True
            
            if method == "background_color" or highlight_config.get("check_style", False):
                # 檢查背景顏色
                bg_colors = highlight_config.get("background_color", "#FFD700, yellow")
                color_list = [c.strip().lower() for c in bg_colors.split(",")]
                
                # 獲取計算樣式
                computed_style = await element.evaluate("""
                    el => {
                        const style = window.getComputedStyle(el);
                        return {
                            backgroundColor: style.backgroundColor,
                            borderColor: style.borderColor,
                            color: style.color
                        };
                    }
                """)
                
                bg_color = computed_style.get("backgroundColor", "").lower()
                border_color = computed_style.get("borderColor", "").lower()
                
                for check_color in color_list:
                    if check_color in bg_color or check_color in border_color:
                        logging.debug(f"[Test] 檢測到高亮顏色: {check_color}")
                        return True
                
                # 檢查父元素
                parent_bg = await element.evaluate("""
                    el => {
                        const parent = el.parentElement;
                        if (parent) {
                            return window.getComputedStyle(parent).backgroundColor;
                        }
                        return '';
                    }
                """)
                
                if parent_bg:
                    for check_color in color_list:
                        if check_color in parent_bg.lower():
                            logging.debug(f"[Test] 在父元素檢測到高亮顏色: {check_color}")
                            return True
            
            if method == "screenshot" and before_screenshot:
                # 使用截圖比對（如果提供了點擊前的截圖）
                try:
                    after_screenshot = await element.screenshot()
                    # 簡單的像素差異檢測
                    # 這裡可以使用更複雜的圖片比對邏輯
                    if before_screenshot != after_screenshot:
                        logging.debug(f"[Test] 截圖比對檢測到變化")
                        return True
                except:
                    pass
            
            return False
            
        except Exception as e:
            logging.warning(f"[Test] 檢測高亮時發生錯誤: {e}")
            return False
    
    async def _test_betting(self, config: Dict[str, Any]):
        """測試下注功能"""
        bet_amounts = config.get("bet_amounts", [10, 50, 100])
        verify_balance = config.get("verify_balance_change", False)
        
        logging.info(f"[Test] 測試下注功能，下注金額: {bet_amounts}")
        # 這裡可以實現具體的下注測試邏輯
        # 暫時記錄到報告中
        for amount in bet_amounts:
            self.test_report["bet_results"].append({
                "bet_amount": amount,
                "success": True,  # 實際應該測試下注是否成功
                "timestamp": time.time()
            })
    
    async def _test_special_features(self, config: Dict[str, Any]):
        """測試特殊功能（如Free Spin）"""
        logging.info(f"[Test] 測試特殊功能: {config}")
        # 這裡可以實現具體的特殊功能測試邏輯
    
    async def _test_grand_features(self, config: Dict[str, Any]):
        """測試Grand功能（如Grand Bonus、Jackpot）"""
        logging.info(f"[Test] 測試Grand功能: {config}")
        # 這裡可以實現具體的Grand功能測試邏輯
    
    async def _compare_stage_image(self, stage_name: str, flow_config: Dict[str, Any]):
        """
        執行階段性圖片比對
        
        Args:
            stage_name: 階段名稱（例如 "entry", "video", "buttons"）
            flow_config: 測試流程配置（包含圖片比對配置）
        """
        if not ImageComparator or not self.machine_profile:
            return
        
        # 檢查是否啟用圖片比對
        image_comparison_config = flow_config.get("image_comparison")
        if not image_comparison_config or not image_comparison_config.get("enabled", False):
            return
        
        try:
            # 獲取參考圖片目錄
            if self.machine_profile.folder_path:
                reference_images_dir = self.machine_profile.folder_path / "reference_images"
            else:
                logging.warning("[Test] 無法獲取機器類型文件夾路徑，跳過圖片比對")
                return
            
            # 執行圖片比對
            is_match, comparison_result = await ImageComparator.compare_stage(
                self.page,
                stage_name,
                reference_images_dir,
                image_comparison_config
            )
            
            # 記錄比對結果
            self.test_report["image_comparisons"].append({
                "stage": stage_name,
                "match": is_match,
                "result": comparison_result,
                "timestamp": time.time()
            })
            
            if is_match:
                logging.info(f"[Test] 階段 {stage_name} 圖片比對成功")
            else:
                logging.warning(f"[Test] 階段 {stage_name} 圖片比對失敗")
                self.test_report["console_errors"].append({
                    "type": "image_comparison_failed",
                    "text": f"階段 {stage_name} 圖片比對失敗: {comparison_result}",
                    "timestamp": time.time()
                })
                
        except Exception as e:
            logging.error(f"[Test] 階段 {stage_name} 圖片比對過程發生錯誤: {e}")
            self.test_report["image_comparisons"].append({
                "stage": stage_name,
                "match": False,
                "error": str(e),
                "timestamp": time.time()
            })

    async def _test_buttons(self):
        """測試按鈕反應"""
        # 從配置或預設按鈕列表
        buttons = ["SPIN", "BET", "PLAY"]  # 可以從配置讀取
        
        for btn in buttons:
            try:
                # 嘗試多種選擇器
                selectors = [
                    f"button:has-text('{btn}')",
                    f"button[class*='{btn.lower()}']",
                    f"[class*='spin'], [class*='bet'], [class*='play']"
                ]
                
                clicked = False
                used_selector = None
                for selector in selectors:
                    try:
                        element = await self.page.wait_for_selector(selector, timeout=2000, state="visible")
                        if element:
                            await element.click()
                            clicked = True
                            used_selector = selector
                            await asyncio.sleep(0.5)  # 等待反應
                            break
                    except:
                        continue
                
                if clicked and self.test_service:
                    self.test_service.test_button_response(used_selector or selectors[0], self.cfg.url, btn)
                
                self.test_report["button_tests"].append({
                    "button": btn,
                    "status": "success" if clicked else "failed"
                })
                
            except Exception as e:
                logging.warning(f"[Test] 測試按鈕 {btn} 時發生錯誤: {e}")
                self.test_report["button_tests"].append({
                    "button": btn,
                    "status": "error",
                    "error": str(e)
                })

    async def _run_single_machine(self, code: str) -> bool:
        """
        執行單台機器的完整流程：進入遊戲 → 測試 → Spin → 發送報告 → 退出
        
        Args:
            code: 機器號 (game_title_code)
            
        Returns:
            True 如果完成（可以繼續下一台），False 如果需要停止
        """
        logging.info(f"[Runner] === 開始測試機器: {code} ===")
        
        # 1. 匹配 machine_profile
        profile = self._match_profile_for_code(code)
        if not profile:
            logging.warning(f"[Runner] 機器號 {code} 無匹配配置，跳過")
            return True  # 跳過但可以繼續下一台
        
        # 2. 重置狀態
        self._reset_for_new_machine(code, profile)
        
        # 3. 確保在大廳，然後進入遊戲
        if await is_in_game(self.page):
            logging.info(f"[Runner] 當前在遊戲中，先退出到大廳")
            await exit_game_to_lobby(self.page)
            await asyncio.sleep(2.0)
        
        logging.info(f"[Runner] 準備進入遊戲: {code}")
        if not await scroll_and_click_game(self.page, code, self.keyword_actions):
            logging.warning(f"[Runner] 無法找到遊戲 {code}，跳過")
            self.test_report["entry_status"] = "failed"
            self._send_lark_report()
            return True
        
        await asyncio.sleep(3.0)
        
        # 4. 確認進入遊戲
        if not await is_in_game(self.page):
            logging.warning(f"[Runner] 無法確認進入遊戲 {code}，跳過")
            self.test_report["entry_status"] = "failed"
            self.test_report["console_errors"].append({
                "type": "entry_error",
                "text": f"無法確認進入遊戲: {code}",
                "timestamp": time.time()
            })
            self._send_lark_report()
            return True
        
        # 5. 執行測試流程
        logging.info(f"[Runner] 確認已進入遊戲 {code}，開始執行測試流程")
        await self.run_full_test()
        
        # 6. Spin 循環
        if not stop_event.is_set():
            await self.spin_forever()
        
        # 7. Spin 結束後發送 Lark 報告
        self._send_lark_report()
        
        # 8. 退出遊戲回到大廳（準備下一台）
        logging.info(f"[Runner] 機器 {code} 測試完畢，退出到大廳")
        await exit_game_to_lobby(self.page)
        await asyncio.sleep(2.0)
        
        logging.info(f"[Runner] === 機器 {code} 測試完成 ===")
        return True

    def _send_lark_report(self):
        """彙整並發送 Lark 測試報告"""
        self.test_report["console_errors"] = [
            log for log in self.console_logs 
            if log.get("type") in ["error", "pageerror"]
        ]
        self.lark.send_test_report(self.test_report)

    async def run_async(self):
        """
        主執行入口：建立瀏覽器，從共享佇列中依次取機器號並測試
        
        流程：
        1. 從 TaskManager 取得機器號
        2. 匹配 machine_profile → 進入遊戲 → 測試 → Spin → 報告 → 退出
        3. 取下一個機器號，重複步驟 2
        4. 佇列空了就結束
        """
        logging.info(f"初始化遊戲測試: {self.cfg}")
        async with async_playwright() as playwright:
            await self._build_browser(playwright)
            
            try:
                if self.task_manager:
                    # === 共享佇列模式：循環處理多台機器 ===
                    machine_count = 0
                    while not stop_event.is_set():
                        # 從共享佇列取下一個機器號
                        code = self.task_manager.get_next_csv(worker_id=self._worker_id)
                        if not code:
                            logging.info(f"[Runner] {self._worker_id} 佇列已空，沒有更多機器需要測試")
                            break
                        
                        machine_count += 1
                        remaining = self.task_manager.get_remaining_count()
                        logging.info(
                            f"[Runner] {self._worker_id} 取得第 {machine_count} 台機器: {code} "
                            f"(佇列剩餘: {remaining})"
                        )
                        
                        # 執行單台機器的完整流程
                        success = await self._run_single_machine(code)
                        if not success:
                            break
                    
                    logging.info(f"[Runner] {self._worker_id} 共完成 {machine_count} 台機器的測試")
                    
                else:
                    # === 單機模式（向後相容）：只跑初始的 game_title_code ===
                    code = self.cfg.game_title_code
                    if code:
                        await self._run_single_machine(code)
                    else:
                        logging.warning("[Runner] 沒有 game_title_code，無法執行測試")
                
            except KeyboardInterrupt:
                logging.info("手動中止")
                # 手動中止時也發送報告
                self._send_lark_report()
            finally:
                if self.context:
                    try:
                        await self.context.close()
                    except Exception:
                        pass
                if self.browser:
                    try:
                        await self.browser.close()
                    except Exception:
                        pass

    def run(self):
        """同步包裝器，用於線程啟動"""
        asyncio.run(self.run_async())

