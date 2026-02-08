# 測試配置說明

## 概述

`test_config.json` 允許您輕鬆測試不同的功能組合，無需修改代碼。

## 使用方法

### 1. 啟用測試模式

在 `test_config.json` 中設置：
```json
{
  "test_mode": true,
  "active_scenario": "basic"
}
```

### 2. 選擇測試場景

修改 `active_scenario` 為您想要的場景名稱：
- `basic` - 基礎測試
- `balance_test` - 餘額測試
- `full_test` - 完整測試
- `navigation_test` - 導航測試

### 3. 自定義場景

您可以在 `test_scenarios` 中添加或修改場景：

```json
{
  "my_custom_test": {
    "name": "我的自定義測試",
    "description": "測試特定功能組合",
    "enabled": true,
    "features": {
      "enable_balance_check": true,
      "enable_exit_flow": false,
      "enable_random_bet": true,
      "enable_special_actions": false,
      "enable_404_check": false
    },
    "spin_count": 10,
    "spin_interval": 1.5,
    "balance_threshold": 15000
  }
}
```

## 功能開關說明

### `enable_balance_check`
- `true`: 啟用餘額檢查
- `false`: 禁用餘額檢查（不會檢測餘額變化）

### `enable_exit_flow`
- `true`: 啟用退出流程（餘額過低時會退出並重新進入）
- `false`: 禁用退出流程（即使餘額過低也不會退出）

### `enable_random_bet`
- `true`: 啟用隨機下注點擊
- `false`: 禁用隨機下注點擊

### `enable_special_actions`
- `true`: 啟用特殊動作（連續無變化時觸發的座標點擊）
- `false`: 禁用特殊動作

### `enable_404_check`
- `true`: 啟用 404 頁面檢測和刷新
- `false`: 禁用 404 頁面檢測

## 測試參數

### `spin_count`
- 測試模式下的最大 Spin 次數
- `null` 或省略：無限制（持續運行）
- 數字：達到指定次數後自動停止

### `spin_interval`
- 測試模式下的固定 Spin 間隔（秒）
- 正常模式下會使用熱鍵設定的頻率

### `balance_threshold`
- 餘額閾值（低於此值會觸發退出流程）
- 預設：20000

### `test_exit_after_spins`
- 測試退出流程時，在指定 Spin 次數後執行退出
- 用於測試進入/退出流程

## 預設場景

### 1. basic（基礎測試）
- 只測試進入遊戲和基本 Spin
- 所有功能都關閉
- 5 次 Spin，間隔 2 秒

### 2. balance_test（餘額測試）
- 測試餘額檢測和退出流程
- 20 次 Spin，間隔 1 秒

### 3. full_test（完整測試）
- 測試所有功能
- 50 次 Spin，間隔 1 秒

### 4. navigation_test（導航測試）
- 只測試進入/退出遊戲流程
- 3 次 Spin 後執行退出流程

## 執行測試

1. 編輯 `test_config.json`
2. 設置 `test_mode: true`
3. 選擇 `active_scenario`
4. 執行：`python app.py`

## 關閉測試模式

設置 `test_mode: false` 或刪除 `test_config.json`，程序會以正常模式運行。

