# 機器類型配置文件夾結構說明

## 文件夾結構

每個機器類型都有自己的文件夾，文件夾名稱即為機器類型名稱（不區分大小寫）：

```
machine_profiles/
├── DFDC/
│   ├── config.json          # 機器類型基本配置
│   ├── test_flows.json      # 測試流程配置（可選）
│   └── reference_images/    # 參考圖片目錄（可選）
│       ├── entry/           # 進入機器階段的參考圖片
│       ├── video/            # 視頻檢測階段的參考圖片
│       ├── buttons/          # 按鈕測試階段的參考圖片
│       └── ...
├── JJBX/
│   ├── config.json
│   ├── test_flows.json
│   └── reference_images/
├── RISINGROCKETS/
│   ├── config.json
│   ├── test_flows.json
│   └── reference_images/
│       ├── entry/
│       ├── video/
│       └── buttons/
├── default/
│   ├── config.json          # 默認配置
│   └── test_flows.json
└── [新機器類型]/
    ├── config.json
    ├── test_flows.json
    └── reference_images/
```

## 配置文件說明

### config.json

機器類型的基本配置：

```json
{
  "name": "機器類型名稱",
  "description": "描述",
  "enabled": true,
  "match_rules": {
    "gameid": ["gameid1", "gameid2"],
    "game_title_code_pattern": ["PATTERN1", "PATTERN2"],
    "url_pattern": ["pattern1", "pattern2"]
  },
  "button_selectors": {
    "spin": "button.spin",
    "bet": "button.bet"
  },
  "video_detection": {
    "selector": "canvas, video",
    "threshold": {
      "black": 10,
      "transparent": 10,
      "monochrome": 5
    }
  },
  "special_config": {
    "balance_check_interval": 10,
    "spin_interval": 1.0
  }
}
```

### test_flows.json（可選）

測試流程配置，如果不存在則從 config.json 的 `test_flows` 欄位讀取：

```json
{
  "flows": [
    {
      "name": "進入機器",
      "description": "進入機器並等待載入",
      "enabled": true,
      "timeout": 15.0,
      "retry_count": 3,
      "config": {
        "wait_for_selector": ".game-container",
        "image_comparison": {
          "enabled": true,
          "similarity_threshold": 0.8,
          "selector": null,
          "region": null,
          "images": []
        }
      }
    }
  ]
}
```

## 圖片比對功能

### reference_images/ 目錄結構

每個階段可以有自己的參考圖片目錄：

```
reference_images/
├── entry/        # 進入機器階段的參考圖片
│   ├── entry_1.png
│   └── entry_2.png
├── video/        # 視頻檢測階段的參考圖片
│   └── video_normal.png
├── buttons/      # 按鈕測試階段的參考圖片
│   └── buttons_visible.png
└── betting/      # 下注測試階段的參考圖片
    └── betting_screen.png
```

### 圖片比對配置

在 `test_flows.json` 的每個流程配置中可以添加 `image_comparison` 配置：

```json
{
  "name": "進入機器",
  "config": {
    "image_comparison": {
      "enabled": true,                    # 是否啟用圖片比對
      "similarity_threshold": 0.8,        # 相似度閾值（0-1，0.8表示80%相似）
      "selector": "canvas",               # 可選：只比對特定元素的截圖
      "region": {                         # 可選：只比對特定區域
        "x": 0,
        "y": 0,
        "width": 500,
        "height": 200
      },
      "images": []                        # 可選：指定要比對的圖片（空則使用目錄下所有圖片）
    }
  }
}
```

### 圖片比對參數說明

- **enabled**: 是否啟用圖片比對（預設 false）
- **similarity_threshold**: 相似度閾值（0-1）
  - 0.9 = 90% 相似（非常嚴格）
  - 0.8 = 80% 相似（推薦）
  - 0.7 = 70% 相似（較寬鬆）
- **selector**: CSS 選擇器，只比對特定元素的截圖（null 表示整個頁面）
- **region**: 只比對特定區域的圖片
  - x, y: 起始座標
  - width, height: 區域大小
- **images**: 指定要比對的圖片列表（空則使用目錄下所有 .png/.jpg/.jpeg）

### 圖片比對結果

圖片比對結果會記錄在測試報告中：
- 每個階段的比對結果
- 相似度分數
- 匹配的圖片數量
- 比對失敗的詳細信息

## 匹配規則

系統會按照以下優先級匹配機器類型：

