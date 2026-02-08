"""瀏覽器工具函數"""
import asyncio
import logging
from playwright.async_api import Page, TimeoutError as PWTimeoutError


async def wait_for_selector(page: Page, selector: str, timeout: float = 8.0, state: str = "attached"):
    """等待單一元素存在，回傳 ElementHandle；逾時拋例外
    state: "attached" (存在即可), "visible" (必須可見), "hidden" (必須隱藏)
    """
    return await page.wait_for_selector(selector, timeout=timeout * 1000, state=state)


async def wait_for_all_selectors(page: Page, selector: str, timeout: float = 8.0, state: str = "attached"):
    """等待多個元素存在，回傳 ElementHandle 清單；逾時拋例外
    state: "attached" (存在即可), "visible" (必須可見), "hidden" (必須隱藏)
    """
    await page.wait_for_selector(selector, timeout=timeout * 1000, state=state)
    return await page.query_selector_all(selector)


async def safe_click(page: Page, selector: str, timeout: float = 5.0) -> bool:
    """通用點擊：等待元素存在並使用 JavaScript 強制點擊，失敗不拋例外而回傳 False"""
    try:
        element = await page.wait_for_selector(selector, timeout=timeout * 1000, state="attached")
        if element:
            try:
                await element.scroll_into_view_if_needed()
            except Exception:
                pass
            await asyncio.sleep(0.15)  # 很短暫的穩定延遲
            # 使用 JavaScript 強制點擊（可點擊 hidden 元素）
            await page.evaluate("(el) => el.click()", element)
            return True
        return False
    except Exception as e:
        logging.warning(f"safe_click failed: {e}")
        return False


async def is_404_page(page: Page) -> bool:
    """
    檢測當前頁面是否為 404 錯誤頁面
    回傳 True 如果是 404 頁面，False 如果不是
    """
    try:
        # 檢查頁面標題
        page_title = (await page.title()).lower()
        if "404" in page_title or "not found" in page_title:
            logging.warning("🚨 檢測到 404 頁面（通過標題）")
            return True
        
        # 檢查頁面內容
        page_content = (await page.content()).lower()
        if "404 not found" in page_content or "nginx/1.20.1" in page_content:
            logging.warning("🚨 檢測到 404 頁面（通過內容）")
            return True
        
        # 檢查 URL
        current_url = page.url.lower()
        if "404" in current_url:
            logging.warning("🚨 檢測到 404 頁面（通過 URL）")
            return True
        
        return False
        
    except Exception as e:
        logging.debug(f"檢測 404 頁面時發生錯誤: {e}")
        return False

