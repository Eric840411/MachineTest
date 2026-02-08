"""遊戲導航相關功能（進入/離開遊戲）"""
import asyncio
import logging
import traceback
from typing import Optional, Dict, List
from playwright.async_api import Page, TimeoutError as PWTimeoutError

from core.browser import wait_for_selector, wait_for_all_selectors
from game.actions import click_multiple_positions


async def is_in_game(page: Page) -> bool:
    """
    檢查是否在遊戲中（而非大廳）
    回傳 True 如果在遊戲中，False 如果在大廳
    """
    if not page:
        return False
        
    try:
        # 先檢查大廳元素（優先判斷）
        try:
            lobby_elem = await page.query_selector("#grid_gm_item")
            if lobby_elem and await lobby_elem.is_visible():
                logging.info("檢測到大廳元素，當前在大廳")
                return False
        except Exception:
            pass
        
        # 檢查遊戲中的指標元素
        game_indicators = [
            ".my-button.btn_spin",      # Spin 按鈕
            ".balance-bg.hand_balance", # 餘額顯示
            ".h-balance.hand_balance",  # 特殊機台餘額顯示
        ]
        
        for indicator in game_indicators:
            try:
                elements = await page.query_selector_all(indicator)
                for elem in elements:
                    if await elem.is_visible():
                        return True
            except Exception:
                continue
        
        # 如果都找不到，預設認為不在遊戲中
        logging.debug("無法確定頁面狀態，預設認為不在遊戲中")
        return False
        
    except Exception as e:
        logging.warning(f"檢查遊戲狀態時發生錯誤: {e}")
        return False


async def scroll_and_click_game(
    page: Page,
    game_title_code: str,
    keyword_actions: Dict[str, List[str]]
) -> bool:
    """
    在大廳尋找 title 包含 game_title_code 的卡片，點擊後嘗試點 Join。
    若 actions.json 定義了 keyword_actions，Join 後可附加點擊流程。
    """
    if not page:
        return False
        
    try:
        # 先檢查是否已在遊戲中
        if await is_in_game(page):
            logging.info("✅ 已在遊戲內，跳過大廳找卡片流程")
            return True
        
        # 嘗試等待大廳元素出現
        try:
            items = await wait_for_all_selectors(page, "#grid_gm_item", timeout=10)
        except PWTimeoutError:
            logging.warning(f"⚠️ 等待大廳元素 'grid_gm_item' 超時（10秒），可能不在大廳頁面或頁面未載入完成")
            # 嘗試檢查當前頁面狀態
            try:
                current_url = page.url
                page_title = await page.title()
                logging.info(f"當前 URL: {current_url[:100]}...")
                logging.info(f"當前標題: {page_title}")
                # 檢查是否在遊戲中（可能已經在遊戲內，只是找不到大廳元素）
                if await is_in_game(page):
                    logging.info("✅ 檢測到已在遊戲內（雖然找不到大廳元素），返回成功")
                    return True
            except Exception:
                pass
            return False
        
        if not items or len(items) == 0:
            logging.warning(f"⚠️ 大廳中沒有找到任何遊戲卡片（grid_gm_item 為空）")
            return False
            
        for item in items:
            title = await item.get_attribute("title")
            if title and game_title_code in title:
                try:
                    await item.scroll_into_view_if_needed()
                    # 使用 JavaScript 強制點擊
                    await page.evaluate("(el) => el.click()", item)
                    logging.info(f"點擊遊戲卡片: {title}")
                    await asyncio.sleep(1.2)
                except Exception:
                    continue

                # Join 按鈕不一定是卡片內部 DOM；改抓全局 gm-info-box
                # 注意：Join 按鈕可能不會每次出現，這是正常的
                try:
                    join_btns = await wait_for_all_selectors(
                        page,
                        "//div[contains(@class, 'gm-info-box')]//span[normalize-space(text())='Join']",
                        timeout=3,  # 縮短超時時間，快速判斷是否存在
                    )
                    for btn in join_btns:
                        try:
                            # 使用 JavaScript 強制點擊
                            await page.evaluate("(el) => el.click()", btn)
                            logging.info("點擊 Join 進入遊戲")
                            await asyncio.sleep(3.0)
                            break
                        except Exception as e:
                            # 處理 stale element reference 或其他錯誤，直接跳過
                            logging.debug(f"點擊 Join 時發生錯誤（已跳過）: {e}")
                except PWTimeoutError:
                    # Join 按鈕不存在是正常的，直接跳過
                    logging.info("Join 按鈕未出現（這是正常的），跳過 Join 步驟")
                except Exception as e:
                    # 其他錯誤也直接跳過，不重試
                    logging.info(f"Join 按鈕查找失敗（已跳過）: {e}")
                
                # 不再在這裡執行 keyword_actions
                # keyword_actions 將在 entry 測試完成後執行
                
                # 無論 Join 是否成功，都返回 True 讓流程繼續
                return True
                    
        logging.warning(f"大廳找不到遊戲: {game_title_code}")
    except Exception as e:
        logging.error(f"scroll_and_click_game 失敗: {e}")
        logging.error(traceback.format_exc())
    return False


