"""餘額相關功能"""
import logging
from typing import Optional
from playwright.async_api import Page

# 特殊機台集合：影響餘額 selector 與 spin 按鈕 selector 的選擇
SPECIAL_GAMES = {"BULLBLITZ", "ALLABOARD"}


async def parse_balance(page: Page, is_special: bool) -> Optional[int]:
    """
    擷取餘額文字並轉換為 int；若格式異常回傳 None
    - 特殊機台與一般機台使用不同的 selector
    """
    if not page:
        return None
        
    sel = ".h-balance.hand_balance .text2" if is_special else ".balance-bg.hand_balance .text2"
    try:
        el = await page.query_selector(sel)
        if el:
            txt = (await el.inner_text() or "").replace(",", "").strip()
            # 容錯：只保留數字
            nums = "".join(ch for ch in txt if ch.isdigit())
            return int(nums) if nums else None
    except Exception:
        pass
    return None

