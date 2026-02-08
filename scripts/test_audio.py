"""
音頻測試工具 - 即時顯示遊戲音頻的分貝、聲道、爆音狀態

使用方法：
  python scripts/test_audio.py                  # 從 game_config.json 讀取 URL
  python scripts/test_audio.py "https://..."     # 指定 URL

操作：
  Enter  → 開始/重新採樣分析
  l      → 即時音量監控（持續顯示，按 Ctrl+C 停止）
  q      → 結束
"""
import asyncio
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from playwright.async_api import async_playwright
from qa.audio_detector import AudioDetector, load_audio_config, DEFAULT_AUDIO_CONFIG


def format_db_bar(db: float, width: int = 40) -> str:
    """把 dB 值轉成視覺化條形圖"""
    # dB 範圍: -60 ~ 0
    normalized = max(0, min(1, (db + 60) / 60))
    filled = int(normalized * width)
    bar = "#" * filled + "-" * (width - filled)

    # 顏色提示
    if db > -3:
        label = "!! CLIP"
    elif db > -10:
        label = "LOUD"
    elif db > -30:
        label = "OK"
    elif db > -50:
        label = "LOW"
    else:
        label = "SILENT"

    return f"[{bar}] {db:>7.1f} dB  {label}"


async def run_audio_test(url: str):
    """執行音頻測試"""
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 500, "height": 859},
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/85.0.4183.127 Mobile Safari/537.36"
            ),
        )

        # 注入音頻監控（必須在導航前）
        page = await context.new_page()
        await AudioDetector.inject_monitor(page)

        print("=" * 60)
        print("  音頻測試工具")
        print("=" * 60)
        print(f"URL: {url[:70]}...")
        print()

        try:
            print("正在載入頁面...")
            await page.goto(url, timeout=30000)
            await page.wait_for_load_state("networkidle", timeout=10000)
            print("頁面載入完成!")
            print()
            print("請先在遊戲中操作（進入遊戲、Spin 等）讓音頻開始播放，")
            print("然後使用以下指令：")
            print()
            print("-" * 60)
            print("  Enter  ->  採樣 5 秒並分析")
            print("  l      ->  即時音量監控")
            print("  q      ->  結束")
            print("-" * 60)

            while True:
                try:
                    user_input = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: input("\n指令 (Enter/l/q): ").strip().lower()
                    )
                except EOFError:
                    break

                if user_input == "q":
                    print("結束音頻測試。")
                    break

                elif user_input == "l":
                    await _realtime_monitor(page)

                else:
                    await _full_analysis(page)

        except Exception as e:
            print(f"錯誤: {e}")
        finally:
            await browser.close()


async def _full_analysis(page):
    """執行完整音頻分析"""
    print()
    print("=" * 60)
    print("  開始採樣分析 (5 秒)")
    print("=" * 60)

    result = await AudioDetector.analyze(page, DEFAULT_AUDIO_CONFIG)

    print()
    print("  分析結果")
    print("-" * 60)

    # 音量
    print(f"  有聲音:       {'YES' if result.has_audio else 'NO'}")
    if result.has_audio:
        print(f"  平均音量:     {format_db_bar(result.avg_volume_db)}")
        print(f"  峰值音量:     {format_db_bar(result.peak_volume_db)}")
        print(f"  最低音量:     {format_db_bar(result.min_volume_db)}")
    else:
        print(f"  平均音量:     -- (無音頻)")

    print()

    # 爆音
    if result.clipping_detected:
        print(f"  爆音檢測:     !! 偵測到爆音 (clipping ratio: {result.clipping_ratio:.4f})")
    else:
        print(f"  爆音檢測:     OK (clipping ratio: {result.clipping_ratio:.4f})")

    # 聲道
    if result.has_audio:
        stereo_str = "Stereo" if result.is_stereo else "Mono (疑似單聲道)"
        print(f"  聲道:         {stereo_str}")
        print(f"  聲道相關性:   {result.channel_correlation:.4f} (1.0=完全相同=單聲道)")
    else:
        print(f"  聲道:         -- (無音頻)")

    print()

    # 底噪
    print(f"  底噪:         {result.noise_floor_db:.1f} dB")
    print(f"  採樣數:       {result.sample_count}")

    # 詳情
    details = result.details
    print(f"  取樣率:       {details.get('sample_rate', 'N/A')} Hz")
    print(f"  AudioContext: {details.get('context_count', 0)} 個")
    print(f"  聲道數:       {details.get('channel_count', 'N/A')}")

    print()

    # 問題彙整
    if result.issues:
        print("  !! 檢測到的問題:")
        for i, issue in enumerate(result.issues, 1):
            print(f"     {i}. {issue}")
    else:
        print("  OK 所有檢測通過!")

    print()
    print("-" * 60)

    # 顯示建議閾值
    if result.has_audio:
        print("  建議閾值 (可填入 audio_config.json):")
        print(f'    "volume": {{ "min_db": {int(result.avg_volume_db - 10)}, "max_db": {int(result.peak_volume_db + 3)} }}')
    print()


