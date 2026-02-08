# 按鈕測試配置指南

## 概述

按鈕測試功能支持點擊按鈕後檢測視覺反饋（如黃色高亮），確保按鈕點擊有效。每個機器類型可以配置自己的按鈕列表和高亮檢測方式。

## 配置結構

### 1. 在 `config.json` 中配置按鈕測試

```json
{
  "button_test_config": {
    "highlight_detection": {
      "method": "css_class",
      "css_class": "active, selected, highlight, yellow, [class*='active'], [class*='selected']",
      "background_color": "#FFD700, #FFEB3B, #FFC107, yellow, rgb(255, 215, 0)",
      "check_style": true
    },
    "buttons": [
      {
        "name": "BET x1",
        "selector": "button:has-text('BET x1'), [class*='bet'][class*='x1']",
        "highlight_check": true
      },
      {
        "name": "BET x2",
        "selector": "button:has-text('BET x2'), [class*='bet'][class*='x2']",
        "highlight_check": true
      }
    ]
  }
}
```

### 2. 在 `test_flows.json` 中配置按鈕測試流程

```json
{
  "name": "按鈕測試",
  "config": {
    "buttons": ["BET x1", "BET x2", "PLAY 9 Credits"],
    "check_highlight": true,
    "image_comparison": {
      "enabled": true,
      "similarity_threshold": 0.8
    }
  }
}
```

## 配置參數說明

### highlight_detection（高亮檢測配置）

#### method
- **類型**: string
- **可選值**: `"css_class"`, `"background_color"`, `"screenshot"`
- **說明**: 高亮檢測方法
  - `css_class`: 檢查 CSS 類名（推薦）
  - `background_color`: 檢查背景顏色
  - `screenshot`: 使用截圖比對

#### css_class
- **類型**: string（逗號分隔）
- **說明**: 高亮狀態的 CSS 類名列表
- **範例**: `"active, selected, highlight, yellow, [class*='active']"`
- **注意**: 支持完整匹配和部分匹配（使用 `[class*='xxx']` 語法）

#### background_color
- **類型**: string（逗號分隔）
- **說明**: 高亮狀態的背景顏色列表
- **範例**: `"#FFD700, #FFEB3B, yellow, rgb(255, 215, 0)"`
- **支持格式**: 
  - 十六進制: `#FFD700`
  - 顏色名稱: `yellow`
  - RGB: `rgb(255, 215, 0)`

#### check_style
- **類型**: boolean
- **說明**: 是否檢查計算樣式（即使 method 不是 background_color 也會檢查）

### buttons（按鈕列表）

每個按鈕配置包含：

#### name
- **類型**: string
- **說明**: 按鈕名稱（用於報告）

#### selector
- **類型**: string（逗號分隔）
- **說明**: CSS 選擇器列表（會依次嘗試）
- **範例**: `"button:has-text('BET x1'), [class*='bet'][class*='x1'], button[data-bet='1']"`

#### highlight_check
- **類型**: boolean
- **說明**: 是否檢測高亮效果
- **預設**: `false`

## 高亮檢測方法詳解

### 1. CSS 類名檢測（推薦）

最簡單和可靠的方法，檢查按鈕是否有特定的 CSS 類名。

```json
{
  "method": "css_class",
  "css_class": "active, selected, highlight, [class*='active']"
}
```

**工作原理：**
1. 點擊按鈕
2. 檢查按鈕元素的 `class` 屬性
3. 如果包含配置中的任何類名，認為檢測到高亮
4. 也會檢查父元素的類名

### 2. 背景顏色檢測

檢查按鈕的背景顏色是否為黃色或指定的高亮顏色。

```json
{
  "method": "background_color",
  "background_color": "#FFD700, #FFEB3B, yellow, rgb(255, 215, 0)",
  "check_style": true
}
```

**工作原理：**
1. 點擊按鈕
2. 獲取按鈕的計算樣式（computed style）
3. 檢查 `backgroundColor` 和 `borderColor`
4. 如果匹配配置中的任何顏色，認為檢測到高亮
5. 也會檢查父元素的背景顏色

