"""
圖片比對可視化工具 - 幫助理解圖片比對過程

功能：
1. 載入參考圖片和當前截圖
2. 顯示比對過程（調整尺寸、轉換灰度、計算相似度）
3. 生成可視化結果（差異圖、相似度報告）
4. 支持區域比對
5. 使用 OpenCV SSIM 進行結構相似性比對
"""
import sys
import asyncio
import io
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from playwright.async_api import async_playwright

# 嘗試導入 OpenCV
try:
    import cv2
    from skimage.metrics import structural_similarity as ssim
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    print("[WARNING] OpenCV 或 scikit-image 未安裝，將使用基礎 PSNR 方法")
    print("         安裝: pip install opencv-python scikit-image")

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

try:
    from qa.image_comparator import ImageComparator
except ImportError:
    print("[ERROR] 無法導入 ImageComparator")
    sys.exit(1)

# 導入遊戲導航功能
try:
    from game.navigation import is_in_game, scroll_and_click_game
    from game.actions import click_multiple_positions
except ImportError:
    is_in_game = None
    scroll_and_click_game = None
    click_multiple_positions = None
    print("[WARNING] 無法導入遊戲導航功能，將無法自動進入遊戲")


def calculate_similarity_visual(img1: np.ndarray, img2: np.ndarray) -> Tuple[float, Dict[str, Any]]:
    """
    計算兩張圖片的相似度（使用多種方法）
    
    方法：
    1. SSIM (結構相似性) - 主要指標，對動態內容更準確
    2. 直方圖比較 - 比較顏色分佈
    3. PSNR (峰值信噪比) - 傳統像素比較
    
    Returns:
        (相似度分數, 詳細信息)
    """
    info = {
        "original_shape_1": img1.shape,
        "original_shape_2": img2.shape,
        "resized": False,
        "method": "opencv_ssim" if OPENCV_AVAILABLE else "psnr",
        "ssim": 0.0,
        "histogram_similarity": 0.0,
        "mse": 0.0,
        "psnr": 0.0,
        "similarity": 0.0
    }
    
    try:
        # 檢查圖片是否為空
        if img1.size == 0 or img2.size == 0:
            info["error"] = f"圖片為空: img1.size={img1.size}, img2.size={img2.size}"
            return 0.0, info
        
        # 確保兩張圖片尺寸相同
        if img1.shape != img2.shape:
            info["resized"] = True
            img1_pil = Image.fromarray(img1)
            img2_pil = Image.fromarray(img2)
            
            # 比較像素總數，調整較小的圖片
            img1_pixels = img1.shape[0] * img1.shape[1] if len(img1.shape) >= 2 else 0
            img2_pixels = img2.shape[0] * img2.shape[1] if len(img2.shape) >= 2 else 0
            
            if img1_pixels < img2_pixels:
                img1_pil = img1_pil.resize(img2_pil.size, Image.Resampling.LANCZOS)
                img1 = np.array(img1_pil)
            else:
                img2_pil = img2_pil.resize(img1_pil.size, Image.Resampling.LANCZOS)
                img2 = np.array(img2_pil)
            info["final_shape"] = img1.shape
        
        # 使用 OpenCV SSIM（如果可用）
        if OPENCV_AVAILABLE:
            # 轉換為灰度圖（OpenCV 格式）
            if len(img1.shape) == 3:
                img1_gray = cv2.cvtColor(img1, cv2.COLOR_RGB2GRAY)
                img2_gray = cv2.cvtColor(img2, cv2.COLOR_RGB2GRAY)
            else:
                img1_gray = img1.astype(np.uint8)
                img2_gray = img2.astype(np.uint8)
            
            # 計算 SSIM（結構相似性指數）
            ssim_score, ssim_diff = ssim(img1_gray, img2_gray, full=True)
            info["ssim"] = float(ssim_score)
            
            # 計算直方圖相似度
            hist1 = cv2.calcHist([img1_gray], [0], None, [256], [0, 256])
            hist2 = cv2.calcHist([img2_gray], [0], None, [256], [0, 256])
            hist1 = cv2.normalize(hist1, hist1).flatten()
            hist2 = cv2.normalize(hist2, hist2).flatten()
            hist_similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
            info["histogram_similarity"] = float(hist_similarity)
            
            # 綜合相似度：SSIM 權重 70%，直方圖權重 30%
            # SSIM 範圍 [-1, 1]，轉換到 [0, 1]
            ssim_normalized = (ssim_score + 1) / 2
            hist_normalized = max(0, hist_similarity)  # 直方圖相關係數可能為負
            
            similarity = ssim_normalized * 0.7 + hist_normalized * 0.3
            info["similarity"] = float(similarity)
            
            # 也計算傳統的 MSE 和 PSNR 作為參考
            mse = np.mean((img1_gray.astype(float) - img2_gray.astype(float)) ** 2)
            info["mse"] = float(mse)
            if mse > 0:
                psnr = 20 * np.log10(255.0 / np.sqrt(mse))
                info["psnr"] = float(psnr)
            else:
                info["psnr"] = float('inf')
            
            return similarity, info
        
        # 備用方法：使用 PSNR
        # 轉換為灰度圖
        if len(img1.shape) == 3:
            img1_gray = np.dot(img1[..., :3], [0.2989, 0.5870, 0.1140])
            img2_gray = np.dot(img2[..., :3], [0.2989, 0.5870, 0.1140])
        else:
            img1_gray = img1
            img2_gray = img2
        
        # 計算均方誤差（MSE）
        mse = np.mean((img1_gray - img2_gray) ** 2)
        info["mse"] = float(mse)
        
        # 如果 MSE 為 0，圖片完全相同
        if mse == 0:
            info["psnr"] = float('inf')
            info["similarity"] = 1.0
            return 1.0, info
        
        # 計算峰值信噪比（PSNR）
        psnr = 20 * np.log10(255.0 / np.sqrt(mse))
        info["psnr"] = float(psnr)
        
        # 將 PSNR 轉換為 0-1 的相似度分數
        similarity = min(1.0, psnr / 30.0)
        info["similarity"] = float(similarity)
        
        return similarity, info
        
    except Exception as e:
        info["error"] = str(e)
        return 0.0, info


