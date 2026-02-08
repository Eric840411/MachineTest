# 圖片比對功能使用指南

## 概述

圖片比對功能允許您為每個測試階段設置參考圖片，系統會自動比對當前頁面與參考圖片，確認每個階段是否正確執行。

## 文件夾結構

每個機器類型可以有一個 `reference_images/` 目錄，包含各階段的參考圖片：

```
machine_profiles/
└── RISINGROCKETS/
    ├── config.json
    ├── test_flows.json
    └── reference_images/
        ├── entry/           # 進入機器階段的參考圖片
        │   ├── entry_1.png
        │   └── entry_2.png
        ├── video/           # 視頻檢測階段的參考圖片
        │   └── video_normal.png
        ├── buttons/         # 按鈕測試階段的參考圖片
        │   └── buttons_visible.png
        └── betting/         # 下注測試階段的參考圖片
            └── betting_screen.png
```

## 配置圖片比對

在 `test_flows.json` 的每個測試流程配置中添加 `image_comparison` 配置：

```json
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
```

### 配置參數說明

#### enabled
- **類型**: boolean
- **預設**: false
- **說明**: 是否啟用圖片比對

#### similarity_threshold
- **類型**: float (0-1)
- **預設**: 0.8
- **說明**: 相似度閾值
  - `0.9` = 90% 相似（非常嚴格，幾乎完全相同）
  - `0.8` = 80% 相似（推薦，允許一些差異）
  - `0.7` = 70% 相似（較寬鬆，允許較多差異）
  - `0.6` = 60% 相似（很寬鬆）

#### selector
- **類型**: string | null
- **預設**: null
- **說明**: CSS 選擇器，只比對特定元素的截圖
  - `null`: 比對整個頁面
  - `"canvas"`: 只比對 canvas 元素
  - `".game-container"`: 只比對遊戲容器

#### region
- **類型**: object | null
- **預設**: null
- **說明**: 只比對特定區域的圖片
  ```json
  {
    "x": 0,        // 起始 X 座標
    "y": 0,        // 起始 Y 座標
    "width": 500,  // 區域寬度
    "height": 200  // 區域高度
  }
  ```

#### images
- **類型**: array
- **預設**: []
- **說明**: 指定要比對的圖片列表
  - `[]`: 使用目錄下所有圖片（.png, .jpg, .jpeg）
  - `["entry_1.png", "entry_2.png"]`: 只比對指定的圖片

## 階段名稱對應

測試流程名稱會自動映射到對應的參考圖片目錄：

| 測試流程名稱 | 目錄名稱 | 說明 |
|------------|---------|------|
| 進入機器 | `entry/` | 進入機器後的畫面 |
| 視頻檢測 | `video/` | 視頻正常顯示的畫面 |
| 按鈕測試 | `buttons/` | 按鈕測試時的畫面 |
| 下注測試 | `betting/` | 下注測試時的畫面 |
| 特殊功能測試 | `special/` | 特殊功能測試時的畫面 |
| Grand功能測試 | `grand/` | Grand功能測試時的畫面 |

## 使用範例

### 範例 1: 基本圖片比對

```json
{
  "name": "進入機器",
  "config": {
    "image_comparison": {
      "enabled": true,
      "similarity_threshold": 0.8
    }
  }
}
```

這會：
1. 比對 `reference_images/entry/` 目錄下的所有圖片
2. 使用 80% 相似度閾值
3. 比對整個頁面

### 範例 2: 只比對特定元素

```json
{
  "name": "視頻檢測",
  "config": {
    "image_comparison": {
      "enabled": true,
      "similarity_threshold": 0.75,
      "selector": "canvas, video"
    }
  }
}
```

這會：
1. 只比對 `canvas` 或 `video` 元素的截圖
2. 使用 75% 相似度閾值

### 範例 3: 比對特定區域

```json
{
  "name": "按鈕測試",
  "config": {
    "image_comparison": {
      "enabled": true,
      "similarity_threshold": 0.8,
      "region": {
        "x": 0,
        "y": 0,
        "width": 500,
        "height": 200
      }
    }
  }
}
```

