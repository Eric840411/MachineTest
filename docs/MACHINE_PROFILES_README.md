# 機器類型配置系統說明

本系統支援為不同類型的機器（DFDC、JJBX、JJBXGRAND等）定義專屬的測試流程。

## 概述

系統採用**文件夾結構**管理機器類型配置，每個機器類型有自己的文件夾，便於擴展和維護。

系統會根據以下規則自動匹配機器類型（按優先級排序）：
1. **手動指定** - 在 game_config.json 中指定 machine_type（最高優先級）
2. **從 game_title_code 提取關鍵字匹配文件夾名稱** - 從 CSV 的 game_title_code 中提取關鍵字（例如 "873-RISINGROCKETS-0140" -> "RISINGROCKETS"），然後匹配對應的文件夾名稱
3. **gameid** - 從 URL 中提取的遊戲 ID（在 match_rules 中定義）
4. **game_title_code_pattern** - 遊戲標題代碼中的關鍵字（在 match_rules 中定義）
5. **url_pattern** - URL 中的關鍵字（在 match_rules 中定義）
6. **默認配置** - 如果都不匹配，使用 default 文件夾的配置

匹配成功後，系統會使用該機器類型的專屬測試流程。

## 文件夾結構

```
machine_profiles/
├── DFDC/
│   ├── config.json          # 機器類型基本配置
│   └── test_flows.json      # 測試流程配置（可選）
├── JJBX/
│   ├── config.json
│   └── test_flows.json
├── JJBXGRAND/
│   ├── config.json
│   └── test_flows.json
├── default/
│   ├── config.json          # 默認配置
│   └── test_flows.json
└── [新機器類型]/
    ├── config.json
    └── test_flows.json
```

## 配置文件說明

### config.json

```json
{
  "default_profile": "default",
  "profiles": {
    "DFDC": {
      "name": "DFDC 機器類型",
      "description": "DFDC 機器的專屬測試流程",
      "enabled": true,
      "match_rules": {
        "gameid": ["osmbwjl"],
        "game_title_code_pattern": ["DFDC", "BWJL"]
      },
      "test_flows": [...],
      "button_selectors": {...},
      "video_detection": {...},
      "special_config": {...}
    }
  }
}
```

## 機器類型配置說明

### 1. match_rules（匹配規則）

定義如何識別該機器類型：

- **gameid**: 從 URL 參數中提取的遊戲 ID 列表
- **game_title_code_pattern**: 遊戲標題代碼中需要包含的關鍵字
- **url_pattern**: URL 中需要包含的關鍵字

**範例：**
```json
"match_rules": {
  "gameid": ["osmbwjl", "osmdfdc"],
  "game_title_code_pattern": ["DFDC", "BWJL"],
  "url_pattern": ["dfdc", "bwjl"]
}
```

### 2. test_flows（測試流程）

定義該機器類型的測試步驟：

```json
"test_flows": [
  {
    "name": "進入機器",
    "description": "進入DFDC機器並等待載入",
    "enabled": true,
    "timeout": 15.0,
    "retry_count": 3,
    "config": {
      "wait_for_selector": ".game-container",
      "check_loading": true
    }
  },
  {
    "name": "視頻檢測",
    "description": "檢測DFDC視頻是否正常顯示",
    "enabled": true,
    "timeout": 10.0,
    "retry_count": 2,
    "config": {
      "selector": "canvas#game-canvas",
      "threshold": {
        "black": 10,
        "transparent": 10,
        "monochrome": 5
      }
    }
  }
]
```

**支援的測試流程名稱：**
- `進入機器` - 進入機器並等待載入
- `視頻檢測` - 檢測視頻是否正常顯示
- `按鈕測試` - 測試按鈕反應
- `下注測試` - 測試下注功能
- `特殊功能測試` - 測試特殊功能（如Free Spin）
- `Grand功能測試` - 測試Grand功能（如Grand Bonus、Jackpot）

### 3. button_selectors（按鈕選擇器）

定義該機器類型的按鈕 CSS 選擇器：

```json
"button_selectors": {
  "spin": "button.spin-btn",
  "bet": "button.bet-btn",
  "auto": "button.auto-btn",
  "balance": ".balance-display"
}
```

### 4. video_detection（視頻檢測配置）

定義視頻檢測的選擇器和閾值：

```json
"video_detection": {
  "selector": "canvas#game-canvas",
  "threshold": {
    "black": 10,
    "transparent": 10,
    "monochrome": 5
  }
}
```

