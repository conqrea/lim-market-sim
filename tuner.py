import matplotlib
matplotlib.use('Agg')
from simulator import MarketSimulator
from reporter import generate_report
import os

def run_price_war_scenario(config, turns=30):
    """
    [목표 1 수정] 'Others'와 경쟁 가능한 마케팅비를 쓰면서 가격 인하
    (R&D 투자는 0으로 고정)
    """
    print("--- [목표 1 검증] 가격 전쟁 시나리오 시작 ---")
    market = MarketSimulator(['A', 'B'], config)
    price_A = 10000
    price_B = 10000
    # [수정] 'Others'(250만)와 최소한 경쟁할 수 있는 마케팅비로 변경
    baseline_marketing = 2000000 
    baseline_rd = 0 # [수정] R&D 변수 제거

    for i in range(1, turns + 1):
        price_A *= 0.96
        price_B *= 0.96
        decisions = {
            'A': {'price': price_A, 'marketing_spend': baseline_marketing, 'rd_spend': baseline_rd},
            'B': {'price': price_B, 'marketing_spend': baseline_marketing, 'rd_spend': baseline_rd}
        }
        market.process_turn(decisions)
        
        last_result = market.history[-1]
        print(f"턴 {i}: A Price={price_A:,.0f}, A Profit={last_result['A_profit']:,.0f}, B Profit={last_result['B_profit']:,.0f}")

    history_df = market.get_history_df()
    csv_path = "results/tuning_price_war.csv"
    history_df.to_csv(csv_path, index=False)
    generate_report(csv_path)
    print(f"가격 전쟁 시나리오 완료. 결과는 'results/tuning_price_war.png'에서 확인하세요.")


def run_marketing_war_scenario(config, turns=30):
    """
    [목표 2 수정] 'A'사만 마케팅 지출을 늘릴 때, 수확 체감이 발생하는지 관찰
    (R&D 투자는 0으로 고정)
    """
    print("\n--- [목표 2 검증] 마케팅 전쟁 시나리오 시작 ---")
    market = MarketSimulator(['A', 'B'], config)
    marketing_spend_A = 1000
    profit_turned_negative = False
    baseline_rd = 0 # [수정] R&D 변수를 0으로 고정하여 마케팅만 테스트

    for i in range(1, turns + 1):
        marketing_spend_A += config['marketing_step'] 
        decisions = {
            'A': {'price': 10000, 'marketing_spend': marketing_spend_A, 'rd_spend': baseline_rd},
            'B': {'price': 10000, 'marketing_spend': 100000, 'rd_spend': baseline_rd} 
        }
        market.process_turn(decisions)

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
    print(f"마케팅 전쟁 시나리오 완료. 결과는 'results/tuning_marketing_war.png'에서 확인하세요.")


def run_rd_investment_scenario(config, turns=30):
    """
    [R&D 검증] 'A'사만 R&D에 투자할 때, 'A'사의 단위 원가(unit_cost)가 하락하는지 관찰합니다.
    (이 시나리오는 이미 성공적이므로 수정 없음)
    """
    print("\n--- [R&D 검증] R&D 투자 시나리오 시작 ---")
    market = MarketSimulator(['A', 'B'], config)

    rd_spend_A = 2000000
    rd_spend_B = 0

    for i in range(1, turns + 1):
        decisions = {
            'A': {'price': 10000, 'marketing_spend': 1000000, 'rd_spend': rd_spend_A},
            'B': {'price': 10000, 'marketing_spend': 1000000, 'rd_spend': rd_spend_B}
        }
        market.process_turn(decisions)

        last_result = market.history[-1]
        a_cost = last_result['A_unit_cost']
        b_cost = last_result['B_unit_cost']
        print(f"턴 {i}: A Unit Cost={a_cost:,.2f} (R&D 투자 중), B Unit Cost={b_cost:,.2f} (R&D 투자 안함)")

    history_df = market.get_history_df()
    csv_path = "results/tuning_rd_investment.csv"
    history_df.to_csv(csv_path, index=False)
    generate_report(csv_path)
    print(f"R&D 투자 시나N리오 완료. 결과는 'results/tuning_rd_investment.png'에서 확인하세요.")
    print("****** (성공) '단위 원가 변화' 그래프에서 A가 B와 달리 하락하는지 확인하세요. ******")


if __name__ == '__main__':
    if not os.path.exists("results"):
        os.makedirs("results")

    # === 최종 튜닝된 설정값 (api_main.py와 동기화) ===
    final_tuned_config = {
        'price_sensitivity': 2.0, 
        'max_marketing_boost': 0.8, 
        'marketing_midpoint': 5000000,
        'marketing_steepness': 0.0000025,
        'market_size': 10000,
        'unit_costs': {'A': 8500, 'B': 8500}, 
        'initial_capital': 25000000,
        
        'rd_effectiveness_divisor': 50000000, 
        
        'marketing_step': 700000 
    }
    
    # --- 실행할 시나리오 선택 ---
    run_price_war_scenario(final_tuned_config)
    run_marketing_war_scenario(final_tuned_config)
    run_rd_investment_scenario(final_tuned_config)