def create_comparison_visualization(
    ref_img: Image.Image,
    current_img: Image.Image,
    similarity: float,
    info: Dict[str, Any],
    output_path: Path
):
    """創建可視化比對結果"""
    # 調整尺寸以匹配
    if ref_img.size != current_img.size:
        if ref_img.size[0] * ref_img.size[1] < current_img.size[0] * current_img.size[1]:
            ref_img = ref_img.resize(current_img.size, Image.Resampling.LANCZOS)
        else:
            current_img = current_img.resize(ref_img.size, Image.Resampling.LANCZOS)
    
    # 轉換為灰度
    ref_gray = ref_img.convert("L")
    current_gray = current_img.convert("L")
    
    # 計算差異圖
    ref_array = np.array(ref_gray, dtype=np.float32)
    current_array = np.array(current_gray, dtype=np.float32)
    diff_array = np.abs(ref_array - current_array)
    diff_img = Image.fromarray(diff_array.astype(np.uint8))
    
    # 創建可視化畫布（4個區域：參考圖、當前圖、差異圖、信息）
    width, height = ref_img.size
    canvas_width = width * 2 + 40
    canvas_height = max(height * 2 + 200, 600)
    
    canvas = Image.new("RGB", (canvas_width, canvas_height), color=(240, 240, 240))
    draw = ImageDraw.Draw(canvas)
    
    # 嘗試載入字體
    try:
        font_large = ImageFont.truetype("arial.ttf", 20)
        font_medium = ImageFont.truetype("arial.ttf", 14)
        font_small = ImageFont.truetype("arial.ttf", 12)
    except:
        try:
            font_large = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 20)
            font_medium = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 14)
            font_small = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 12)
        except:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
    
    # 標題
    draw.text((10, 10), "圖片比對可視化結果", fill=(0, 0, 0), font=font_large)
    
    # 參考圖片
    y_offset = 50
    draw.text((10, y_offset), "參考圖片", fill=(0, 0, 0), font=font_medium)
    canvas.paste(ref_img, (10, y_offset + 25))
    
    # 當前圖片
    draw.text((width + 30, y_offset), "當前截圖", fill=(0, 0, 0), font=font_medium)
    canvas.paste(current_img, (width + 30, y_offset + 25))
    
    # 差異圖（下方）
    y_offset2 = y_offset + height + 50
    draw.text((10, y_offset2), "差異圖（白色=相同，黑色=不同）", fill=(0, 0, 0), font=font_medium)
    canvas.paste(diff_img, (10, y_offset2 + 25))
    
    # 信息面板
    info_x = width + 30
    info_y = y_offset2
    draw.rectangle([info_x - 5, info_y - 5, canvas_width - 10, info_y + 200], 
                   fill=(255, 255, 255), outline=(0, 0, 0), width=2)
    
    # 根據使用的方法顯示不同的信息
    if info.get('method') == 'opencv_ssim':
        info_text = [
            f"相似度: {similarity:.2%}",
            f"SSIM: {info.get('ssim', 0):.4f}",
            f"直方圖相似度: {info.get('histogram_similarity', 0):.4f}",
            f"PSNR: {info.get('psnr', 0):.2f} dB",
            f"參考圖片尺寸: {info.get('original_shape_1', 'N/A')}",
            f"當前圖片尺寸: {info.get('original_shape_2', 'N/A')}",
        ]
    else:
        info_text = [
            f"相似度: {similarity:.2%}",
            f"PSNR: {info.get('psnr', 0):.2f} dB",
            f"MSE: {info.get('mse', 0):.2f}",
            f"參考圖片尺寸: {info.get('original_shape_1', 'N/A')}",
            f"當前圖片尺寸: {info.get('original_shape_2', 'N/A')}",
            f"是否調整尺寸: {'是' if info.get('resized', False) else '否'}",
        ]
    
    for i, text in enumerate(info_text):
        draw.text((info_x, info_y + i * 25), text, fill=(0, 0, 0), font=font_small)
    
    # 相似度條
    bar_x = info_x
    bar_y = info_y + len(info_text) * 25 + 10
    bar_width = 200
    bar_height = 20
    
    # 背景
    draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height], 
                   fill=(200, 200, 200), outline=(0, 0, 0))
    
    # 相似度條（綠色=高相似度，紅色=低相似度）
    similarity_width = int(bar_width * similarity)
    color = (0, 255, 0) if similarity > 0.7 else (255, 0, 0) if similarity < 0.5 else (255, 165, 0)
    draw.rectangle([bar_x, bar_y, bar_x + similarity_width, bar_y + bar_height], fill=color)
    
    # 閾值線（如果設置了閾值）
    threshold = 0.7
    threshold_x = bar_x + int(bar_width * threshold)
    draw.line([threshold_x, bar_y - 5, threshold_x, bar_y + bar_height + 5], 
              fill=(0, 0, 255), width=2)
    draw.text((threshold_x + 5, bar_y - 20), f"閾值: {threshold:.0%}", 
              fill=(0, 0, 255), font=font_small)
    
    canvas.save(output_path)
    print(f"\n可視化結果已保存: {output_path}")