async def find_cashout_button(page: Page):
    """
    尋找 Cashout 按鈕，直接定位到 handle-main 底層的按鈕
    避免被 select-main 遮罩層阻擋
    """
    if not page:
        return None
        
    # 優先使用 handle-main 底層的選擇器
    handle_main_selectors = [
        ".handle-main .my-button.btn_cashout",
        ".handle-main .my-button--normal.btn_cashout",
        ".handle-main .my-button.my-button--normal.btn_cashout",
        ".handle-main .btn_cashout",
        ".handle-main div[class*='btn_cashout']",
        ".handle-main button[class*='cashout']",
    ]
    
    # 嘗試 handle-main 底層的選擇器
    for selector in handle_main_selectors:
        try:
            logging.debug(f"🔍 嘗試 handle-main 選擇器: {selector}")
            elements = await page.query_selector_all(selector)
            
            for elem in elements:
                try:
                    is_displayed = await elem.is_visible()
                    is_enabled = await elem.is_enabled()
                    box = await elem.bounding_box()
                    has_size = box and box['width'] > 0 and box['height'] > 0
                    
                    # 檢查元素是否在 handle-main 內
                    in_handle_main = await page.evaluate(
                        "el => !!el.closest('.handle-main')", elem
                    )
                    
                    logging.debug(f"🔍 handle-main 元素狀態: displayed={is_displayed}, enabled={is_enabled}, has_size={has_size}, in_handle_main={in_handle_main}")
                    
                    if is_displayed and is_enabled and has_size and in_handle_main:
                        logging.info(f"✅ 找到 handle-main 底層 Cashout 按鈕，使用選擇器: {selector}")
                        return elem
                except Exception as e:
                    logging.debug(f"檢查 handle-main 元素狀態時發生錯誤: {e}")
                    continue
        except Exception as e:
            logging.debug(f"handle-main 選擇器 {selector} 失敗: {e}")
            continue
    
    # 如果 handle-main 選擇器都失敗，嘗試其他備用選擇器
    logging.info("⚠️ handle-main 選擇器都失敗，嘗試備用選擇器...")
    
    backup_selectors = [
        ".my-button.btn_cashout",
        ".btn_cashout",
        ".my-button--normal.btn_cashout",
        "div.my-button.btn_cashout",
        "div[class*='btn_cashout']",
        ".my-button.my-button--normal.btn_cashout",
        "button[class*='cashout']",
        "button[class*='cash']",
        "//div[contains(@class, 'btn_cashout')]",
        "//div[contains(@class, 'my-button') and contains(@class, 'btn_cashout')]",
        "//button[contains(@class, 'cashout')]",
        "//button[contains(text(), 'Cashout')]",
        "//button[contains(text(), 'Cash')]",
    ]
    
    for selector in backup_selectors:
        try:
            if selector.startswith("//"):
                elements = await page.query_selector_all(selector)
            else:
                elements = await page.query_selector_all(selector)
            
            for elem in elements:
                try:
                    is_displayed = await elem.is_visible()
                    is_enabled = await elem.is_enabled()
                    box = await elem.bounding_box()
                    has_size = box and box['width'] > 0 and box['height'] > 0
                    
                    if is_displayed and is_enabled and has_size:
                        logging.info(f"✅ 找到 Cashout 按鈕，使用選擇器: {selector}")
                        return elem
                except Exception as e:
                    logging.debug(f"檢查元素狀態時發生錯誤: {e}")
                    continue
        except Exception as e:
            logging.debug(f"選擇器 {selector} 失敗: {e}")
            continue
    
    logging.warning("⚠️ 所有 Cashout 按鈕選擇器都失敗")
    return None


