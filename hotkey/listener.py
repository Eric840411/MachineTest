"""熱鍵監聽 - Pause/Resume 和 Stop"""
import logging
import threading
from pynput import keyboard

# 全域停止旗標：Ctrl+C 或外部觸發可讓迴圈收斂退出
stop_event = threading.Event()
pause_event = threading.Event()   # 置位時代表「暫停」

# ---- 全域熱鍵監聽：Space 切換暫停/恢復；Esc 結束 ----
pressed_keys = set()


def _toggle_pause():
    if pause_event.is_set():
        pause_event.clear()
        logging.info("[Hotkey] 解除暫停（Resume）")
        print("▶️  Resume")
    else:
        pause_event.set()
        logging.info("[Hotkey] 進入暫停（Pause）")
        print("⏸️  Paused")


def _on_press(key):
    try:
        pressed_keys.add(key)
        # 偵測 Ctrl + Space
        if key == keyboard.Key.space and keyboard.Key.ctrl_l in pressed_keys:
            _toggle_pause()
        elif key == keyboard.Key.esc and keyboard.Key.ctrl_l in pressed_keys:
            logging.info("[Hotkey] ESC 被按下，停止所有執行緒")
            print("🛑 Stop requested (ESC)")
            stop_event.set()
    except Exception as e:
        logging.warning(f"[Hotkey] 監聽例外：{e}")


def _on_release(key):
    try:
        # 放開的時候從集合中移除
        if key in pressed_keys:
            pressed_keys.remove(key)
    except Exception:
        pass


def start_hotkey_listener():
    logging.info("[Hotkey] 啟動全域熱鍵監聽（Ctrl+Space=Pause/Resume, Ctrl+Esc=Stop）")
    print("🔧 Hotkeys: Ctrl+Space = Pause/Resume | Ctrl+Esc = Stop")
    listener = keyboard.Listener(on_press=_on_press, on_release=_on_release)
    listener.daemon = True
    listener.start()
