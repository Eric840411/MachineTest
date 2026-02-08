"""視頻顯示檢測器 - 檢測視頻/畫布是否正常顯示"""
import io
import logging
from typing import Tuple
import numpy as np
from PIL import Image
from playwright.async_api import Page


class VideoDetector:
    """檢測視頻是否正常顯示（非黑畫面/透明畫面）"""
    
    @staticmethod
    async def check_video_display(
        page: Page, 
        selector: str = "canvas, video",
        black_threshold: float = 10.0,
        transparent_threshold: float = 10.0,
        monochrome_threshold: float = 5.0
    ) -> Tuple[bool, str]:
        """
        檢查視頻/畫布是否正常顯示
        
        Args:
            page: Playwright Page對象
            selector: 要檢測的元素選擇器（預設為 canvas 或 video）
            black_threshold: 黑畫面檢測閾值（平均亮度低於此值視為黑畫面）
            transparent_threshold: 透明畫面檢測閾值（alpha通道平均值低於此值視為透明）
            monochrome_threshold: 單色畫面檢測閾值（像素變異數低於此值視為單色）
            
        Returns:
            (是否正常, 問題描述)
        """
        try:
            # 等待元素出現
            element = await page.wait_for_selector(selector, timeout=5000, state="attached")
            if not element:
                return False, "找不到視頻/畫布元素"
            
            # 截圖
            screenshot = await element.screenshot()
            img = Image.open(io.BytesIO(screenshot))
            img_array = np.array(img)
            
            # 檢查是否為黑畫面（所有像素接近黑色）
            if len(img_array.shape) == 3:
                # RGB 或 RGBA
                rgb_mean = np.mean(img_array[:, :, :3])
                if rgb_mean < black_threshold:
                    return False, f"檢測到黑畫面（平均亮度: {rgb_mean:.2f}）"
                
                # 檢查是否為透明畫面（alpha通道全為0或接近0）
                if img_array.shape[2] == 4:  # RGBA
                    alpha = img_array[:, :, 3]
                    alpha_mean = np.mean(alpha)
                    if alpha_mean < transparent_threshold:
                        return False, f"檢測到透明畫面（alpha平均值: {alpha_mean:.2f}）"
                
                # 檢查是否為單色畫面（變異數極低）
                std = np.std(img_array)
                if std < monochrome_threshold:
                    return False, f"檢測到單色畫面（可能未載入，變異數: {std:.2f}）"
            else:
                # 灰度圖
                mean = np.mean(img_array)
                if mean < black_threshold:
                    return False, f"檢測到黑畫面（平均亮度: {mean:.2f}）"
                std = np.std(img_array)
                if std < monochrome_threshold:
                    return False, f"檢測到單色畫面（可能未載入，變異數: {std:.2f}）"
            
            return True, "視頻正常顯示"
            
        except Exception as e:
            logging.error(f"[VideoDetector] 檢測過程發生錯誤: {e}")
            return False, f"檢測過程發生錯誤: {str(e)}"

