"""
區域座標獲取工具 - 幫助確定圖片比對的區域座標

使用方法：
1. 運行此腳本
2. 它會打開瀏覽器並截圖
3. 顯示圖片尺寸信息
4. 您可以根據需要設置區域座標
"""
import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


async def get_page_info(url: str):
    """獲取頁面信息並截圖"""
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
        
        print("="*60)
        print("區域座標獲取工具")
        print("="*60)
        
        try:
            await page.goto(url, timeout=30000)
            await page.wait_for_load_state("networkidle", timeout=10000)
            
            # 獲取視窗尺寸
            viewport_size = page.viewport_size
            print(f"\n視窗尺寸: {viewport_size['width']} x {viewport_size['height']} 像素")
            
            # 截圖並保存
            screenshot_path = BASE_DIR / "region_reference.png"
            await page.screenshot(path=str(screenshot_path), full_page=False)
            print(f"\n截圖已保存: {screenshot_path}")
            
            # 讀取圖片尺寸
            from PIL import Image
            img = Image.open(screenshot_path)
            print(f"截圖尺寸: {img.width} x {img.height} 像素")
            
            print("\n" + "="*60)
            print("區域座標說明")
            print("="*60)
            print("""
座標系統：
- 原點 (0, 0) 在左上角
- X 軸向右遞增
- Y 軸向下遞增

區域配置格式：
{
  "x": 起始X座標,
  "y": 起始Y座標,
  "width": 區域寬度,
  "height": 區域高度
}

常用區域範例：

1. 只比對上半部分（遊戲區域）：
   {
     "x": 0,
     "y": 0,
     "width": 500,
     "height": 400
   }

2. 只比對中間部分（轉輪區域）：
   {
     "x": 0,
     "y": 150,
     "width": 500,
     "height": 300
   }

3. 只比對下半部分（控制按鈕區域）：
   {
     "x": 0,
     "y": 500,
     "width": 500,
     "height": 359
   }

4. 只比對左半部分：
   {
     "x": 0,
     "y": 0,
     "width": 250,
     "height": 859
   }

5. 只比對右半部分：
   {
     "x": 250,
     "y": 0,
     "width": 250,
     "height": 859
   }

6. 只比對中心區域（避開邊緣）：
   {
     "x": 50,
     "y": 50,
     "width": 400,
     "height": 759
   }
""")
            
            print("\n請打開截圖文件查看，然後根據需要設置區域座標。")
            print("建議：選擇遊戲的主要區域，避開可能變化的 UI 元素。")
            
            input("\n按 Enter 鍵關閉瀏覽器...")
            
        except Exception as e:
            print(f"錯誤: {e}")
        finally:
            await browser.close()


def main():
    # 如果沒有提供 URL，嘗試從 game_config.json 讀取
    if len(sys.argv) < 2:
        try:
            import json
            config_path = BASE_DIR / "game_config.json"
            if config_path.exists():
                with config_path.open("r", encoding="utf-8") as f:
                    games = json.load(f)
                for game in games:
                    if game.get("enabled", True):
                        url = game.get("url")
                        if url:
                            print(f"從 game_config.json 讀取 URL: {url[:60]}...")
                            asyncio.run(get_page_info(url))
                            return
                print("[ERROR] game_config.json 中沒有 enabled 的遊戲")
                print("\n使用方法:")
                print("  python get_region_coords.py <URL>")
                print("\nPowerShell 使用方式（URL 必須用引號括起來）:")
                print('  python get_region_coords.py "https://example.com/game?param=value&other=value"')
            else:
                print("[ERROR] game_config.json 不存在")
                print("\n使用方法:")
                print("  python get_region_coords.py <URL>")
        except Exception as e:
            print(f"[ERROR] 讀取 game_config.json 失敗: {e}")
            print("\n使用方法:")
            print("  python get_region_coords.py <URL>")
            print("\nPowerShell 使用方式（URL 必須用引號括起來）:")
            print('  python get_region_coords.py "https://example.com/game?param=value&other=value"')
        return
    
    url = sys.argv[1]
    asyncio.run(get_page_info(url))


if __name__ == "__main__":
    main()

