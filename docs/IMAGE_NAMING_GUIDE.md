# 圖片命名指南

## 階段映射表

系統會根據測試流程名稱自動映射到對應的目錄：

| 測試流程名稱 | 目錄名稱 | 建議命名格式 | 說明 |
|------------|---------|------------|------|
| **進入機器** | `entry/` | `entry_*.png` | 進入機器後的畫面 |
| **視頻檢測** | `video/` | `video_*.png` | 視頻正常顯示的畫面 |
| **按鈕測試** | `buttons/` | `buttons_*.png` | 按鈕測試時的畫面 |
| **下注測試** | `betting/` | `betting_*.png` | 下注測試時的畫面 |
| **特殊功能測試** | `special/` | `special_*.png` | 特殊功能測試時的畫面 |
| **Grand功能測試** | `grand/` | `grand_*.png` | Grand功能測試時的畫面 |

## 命名規則

### 1. 基本格式

```
階段名稱_描述_編號.png
```

**範例：**
- `entry_main.png` - 進入機器後的主畫面
- `entry_loaded.png` - 進入機器後載入完成的畫面
- `video_normal.png` - 視頻正常顯示的畫面
- `video_playing.png` - 視頻播放中的畫面
- `buttons_spin.png` - 按鈕測試時的 SPIN 按鈕畫面
- `buttons_bet.png` - 按鈕測試時的 BET 按鈕畫面
- `betting_screen.png` - 下注測試時的畫面

### 2. 如果同一階段有多張圖片

使用編號區分：

```
entry_1.png
entry_2.png
entry_3.png
```

或者使用描述：

```
entry_main.png
entry_loaded.png
entry_ready.png
```

### 3. 命名建議

**進入機器階段 (entry/)：**
- `entry_main.png` - 主畫面
- `entry_loaded.png` - 載入完成
- `entry_ready.png` - 準備就緒
- `entry_game_start.png` - 遊戲開始

**視頻檢測階段 (video/)：**
- `video_normal.png` - 正常顯示
- `video_playing.png` - 播放中
- `video_loaded.png` - 載入完成

**按鈕測試階段 (buttons/)：**
- `buttons_spin.png` - SPIN 按鈕
- `buttons_bet.png` - BET 按鈕
- `buttons_play.png` - PLAY 按鈕
- `buttons_visible.png` - 按鈕可見狀態

**下注測試階段 (betting/)：**
- `betting_screen.png` - 下注畫面
- `betting_bet_placed.png` - 下注完成
- `betting_balance.png` - 餘額顯示

## 目錄結構

圖片應該放在以下目錄結構中：

```
machine_profiles/
└── COINCOMBO/
    ├── config.json
    ├── test_flows.json
    └── reference_images/
        ├── entry/           # 進入機器階段的參考圖片
        │   ├── entry_main.png
        │   └── entry_loaded.png
        ├── video/            # 視頻檢測階段的參考圖片
        │   └── video_normal.png
        ├── buttons/          # 按鈕測試階段的參考圖片
        │   ├── buttons_spin.png
        │   └── buttons_bet.png
        ├── betting/          # 下注測試階段的參考圖片
        │   └── betting_screen.png
        ├── special/          # 特殊功能測試階段的參考圖片
        └── grand/            # Grand功能測試階段的參考圖片
```

## 使用工具組織圖片

我們提供了一個工具來幫助您組織圖片：

```bash
python organize_images.py machine_profiles/COINCOMBO
```

這個工具會：
1. 自動創建 `reference_images/` 目錄結構
2. 提供交互式界面讓您選擇每張圖片對應的階段
3. 自動移動圖片到對應目錄並重命名

## 配置圖片比對

在 `test_flows.json` 中配置圖片比對：

```json
{
  "flows": [
    {
      "name": "進入機器",
      "config": {
        "image_comparison": {
          "enabled": true,
          "similarity_threshold": 0.8,
          "selector": null,
          "region": null,
          "images": []  // 空則使用目錄下所有圖片
        }
      }
    }
  ]
}
```

## 注意事項

1. **圖片格式**：建議使用 PNG 格式以獲得更好的比對效果
2. **圖片品質**：使用清晰的截圖，避免模糊或壓縮過度的圖片
3. **命名一致性**：保持命名風格一致，方便管理
4. **圖片數量**：每個階段可以有多張參考圖片，系統會比對所有圖片
5. **自動重命名**：使用 `organize_images.py` 工具會自動添加階段前綴

## 快速開始

1. **準備截圖**：將所有截圖放在 `machine_profiles/COINCOMBO/` 目錄下
2. **運行工具**：執行 `python organize_images.py machine_profiles/COINCOMBO`
3. **選擇階段**：根據每張截圖的內容選擇對應的測試階段
4. **完成**：圖片會自動移動到 `reference_images/階段名稱/` 目錄並重命名

## 範例：COINCOMBO 圖片組織

假設您有以下截圖：
- `螢幕擷取畫面 2026-01-26 223209.png` - 進入機器後的畫面
- `螢幕擷取畫面 2026-01-26 223237.png` - 視頻正常顯示
- `螢幕擷取畫面 2026-01-26 223248.png` - 按鈕測試畫面

運行工具後，這些圖片會被組織為：
- `reference_images/entry/entry_螢幕擷取畫面_2026-01-26_223209.png`
- `reference_images/video/video_螢幕擷取畫面_2026-01-26_223237.png`
- `reference_images/buttons/buttons_螢幕擷取畫面_2026-01-26_223248.png`