def run_price_war_scenario(config, turns=30):
    """
    [목표 1 검증] 모든 회사가 기계적으로 가격을 인하할 때, 공멸하는지 관찰합니다.
    (R&D 투자는 최소한으로 고정)
    """
    print("--- [목표 1 검증] 가격 전쟁 시나리오 시작 ---")
    market = MarketSimulator(['A', 'B'], config)
    price_A = 10000
    price_B = 10000
    baseline_rd = 500000 # R&D 지출 고정

    for i in range(1, turns + 1):
        price_A *= 0.96
        price_B *= 0.96
        decisions = {
            'A': {'price': price_A, 'marketing_spend': 10000, 'rd_spend': baseline_rd},
            'B': {'price': price_B, 'marketing_spend': 10000, 'rd_spend': baseline_rd}
        }
        market.process_turn(decisions)
        
        last_result = market.history[-1]
        print(f"턴 {i}: A Profit={last_result['A_profit']:,.0f}, B Profit={last_result['B_profit']:,.0f}")

    history_df = market.get_history_df()
    csv_path = "results/tuning_price_war.csv"
    history_df.to_csv(csv_path, index=False)
    generate_report(csv_path)
    print(f"가격 전쟁 시나리오 완료. 결과는 'results/tuning_price_war.png'에서 확인하세요.")


def run_marketing_war_scenario(config, turns=30):
    """
    [목표 2 검증] 'A'사가 과도한 마케팅을 지속할 때, 수확 체감으로 이익이 감소하는지 관찰합니다.
    (R&D 투자는 최소한으로 고정)
    """
    print("\n--- [목표 2 검증] 마케팅 전쟁 시나리오 시작 ---")
    market = MarketSimulator(['A', 'B'], config)
    marketing_spend_A = 1000
    profit_turned_negative = False
    baseline_rd = 500000 # R&D 지출 고정

    for i in range(1, turns + 1):
        marketing_spend_A += config['marketing_step'] 
        decisions = {
            'A': {'price': 10000, 'marketing_spend': marketing_spend_A, 'rd_spend': baseline_rd},
            'B': {'price': 10000, 'marketing_spend': 100000, 'rd_spend': baseline_rd} 
        }
        market.process_turn(decisions)

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
    print(f"마케팅 전쟁 시나리오 완료. 결과는 'results/tuning_marketing_war.png'에서 확인하세요.")


def run_rd_investment_scenario(config, turns=30):
    """
    [R&D 검증] 'A'사만 R&D에 투자할 때, 'A'사의 단위 원가(unit_cost)가 하락하는지 관찰합니다.
    (가격과 마케팅은 동일하게 고정)
    """
    print("\n--- [R&D 검증] R&D 투자 시나리오 시작 ---")
    market = MarketSimulator(['A', 'B'], config)

    # A는 R&D 투자, B는 R&D 투자 안 함
    rd_spend_A = 2000000
    rd_spend_B = 0

    for i in range(1, turns + 1):
        decisions = {
            'A': {'price': 10000, 'marketing_spend': 1000000, 'rd_spend': rd_spend_A},
            'B': {'price': 10000, 'marketing_spend': 1000000, 'rd_spend': rd_spend_B}
        }
        market.process_turn(decisions)

        # A사와 B사의 현재 단위 원가(unit_cost)를 추적
        last_result = market.history[-1]
        a_cost = last_result['A_unit_cost']
        b_cost = last_result['B_unit_cost']
        print(f"턴 {i}: A Unit Cost={a_cost:,.2f} (R&D 투자 중), B Unit Cost={b_cost:,.2f} (R&D 투자 안함)")

    history_df = market.get_history_df()
    csv_path = "results/tuning_rd_investment.csv"
    history_df.to_csv(csv_path, index=False)
    generate_report(csv_path)
    print(f"R&D 투자 시나리오 완료. 결과는 'results/tuning_rd_investment.png'에서 확인하세요.")
    print("****** '단위 원가 변화' 그래프에서 A(파란색)가 B(주황색)와 달리 하락하는지 꼭 확인하세요! ******")


if __name__ == '__main__':
    if not os.path.exists("results"):
        os.makedirs("results")

    # === 최종 튜닝된 설정값 (api_main.py와 동기화) ===
    final_tuned_config = {
        'price_sensitivity': 2.0, 
        'max_marketing_boost': 1.0, 
        'marketing_midpoint': 5000000,
        'marketing_steepness': 0.0000015,
        'market_size': 10000,
        'unit_costs': {'A': 8500, 'B': 8500}, # R&D 테스트를 위해 초기 원가를 동일하게 설정
        'initial_capital': 25000000,
        
        # [R&D 수정] R&D 효과 조절 변수 추가 (api_main.py의 SimulationConfig와 동일)
        'rd_effectiveness_divisor': 50000000, 
        
        # --- 튜너 시나리오용 변수 ---
        'marketing_step': 700000 
    }
    
    # --- 실행할 시나리오 선택 ---
    run_price_war_scenario(final_tuned_config)
    run_marketing_war_scenario(final_tuned_config)
    run_rd_investment_scenario(final_tuned_config) # R&D 테스트 실행