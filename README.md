# Web 博弈遊戲自動化測試框架

針對線上博弈遊戲的自動化品質檢測工具，支援多機台並行測試、共享佇列任務分配、階段式圖片比對（OpenCV SSIM）、音頻品質檢測、影片檢測、按鈕測試，並透過 Lark 即時推送測試報告。

**當前版本**: 見 `version.py`（啟動時自動顯示）

---

## 目錄結構

```
Machine test/
├── app.py                    # 主程式入口
├── version.py                # 版本號管理
├── requirements.txt          # Python 依賴
├── dotenv.env                # 環境變數（Lark Webhook 等，不上傳 Git）
│
├── game_config.json          # 遊戲 URL 列表（啟用/停用）
├── game_title_codes.csv      # 機器號清單（共享佇列依序分配）
├── actions.json              # 點擊動作配置（keyword_actions）
├── test_config.json          # 測試場景配置（測試模式/正常模式）
│
├── config/                   # 配置模組（載入/解析設定檔）
├── core/                     # 核心模組（瀏覽器管理、工具函數）
├── game/                     # 遊戲模組（執行器、導航、動作、餘額）
├── qa/                       # QA 品質檢測（圖片比對、影片檢測、音頻檢測、測試管理）
├── hotkey/                   # 熱鍵監聽（Ctrl+Space 暫停/恢復、Ctrl+Esc 停止）
├── notification/             # 通知模組（Lark Webhook）
│
├── machine_profiles/         # 各機器類型設定檔、參考圖片、音頻配置
│   └── _default/             # 全域預設配置（audio_config.json 等）
│
├── tools/                    # 互動式工具腳本
├── scripts/                  # 測試/除錯腳本
├── docs/                     # 詳細文檔
├── changelogs/               # 版本變更記錄（每版一個 .md 檔）
│
├── screenshots/              # 手動截圖輸出
├── comparison_results/       # 圖片比對結果輸出
├── _unsorted_screenshots/    # 未分類截圖暫存
└── _legacy/                  # 舊版備份
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

### 4. 設定機器號清單

編輯 `game_title_codes.csv`，列出所有要測試的機器號：

```csv
game_title_code
873-JJBX-0004
873-DFDC-0001
873-COINCOMBO-0002
```

> 系統會從代碼中提取關鍵字（如 `JJBX`）自動匹配 `machine_profiles/` 中對應的機器設定。
> 多個 URL（Worker）共享同一佇列，依序自動領取下一台機器。

### 5. 執行

```bash
python app.py
```

---

## 核心模組說明

| 模組 | 路徑 | 功能 |
|------|------|------|
| **配置管理** | `config/` | 載入 JSON/CSV 設定、解析機器類型、測試場景 |
| **瀏覽器核心** | `core/` | Playwright 瀏覽器生命週期管理、404 偵測 |
| **遊戲執行器** | `game/game_runner.py` | 進入遊戲、Spin 迴圈、餘額檢測、觸發測試流程 |
| **遊戲導航** | `game/navigation.py` | 大廳捲動搜尋、點擊遊戲卡片、進入/退出遊戲 |
| **遊戲動作** | `game/actions.py` | 座標點擊、多點操作 |
| **圖片比對** | `qa/image_comparator.py` | OpenCV SSIM + 直方圖比對，支援區域裁切 |
| **影片檢測** | `qa/video_detector.py` | 偵測黑屏、透明、單色異常畫面 |
| **音頻檢測** | `qa/audio_detector.py` | Web Audio API 注入，檢測音量/爆音/聲道 |
| **測試管理** | `qa/test_manager.py` | 共享佇列分配機器號，多 Worker 並行處理 |
| **Lark 通知** | `notification/lark.py` | 測試報告推送至 Lark 群組（含版本號） |
| **熱鍵監聽** | `hotkey/listener.py` | Ctrl+Space 暫停/恢復、Ctrl+Esc 停止 |
| **版本管理** | `version.py` | 版本號與版本名稱，啟動和報告自動引用 |

---

## 機器類型設定（machine_profiles）

每種遊戲類型有獨立的設定資料夾：

```
machine_profiles/
├── _default/
│   └── audio_config.json      # 全域預設音頻檢測閾值
├── JJBX/
│   ├── config.json            # 機器配置（匹配規則、特殊設定）
│   ├── test_flows.json        # 測試流程定義（進入、影片、按鈕、音頻、投注）
│   ├── audio_config.json      # [可選] 遊戲專屬音頻閾值（覆蓋 _default）
│   └── reference_images/      # 參考圖片
│       ├── entry/             # 進入遊戲後的畫面
│       ├── video/             # 影片正常播放畫面
│       ├── buttons/           # 按鈕狀態截圖
│       └── betting/           # 投注相關截圖
├── COINCOMBO/
├── DFDC/
├── default/                   # 預設 fallback 配置
└── ...
```

---

## 運行模式

### 測試模式（test_mode: true）

依據 `test_config.json` 中的 `active_scenario` 執行：

| 場景 | 說明 | 執行的流程 |
|------|------|-----------|
| `basic` | 基本測試 | 只執行 entry 流程 + 少量 Spin |
| `balance_test` | 餘額測試 | entry + 按鈕測試 |
| `full_test` | 完整測試 | 所有啟用的測試流程 |
| `navigation_test` | 導航測試 | 只測試進入/退出遊戲 |

- 每個場景可設定 `test_flows` 白名單，限制只執行特定流程
- Spin 次數、間隔、退出條件皆可配置
- 低餘額自動退出並重新進入

### 正常模式（test_mode: false）

- 自動 Spin 10 次，每次間隔 5 秒
- 不執行低餘額退出
- 餘額僅記錄，不做判斷

---

## 共享佇列機制

當有多個 URL（Worker）時，系統採用共享佇列分配機器號：

```
game_title_codes.csv 中的機器號 → 放入共享佇列
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
         Worker A (URL 1)     Worker B (URL 2)      Worker C (URL 3)
         領取機器 #1           領取機器 #2           領取機器 #3
         測試完畢 →            測試完畢 →            測試完畢 →
         領取機器 #4           領取機器 #5           領取機器 #6
              ⋮                     ⋮                     ⋮
         佇列空 → 結束         佇列空 → 結束         佇列空 → 結束
