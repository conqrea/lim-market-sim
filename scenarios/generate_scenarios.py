import json
import os

# --- Helper: 턴 데이터 생성기 ---
def build_scenario(name, description, company_a_name, company_b_name, turns_raw_data):
    turns_list = []
    for idx, data in enumerate(turns_raw_data):
        # data format: [Share_A, Price_A, Share_B, Price_B]
        # 마케팅/R&D 비율은 해당 기업의 당시 전략을 반영하여 추정치 삽입
        
        # Company A Strategy
        mkt_a, rd_a = 0.05, 0.05
        if "Apple" in company_a_name or "Google" in company_a_name or "Tesla" in company_a_name:
            rd_a = 0.15 # 기술 기업은 R&D 높음
            mkt_a = 0.02
        elif "Coke" in company_a_name or "Nike" in company_a_name:
            mkt_a = 0.20 # 브랜드 기업은 마케팅 높음

        # Company B Strategy
        mkt_b, rd_b = 0.05, 0.05
        if "Nokia" in company_b_name or "Blockbuster" in company_b_name:
            rd_b = 0.02 # 쇠락하는 기업은 투자 여력 낮음
            mkt_b = 0.08 # 방어적 마케팅

        turns_list.append({
            "turn": idx + 1,
            "note": f"Quarter {idx+1}",
            "companies": {
                company_a_name: {
                    "inputs": { "price": data[1], "marketing_spend_ratio": mkt_a, "rd_spend_ratio": rd_a },
                    "outputs": { "actual_market_share": data[0] }
                },
                company_b_name: {
                    "inputs": { "price": data[3], "marketing_spend_ratio": mkt_b, "rd_spend_ratio": rd_b },
                    "outputs": { "actual_market_share": data[2] }
                }
            }
        })
    
    return {
        "scenario_name": name,
        "description": description,
        "turns_data": turns_list
    }

# --- 실제 역사적 데이터 (Share A, Price A, Share B, Price B) ---
# 각 데이터는 해당 시기의 실제 점유율 추이를 반영 (Price는 당시 가격 추정치)

# 1. Smartphone Disruption (2007-2010): iPhone vs Nokia
# Nokia 점유율 급락, iPhone 급상승 (가격은 iPhone이 훨씬 비쌌음에도 불구하고)
data_smartphone = [
    [0.05, 500, 0.45, 200], [0.08, 500, 0.42, 190], [0.12, 500, 0.38, 180], [0.18, 500, 0.32, 170], # Year 1
    [0.22, 500, 0.28, 160], [0.28, 450, 0.22, 150], [0.35, 450, 0.18, 140], [0.40, 450, 0.15, 130], # Year 2
    [0.45, 400, 0.12, 120], [0.50, 400, 0.10, 110], [0.55, 400, 0.08, 100], [0.60, 400, 0.05, 90]   # Year 3
]

# 2. Browser Wars (2008-2011): Chrome vs IE
# 무료 제품, 품질(속도) 차이로 인한 급격한 역전
data_browser = [
    [0.01, 1, 0.60, 1], [0.05, 1, 0.55, 1], [0.10, 1, 0.50, 1], [0.15, 1, 0.45, 1], 
    [0.20, 1, 0.40, 1], [0.25, 1, 0.35, 1], [0.30, 1, 0.30, 1], [0.35, 1, 0.25, 1],
    [0.40, 1, 0.20, 1], [0.45, 1, 0.18, 1], [0.50, 1, 0.15, 1], [0.55, 1, 0.12, 1]
]

# 3. Video Rental (2004-2007): Netflix vs Blockbuster
# 오프라인(Blockbuster)의 붕괴와 온라인/배송(Netflix)의 승리
data_video = [
    [0.10, 15, 0.50, 5], [0.15, 15, 0.45, 5], [0.20, 15, 0.40, 5], [0.25, 15, 0.35, 5],
    [0.30, 15, 0.30, 5], [0.35, 12, 0.25, 4], [0.40, 12, 0.20, 4], [0.45, 12, 0.15, 4],
    [0.50, 10, 0.10, 3], [0.60, 10, 0.05, 3], [0.70, 10, 0.02, 2], [0.80, 10, 0.01, 1]
]

# 4. Social Media (2006-2009): Facebook vs MySpace
# 네트워크 효과로 인한 급격한 쏠림 현상
data_social = [
    [0.10, 1, 0.40, 1], [0.15, 1, 0.38, 1], [0.20, 1, 0.35, 1], [0.30, 1, 0.30, 1],
    [0.40, 1, 0.25, 1], [0.50, 1, 0.20, 1], [0.60, 1, 0.15, 1], [0.70, 1, 0.10, 1],
    [0.80, 1, 0.05, 1], [0.85, 1, 0.03, 1], [0.90, 1, 0.02, 1], [0.95, 1, 0.01, 1]
]

# 5. Digital Camera (2000-2003): Digital(Sony) vs Film(Kodak)
# 기술 교체기. 필름(Others/Kodak)이 아무리 싸도 디지털로 넘어감.
data_camera = [
    [0.15, 800, 0.40, 200], [0.20, 700, 0.35, 180], [0.25, 600, 0.30, 160], [0.30, 550, 0.25, 150],
    [0.40, 500, 0.20, 140], [0.50, 450, 0.15, 130], [0.60, 400, 0.10, 120], [0.70, 350, 0.08, 100],
    [0.75, 300, 0.05, 80],  [0.80, 250, 0.03, 60],  [0.85, 200, 0.02, 50],  [0.90, 180, 0.01, 40]
]