async def low_balance_exit_and_reenter(
    page: Page,
    bal: int,
    game_title_code: Optional[str],
    keyword_actions: Dict[str, List[str]]
):
    """標準退出流程"""
    logging.warning(f"BAL 過低（{bal}），執行退出流程")
    try:
        quit_btn = await find_cashout_button(page)
        if quit_btn:
            # 使用 JavaScript 強制點擊
            await page.evaluate("(el) => el.click()", quit_btn)
            await asyncio.sleep(1.0)
        else:
            logging.error("❌ 找不到 Cashout 按鈕，無法執行退出流程")
            return False

        try:
            exit_btn = await wait_for_selector(page, ".function-btn .reserve-btn-gray", timeout=2)
            if exit_btn:
                # 使用 JavaScript 強制點擊
                await page.evaluate("(el) => el.click()", exit_btn)
                logging.info("[ExitFlow] 已點擊 Exit / Exit To Lobby")
                await asyncio.sleep(1.0)
        except PWTimeoutError:
            logging.info("[ExitFlow] 找不到 Exit，直接嘗試 Confirm")

        confirm_btn = await wait_for_selector(
            page, "//button[.//div[normalize-space(text())='Confirm']]", timeout=2
        )
        if confirm_btn:
            # 使用 JavaScript 強制點擊
            await page.evaluate("(el) => el.click()", confirm_btn)
            await asyncio.sleep(3.0)
        
        # ✅ 驗證是否成功回到大廳
        if not await is_in_game(page):
            logging.info("[ExitFlow] 已成功回到大廳")
        else:
            logging.warning("[ExitFlow] 退出後仍在遊戲中，可能需要額外等待")
            await asyncio.sleep(2.0)
    except Exception as e:
        logging.error(f"退出流程失敗: {e}")

    # ✅ 重新進入遊戲，並驗證是否成功進入
    if game_title_code:
        logging.info(f"[ExitFlow] 準備重新進入遊戲: {game_title_code}")
        if await scroll_and_click_game(page, game_title_code, keyword_actions):
            # 等待遊戲加載並驗證是否成功進入
            await asyncio.sleep(3.0)
            if await is_in_game(page):
                logging.info("[ExitFlow] 成功重新進入遊戲")
            else:
                logging.warning("[ExitFlow] 重新進入遊戲後仍在大廳，可能需要額外等待")
                await asyncio.sleep(2.0)
        else:
            logging.warning("[ExitFlow] 重新進入遊戲失敗")


