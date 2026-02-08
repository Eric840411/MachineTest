# Web 博弈遊戲自動化測試框架

針對線上博弈遊戲的自動化品質檢測工具，支援多機台並行測試、階段式圖片比對（OpenCV SSIM）、影片檢測、按鈕測試，並透過 Lark 即時推送測試報告。

---

## 目錄結構

```
Machine test/
├── app.py                    # 主程式入口
├── requirements.txt          # Python 依賴
├── dotenv.env                # 環境變數（Lark Webhook 等）
│
├── game_config.json          # 遊戲 URL 列表（啟用/停用）
├── game_title_codes.csv      # 遊戲代碼對照表（用於匹配機器類型）
├── actions.json              # 點擊動作配置（keyword_actions）
├── machine_profiles.json     # 機器類型匹配規則
├── test_config.json          # 測試場景配置
│
├── config/                   # 配置模組（載入/解析設定檔）
├── core/                     # 核心模組（瀏覽器管理、工具函數）
├── game/                     # 遊戲模組（執行器、導航、動作、餘額）
├── qa/                       # QA 品質檢測（圖片比對、影片檢測、測試管理）
├── hotkey/                   # 熱鍵監聽（Ctrl+C 優雅退出）
├── notification/             # 通知模組（Lark Webhook）
├── machine_profiles/         # 各機器類型設定檔與參考圖片
│
├── tools/                    # 獨立工具腳本
├── scripts/                  # 測試/除錯腳本
├── docs/                     # 詳細文檔
├── _legacy/                  # 舊版備份
├── comparison_results/       # 圖片比對結果輸出
└── screenshots/              # 截圖輸出
```

---

## 快速開始

### 1. 安裝依賴

```bash
pip install -r requirements.txt
playwright install
```

### 2. 設定環境變數

編輯 `dotenv.env`，填入 Lark Webhook URL：

```
LARK_WEBHOOK_URL=https://open.larksuite.com/open-apis/bot/v2/hook/your-webhook-id
```

### 3. 設定遊戲 URL

編輯 `game_config.json`，將要測試的遊戲設為 `"enabled": true`：

```json
[
    {
        "url": "https://your-game-url...",
        "enabled": true
    }
]
```

### 4. 設定遊戲代碼對照

編輯 `game_title_codes.csv`，每行對應一個 `game_config.json` 中 enabled 的遊戲：

```csv
game_title_code
873-JJBX-0004
```

> 系統會從代碼中提取關鍵字（如 `JJBX`）來匹配 `machine_profiles/` 中對應的機器設定。

### 5. 執行

```bash
python app.py
```

---

## 核心模組說明

| 模組 | 路徑 | 功能 |
|------|------|------|
| **配置管理** | `config/` | 載入 JSON/CSV 設定、解析機器類型、測試場景 |
| **瀏覽器核心** | `core/` | Playwright 瀏覽器生命週期管理 |
| **遊戲執行器** | `game/game_runner.py` | 進入遊戲、Spin 迴圈、餘額檢測、觸發測試流程 |
| **遊戲導航** | `game/navigation.py` | 大廳捲動搜尋、點擊遊戲卡片、進入遊戲 |
| **遊戲動作** | `game/actions.py` | 座標點擊、多點操作 |
| **圖片比對** | `qa/image_comparator.py` | OpenCV SSIM + 直方圖比對，支援區域裁切 |
| **影片檢測** | `qa/video_detector.py` | 偵測黑屏、透明、單色異常畫面 |
| **測試管理** | `qa/test_manager.py` | 多機台測試任務排程 |
| **Lark 通知** | `notification/lark.py` | 測試報告推送至 Lark 群組 |
| **熱鍵監聽** | `hotkey/listener.py` | 支援 Ctrl+C 優雅中止所有執行緒 |

---

## 機器類型設定（machine_profiles）

每種遊戲類型有獨立的設定資料夾：

```
machine_profiles/
├── JJBX/
│   ├── config.json           # 機器配置（匹配規則、特殊設定）
│   ├── test_flows.json       # 測試流程定義（進入、影片、按鈕、投注）
│   └── reference_images/     # 參考圖片
│       ├── entry/            # 進入遊戲後的畫面
│       ├── video/            # 影片正常播放畫面
│       ├── buttons/          # 按鈕狀態截圖
│       └── betting/          # 投注相關截圖
├── COINCOMBO/
├── DFDC/
└── ...
```

---

## 測試場景（test_config.json）

支援多種預設測試場景，透過 `active_scenario` 切換：

| 場景 | 說明 |
|------|------|
| `basic` | 只測試進入遊戲和基本 Spin |
| `balance_test` | 餘額檢測 + 退出流程 |
| `full_test` | 所有功能完整測試 |
| `navigation_test` | 只測試進入/退出遊戲流程 |

---

## 工具腳本（tools/）

| 腳本 | 用途 | 執行方式 |
|------|------|----------|
| `image_comparison_visualizer.py` | 圖片比對可視化（支援連續比對） | `python tools/image_comparison_visualizer.py auto --quick --continuous` |
| `organize_images.py` | 整理截圖到參考圖片目錄 | `python tools/organize_images.py machine_profiles/JJBX` |
| `get_region_coords.py` | 取得圖片比對區域座標 | `python tools/get_region_coords.py` |

---

## 除錯腳本（scripts/）

| 腳本 | 用途 |
|------|------|
| `simulate_test.py` | 模擬完整測試流程（不啟動瀏覽器） |
| `test_components.py` | 個別組件單元測試 |
| `test_integration.py` | 模組間集成測試 |
| `test_lark.py` | Lark 通知功能驗證 |
| `debug_matching.py` | 機器類型匹配邏輯除錯 |

---

## 圖片比對機制

使用 **OpenCV SSIM + 直方圖** 綜合評分：

- **SSIM（結構相似性）**：權重 70%，比較亮度、對比度、結構
- **直方圖相關性**：權重 30%，比較整體顏色分佈
- 支援指定區域比對（排除動態 UI 元素如跑馬燈）
- 備用方案：無 OpenCV 時自動降級為 PSNR

---

## 執行流程

```
app.py 啟動
  │
  ├── 載入配置（game_config.json, actions.json, game_title_codes.csv）
  ├── 載入機器類型（machine_profiles/）
  ├── 初始化 Lark 通知
  │
  └── 對每個 enabled 遊戲：
       ├── 匹配機器類型（透過 game_title_code 關鍵字）
       ├── 建立 GameRunner 執行緒
       │
       └── GameRunner 執行：
            ├── 啟動瀏覽器 → 開啟遊戲 URL
            ├── 大廳導航 → 進入遊戲
            ├── 階段測試（依 test_flows.json）：
            │    ├── 進入機器 → 圖片比對
            │    ├── 影片檢測 → 圖片比對
            │    ├── 按鈕測試 → 圖片比對
            │    └── 投注測試 → 圖片比對
            ├── Spin 迴圈 + 餘額監測
            └── 發送 Lark 測試報告
```
