"""
圖片組織工具 - 幫助將截圖整理到對應的參考圖片目錄

使用方法：
1. 將所有截圖放在機器類型目錄下（例如 machine_profiles/COINCOMBO/）
2. 運行此腳本，它會：
   - 創建 reference_images/ 目錄結構
   - 提供交互式界面讓您選擇每張圖片對應的階段
   - 自動移動圖片到對應目錄並重命名
"""
import sys
import shutil
from pathlib import Path
from typing import Dict, List, Optional

# 階段映射表（測試流程名稱 -> 目錄名稱）
STAGE_MAPPING = {
    "進入機器": "entry",
    "視頻檢測": "video",
    "按鈕測試": "buttons",
    "下注測試": "betting",
    "特殊功能測試": "special",
    "Grand功能測試": "grand",
    "其他": "other"
}

# 階段顯示名稱
STAGE_DISPLAY = {
    "entry": "進入機器 (entry)",
    "video": "視頻檢測 (video)",
    "buttons": "按鈕測試 (buttons)",
    "betting": "下注測試 (betting)",
    "special": "特殊功能測試 (special)",
    "grand": "Grand功能測試 (grand)",
    "other": "其他 (other)"
}


def get_image_files(directory: Path) -> List[Path]:
    """獲取目錄下的所有圖片文件"""
    image_extensions = ['.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG']
    images = []
    for ext in image_extensions:
        images.extend(directory.glob(f'*{ext}'))
    return sorted(images)


def create_reference_dirs(base_dir: Path, stages: List[str]):
    """創建參考圖片目錄結構"""
    ref_dir = base_dir / "reference_images"
    ref_dir.mkdir(exist_ok=True)
    
    for stage in stages:
        stage_dir = ref_dir / stage
        stage_dir.mkdir(exist_ok=True)
    
    return ref_dir


def organize_images_interactive(machine_type_dir: Path):
    """交互式組織圖片"""
    print("="*60)
    print("圖片組織工具")
    print("="*60)
    print(f"\n機器類型目錄: {machine_type_dir}")
    
    # 獲取所有圖片
    images = get_image_files(machine_type_dir)
    if not images:
        print("\n[WARN] 未找到任何圖片文件")
        return
    
    print(f"\n找到 {len(images)} 張圖片:")
    for i, img in enumerate(images, 1):
        print(f"  {i}. {img.name}")
    
    # 創建參考圖片目錄
    stages = list(STAGE_MAPPING.values())
    ref_dir = create_reference_dirs(machine_type_dir, stages)
    print(f"\n[OK] 已創建參考圖片目錄: {ref_dir}")
    
    # 顯示階段選項
    print("\n階段選項:")
    stage_options = {}
    for idx, (key, value) in enumerate(STAGE_MAPPING.items(), 1):
        stage_options[idx] = value
        print(f"  {idx}. {key} -> {value}/")
    
    print("\n開始組織圖片...")
    print("(輸入 's' 跳過，'q' 退出，'a' 全部使用當前選擇)")
    
    current_stage = None
    organized_count = 0
    
    for img in images:
        # 跳過已經在 reference_images 目錄下的圖片
        if "reference_images" in str(img):
            continue
        
        print(f"\n當前圖片: {img.name}")
        
        # 如果已經選擇了階段，詢問是否使用相同階段
        if current_stage:
            use_same = input(f"使用相同階段 '{STAGE_DISPLAY[current_stage]}'? (y/n/s/q): ").strip().lower()
            if use_same == 'y':
                stage = current_stage
            elif use_same == 's':
                print("跳過此圖片")
                continue
            elif use_same == 'q':
                print("退出")
                break
            else:
                current_stage = None
        
        # 如果沒有當前階段，讓用戶選擇
        if not current_stage:
            choice = input("請選擇階段 (1-7/s/q): ").strip().lower()
            
            if choice == 's':
                print("跳過此圖片")
                continue
            elif choice == 'q':
                print("退出")
                break
            elif choice == 'a' and current_stage:
                # 使用當前階段處理所有剩餘圖片
                stage = current_stage
            else:
                try:
                    choice_num = int(choice)
                    if choice_num in stage_options:
                        stage = stage_options[choice_num]
                        current_stage = stage
                    else:
                        print("[ERROR] 無效的選項，跳過此圖片")
                        continue
                except ValueError:
                    print("[ERROR] 無效的輸入，跳過此圖片")
                    continue
        
        # 移動圖片到對應目錄
        stage_dir = ref_dir / stage
        new_name = f"{stage}_{img.stem}{img.suffix}"
        dest_path = stage_dir / new_name
        
        # 如果目標文件已存在，添加編號
        counter = 1
        while dest_path.exists():
            new_name = f"{stage}_{img.stem}_{counter}{img.suffix}"
            dest_path = stage_dir / new_name
            counter += 1
        
        try:
            shutil.move(str(img), str(dest_path))
            print(f"[OK] 已移動到: {dest_path.name}")
            organized_count += 1
        except Exception as e:
            print(f"[ERROR] 移動失敗: {e}")
    
    print(f"\n完成！共組織 {organized_count} 張圖片")
    print(f"\n參考圖片目錄結構:")
    for stage in stages:
        stage_dir = ref_dir / stage
        images_in_stage = list(stage_dir.glob("*.png")) + list(stage_dir.glob("*.jpg")) + list(stage_dir.glob("*.jpeg"))
        if images_in_stage:
            print(f"  {stage}/: {len(images_in_stage)} 張")
            for img in images_in_stage[:3]:  # 只顯示前3張
                print(f"    - {img.name}")
            if len(images_in_stage) > 3:
                print(f"    ... 還有 {len(images_in_stage) - 3} 張")


