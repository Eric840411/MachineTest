"""遊戲動作相關功能"""
import asyncio
import logging
from typing import List, Optional
from playwright.async_api import Page, TimeoutError as PWTimeoutError

from core.browser import wait_for_selector


async def click_spin(page: Page, is_special: bool) -> bool:
    """
    依特殊機台與否選擇不同 Spin selector，成功點擊回傳 True
    """
    if not page:
        return False
        
    spin_selector = ".btn_spin .my-button" if is_special else ".my-button.btn_spin"
    try:
        btn = await wait_for_selector(page, spin_selector, timeout=8)
        if btn:
            # 使用 JavaScript 強制點擊
            await page.evaluate("(el) => el.click()", btn)
            return True
        return False
    except PWTimeoutError:
        # 元素不存在或超時
        current_url = page.url if page else "未知"
        current_title = await page.title() if page else "未知"
        logging.warning(
            f"[Spin] 找不到 Spin 按鈕（選擇器: {spin_selector}, 特殊機台: {is_special}）\n"
            f"  當前 URL: {current_url}\n"
            f"  頁面標題: {current_title}"
        )
        return False
    except Exception as e:
        # 其他異常
        current_url = page.url if page else "未知"
        current_title = await page.title() if page else "未知"
        logging.warning(
            f"[Spin] 點擊 Spin 按鈕時發生錯誤（選擇器: {spin_selector}, 特殊機台: {is_special}）\n"
            f"  錯誤: {e}\n"
            f"  當前 URL: {current_url}\n"
            f"  頁面標題: {current_title}"
        )
        return False


async def click_multiple_positions(page: Page, positions: List[str], click_take: bool = False):
    """
    依序點擊由文字（span 的可見文字）定位的節點；必要時補點 Take 按鈕
    - positions：["X1","X2",...]
    - click_take：True 時，額外點 .my-button.btn_take
    - 統一使用 JavaScript 強制點擊（可點擊 hidden 元素）
    - 快速連續點擊所有座標，不等待元素可見
    """
    if not page:
        return
    
    logging.info(f"開始連續點擊 {len(positions)} 個座標點: {positions}")
        
    for pos in positions:
        try:
            # 直接查詢元素（不等待，因為元素可能已經存在但 hidden）
            elems = await page.query_selector_all(f"//span[normalize-space(text())='{pos}']")
            
            if elems and len(elems) > 0:
                elem = elems[0]
                # 統一使用 JavaScript 強制點擊（不需要滾動，因為是 hidden 元素）
                await page.evaluate("(el) => el.click()", elem)
                logging.info(f"已點擊座標位: {pos}")
                await asyncio.sleep(1.0)  # 減少延遲時間，加快點擊速度
            else:
                logging.warning(f"找不到座標位 {pos} 的元素")
        except Exception as e:
            logging.warning(f"點擊座標位 {pos} 時發生錯誤: {e}")

    if click_take:
        try:
            take_btn = await wait_for_selector(page, ".my-button.btn_take", timeout=3, state="attached")
            if take_btn:
                # 統一使用 JavaScript 強制點擊
                await page.evaluate("(el) => el.click()", take_btn)
                logging.info("已點擊 Take 按鈕")
        except Exception as e:
            logging.warning(f"找不到 Take 按鈕: {e}")
    
    logging.info(f"完成連續點擊 {len(positions)} 個座標點")