這會：
1. 只比對頁面左上角 500x200 的區域
2. 使用 80% 相似度閾值

### 範例 4: 指定特定圖片

```json
{
  "name": "進入機器",
  "config": {
    "image_comparison": {
      "enabled": true,
      "similarity_threshold": 0.8,
      "images": ["entry_main.png", "entry_loaded.png"]
    }
  }
}
```

這會：
1. 只比對 `entry_main.png` 和 `entry_loaded.png`
2. 忽略目錄下的其他圖片

## 準備參考圖片

### 步驟 1: 創建參考圖片目錄

```bash
mkdir machine_profiles/RISINGROCKETS/reference_images
mkdir machine_profiles/RISINGROCKETS/reference_images/entry
mkdir machine_profiles/RISINGROCKETS/reference_images/video
mkdir machine_profiles/RISINGROCKETS/reference_images/buttons
```

### 步驟 2: 截取參考圖片

1. 手動運行一次測試，進入正確的狀態
2. 截取該狀態的圖片
3. 將圖片保存到對應的目錄

**建議：**
- 使用清晰的圖片（PNG 格式推薦）
- 確保圖片是在正常狀態下截取的
- 可以有多張參考圖片（系統會比對所有圖片）

### 步驟 3: 配置測試流程

在 `test_flows.json` 中啟用圖片比對：

```json
{
  "flows": [
    {
      "name": "進入機器",
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

## 比對結果

圖片比對結果會記錄在測試報告中：

```json
{
  "image_comparisons": [
    {
      "stage": "entry",
      "match": true,
      "result": {
        "status": "success",
        "total_images": 2,
        "matched_images": 2,
        "results": [
          {
            "reference_image": "entry_1.png",
            "match": true,
            "similarity": 0.85,
            "message": "相似度: 85.00% (匹配, 閾值: 80.00%)"
          },
          {
            "reference_image": "entry_2.png",
            "match": true,
            "similarity": 0.82,
            "message": "相似度: 82.00% (匹配, 閾值: 80.00%)"
          }
        ]
      },
      "timestamp": 1234567890.123
    }
  ]
}
```

## 最佳實踐

1. **相似度閾值選擇**
   - 靜態畫面：使用 0.8-0.9（較嚴格）
   - 動態畫面：使用 0.7-0.8（較寬鬆）
   - 有動畫的畫面：使用 0.6-0.7（很寬鬆）

2. **參考圖片準備**
   - 使用多張參考圖片覆蓋不同狀態
   - 確保參考圖片是在正常狀態下截取的
   - 定期更新參考圖片（如果遊戲界面改變）

3. **區域比對**
   - 如果只需要驗證特定區域，使用 `region` 配置
   - 可以減少比對時間和提高準確度

4. **選擇器使用**
   - 如果只需要驗證特定元素，使用 `selector` 配置
   - 例如：只比對遊戲畫布，忽略其他UI元素

## 故障排除

### 問題：圖片比對總是失敗

**可能原因：**
1. 相似度閾值設置過高
2. 參考圖片與當前狀態差異太大
3. 頁面有動畫或動態內容

**解決方法：**
- 降低 `similarity_threshold`（例如從 0.8 降到 0.7）
- 更新參考圖片
- 使用 `region` 只比對穩定的區域

### 問題：找不到參考圖片

**可能原因：**
1. 參考圖片目錄不存在
2. 圖片文件名不正確
3. 圖片格式不支持

**解決方法：**
- 確保目錄結構正確：`reference_images/階段名稱/`
- 使用 .png、.jpg 或 .jpeg 格式
- 檢查圖片文件名是否正確

### 問題：比對時間過長

**可能原因：**
1. 參考圖片太多
2. 圖片尺寸太大
3. 比對整個頁面

**解決方法：**
- 使用 `images` 配置指定特定圖片
- 使用 `region` 只比對關鍵區域
- 使用 `selector` 只比對特定元素

