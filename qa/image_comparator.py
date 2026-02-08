"""圖片比對模組 - 用於階段性圖片比對驗證

使用 OpenCV SSIM（結構相似性）+ 直方圖比較的綜合方法，
與 tools/image_comparison_visualizer.py 保持一致。
"""
import io
import logging
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List
import numpy as np
from PIL import Image
from playwright.async_api import Page

# 嘗試導入 OpenCV 和 scikit-image
try:
    import cv2
    from skimage.metrics import structural_similarity as ssim
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    logging.warning("[ImageComparator] OpenCV 或 scikit-image 未安裝，將使用備用 PSNR 方法")
    logging.warning("[ImageComparator] 安裝: pip install opencv-python scikit-image")


class ImageComparator:
    """圖片比對器 - 使用 OpenCV SSIM + 直方圖的綜合比對方法"""
    
    @staticmethod
    def calculate_similarity(img1: np.ndarray, img2: np.ndarray) -> Tuple[float, Dict[str, Any]]:
        """
        計算兩張圖片的相似度
        
        方法（與 image_comparison_visualizer.py 一致）：
        1. SSIM (結構相似性) - 權重 70%，對動態內容更準確
        2. 直方圖比較 - 權重 30%，比較顏色分佈
        3. PSNR (峰值信噪比) - 作為參考指標
        
        Args:
            img1: 第一張圖片的數組 (RGB)
            img2: 第二張圖片的數組 (RGB)
            
        Returns:
            (相似度分數 0-1, 詳細信息字典)
        """
        info = {
            "method": "opencv_ssim" if OPENCV_AVAILABLE else "psnr",
            "ssim": 0.0,
            "histogram_similarity": 0.0,
            "mse": 0.0,
            "psnr": 0.0,
            "resized": False
        }
        
        try:
            # 檢查圖片是否為空
            if img1.size == 0 or img2.size == 0:
                logging.warning(f"[ImageComparator] 圖片為空: img1.size={img1.size}, img2.size={img2.size}")
                return 0.0, info
            
            # 確保兩張圖片尺寸相同
            if img1.shape != img2.shape:
                info["resized"] = True
                img1_pil = Image.fromarray(img1)
                img2_pil = Image.fromarray(img2)
                
                # 比較像素總數，調整較小的圖片到較大的尺寸
                img1_pixels = img1.shape[0] * img1.shape[1] if len(img1.shape) >= 2 else 0
                img2_pixels = img2.shape[0] * img2.shape[1] if len(img2.shape) >= 2 else 0
                
                if img1_pixels < img2_pixels:
                    img1_pil = img1_pil.resize(img2_pil.size, Image.Resampling.LANCZOS)
                    img1 = np.array(img1_pil)
                else:
                    img2_pil = img2_pil.resize(img1_pil.size, Image.Resampling.LANCZOS)
                    img2 = np.array(img2_pil)
            
            # === OpenCV SSIM + 直方圖方法 ===
            if OPENCV_AVAILABLE:
                # 轉換為灰度圖
                if len(img1.shape) == 3:
                    img1_gray = cv2.cvtColor(img1, cv2.COLOR_RGB2GRAY)
                    img2_gray = cv2.cvtColor(img2, cv2.COLOR_RGB2GRAY)
                else:
                    img1_gray = img1.astype(np.uint8)
                    img2_gray = img2.astype(np.uint8)
                
                # 1. 計算 SSIM（結構相似性指數）
                ssim_score, _ = ssim(img1_gray, img2_gray, full=True)
                info["ssim"] = float(ssim_score)
                
                # 2. 計算直方圖相似度（Correlation 方法）
                hist1 = cv2.calcHist([img1_gray], [0], None, [256], [0, 256])
                hist2 = cv2.calcHist([img2_gray], [0], None, [256], [0, 256])
                hist1 = cv2.normalize(hist1, hist1).flatten()
                hist2 = cv2.normalize(hist2, hist2).flatten()
                hist_similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
                info["histogram_similarity"] = float(hist_similarity)
                
                # 3. 綜合相似度：SSIM 權重 70%，直方圖權重 30%
                # SSIM 範圍 [-1, 1]，轉換到 [0, 1]
                ssim_normalized = (ssim_score + 1) / 2
                hist_normalized = max(0, hist_similarity)  # 直方圖相關係數可能為負
                
                similarity = ssim_normalized * 0.7 + hist_normalized * 0.3
                
                # 也計算 MSE 和 PSNR 作為參考
                mse = np.mean((img1_gray.astype(float) - img2_gray.astype(float)) ** 2)
                info["mse"] = float(mse)
                if mse > 0:
                    info["psnr"] = float(20 * np.log10(255.0 / np.sqrt(mse)))
                else:
                    info["psnr"] = float('inf')
                
                logging.debug(
                    f"[ImageComparator] SSIM={ssim_score:.4f}, "
                    f"Hist={hist_similarity:.4f}, "
                    f"Combined={similarity:.4f}"
                )
                return similarity, info
            
            # === 備用方法：PSNR ===
            if len(img1.shape) == 3:
                img1_gray = np.dot(img1[..., :3], [0.2989, 0.5870, 0.1140])
                img2_gray = np.dot(img2[..., :3], [0.2989, 0.5870, 0.1140])
            else:
                img1_gray = img1
                img2_gray = img2
            
            mse = np.mean((img1_gray - img2_gray) ** 2)
            info["mse"] = float(mse)
            
            if mse == 0:
                info["psnr"] = float('inf')
                return 1.0, info
            
            psnr = 20 * np.log10(255.0 / np.sqrt(mse))
            info["psnr"] = float(psnr)
            
            similarity = min(1.0, psnr / 30.0)
            return similarity, info
            
        except Exception as e:
            logging.error(f"[ImageComparator] 計算相似度時發生錯誤: {e}")
            return 0.0, info
    
    @staticmethod
    async def compare_with_reference(
        page: Page,
        reference_image_path: Path,
        selector: Optional[str] = None,
        similarity_threshold: float = 0.8,
        region: Optional[Dict[str, int]] = None
    ) -> Tuple[bool, float, str]:
        """
        比對當前頁面截圖與參考圖片
        
        Args:
            page: Playwright Page 對象
            reference_image_path: 參考圖片路徑
            selector: 要截圖的元素選擇器（如果為 None，則截整個頁面）
            similarity_threshold: 相似度閾值（0-1），超過此值認為匹配成功
            region: 可選的區域設定 {"x": 0, "y": 0, "width": 100, "height": 100}
            
        Returns:
            (是否匹配, 相似度分數, 訊息)
        """
        try:
            # 檢查參考圖片是否存在
            if not reference_image_path.exists():
                return False, 0.0, f"參考圖片不存在: {reference_image_path}"
            
            # 載入參考圖片
            ref_img = Image.open(reference_image_path)
            ref_array = np.array(ref_img)
            
            # 截取當前頁面
            if selector:
                try:
                    element = await page.wait_for_selector(selector, timeout=3000, state="visible")
                    if element:
                        screenshot = await element.screenshot()
                    else:
                        return False, 0.0, f"找不到元素: {selector}"
                except Exception as e:
                    return False, 0.0, f"截圖失敗: {str(e)}"
            else:
                screenshot = await page.screenshot()
            
            current_img = Image.open(io.BytesIO(screenshot))
            current_array = np.array(current_img)
            
            # 如果指定了區域，裁剪圖片（帶邊界檢查）
            if region:
                x = region.get("x", 0)
                y = region.get("y", 0)
                width = region.get("width", current_img.width)
                height = region.get("height", current_img.height)
                
                # 確保裁剪區域在圖片範圍內
                ref_h, ref_w = ref_array.shape[:2]
                x = max(0, min(x, ref_w - 1))
                y = max(0, min(y, ref_h - 1))
                ref_crop_w = min(width, ref_w - x)
                ref_crop_h = min(height, ref_h - y)
                
                if ref_crop_w > 0 and ref_crop_h > 0:
                    ref_array = ref_array[y:y+ref_crop_h, x:x+ref_crop_w]
                else:
                    return False, 0.0, f"參考圖片裁剪區域無效: x={x}, y={y}, w={width}, h={height}"
                
                cur_h, cur_w = current_array.shape[:2]
                cx = max(0, min(x, cur_w - 1))
                cy = max(0, min(y, cur_h - 1))
                cur_crop_w = min(width, cur_w - cx)
                cur_crop_h = min(height, cur_h - cy)
                
                if cur_crop_w > 0 and cur_crop_h > 0:
                    current_array = current_array[cy:cy+cur_crop_h, cx:cx+cur_crop_w]
                else:
                    return False, 0.0, f"當前截圖裁剪區域無效: x={cx}, y={cy}, w={width}, h={height}"
            
            # 計算相似度（使用 SSIM + 直方圖方法）
            similarity, info = ImageComparator.calculate_similarity(ref_array, current_array)
            
            # 判斷是否匹配
            is_match = similarity >= similarity_threshold
            
            # 構建訊息
            method = info.get("method", "unknown")
            if method == "opencv_ssim":
                message = (
                    f"相似度: {similarity:.2%} ({'匹配' if is_match else '不匹配'}, "
                    f"閾值: {similarity_threshold:.2%}) | "
                    f"SSIM: {info.get('ssim', 0):.4f}, "
                    f"直方圖: {info.get('histogram_similarity', 0):.4f}"
                )
            else:
                message = (
                    f"相似度: {similarity:.2%} ({'匹配' if is_match else '不匹配'}, "
                    f"閾值: {similarity_threshold:.2%}) | "
                    f"PSNR: {info.get('psnr', 0):.2f} dB"
                )
            
            return is_match, similarity, message
            
        except Exception as e:
            logging.error(f"[ImageComparator] 圖片比對過程發生錯誤: {e}")
            return False, 0.0, f"比對過程發生錯誤: {str(e)}"
    
    @staticmethod
    async def compare_stage(
        page: Page,
        stage_name: str,
        reference_images_dir: Path,
        config: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        比對特定階段的圖片
        
        Args:
            page: Playwright Page 對象
            stage_name: 階段名稱（例如 "entry", "video", "buttons"）
            reference_images_dir: 參考圖片目錄
            config: 比對配置
            
        Returns:
            (是否匹配, 比對結果詳情)
        """
        stage_dir = reference_images_dir / stage_name
        
        if not stage_dir.exists():
            logging.warning(f"[ImageComparator] 階段 {stage_name} 的參考圖片目錄不存在: {stage_dir}")
            return True, {"status": "skipped", "reason": "參考圖片目錄不存在"}
        
        # 獲取配置
        similarity_threshold = config.get("threshold", config.get("similarity_threshold", 0.8))
        selector = config.get("selector")
        region = config.get("region")
        image_files = config.get("images", [])
        
        # 獲取參考圖片列表
        if image_files:
            ref_images = [stage_dir / img for img in image_files if (stage_dir / img).exists()]
        else:
            ref_images = (
                list(stage_dir.glob("*.png")) + 
                list(stage_dir.glob("*.jpg")) + 
                list(stage_dir.glob("*.jpeg"))
            )
        
        if not ref_images:
            logging.warning(f"[ImageComparator] 階段 {stage_name} 沒有找到參考圖片")
            return True, {"status": "skipped", "reason": "沒有參考圖片"}
        
        results = []
        all_match = True
        
        for ref_img_path in ref_images:
            is_match, similarity, message = await ImageComparator.compare_with_reference(
                page,
                ref_img_path,
                selector=selector,
                similarity_threshold=similarity_threshold,
                region=region
            )
            
            results.append({
                "reference_image": ref_img_path.name,
                "match": is_match,
                "similarity": similarity,
                "message": message
            })
            
            if not is_match:
                all_match = False
                logging.warning(f"[ImageComparator] 階段 {stage_name} 圖片比對失敗: {ref_img_path.name} - {message}")
            else:
                logging.info(f"[ImageComparator] 階段 {stage_name} 圖片比對成功: {ref_img_path.name} - {message}")
        
        return all_match, {
            "status": "success" if all_match else "failed",
            "method": "opencv_ssim" if OPENCV_AVAILABLE else "psnr",
            "results": results,
            "total_images": len(ref_images),
            "matched_images": sum(1 for r in results if r["match"])
        }