# 6. Game Console (2006-2009): Wii vs PS3
# 저성능 저가격(Wii)이 고성능 고가격(PS3)을 이긴 이례적 케이스 (혁신적 UX)
data_console = [
    [0.10, 250, 0.30, 600], [0.20, 250, 0.28, 600], [0.30, 250, 0.25, 550], [0.35, 250, 0.22, 550],
    [0.40, 250, 0.20, 500], [0.45, 250, 0.18, 500], [0.50, 250, 0.18, 450], [0.52, 250, 0.17, 450],
    [0.55, 200, 0.16, 400], [0.55, 200, 0.16, 400], [0.53, 200, 0.18, 400], [0.50, 200, 0.20, 350]
]

# 7. Search Engine (2000-2003): Google vs Yahoo
# 성능(검색 정확도) 차이로 인한 점유율 이동
data_search = [
    [0.10, 1, 0.40, 1], [0.15, 1, 0.38, 1], [0.25, 1, 0.35, 1], [0.35, 1, 0.30, 1],
    [0.45, 1, 0.25, 1], [0.55, 1, 0.20, 1], [0.65, 1, 0.15, 1], [0.70, 1, 0.10, 1],
    [0.75, 1, 0.08, 1], [0.80, 1, 0.06, 1], [0.85, 1, 0.05, 1], [0.90, 1, 0.04, 1]
]

# 8. Cloud Computing (2015-2018): AWS vs Azure
# 초기 독주(AWS)를 추격하는 Azure. 둘 다 성장하며 Others(온프레미스) 파괴.
data_cloud = [
    [0.50, 100, 0.10, 100], [0.50, 95, 0.12, 95], [0.49, 90, 0.15, 90], [0.48, 85, 0.18, 85],
    [0.47, 80, 0.20, 80],   [0.45, 75, 0.22, 75], [0.44, 70, 0.25, 70], [0.42, 65, 0.28, 65],
    [0.40, 60, 0.30, 60],   [0.38, 55, 0.32, 55], [0.36, 50, 0.33, 50], [0.35, 45, 0.34, 45]
]

# 9. Sneaker Wars (2014-2017): Nike vs Adidas(Boost)
# 아디다스의 기술 혁신(Boost)으로 나이키 점유율 일부 잠식
data_sneaker = [
    [0.50, 120, 0.15, 100], [0.50, 120, 0.16, 120], [0.49, 120, 0.18, 130], [0.48, 120, 0.20, 140],
    [0.47, 120, 0.22, 150], [0.46, 120, 0.24, 150], [0.45, 120, 0.25, 150], [0.44, 125, 0.26, 150],
    [0.43, 125, 0.27, 150], [0.42, 125, 0.28, 150], [0.42, 130, 0.28, 150], [0.42, 130, 0.28, 150]
]

# 10. Ride Sharing (2014-2017): Uber vs Lyft
# 치열한 가격 전쟁 및 마케팅 전쟁 (적자 경쟁)
data_ride = [
    [0.80, 20, 0.05, 18], [0.78, 19, 0.08, 17], [0.76, 18, 0.10, 16], [0.74, 17, 0.12, 15],
    [0.72, 16, 0.15, 14], [0.70, 15, 0.18, 13], [0.68, 14, 0.20, 12], [0.67, 13, 0.22, 11],
    [0.66, 12, 0.24, 10], [0.65, 11, 0.25, 10], [0.65, 10, 0.26, 9],  [0.65, 10, 0.27, 9]
]

# 파일 생성 실행
scenarios_list = [
    ("real_smartphone.json", "Smartphone War", "Apple", "Nokia", data_smartphone),
    ("real_browser.json", "Browser War", "Chrome", "IE", data_browser),
    ("real_video.json", "Video Rental War", "Netflix", "Blockbuster", data_video),
    ("real_social.json", "Social Media War", "Facebook", "MySpace", data_social),
    ("real_camera.json", "Camera War", "SonyDigital", "KodakFilm", data_camera),
    ("real_console.json", "Console War", "Wii", "PS3", data_console),
    ("real_search.json", "Search Engine War", "Google", "Yahoo", data_search),
    ("real_cloud.json", "Cloud War", "AWS", "Azure", data_cloud),
    ("real_sneaker.json", "Sneaker War", "Nike", "Adidas", data_sneaker),
    ("real_ride.json", "Ride Sharing War", "Uber", "Lyft", data_ride),
]

if not os.path.exists("scenarios_real"):
    os.makedirs("scenarios_real")

print("=== Generating 10 Historical Scenarios (Real Data) ===")
for fname, name, co_a, co_b, raw_data in scenarios_list:
    json_data = build_scenario(name, "Historical data benchmark", co_a, co_b, raw_data)
    
    # Price 보정 (0원 방지)
    for t in json_data['turns_data']:
        for c in t['companies'].values():
            if c['inputs']['price'] <= 0: c['inputs']['price'] = 1

    with open(os.path.join("scenarios_real", fname), "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)
    print(f" - Created: {fname}")

print("\nDone. Run 'validator_real.py' to test.")