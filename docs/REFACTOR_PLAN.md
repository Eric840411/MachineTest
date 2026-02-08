# 模組化重構計劃

## 目標
將現有的 `main.py` 拆分成多個獨立模組，方便未來一個一個功能拆出來，最後用執行程序處理執行順序。

## 建議的目錄結構

```
Machine test/
├── config/              # 配置管理模組
│   ├── __init__.py
│   ├── loader.py        # 讀取 JSON/CSV 配置
│   └── models.py        # 配置數據模型（GameConfig）
│
├── core/                # 核心工具模組
│   ├── __init__.py
│   ├── browser.py       # 瀏覽器工具函數（wait_for_selector, safe_click 等）
│   └── utils.py         # 通用工具函數（file_md5, is_404_page 等）
│
├── game/                # 遊戲邏輯模組
│   ├── __init__.py
│   ├── runner.py        # GameRunner 類（主要遊戲執行邏輯）
│   ├── navigation.py    # 遊戲導航（進入/離開遊戲）
│   ├── actions.py       # 遊戲動作（點擊、Spin、座標點擊等）
│   └── balance.py       # 餘額檢查邏輯
│
├── notification/        # 通知模組
│   ├── __init__.py
│   └── lark.py          # LarkClient
│
├── hotkey/              # 熱鍵監聽模組
│   ├── __init__.py
│   └── listener.py      # 熱鍵監聽和頻率控制
│
├── runner.py            # 主執行程序（協調所有模組）
│
├── main.py              # 入口點（可選，或直接使用 runner.py）
│
├── config/              # 配置文件目錄（保持現有）
│   ├── game_config.json
│   ├── game_title_codes.csv
│   ├── actions.json
│   └── bet_random.json
│
└── requirements.txt
```

## 模組職責劃分

### 1. config/loader.py
- 讀取 `game_config.json`
- 讀取 `game_title_codes.csv`
- 讀取 `actions.json`
- 讀取 `bet_random.json`
- 配對 game_title_code 和 URL

### 2. config/models.py
- `GameConfig` 數據類

### 3. core/browser.py
- `wait_for_selector()`
- `wait_for_all_selectors()`
- `safe_click()`
- `is_404_page()`

### 4. core/utils.py
- `file_md5()`
- 其他通用工具函數

### 5. game/runner.py
- `GameRunner` 類的主要結構
- 初始化邏輯
- `spin_forever()` 主循環

### 6. game/navigation.py
- `scroll_and_click_game()` - 進入遊戲
- `_is_in_game()` - 檢查遊戲狀態
- `_low_balance_exit_and_reenter()` - 退出並重新進入
- `_fast_low_balance_exit_and_reenter()` - 快速退出流程
- `_find_cashout_button()` - 尋找退出按鈕

### 7. game/actions.py
- `_click_spin()` - 點擊 Spin 按鈕
- `click_multiple_positions()` - 點擊多個座標
- `_maybe_random_bet_click()` - 隨機下注點擊

### 8. game/balance.py
- `_parse_balance()` - 解析餘額
- 餘額變化檢測邏輯

### 9. notification/lark.py
- `LarkClient` 類

### 10. hotkey/listener.py
- `start_hotkey_listener()`
- `_toggle_pause()`
- `_handle_frequency_keys()`
- `get_current_frequency_status()`
- 全局變量：`stop_event`, `pause_event`, `spin_frequency`

### 11. runner.py
- `main()` 函數
- 協調所有模組的執行順序
- 初始化配置、啟動熱鍵、啟動遊戲執行器

## 執行順序（在 runner.py 中）

```python
1. 初始化日誌和環境變量
2. 啟動熱鍵監聽器
3. 讀取配置（config/loader.py）
4. 初始化通知客戶端（notification/lark.py）
5. 為每個遊戲創建 GameRunner（game/runner.py）
6. 啟動所有遊戲執行器
7. 等待所有執行完成
```

## 優點

1. **模組化**：每個功能獨立，易於測試和維護
2. **可擴展**：未來可以輕鬆添加新功能（例如新的通知方式、新的遊戲動作）
3. **清晰**：職責分明，代碼結構清晰
4. **可重用**：工具函數可以在多個地方重用
5. **易於測試**：每個模組可以獨立測試

## 遷移步驟

1. 創建目錄結構
2. 逐步移動代碼到對應模組
3. 更新導入語句
4. 測試每個模組
5. 更新 runner.py 協調執行