1. **手動指定** - 在 `game_config.json` 中指定 `machine_type`（最高優先級）
2. **從 game_title_code 提取關鍵字匹配文件夾名稱** - 從 CSV 的 game_title_code 中提取關鍵字（例如 "873-RISINGROCKETS-0140" -> "RISINGROCKETS"），然後匹配對應的文件夾名稱
3. **gameid 匹配** - 從 URL 提取 gameid 進行匹配（在 match_rules 中定義）
4. **game_title_code 模式匹配** - 檢查 game_title_code 是否包含關鍵字（在 match_rules 中定義）
5. **URL 模式匹配** - 檢查 URL 是否包含關鍵字（在 match_rules 中定義）
6. **默認配置** - 如果都不匹配，使用 `default` 文件夾的配置

### 關鍵字提取規則

從 `game_title_code` 中提取關鍵字的邏輯：
- 格式通常為：`數字-關鍵字-數字`（例如 "873-RISINGROCKETS-0140"）
- 系統會提取中間部分作為關鍵字（例如 "RISINGROCKETS"）
- 然後用這個關鍵字去匹配 `machine_profiles/` 文件夾下的文件夾名稱

**範例：**
- `game_title_code = "873-RISINGROCKETS-0140"` → 提取 `RISINGROCKETS` → 匹配 `machine_profiles/RISINGROCKETS/`
- `game_title_code = "873-DFDC-0140"` → 提取 `DFDC` → 匹配 `machine_profiles/DFDC/`
- `game_title_code = "873-JJBX-0140"` → 提取 `JJBX` → 匹配 `machine_profiles/JJBX/`

## 測試流程名稱

支援的測試流程名稱（在 `test_flows.json` 中）：

- `進入機器` - 進入機器並等待載入（自動執行，無需在流程中定義）
- `視頻檢測` - 檢測視頻是否正常顯示
- `按鈕測試` - 測試按鈕反應
- `下注測試` - 測試下注功能
- `特殊功能測試` - 測試特殊功能（如Free Spin）
- `Grand功能測試` - 測試Grand功能（如Grand Bonus、Jackpot）

## 添加新機器類型

### 步驟 1: 創建文件夾

在 `machine_profiles/` 目錄下創建新的文件夾，文件夾名稱即為機器類型名稱：

```bash
mkdir machine_profiles/NEW_TYPE
mkdir machine_profiles/NEW_TYPE/reference_images
```

### 步驟 2: 創建 config.json

在文件夾中創建 `config.json`：

```json
{
  "name": "新機器類型",
  "description": "新機器類型的描述",
  "enabled": true,
  "match_rules": {
    "gameid": ["newgameid"],
    "game_title_code_pattern": ["NEW", "TYPE"]
  },
  "button_selectors": {
    "spin": "button.new-spin"
  },
  "video_detection": {
    "selector": "canvas.new-canvas"
  },
  "special_config": {}
}
```

### 步驟 3: 創建 test_flows.json（可選）

在文件夾中創建 `test_flows.json`：

```json
{
  "flows": [
    {
      "name": "進入機器",
      "description": "進入新機器",
      "enabled": true,
      "timeout": 15.0,
      "retry_count": 3,
      "config": {
        "image_comparison": {
          "enabled": true,
          "similarity_threshold": 0.8
        }
      }
    }
  ]
}
```

### 步驟 4: 準備參考圖片（可選）

在 `reference_images/` 目錄下創建各階段的參考圖片：

```bash
# 進入機器階段的參考圖片
mkdir machine_profiles/NEW_TYPE/reference_images/entry
# 將參考圖片放入 entry/ 目錄

# 視頻檢測階段的參考圖片
mkdir machine_profiles/NEW_TYPE/reference_images/video
# 將參考圖片放入 video/ 目錄
```

## 注意事項

1. **文件夾名稱** - 文件夾名稱會自動轉為大寫作為機器類型識別碼
2. **默認配置** - `default` 文件夾是特殊文件夾，當沒有匹配到任何類型時使用
3. **啟用狀態** - 只有 `enabled: true` 的配置才會被使用
4. **測試流程啟用** - 每個測試流程也有 `enabled` 屬性，可以單獨控制
5. **配置文件格式** - 必須是有效的 JSON 格式
6. **圖片格式** - 參考圖片支援 .png、.jpg、.jpeg 格式
7. **圖片比對** - 圖片比對是可選功能，如果沒有參考圖片目錄或未啟用，會自動跳過

## 範例

完整的配置範例請參考：
- `DFDC/config.json` 和 `DFDC/test_flows.json`
- `JJBX/config.json` 和 `JJBX/test_flows.json`
- `RISINGROCKETS/config.json` 和 `RISINGROCKETS/test_flows.json`（包含圖片比對配置）
- `default/config.json` 和 `default/test_flows.json`
