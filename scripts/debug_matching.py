"""
調試機器類型匹配邏輯
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config.machine_profiles import load_machine_profiles, match_machine_profile

# 加載配置
profiles = load_machine_profiles(BASE_DIR)

# 機器1和機器2的配置
url1 = "https://osm-redirect.osmslot.org/?token=f76856cf4429ddc75925dbf98b14b1ab-325599&platform=pc&mode=live&language=zh_cn&studioid=cp&gameid=osmbwjl&lang=en_us&username=osmel002&device=mobile&isPwaClaimed=1"
url2 = "https://osm-redirect.osmslot.org/?token=c3e16bf4c1526b75ca8be1083174e8be-325601&platform=pc&mode=live&language=zh_cn&studioid=cp&gameid=osmbwjl&lang=en_us&username=osmel003&device=mobile&isPwaClaimed=1"

game_title_code1 = "873-JJBX-0004"
game_title_code2 = None  # 機器2沒有 game_title_code（CSV只有1行）

gameid = "osmbwjl"

print("="*60)
print("機器類型匹配調試")
print("="*60)

print(f"\n機器1:")
print(f"  URL: {url1[:60]}...")
print(f"  game_title_code: {game_title_code1}")
print(f"  gameid: {gameid}")
p1 = match_machine_profile(profiles, url1, game_title_code1, gameid)
print(f"  匹配結果: {p1.name if p1 else 'None'}")

print(f"\n機器2:")
print(f"  URL: {url2[:60]}...")
print(f"  game_title_code: {game_title_code2}")
print(f"  gameid: {gameid}")
p2 = match_machine_profile(profiles, url2, game_title_code2, gameid)
print(f"  匹配結果: {p2.name if p2 else 'None'}")

print("\n" + "="*60)
print("問題分析:")
print("="*60)
print("機器1有 game_title_code '873-JJBX-0004'，會提取關鍵字 'JJBX' 匹配到 JJBX")
print("機器2沒有 game_title_code，只能通過 gameid='osmbwjl' 匹配")
print("DFDC 的 match_rules 包含 'gameid': ['osmbwjl']，所以機器2匹配到 DFDC")
print("\n解決方案:")
print("1. 在 game_title_codes.csv 中添加第二行的 game_title_code（例如 873-JJBX-0005）")
print("2. 在 game_config.json 中為機器2手動指定 'machine_type': 'JJBX'")
print("3. 修改 DFDC 的 match_rules，移除 'osmbwjl'（如果 osmbwjl 應該只匹配 JJBX）")

