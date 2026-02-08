# 圖片比對流程說明

## 比對流程

### 1. 準備階段

當執行測試流程時（例如「進入機器」），系統會：

1. **獲取參考圖片目錄**
   - 從 `machine_profiles/COINCOMBO/reference_images/entry/` 讀取所有參考圖片
   - 例如：`entry_1.png`, `entry_2.png`

2. **截取當前頁面**
   - 使用 Playwright 截取當前頁面或指定元素的截圖
   - 如果配置了 `selector`，只截取該元素（例如 `canvas, video`）
   - 如果配置了 `region`，只截取指定區域

### 2. 比對過程

對每張參考圖片執行以下步驟：

#### 步驟 1: 載入圖片
```python
# 載入參考圖片
ref_img = Image.open(reference_image_path)  # 例如 entry_1.png
ref_array = np.array(ref_img)  # 轉換為 numpy 數組

# 截取當前頁面
screenshot = await page.screenshot()  # 或 element.screenshot()
current_img = Image.open(io.BytesIO(screenshot))
current_array = np.array(current_img)
```

#### 步驟 2: 調整尺寸
如果兩張圖片尺寸不同，會自動調整：
```python
if img1.shape != img2.shape:
    # 使用 LANCZOS 算法調整參考圖片尺寸以匹配當前截圖
    img2_pil = img2_pil.resize(img1_pil.size, Image.Resampling.LANCZOS)
```

#### 步驟 3: 轉換為灰度圖
將彩色圖片轉換為灰度圖以便比較：
```python
# RGB 轉灰度公式：Gray = 0.2989*R + 0.5870*G + 0.1140*B
img1_gray = np.dot(img1[..., :3], [0.2989, 0.5870, 0.1140])
img2_gray = np.dot(img2[..., :3], [0.2989, 0.5870, 0.1140])
```

#### 步驟 4: 計算相似度

使用 **PSNR (Peak Signal-to-Noise Ratio)** 算法：

```python
# 1. 計算均方誤差 (MSE)
mse = np.mean((img1_gray - img2_gray) ** 2)

# 2. 如果 MSE = 0，圖片完全相同
if mse == 0:
    return 1.0  # 100% 相似

# 3. 計算峰值信噪比 (PSNR)
max_pixel = 255.0
psnr = 20 * np.log10(max_pixel / np.sqrt(mse))

# 4. 將 PSNR 轉換為 0-1 的相似度分數
# PSNR > 30 通常認為很相似，所以除以 30
similarity = min(1.0, psnr / 30.0)
```

**PSNR 說明：**
- PSNR 越高，圖片越相似
- PSNR = 30 dB 時，相似度 = 1.0 (100%)
- PSNR = 15 dB 時，相似度 = 0.5 (50%)
- PSNR = 0 dB 時，相似度 = 0.0 (0%)

#### 步驟 5: 判斷是否匹配

```python
is_match = similarity >= similarity_threshold
# 例如：similarity = 0.4373 (43.73%) < 0.8 (80%) = False
```

### 3. 比對結果

系統會比對目錄下的**所有參考圖片**，只有**全部匹配**才算成功：

```python
for ref_img_path in ref_images:  # entry_1.png, entry_2.png
    is_match, similarity, message = compare_with_reference(...)
    
    if not is_match:
        all_match = False  # 只要有一張不匹配，整體失敗
```

## 您的日誌分析

從您的日誌可以看到：

### Entry 階段
- **entry_1.png**: 相似度 43.73% < 80% 閾值 → 不匹配
- **entry_2.png**: 相似度 43.67% < 80% 閾值 → 不匹配
- **結果**: 整體失敗（因為兩張都不匹配）

### Video 階段
- **video_1.png**: 相似度 28.21% < 75% 閾值 → 不匹配
- **結果**: 失敗

## 為什麼相似度這麼低？

可能的原因：

1. **畫面內容不同**
   - 參考圖片是某個特定狀態的畫面
   - 當前截圖是另一個狀態（例如載入中、不同遊戲狀態）

2. **UI 元素位置不同**
   - 按鈕、文字位置有變化
   - 動畫或過渡效果

3. **顏色/亮度差異**
   - 畫面亮度不同
   - 顏色飽和度不同

4. **尺寸不匹配**
   - 雖然會自動調整，但可能導致失真

5. **時間點不同**
   - 參考圖片是穩定狀態
   - 當前截圖可能是載入中或過渡狀態

## 如何改善

### 1. 降低相似度閾值

在 `test_flows.json` 中調整：

```json
{
  "image_comparison": {
    "similarity_threshold": 0.6  // 從 0.8 降到 0.6
  }
}
```

### 2. 使用區域比對

只比對關鍵區域，忽略變化較大的部分：

```json
{
  "image_comparison": {
    "region": {
      "x": 0,
      "y": 0,
      "width": 500,
      "height": 300  // 只比對上半部分
    }
  }
}
```

### 3. 更新參考圖片

確保參考圖片是在正確狀態下截取的：
- 等待頁面完全載入
- 等待動畫完成
- 確保是穩定狀態

### 4. 使用選擇器比對

只比對特定元素，而不是整個頁面：

```json
{
  "image_comparison": {
    "selector": "canvas, video"  // 只比對遊戲畫布
  }
}
```

### 5. 等待頁面穩定

在比對前增加等待時間，確保頁面已穩定：

```json
{
  "config": {
    "wait_after_action": 3.0  // 執行後等待 3 秒再比對
  }
}
```

## 比對算法詳解

### PSNR 計算公式

```
MSE = (1/N) * Σ(參考圖片像素 - 當前圖片像素)²

PSNR = 20 * log₁₀(255 / √MSE)

相似度 = min(1.0, PSNR / 30.0)
```

### 範例計算

假設兩張圖片有中等差異：
- MSE = 1000
- PSNR = 20 * log₁₀(255 / √1000) ≈ 20 * log₁₀(8.06) ≈ 18.1 dB
- 相似度 = 18.1 / 30.0 ≈ 0.603 (60.3%)

### 相似度對照表

| PSNR (dB) | 相似度 | 說明 |
|-----------|--------|------|
| ≥ 30 | 100% | 幾乎完全相同 |
| 24-30 | 80-100% | 非常相似 |
| 18-24 | 60-80% | 較為相似 |
| 12-18 | 40-60% | 中等差異 |
| 6-12 | 20-40% | 差異較大 |
| < 6 | < 20% | 差異很大 |

您的日誌顯示：
- Entry: 43.73% → PSNR ≈ 13.1 dB（中等差異）
- Video: 28.21% → PSNR ≈ 8.5 dB（差異較大）

## 建議

根據您的日誌，建議：

1. **檢查參考圖片是否正確**
   - 確認 `entry_1.png` 和 `entry_2.png` 是否是在正確狀態下截取的
   - 確認 `video_1.png` 是否是在視頻正常顯示時截取的

2. **調整閾值**
   - Entry 階段：從 80% 降到 60-70%
   - Video 階段：從 75% 降到 50-60%

3. **增加等待時間**
   - 在進入機器後等待更長時間再比對
   - 確保頁面完全載入

4. **使用區域比對**
   - 只比對關鍵區域（例如遊戲畫布區域）
   - 忽略 UI 按鈕等可能變化的部分