### 3. 截圖比對

使用點擊前後的截圖比對來檢測變化。

```json
{
  "method": "screenshot"
}
```

**工作原理：**
1. 點擊前截圖
2. 點擊按鈕
3. 點擊後截圖
4. 比對兩張截圖，如果有變化認為檢測到高亮

## 完整配置範例

### COINCOMBO 配置範例

```json
{
  "button_test_config": {
    "highlight_detection": {
      "method": "css_class",
      "css_class": "active, selected, highlight, yellow, [class*='active'], [class*='selected'], [class*='highlight']",
      "background_color": "#FFD700, #FFEB3B, #FFC107, yellow, rgb(255, 215, 0), rgb(255, 235, 59)",
      "check_style": true
    },
    "buttons": [
      {
        "name": "BET x1",
        "selector": "button:has-text('BET x1'), [class*='bet'][class*='x1'], button[data-bet='1']",
        "highlight_check": true
      },
      {
        "name": "BET x2",
        "selector": "button:has-text('BET x2'), [class*='bet'][class*='x2'], button[data-bet='2']",
        "highlight_check": true
      },
      {
        "name": "PLAY 88 Credits",
        "selector": "button:has-text('PLAY 88'), [class*='play'][class*='88'], button[data-credits='88']",
        "highlight_check": true
      }
    ]
  }
}
```

## 測試流程配置

在 `test_flows.json` 中配置按鈕測試流程：

```json
{
  "name": "按鈕測試",
  "description": "測試按鈕點擊和高亮效果",
  "enabled": true,
  "timeout": 10.0,
  "retry_count": 2,
  "config": {
    "check_highlight": true,
    "image_comparison": {
      "enabled": true,
      "similarity_threshold": 0.8
    }
  }
}
```

**注意：**
- 如果配置了 `button_test_config.buttons`，會優先使用該配置
- 如果沒有配置，會使用 `config.buttons` 列表
- `check_highlight` 控制是否啟用高亮檢測

## 測試結果

按鈕測試結果會記錄在測試報告中：

```json
{
  "button_tests": [
    {
      "button": "BET x1",
      "status": "success",
      "selector": "button:has-text('BET x1')",
      "highlight_detected": true
    },
    {
      "button": "BET x2",
      "status": "failed",
      "selector": "[class*='bet'][class*='x2']",
      "highlight_detected": false,
      "reason": "未檢測到高亮效果"
    }
  ]
}
```

## 最佳實踐

1. **優先使用 CSS 類名檢測**：最可靠且快速
2. **配置多個選擇器**：提高找到按鈕的成功率
3. **測試所有按鈕**：確保所有按鈕都有配置
4. **調整超時時間**：根據按鈕數量調整 `timeout`
5. **啟用圖片比對**：作為高亮檢測的補充驗證

## 故障排除

### 問題：無法檢測到高亮

**可能原因：**
1. CSS 類名配置不正確
2. 顏色值不匹配
3. 高亮效果延遲出現

**解決方法：**
1. 檢查瀏覽器開發者工具，查看實際的 CSS 類名或顏色
2. 增加點擊後的等待時間（在代碼中已設置為 0.3 秒）
3. 嘗試使用 `background_color` 方法
4. 檢查父元素是否有高亮類名

### 問題：找不到按鈕元素

**可能原因：**
1. 選擇器不正確
2. 按鈕尚未載入

**解決方法：**
1. 使用瀏覽器開發者工具驗證選擇器
2. 配置多個備選選擇器
3. 增加超時時間

## 範例：為新機器類型配置按鈕測試

1. **在 `config.json` 中添加 `button_test_config`**
2. **配置高亮檢測方式**（建議使用 `css_class`）
3. **列出所有要測試的按鈕**
4. **在 `test_flows.json` 中啟用按鈕測試流程**
5. **運行測試並檢查結果**