async def exit_game_to_lobby(page: Page) -> bool:
    """
    退出遊戲回到大廳（不重新進入遊戲）
    
    用於在完成一台機器的測試後，退出到大廳以便進入下一台機器。
    
    Returns:
        True 如果成功回到大廳，False 如果失敗
    """
    try:
        # 如果已在大廳，直接返回
        if not await is_in_game(page):
            logging.info("[ExitToLobby] 已在大廳中")
            return True
        
        # 點擊 Cashout 按鈕
        quit_btn = await find_cashout_button(page)
        if quit_btn:
            await page.evaluate("(el) => el.click()", quit_btn)
            await asyncio.sleep(1.0)
        else:
            logging.error("[ExitToLobby] 找不到 Cashout 按鈕")
            return False
        
        # 嘗試點擊 Exit
        try:
            exit_btn = await wait_for_selector(page, ".function-btn .reserve-btn-gray", timeout=2)
            if exit_btn:
                await page.evaluate("(el) => el.click()", exit_btn)
                logging.info("[ExitToLobby] 已點擊 Exit / Exit To Lobby")
                await asyncio.sleep(1.0)
        except PWTimeoutError:
            logging.info("[ExitToLobby] 找不到 Exit，直接嘗試 Confirm")
        
        # 嘗試點擊 Confirm
        confirm_btn = await wait_for_selector(
            page, "//button[.//div[normalize-space(text())='Confirm']]", timeout=2
        )
        if confirm_btn:
            await page.evaluate("(el) => el.click()", confirm_btn)
            await asyncio.sleep(3.0)
        
        # 驗證是否成功回到大廳
        if not await is_in_game(page):
            logging.info("[ExitToLobby] 已成功回到大廳")
            return True
        else:
            logging.warning("[ExitToLobby] 退出後仍在遊戲中，再等待一下")
            await asyncio.sleep(2.0)
            result = not await is_in_game(page)
            if result:
                logging.info("[ExitToLobby] 延遲後成功回到大廳")
            else:
                logging.warning("[ExitToLobby] 仍無法回到大廳")
            return result
            
    except Exception as e:
        logging.error(f"[ExitToLobby] 退出流程失敗: {e}")
        return False


async def fast_low_balance_exit_and_reenter(
    page: Page,
    bal: int,
    game_title_code: Optional[str],
    keyword_actions: Dict[str, List[str]]
):
    """超快頻率的快速退出流程"""
    logging.warning(f"BAL 過低（{bal}），執行快速退出流程")
    try:
        quit_btn = await find_cashout_button(page)
        if quit_btn:
            # 使用 JavaScript 強制點擊
            await page.evaluate("(el) => el.click()", quit_btn)
            await asyncio.sleep(0.5)  # 減少等待時間
        else:
            logging.error("❌ 找不到 Cashout 按鈕，無法執行快速退出流程")
            return False

        try:
            exit_btn = await wait_for_selector(page, ".function-btn .reserve-btn-gray", timeout=1)
            if exit_btn:
                # 使用 JavaScript 強制點擊
                await page.evaluate("(el) => el.click()", exit_btn)
                logging.info("[FastExitFlow] 已點擊 Exit / Exit To Lobby")
                await asyncio.sleep(0.5)  # 減少等待時間
        except PWTimeoutError:
            logging.info("[FastExitFlow] 找不到 Exit，直接嘗試 Confirm")

        confirm_btn = await wait_for_selector(
            page, "//button[.//div[normalize-space(text())='Confirm']]", timeout=1
        )
        if confirm_btn:
            # 使用 JavaScript 強制點擊
            await page.evaluate("(el) => el.click()", confirm_btn)
            await asyncio.sleep(1.5)  # 減少等待時間
        
        # ✅ 驗證是否成功回到大廳
        if not await is_in_game(page):
            logging.info("[FastExitFlow] 已成功回到大廳")
        else:
            logging.warning("[FastExitFlow] 退出後仍在遊戲中，可能需要額外等待")
            await asyncio.sleep(1.0)
    except Exception as e:
        logging.error(f"快速退出流程失敗: {e}")

    # ✅ 重新進入遊戲，並驗證是否成功進入
    if game_title_code:
        logging.info(f"[FastExitFlow] 準備重新進入遊戲: {game_title_code}")
        if await scroll_and_click_game(page, game_title_code, keyword_actions):
            # 等待遊戲加載並驗證是否成功進入
            await asyncio.sleep(2.0)  # 快速流程使用較短等待時間
            if await is_in_game(page):
                logging.info("[FastExitFlow] 成功重新進入遊戲")
            else:
                logging.warning("[FastExitFlow] 重新進入遊戲後仍在大廳，可能需要額外等待")
                await asyncio.sleep(1.0)
        else:
            logging.warning("[FastExitFlow] 重新進入遊戲失敗")

