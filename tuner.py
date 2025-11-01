# tuner.py (새로운 버전)

from simulator import MarketSimulator
from reporter import generate_report
import os

def run_price_war_scenario(config, turns=30):
    """
    [목표 1 검증] 모든 회사가 기계적으로 가격을 인하할 때,
    점진적으로 이익과 누적 자본이 감소하여 공멸하는 과정을 관찰합니다.
    """
    print("--- [목표 1 검증] 가격 전쟁 시나리오 시작 ---")
    market = MarketSimulator(['A', 'B'], config)
    price_A = 10000
    price_B = 10000

    for i in range(1, turns + 1):
        # 매 턴 4%씩 가격 인하 (조금 더 완만한 하락을 위해 5% -> 4%로 조정)
        price_A *= 0.96
        price_B *= 0.96
        decisions = {
            'A': {'price': price_A, 'marketing_spend': 10000}, # 마케팅 지출은 최소화
            'B': {'price': price_B, 'marketing_spend': 10000}
        }
        market.process_turn(decisions)
        
        # 현재 턴의 이익 상황을 터미널에 출력
        last_result = market.history[-1]
        print(f"턴 {i}: A Profit={last_result['A_profit']:,.0f}, B Profit={last_result['B_profit']:,.0f}")


    history_df = market.get_history_df()
    csv_path = "results/tuning_price_war.csv"
    history_df.to_csv(csv_path, index=False)
    generate_report(csv_path)
    print(f"가격 전쟁 시나리오 완료. 결과는 'results' 폴더에서 확인하세요.")

def run_marketing_war_scenario(config, turns=30):
    """
    [목표 2 검증] 'A'사가 과도한 마케팅을 지속할 때,
    초기에는 이득을 보지만 결국 '수확 체감'으로 인해 이익이 감소하여 음수로 전환되는지 관찰합니다.
    """
    print("\n--- [목표 2 검증] 마케팅 전쟁 시나리오 시작 ---")
    market = MarketSimulator(['A', 'B'], config)
    marketing_spend_A = 1000
    profit_turned_negative = False

    for i in range(1, turns + 1):
        marketing_spend_A += config['marketing_step'] # 설정값에 따라 마케팅비 증가
        decisions = {
            'A': {'price': 10000, 'marketing_spend': marketing_spend_A},
            'B': {'price': 10000, 'marketing_spend': 100000} # B는 마케팅비 고정
        }
        market.process_turn(decisions)

        # A사의 이익을 확인하고, 음수로 전환되는 시점을 포착
        last_result = market.history[-1]
        a_profit = last_result['A_profit']
        print(f"턴 {i}: A Marketing Spend={marketing_spend_A:,.0f}, A Profit={a_profit:,.0f}")
        
        if a_profit < 0 and not profit_turned_negative:
            print(f"****** 목표 달성: 턴 {i}에서 A사의 이익이 음수로 전환되었습니다! ******")
            profit_turned_negative = True

    history_df = market.get_history_df()
    csv_path = "results/tuning_marketing_war.csv"
    history_df.to_csv(csv_path, index=False)
    generate_report(csv_path)
    print(f"마케팅 전쟁 시나리오 완료. 결과는 'results' 폴더에서 확인하세요.")


if __name__ == '__main__':
    # 디렉토리 생성
    if not os.path.exists("results"):
        os.makedirs("results")

    # === 최종 튜닝된 설정값 ===
    # 시장이 너무 빨리 붕괴하지 않으면서, 각 현상을 관찰할 수 있도록 조정되었습니다.
    final_tuned_config = {
        'price_sensitivity': 2.0, # 가격 민감도를 약간 높여 기본 경쟁을 강화
    
        # --- 시너지 모델 기반 마케팅 파라미터 ---
        # 최대 효율점(midpoint)에서 마케팅은 기본 매력도를 150%까지 증폭시킬 수 있습니다.
        'max_marketing_boost': 1.5,
        # 마케팅 효율이 가장 좋은 지점은 지출액 500만입니다.
        'marketing_midpoint': 5000000,
        # 곡선의 기울기
        'marketing_steepness': 0.0000015,

        'market_size': 10000,
        'unit_costs': {'A': 8500, 'B': 9000},
        'initial_capital': 25000000,
        'marketing_step': 700000
    }
    
    # --- 실행할 시나리오 선택 ---
    run_price_war_scenario(final_tuned_config)
    #run_marketing_war_scenario(final_tuned_config)