async def _realtime_monitor(page):
    """即時音量監控"""
    print()
    print("=" * 60)
    print("  即時音量監控 (按 Ctrl+C 停止)")
    print("=" * 60)
    print()
    print("  RMS (Overall)    |  L Channel         |  R Channel         | Corr")
    print("-" * 90)

    try:
        while True:
            levels = await AudioDetector.get_realtime_levels(page)

            if levels is None:
                print("  -- 等待音頻數據... (請確認遊戲已開始播放) --", end="\r")
                await asyncio.sleep(0.3)
                continue

            rms_db = levels.get("rms_db", -100)
            peak_db = levels.get("peak_db", -100)
            rms_l = levels.get("rms_l", 0)
            rms_r = levels.get("rms_r", 0)
            corr = levels.get("correlation", 0)
            clip = levels.get("clip_ratio", 0)

            # dB bar for overall
            bar_width = 20
            norm = max(0, min(1, (rms_db + 60) / 60))
            filled = int(norm * bar_width)
            bar = "#" * filled + "-" * (bar_width - filled)

            # L channel bar
            import math as _math
            l_db = 20 * _math.log10(rms_l) if rms_l > 0 else -100
            norm_l = max(0, min(1, (l_db + 60) / 60))
            bar_l = "#" * int(norm_l * bar_width) + "-" * (bar_width - int(norm_l * bar_width))

            # R channel bar
            r_db = 20 * _math.log10(rms_r) if rms_r > 0 else -100
            norm_r = max(0, min(1, (r_db + 60) / 60))
            bar_r = "#" * int(norm_r * bar_width) + "-" * (bar_width - int(norm_r * bar_width))

            clip_warn = " !! CLIP" if clip > 0.01 else ""

            line = (
                f"  [{bar}] {rms_db:>6.1f}dB"
                f" | [{bar_l}] {l_db:>6.1f}dB"
                f" | [{bar_r}] {r_db:>6.1f}dB"
                f" | {corr:.2f}"
                f"{clip_warn}"
            )

            print(line)
            await asyncio.sleep(0.3)

    except KeyboardInterrupt:
        print("\n\n  即時監控已停止。")
    except Exception as e:
        print(f"\n  監控錯誤: {e}")


def main():
    if len(sys.argv) >= 2:
        url = sys.argv[1]
        asyncio.run(run_audio_test(url))
        return

    # 從 game_config.json 讀取
    try:
        import json
        config_path = BASE_DIR / "game_config.json"
        if not config_path.exists():
            print("[ERROR] game_config.json 不存在")
            print('使用方法: python scripts/test_audio.py "https://..."')
            return

        with config_path.open("r", encoding="utf-8") as f:
            games = json.load(f)

        enabled_urls = [g["url"] for g in games if g.get("enabled", True) and g.get("url")]
        if not enabled_urls:
            print("[ERROR] 沒有 enabled 的遊戲")
            return

        if len(enabled_urls) == 1:
            asyncio.run(run_audio_test(enabled_urls[0]))
        else:
            print("選擇要測試的遊戲:")
            for i, u in enumerate(enabled_urls, 1):
                print(f"  {i}. {u[:70]}...")
            try:
                choice = int(input(f"\n請輸入編號 (1-{len(enabled_urls)}): "))
                if 1 <= choice <= len(enabled_urls):
                    asyncio.run(run_audio_test(enabled_urls[choice - 1]))
                else:
                    print("無效選擇")
            except (ValueError, EOFError):
                print("無效輸入")
    except Exception as e:
        print(f"[ERROR] {e}")


if __name__ == "__main__":
    main()