```

- 線程安全，自動分配，不會重複測試
- 單台測試完畢自動退出遊戲回到大廳，再進入下一台

---

## 音頻品質檢測

透過注入 JavaScript 攔截 Web Audio API，在不影響遊戲運行的情況下監控音頻品質：

| 檢測項目 | 說明 |
|---------|------|
| 靜音檢測 | 是否完全無聲音輸出 |
| 音量過小 | 平均音量低於 min_db 閾值（預設 -40 dB） |
| 音量過大 | 峰值超過 max_db 閾值（預設 -3 dB） |
| 爆音/失真 | Clipping ratio 超標（預設 > 1%） |
| 聲道檢測 | 左右聲道相關性判斷是否為單聲道（預設閾值 0.95） |
| 底噪分析 | 最低音量區間分析 |

### 配置優先順序

```
程式碼預設 → _default/audio_config.json → 遊戲專屬/audio_config.json → test_flows 內的 audio 設定
```

### 在 test_flows.json 中啟用

```json
{
  "name": "音頻檢測",
  "description": "檢測音頻品質：音量、爆音、聲道",
  "enabled": true
}
```

---

## 圖片比對機制

使用 **OpenCV SSIM + 直方圖** 綜合評分：

- **SSIM（結構相似性）**：權重 70%，比較亮度、對比度、結構
- **直方圖相關性**：權重 30%，比較整體顏色分佈
- 支援指定區域比對（排除動態 UI 元素如跑馬燈）
- 備用方案：無 OpenCV 時自動降級為 PSNR

---

## 工具腳本（tools/）

| 腳本 | 用途 | 執行方式 |
|------|------|----------|
| `image_comparison_visualizer.py` | 圖片比對可視化（支援連續比對） | `python tools/image_comparison_visualizer.py auto --quick --continuous` |
| `organize_images.py` | 整理截圖到參考圖片目錄 | `python tools/organize_images.py machine_profiles/JJBX` |
| `get_region_coords.py` | 取得圖片比對區域座標 + 手動截圖 | `python tools/get_region_coords.py` |

---

## 測試/除錯腳本（scripts/）

| 腳本 | 用途 | 執行方式 |
|------|------|----------|
| `test_audio.py` | 音頻測試工具（即時顯示 dB、聲道、爆音） | `python scripts/test_audio.py` |
| `simulate_test.py` | 模擬完整測試流程（不啟動瀏覽器） | `python scripts/simulate_test.py` |
| `test_components.py` | 個別組件單元測試 | `python scripts/test_components.py` |
| `test_integration.py` | 模組間集成測試 | `python scripts/test_integration.py` |
| `test_lark.py` | Lark 通知功能驗證 | `python scripts/test_lark.py` |
| `debug_matching.py` | 機器類型匹配邏輯除錯 | `python scripts/debug_matching.py` |

---

## 執行流程

```
app.py 啟動（顯示版本號）
  │
  ├── 載入配置（game_config.json, actions.json, test_config.json）
  ├── 載入機器號佇列（game_title_codes.csv）
  ├── 載入機器類型（machine_profiles/）
  ├── 初始化共享佇列（TestTaskManager）
  ├── 初始化 Lark 通知
  │
  └── 對每個 enabled URL 建立 Worker 執行緒：
       │
       └── GameRunner 迴圈（直到佇列空）：
            │
            ├── 從共享佇列領取機器號
            ├── 匹配 machine_profile
            │
            ├── 啟動瀏覽器（注入音頻監控）→ 開啟遊戲 URL
            ├── 大廳導航 → 進入遊戲
            │
            ├── 階段測試（依 test_flows.json + 場景白名單）：
            │    ├── 進入機器 → 圖片比對
            │    ├── 影片檢測 → 圖片比對
            │    ├── 按鈕測試 → 圖片比對
            │    ├── 投注測試 → 圖片比對
            │    └── 音頻檢測（音量/爆音/聲道）
            │
            ├── Spin 迴圈（測試模式: 依配置 / 正常模式: 10次 × 5秒）
            ├── 發送 Lark 測試報告（含版本號）
            ├── 退出遊戲 → 回到大廳
            └── 領取下一台機器 → 重複
```

---

## 版本控制

- `version.py`：管理當前版本號和版本名稱
- `changelogs/`：每個版本一個 `.md` 檔案，詳細記錄變更內容、修改的檔案、回滾方式
- 啟動時自動顯示版本號，Lark 報告中也會附帶版本資訊

---

## 熱鍵

| 快捷鍵 | 功能 |
|--------|------|
| `Ctrl+Space` | 暫停 / 恢復所有 Worker |
| `Ctrl+Esc` | 停止所有 Worker 並結束程式 |