async def visualize_comparison(
    reference_image_path: Path,
    current_image_path: Optional[Path] = None,
    page_url: Optional[str] = None,
    region: Optional[Dict[str, int]] = None,
    output_dir: Path = None,
    continuous: bool = False,
    interval: float = 2.0,
    game_title_code: Optional[str] = None,
    keyword_actions: Optional[Dict[str, list]] = None
):
    """可視化圖片比對過程（支持自動進入遊戲）"""
    if output_dir is None:
        output_dir = BASE_DIR / "comparison_results"
    output_dir.mkdir(exist_ok=True)
    
    print("="*60)
    print("圖片比對可視化工具")
    if continuous:
        print("持續比對模式（按 Ctrl+C 停止）")
    print("="*60)
    
    # 載入參考圖片
    print(f"\n1. 載入參考圖片: {reference_image_path}")
    if not reference_image_path.exists():
        print(f"[ERROR] 參考圖片不存在: {reference_image_path}")
        return
    
    ref_img = Image.open(reference_image_path)
    print(f"   尺寸: {ref_img.size[0]} x {ref_img.size[1]} 像素")
    ref_array = np.array(ref_img)
    
    # 如果指定了區域，預先裁剪參考圖片
    if region:
        print(f"\n2. 應用區域裁剪: {region}")
        x = region.get("x", 0)
        y = region.get("y", 0)
        width = region.get("width", ref_img.width)
        height = region.get("height", ref_img.height)
        
        # 確保裁剪區域在圖片範圍內
        x = max(0, min(x, ref_img.width - 1))
        y = max(0, min(y, ref_img.height - 1))
        width = min(width, ref_img.width - x)
        height = min(height, ref_img.height - y)
        
        if width > 0 and height > 0:
            ref_img = ref_img.crop((x, y, x + width, y + height))
            ref_array = np.array(ref_img)
            print(f"   參考圖片裁剪後尺寸: {ref_img.size[0]} x {ref_img.size[1]} 像素")
        else:
            print(f"  [ERROR] 無效的裁剪區域: x={x}, y={y}, width={width}, height={height}")
            print(f"  參考圖片尺寸: {ref_img.width} x {ref_img.height}")
            return
    
    # 持續比對模式
    if continuous and page_url:
        print(f"\n3. 啟動持續比對模式（間隔: {interval} 秒）")
        print("   按 Ctrl+C 停止比對")
        
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=False)
            context = await browser.new_context(
                viewport={"width": 500, "height": 859},
                user_agent=(
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.127 Mobile Safari/537.36"
                ),
            )
            page = await context.new_page()
            
            await page.goto(page_url, timeout=30000)
            await page.wait_for_load_state("networkidle", timeout=10000)
            await asyncio.sleep(2)  # 等待頁面穩定
            
            # 自動進入遊戲（如果提供了 game_title_code）
            if game_title_code and is_in_game and scroll_and_click_game:
                if not await is_in_game(page):
                    print(f"\n   檢測到在大廳，準備進入遊戲: {game_title_code}")
                    kw_actions = keyword_actions or {}
                    success = await scroll_and_click_game(page, game_title_code, kw_actions)
                    if success:
                        print(f"   [OK] 成功進入遊戲")
                        await asyncio.sleep(3)  # 等待遊戲載入
                    else:
                        print(f"   [FAIL] 進入遊戲失敗，將在大廳進行比對")
                else:
                    print(f"   已在遊戲中，跳過進入流程")
            
            comparison_count = 0
            best_similarity = 0.0
            best_similarity_time = None
            
            try:
                while True:
                    comparison_count += 1
                    print(f"\n--- 比對 #{comparison_count} ---")
                    
                    # 截圖
                    screenshot = await page.screenshot()
                    current_img = Image.open(io.BytesIO(screenshot))
                    current_array = np.array(current_img)
                    
                    # 應用區域裁剪
                    if region:
                        x = region.get("x", 0)
                        y = region.get("y", 0)
                        width = region.get("width", current_img.width)
                        height = region.get("height", current_img.height)
                        
                        # 確保裁剪區域在圖片範圍內
                        x = max(0, min(x, current_img.width - 1))
                        y = max(0, min(y, current_img.height - 1))
                        width = min(width, current_img.width - x)
                        height = min(height, current_img.height - y)
                        
                        if width > 0 and height > 0:
                            current_img = current_img.crop((x, y, x + width, y + height))
                            current_array = np.array(current_img)
                        else:
                            print(f"  [WARNING] 無效的裁剪區域: x={x}, y={y}, width={width}, height={height}")
                            print(f"  圖片尺寸: {current_img.width} x {current_img.height}")
                            continue
                    
                    # 計算相似度
                    similarity, info = calculate_similarity_visual(ref_array, current_array)
                    
                    # 檢查是否有錯誤
                    if "error" in info:
                        print(f"  [ERROR] 計算相似度時發生錯誤: {info['error']}")
                        print(f"  參考圖片尺寸: {info.get('original_shape_1', 'N/A')}")
                        print(f"  當前圖片尺寸: {info.get('original_shape_2', 'N/A')}")
                        continue
                    
                    # 更新最佳相似度
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_similarity_time = comparison_count
                    
                    # 顯示結果
                    if OPENCV_AVAILABLE:
                        print(f"  相似度: {similarity:.2%} | SSIM: {info.get('ssim', 0):.4f} | 直方圖: {info.get('histogram_similarity', 0):.4f}")
                    else:
                        print(f"  相似度: {similarity:.2%} | PSNR: {info.get('psnr', 0):.2f} dB | MSE: {info.get('mse', 0):.2f}")
                    if best_similarity_time:
                        print(f"  最佳相似度: {best_similarity:.2%} (第 {best_similarity_time} 次比對)")
                    else:
                        print(f"  最佳相似度: {best_similarity:.2%}")
                    
                    # 生成可視化
                    output_path = output_dir / f"comparison_{reference_image_path.stem}_latest.png"
                    create_comparison_visualization(ref_img, current_img, similarity, info, output_path)
                    
                    # 等待下一次比對
                    await asyncio.sleep(interval)
                    
            except KeyboardInterrupt:
                print(f"\n\n停止比對")
                print(f"總共比對: {comparison_count} 次")
                print(f"最佳相似度: {best_similarity:.2%} (第 {best_similarity_time} 次比對)")
            
            await browser.close()
        return
    
    # 單次比對模式
    # 獲取當前截圖
    if current_image_path and current_image_path.exists():
        print(f"\n2. 載入當前截圖: {current_image_path}")
        current_img = Image.open(current_image_path)
        current_array = np.array(current_img)
    elif page_url:
        print(f"\n2. 從網頁截圖: {page_url}")
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=False)
            context = await browser.new_context(
                viewport={"width": 500, "height": 859},
                user_agent=(
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.127 Mobile Safari/537.36"
                ),
            )
            page = await context.new_page()
            
            await page.goto(page_url, timeout=30000)
            await page.wait_for_load_state("networkidle", timeout=10000)
            await asyncio.sleep(2)  # 等待頁面穩定
            
            # 自動進入遊戲（如果提供了 game_title_code）
            if game_title_code and is_in_game and scroll_and_click_game:
                if not await is_in_game(page):
                    print(f"   檢測到在大廳，準備進入遊戲: {game_title_code}")
                    kw_actions = keyword_actions or {}
                    success = await scroll_and_click_game(page, game_title_code, kw_actions)
                    if success:
                        print(f"   [OK] 成功進入遊戲")
                        await asyncio.sleep(3)  # 等待遊戲載入
                    else:
                        print(f"   [FAIL] 進入遊戲失敗")
                else:
                    print(f"   已在遊戲中")
            
            screenshot = await page.screenshot()
            current_img = Image.open(io.BytesIO(screenshot))
            current_array = np.array(current_img)
            
            await browser.close()
    else:
        print("[ERROR] 請提供當前截圖路徑或網頁 URL")
        return
    
    print(f"   尺寸: {current_img.size[0]} x {current_img.size[1]} 像素")
    
    # 如果指定了區域，裁剪圖片
    if region:
        x = region.get("x", 0)
        y = region.get("y", 0)
        width = region.get("width", current_img.width)
        height = region.get("height", current_img.height)
        
        current_img = current_img.crop((x, y, x + width, y + height))
        current_array = np.array(current_img)
        print(f"   當前截圖裁剪後尺寸: {current_img.size[0]} x {current_img.size[1]} 像素")
    
    # 計算相似度
    print("\n3. 計算相似度...")
    similarity, info = calculate_similarity_visual(ref_array, current_array)
    
    print(f"\n比對結果:")
    print(f"  相似度: {similarity:.2%}")
    print(f"  PSNR: {info.get('psnr', 0):.2f} dB")
    print(f"  MSE: {info.get('mse', 0):.2f}")
    print(f"  是否調整尺寸: {'是' if info.get('resized', False) else '否'}")
    
    # 創建可視化
    output_path = output_dir / f"comparison_{reference_image_path.stem}.png"
    print(f"\n4. 生成可視化結果...")
    create_comparison_visualization(ref_img, current_img, similarity, info, output_path)
    
    print(f"\n完成！可視化結果已保存到: {output_path}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="圖片比對可視化工具")
    parser.add_argument("reference", help="參考圖片路徑")
    parser.add_argument("--current", help="當前截圖路徑（可選）")
    parser.add_argument("--url", help="網頁 URL（如果沒有提供當前截圖）")
    parser.add_argument("--region", help="區域配置 JSON 字符串，例如: '{\"x\":0,\"y\":0,\"width\":500,\"height\":600}'")
    parser.add_argument("--output", help="輸出目錄（默認: comparison_results/）")
    parser.add_argument("--continuous", action="store_true", help="持續比對模式（需要 --url）")
    parser.add_argument("--interval", type=float, default=2.0, help="持續比對間隔（秒，默認: 2.0）")
    
    args = parser.parse_args()
    
    reference_path = Path(args.reference)
    current_path = Path(args.current) if args.current else None
    region = None
    if args.region:
        import json
        region = json.loads(args.region)
    
    output_dir = Path(args.output) if args.output else None
    
    asyncio.run(visualize_comparison(
        reference_path,
        current_path,
        args.url,
        region,
        output_dir,
        args.continuous,
        args.interval
    ))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python image_comparison_visualizer.py <參考圖片> [選項]")
        print("\n選項:")
        print("  --current <路徑>    當前截圖路徑")
        print("  --url <URL>         網頁 URL（如果沒有提供當前截圖）")
        print("  --region <JSON>     區域配置，例如: '{\"x\":0,\"y\":0,\"width\":500,\"height\":600}'")
        print("  --output <目錄>     輸出目錄（默認: comparison_results/）")
        print("  --continuous        持續比對模式（需要 --url，按 Ctrl+C 停止）")
        print("  --interval <秒>    持續比對間隔（默認: 2.0 秒）")
        print("\n範例:")
        print('  python image_comparison_visualizer.py reference.png --current current.png')
        print('  python image_comparison_visualizer.py reference.png --url "https://example.com"')
        print('  python image_comparison_visualizer.py reference.png --url "https://example.com" --continuous --interval 3.0')
        print('  python image_comparison_visualizer.py reference.png --current current.png --region \'{"x":0,"y":0,"width":500,"height":600}\'')
        print("\n或者自動從配置讀取:")
        print("  python image_comparison_visualizer.py auto")
        print("  python image_comparison_visualizer.py auto --quick          # 快速模式（自動選擇第一個）")
        print("  python image_comparison_visualizer.py auto --quick --continuous  # 快速持續比對")
    elif sys.argv[1] == "auto":
        # 自動模式：從 CSV 讀取關鍵字並比對
        # 檢查是否有 --quick 參數
        quick_mode = "--quick" in sys.argv
        auto_continuous = "--continuous" in sys.argv
        
        try:
            import json
            import csv
            from config.loader import load_games
            
            print("="*60)
            print("圖片比對可視化工具 - 自動模式" + (" (快速模式)" if quick_mode else ""))
            print("="*60)
            
            # 1. 讀取 CSV 檔案，提取關鍵字
            csv_path = BASE_DIR / "game_title_codes.csv"
            if not csv_path.exists():
                print(f"[ERROR] CSV 檔案不存在: {csv_path}")
                sys.exit(1)
            
            keyword = None
            full_game_title_code = None  # 保存完整的 game_title_code
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    game_title_code = row.get('game_title_code', '').strip()
                    if game_title_code:
                        full_game_title_code = game_title_code  # 保存完整代碼
                        # 提取關鍵字（例如 873-JJBX-0004 -> JJBX）
                        parts = game_title_code.split('-')
                        if len(parts) >= 2:
                            keyword = parts[1].upper()
                            print(f"\n從 CSV 讀取: {game_title_code}")
                            print(f"提取關鍵字: {keyword}")
                        break
            
            if not keyword:
                print("[ERROR] CSV 中沒有找到有效的 game_title_code")
                sys.exit(1)
            
            # 載入 actions.json 獲取 keyword_actions
            actions_path = BASE_DIR / "actions.json"
            keyword_actions_map = {}
            if actions_path.exists():
                try:
                    with open(actions_path, 'r', encoding='utf-8') as f:
                        actions_data = json.load(f)
                        keyword_actions_map = actions_data.get("keyword_actions", {})
                        print(f"載入 actions.json，包含 {len(keyword_actions_map)} 個 keyword_actions")
                except Exception as e:
                    print(f"[WARNING] 載入 actions.json 失敗: {e}")
            
            # 2. 找到對應的 machine_profiles 資料夾
            profiles_dir = BASE_DIR / "machine_profiles"
            profile_dir = profiles_dir / keyword
            
            if not profile_dir.exists():
                print(f"[WARNING] 找不到對應資料夾: {profile_dir}")
                # 列出可用的資料夾讓用戶選擇
                available_profiles = [d.name for d in profiles_dir.iterdir() 
                                     if d.is_dir() and d.name not in ['default'] 
                                     and (d / "reference_images").exists()]
                if not available_profiles:
                    print("[ERROR] 沒有可用的 machine profile 資料夾")
                    sys.exit(1)
                
                print("\n可用的 machine profile:")
                for i, name in enumerate(available_profiles, 1):
                    print(f"  {i}. {name}")
                
                choice = input(f"\n請選擇 (1-{len(available_profiles)}): ").strip()
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(available_profiles):
                        keyword = available_profiles[idx]
                        profile_dir = profiles_dir / keyword
                    else:
                        print("[ERROR] 無效的選擇")
                        sys.exit(1)
                except ValueError:
                    print("[ERROR] 請輸入數字")
                    sys.exit(1)
            
            print(f"\n使用 machine profile: {keyword}")
            
            # 3. 列出 reference_images 下的子資料夾
            ref_images_dir = profile_dir / "reference_images"
            if not ref_images_dir.exists():
                print(f"[ERROR] reference_images 目錄不存在: {ref_images_dir}")
                sys.exit(1)
            
            # 找出有圖片的子資料夾
            stage_dirs = []
            for d in ref_images_dir.iterdir():
                if d.is_dir():
                    images = list(d.glob("*.png")) + list(d.glob("*.jpg"))
                    if images:
                        stage_dirs.append((d.name, len(images)))
            
            if not stage_dirs:
                print(f"[ERROR] reference_images 目錄中沒有包含圖片的子資料夾")
                sys.exit(1)
            
            print("\n可用的測試階段:")
            for i, (name, count) in enumerate(stage_dirs, 1):
                print(f"  {i}. {name} ({count} 張圖片)")
            
            if quick_mode:
                # 快速模式：自動選擇第一個
                selected_stage = stage_dirs[0][0]
                print(f"\n[快速模式] 自動選擇: {selected_stage}")
            else:
                stage_choice = input(f"\n請選擇測試階段 (1-{len(stage_dirs)}): ").strip()
                try:
                    stage_idx = int(stage_choice) - 1
                    if 0 <= stage_idx < len(stage_dirs):
                        selected_stage = stage_dirs[stage_idx][0]
                    else:
                        print("[ERROR] 無效的選擇")
                        sys.exit(1)
                except ValueError:
                    print("[ERROR] 請輸入數字")
                    sys.exit(1)
            
            # 4. 列出該資料夾中的圖片
            stage_dir = ref_images_dir / selected_stage
            ref_images = list(stage_dir.glob("*.png")) + list(stage_dir.glob("*.jpg"))
            
            print(f"\n{selected_stage} 資料夾中的圖片:")
            for i, img in enumerate(ref_images, 1):
                print(f"  {i}. {img.name}")
            
            if quick_mode or len(ref_images) == 1:
                # 快速模式或只有一張圖片：自動選擇第一張
                ref_image = ref_images[0]
                if quick_mode and len(ref_images) > 1:
                    print(f"\n[快速模式] 自動選擇: {ref_image.name}")
            else:
                img_choice = input(f"\n請選擇參考圖片 (1-{len(ref_images)}，直接按 Enter 選擇第一張): ").strip()
                if img_choice:
                    try:
                        img_idx = int(img_choice) - 1
                        if 0 <= img_idx < len(ref_images):
                            ref_image = ref_images[img_idx]
                        else:
                            print("[ERROR] 無效的選擇")
                            sys.exit(1)
                    except ValueError:
                        print("[ERROR] 請輸入數字")
                        sys.exit(1)
                else:
                    ref_image = ref_images[0]
            
            print(f"\n使用參考圖片: {ref_image.name}")
            
            # 5. 載入遊戲 URL
            games = load_games(BASE_DIR)
            if not games:
                print("[ERROR] 沒有找到 enabled 的遊戲配置")
                sys.exit(1)
            
            game = games[0]
            print(f"使用遊戲 URL: {game.url[:60]}...")
            
            # 6. 設定區域配置（可以從 test_flows.json 讀取）
            region_config = {"x": 0, "y": 0, "width": 500, "height": 859}
            
            # 嘗試從 test_flows.json 讀取區域配置
            test_flows_path = profile_dir / "test_flows.json"
            if test_flows_path.exists():
                with open(test_flows_path, 'r', encoding='utf-8') as f:
                    test_flows = json.load(f)
                    for flow in test_flows.get("test_flows", []):
                        if flow.get("name") == selected_stage:
                            if "image_comparison" in flow and "region" in flow["image_comparison"]:
                                region_config = flow["image_comparison"]["region"]
                                print(f"從 test_flows.json 讀取區域配置: {region_config}")
                                break
            
            # 7. 詢問是否使用持續比對模式
            interval = 2.0
            if quick_mode:
                # 快速模式：根據命令行參數決定
                continuous = auto_continuous
                if continuous:
                    print(f"\n[快速模式] 啟用持續比對，間隔: {interval} 秒")
            else:
                use_continuous = input("\n是否使用持續比對模式？(y/n，默認 n): ").strip().lower()
                continuous = use_continuous == 'y'
                if continuous:
                    interval_input = input("比對間隔（秒，默認 2.0）: ").strip()
                    if interval_input:
                        try:
                            interval = float(interval_input)
                        except:
                            pass
            
            asyncio.run(visualize_comparison(
                ref_image,
                None,
                game.url,
                region_config,
                None,
                continuous,
                interval,
                full_game_title_code,  # 傳遞完整的 game_title_code
                keyword_actions_map     # 傳遞 keyword_actions
            ))
        except Exception as e:
            print(f"[ERROR] 自動模式失敗: {e}")
            import traceback
            traceback.print_exc()
    else:
        main()