def organize_images_by_pattern(machine_type_dir: Path, pattern_mapping: Dict[str, str]):
    """
    根據文件名模式自動組織圖片
    
    pattern_mapping: {"關鍵字": "階段名稱"}
    例如: {"entry": "entry", "video": "video", "button": "buttons"}
    """
    print("="*60)
    print("根據模式自動組織圖片")
    print("="*60)
    
    images = get_image_files(machine_type_dir)
    if not images:
        print("\n[WARN] 未找到任何圖片文件")
        return
    
    stages = list(STAGE_MAPPING.values())
    ref_dir = create_reference_dirs(machine_type_dir, stages)
    
    organized = {stage: 0 for stage in stages}
    unmatched = []
    
    for img in images:
        if "reference_images" in str(img):
            continue
        
        matched = False
        img_name_lower = img.name.lower()
        
        for pattern, stage in pattern_mapping.items():
            if pattern.lower() in img_name_lower:
                stage_dir = ref_dir / stage
                new_name = f"{stage}_{img.stem}{img.suffix}"
                dest_path = stage_dir / new_name
                
                counter = 1
                while dest_path.exists():
                    new_name = f"{stage}_{img.stem}_{counter}{img.suffix}"
                    dest_path = stage_dir / new_name
                    counter += 1
                
                try:
                    shutil.move(str(img), str(dest_path))
                    organized[stage] += 1
                    print(f"[OK] {img.name} -> {stage}/{new_name}")
                    matched = True
                    break
                except Exception as e:
                    print(f"[ERROR] 移動 {img.name} 失敗: {e}")
        
        if not matched:
            unmatched.append(img)
    
    print(f"\n組織完成:")
    for stage, count in organized.items():
        if count > 0:
            print(f"  {stage}/: {count} 張")
    
    if unmatched:
        print(f"\n未匹配的圖片 ({len(unmatched)} 張):")
        for img in unmatched:
            print(f"  - {img.name}")
        print("\n請手動處理這些圖片或添加更多模式")


def show_naming_guide():
    """顯示命名指南"""
    print("="*60)
    print("圖片命名指南")
    print("="*60)
    print("""
系統會根據測試流程名稱自動映射到對應的目錄：

測試流程名稱          ->  目錄名稱         ->  建議命名格式
─────────────────────────────────────────────────────────────
進入機器              ->  entry/          ->  entry_*.png
視頻檢測              ->  video/          ->  video_*.png
按鈕測試              ->  buttons/        ->  buttons_*.png
下注測試              ->  betting/        ->  betting_*.png
特殊功能測試          ->  special/        ->  special_*.png
Grand功能測試         ->  grand/          ->  grand_*.png

命名建議：
1. 使用階段前綴：entry_、video_、buttons_ 等
2. 添加描述：entry_main.png、video_loaded.png、buttons_visible.png
3. 添加編號：entry_1.png、entry_2.png（如果同一階段有多張圖片）

範例：
  entry_main.png          - 進入機器後的主畫面
  entry_loaded.png        - 進入機器後載入完成的畫面
  video_normal.png       - 視頻正常顯示的畫面
  video_playing.png       - 視頻播放中的畫面
  buttons_spin.png        - 按鈕測試時的 SPIN 按鈕畫面
  buttons_bet.png         - 按鈕測試時的 BET 按鈕畫面
  betting_screen.png      - 下注測試時的畫面

注意：
- 圖片會自動移動到 reference_images/階段名稱/ 目錄下
- 系統會比對目錄下的所有圖片（除非在配置中指定特定圖片）
- 建議使用 PNG 格式以獲得更好的比對效果
""")


def main():
    """主函數"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python organize_images.py <機器類型目錄>")
        print("  例如: python organize_images.py machine_profiles/COINCOMBO")
        print("\n或者查看命名指南:")
        print("  python organize_images.py --guide")
        return
    
    if sys.argv[1] == "--guide":
        show_naming_guide()
        return
    
    machine_type_dir = Path(sys.argv[1])
    if not machine_type_dir.exists():
        print(f"[ERROR] 目錄不存在: {machine_type_dir}")
        return
    
    if not machine_type_dir.is_dir():
        print(f"[ERROR] 不是目錄: {machine_type_dir}")
        return
    
    print(f"\n機器類型目錄: {machine_type_dir.absolute()}")
    
    mode = input("\n選擇模式:\n  1. 交互式組織 (推薦)\n  2. 根據模式自動組織\n  3. 只查看命名指南\n請選擇 (1/2/3): ").strip()
    
    if mode == "1":
        organize_images_interactive(machine_type_dir)
    elif mode == "2":
        print("\n請輸入文件名模式映射（例如: entry->entry, video->video）")
        print("格式: 關鍵字1->階段1,關鍵字2->階段2")
        pattern_input = input("模式映射: ").strip()
        
        pattern_mapping = {}
        for pair in pattern_input.split(','):
            if '->' in pair:
                key, value = pair.split('->', 1)
                pattern_mapping[key.strip()] = value.strip()
        
        if pattern_mapping:
            organize_images_by_pattern(machine_type_dir, pattern_mapping)
        else:
            print("[ERROR] 無效的模式映射")
    elif mode == "3":
        show_naming_guide()
    else:
        print("[ERROR] 無效的選項")


if __name__ == "__main__":
    main()

