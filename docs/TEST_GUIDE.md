# 組件測試指南

本指南說明如何測試各個組件的功能是否正常。

## 快速開始

### 1. 測試所有組件

```bash
python test_components.py all
```

### 2. 測試單個組件

```bash
# 測試 TestTaskManager
python test_components.py manager

# 測試 VideoDetector
python test_components.py video

# 測試 TestServiceClient
python test_components.py service

# 測試 LarkClient 報告功能
python test_components.py lark

# 測試配置加載
python test_components.py config
```

### 3. 運行集成測試

```bash
python test_integration.py
```

## 各組件測試說明

### TestTaskManager（測試任務管理器）

**功能：**
- 管理多個 URL 的測試任務
- 從 CSV 循環分配資料給每個 URL

**測試內容：**
- ✅ 初始化是否正確
- ✅ CSV 資料分配邏輯（第一輪、第二輪）
- ✅ 完成後返回 None
- ✅ 剩餘數量計算
- ✅ 狀態查詢功能

**預期結果：**
```
測試 TestTaskManager
✅ TestTaskManager 初始化成功
✅ 第一輪分配正確
✅ 第二輪分配正確
✅ 完成後返回 None 正確
✅ 剩餘數量計算正確
```

### VideoDetector（視頻檢測器）

**功能：**
- 檢測視頻/畫布是否正常顯示
- 檢測黑畫面、透明畫面、單色畫面

**測試內容：**
- ✅ 模組導入
- ✅ 圖像檢測邏輯（正常圖像、黑畫面、單色畫面）
- ✅ 實際瀏覽器檢測（可選）

**預期結果：**
```
測試 VideoDetector
✅ VideoDetector 導入成功
✅ 正常圖像檢測邏輯正確
✅ 黑畫面檢測邏輯正確
✅ 單色畫面檢測邏輯正確
```

**注意：** 實際瀏覽器測試需要 Playwright 已安裝瀏覽器（執行 `playwright install`）

### TestServiceClient（測試服務客戶端）

**功能：**
- 與外部測試服務串接
- 發送測試事件

**測試內容：**
- ✅ 未啟用狀態
- ✅ 啟用狀態
- ✅ 方法存在性
- ✅ 方法調用（模擬）

**預期結果：**
```
測試 TestServiceClient
✅ 未啟用狀態正確
✅ 啟用狀態正確
✅ 所有方法存在
```

**注意：** 實際服務測試需要外部服務運行，否則會顯示連線失敗（這是正常的）

### LarkClient（Lark 報告功能）

**功能：**
- 發送結構化測試報告到 Lark

**測試內容：**
- ✅ 未啟用狀態
- ✅ 報告格式化
- ✅ 報告結構驗證
- ✅ 實際發送（可選）

**預期結果：**
```
測試 LarkClient 報告功能
✅ 未啟用狀態正確
✅ send_test_report 方法存在
✅ 報告結構正確
```

**注意：** 實際發送測試需要有效的 Lark Webhook URL

### 配置加載

**功能：**
- 從 test_config.json 加載測試服務配置

**測試內容：**
- ✅ 配置加載
- ✅ 配置結構

**預期結果：**
```
測試配置加載功能
✅ 配置加載成功
```

## 集成測試

集成測試驗證組件之間的協作是否正常。

### GameRunner 整合

測試 GameRunner 與測試組件的整合：
- ✅ 模組導入
- ✅ GameRunner 創建
- ✅ 測試相關屬性
- ✅ 測試報告結構
- ✅ 測試方法存在

### app.py 整合

測試主程序的整合：
- ✅ 配置加載
- ✅ 服務創建
- ✅ 任務管理器創建

## 常見問題

### 1. 導入錯誤

**問題：** `ModuleNotFoundError: No module named 'test'`

**解決：** 確保在項目根目錄運行測試腳本

### 2. Playwright 錯誤

**問題：** `Executable doesn't exist`

**解決：** 執行 `playwright install` 安裝瀏覽器

### 3. 依賴缺失

**問題：** `ModuleNotFoundError: No module named 'PIL'`

**解決：** 執行 `pip install -r requirements.txt`

### 4. 測試失敗但功能正常

某些測試（如實際服務連線、Lark 發送）可能會失敗，這是正常的，因為：
- 外部服務可能未運行
- Webhook URL 可能未配置

這些測試主要驗證代碼邏輯，不依賴外部服務。

## 測試最佳實踐

1. **先運行單元測試**：確保各個組件獨立功能正常
2. **再運行集成測試**：確保組件協作正常
3. **檢查日誌輸出**：查看詳細的測試過程
4. **修復失敗的測試**：確保所有測試通過

## 持續測試

建議在以下情況運行測試：
- 修改組件代碼後
- 添加新功能後
- 部署前
- 定期（如每週）運行完整測試

## 測試輸出示例

```
============================================================
開始運行所有組件測試
============================================================

============================================================
測試 TestTaskManager
============================================================
✅ TestTaskManager 初始化成功
✅ 第一輪分配正確
✅ 第二輪分配正確
✅ 完成後返回 None 正確
✅ 剩餘數量計算正確
✅ TestTaskManager 所有測試通過

...

============================================================
測試總結
============================================================
manager         - ✅ 通過
video           - ✅ 通過
service         - ✅ 通過
lark            - ✅ 通過
config          - ✅ 通過

總計: 5/5 通過, 0 失敗

🎉 所有測試通過！
```