### 5. special_config（特殊配置）

定義該機器類型的特殊配置：

```json
"special_config": {
  "balance_check_interval": 10,
  "spin_interval": 1.0,
  "enable_auto_spin": false,
  "enable_free_spin_detection": true
}
```

## 已預設的機器類型

### 1. DFDC
- **匹配規則**: gameid 包含 `osmbwjl`，或 game_title_code 包含 `DFDC`、`BWJL`
- **專屬測試**: 基本按鈕測試、下注測試
- **特殊配置**: balance_check_interval=10, spin_interval=1.0

### 2. JJBX
- **匹配規則**: gameid 包含 `osmjjbx`，或 game_title_code 包含 `JJBX`
- **專屬測試**: 基本按鈕測試、特殊功能測試（Free Spin）
- **特殊配置**: balance_check_interval=15, spin_interval=1.5, enable_free_spin_detection=true

### 3. JJBXGRAND
- **匹配規則**: gameid 包含 `osmjjbxgold`，或 game_title_code 包含 `JJBXGRAND`、`JJBXGOLD`
- **專屬測試**: 基本按鈕測試、Grand功能測試（Grand Bonus、Jackpot）
- **特殊配置**: balance_check_interval=20, spin_interval=2.0, enable_grand_bonus_detection=true

### 4. default（默認）
- **匹配規則**: 無（當其他類型都不匹配時使用）
- **專屬測試**: 基本測試流程
- **特殊配置**: 通用配置

## 添加新的機器類型

### 步驟 1: 創建文件夾

在 `machine_profiles/` 目錄下創建新的文件夾，文件夾名稱即為機器類型名稱：

```bash
mkdir machine_profiles/NEW_TYPE
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
      "config": {}
    }
  ]
}
```

### 步驟 2: 在 GameRunner 中添加專屬測試邏輯（可選）

如果需要特殊的測試邏輯，可以在 `game/game_runner.py` 的 `_run_machine_specific_tests` 方法中添加：

```python
elif flow.name == "新功能測試":
    await self._test_new_feature(flow.config)
```

然後實現對應的測試方法：

```python
async def _test_new_feature(self, config: Dict[str, Any]):
    """測試新功能"""
    logging.info(f"[Test] 測試新功能: {config}")
    # 實現具體的測試邏輯
```

## 使用方式

### 自動匹配

系統會自動根據 URL 和 game_title_code 匹配機器類型：

```python
# 在 app.py 中自動執行
machine_profile = match_machine_profile(
    machine_profiles,
    conf.url,
    conf.game_title_code,
    gameid
)
```

### 手動指定

也可以在 `game_config.json` 中手動指定機器類型：

```json
{
  "url": "https://example.com/game",
  "machine_type": "DFDC",
  "enabled": true
}
```

## 測試流程執行順序

1. **進入機器** - 自動執行（在 `_build_browser` 中）
2. **視頻檢測** - 根據配置執行
3. **按鈕測試** - 根據配置執行
4. **下注測試** - 根據配置執行（如果配置了）
5. **特殊功能測試** - 根據配置執行（如果配置了）
6. **Grand功能測試** - 根據配置執行（如果配置了）

## 日誌輸出

系統會記錄機器類型的匹配和測試流程執行情況：

```
[Runner] 機器 1 匹配到類型: DFDC
[Test] 執行機器類型專屬測試流程: DFDC 機器類型
[Test] 執行測試流程: 視頻檢測 - 檢測DFDC視頻是否正常顯示
[Test] 執行測試流程: 按鈕測試 - 測試DFDC專屬按鈕
```

## 注意事項

1. **匹配優先級**: 系統會按照配置檔案的順序進行匹配，第一個匹配成功的類型會被使用
2. **默認配置**: 如果沒有匹配到任何類型，會使用 `default_profile` 指定的默認配置
3. **啟用狀態**: 只有 `enabled: true` 的機器類型配置才會被使用
4. **測試流程啟用**: 每個測試流程也有 `enabled` 屬性，可以單獨控制是否執行

## 範例配置

完整的機器類型配置範例請參考：
- `machine_profiles/DFDC/` - DFDC 機器類型配置
- `machine_profiles/JJBX/` - JJBX 機器類型配置
- `machine_profiles/JJBXGRAND/` - JJBXGRAND 機器類型配置
- `machine_profiles/default/` - 默認配置

詳細說明請參考 `machine_profiles/README.md`。

