# main.py

import pandas as pd
from reporter import generate_report
from simulator import MarketSimulator
from agent import AIAgent
import asyncio # 비동기 실행을 위해 asyncio 임포트

# main 함수를 비동기(async) 함수로 정의합니다.
async def main():
    # --- 1. 시뮬레이션 전체 설정 (기존과 동일) ---
    TOTAL_TURNS = 30
    COMPANY_NAMES = ["Apple", "Samsung"]

    sim_config = {
        'price_sensitivity': 2.0,
        'max_marketing_boost': 1.5,
        'marketing_midpoint': 5000000,
        'marketing_steepness': 0.0000015,
        'market_size': 10000,
        'unit_costs': {'Apple': 8500, 'Samsung': 9000},
        'initial_capital': 25000000,
    }

    personas = {
        "Apple": "당신은 시장 점유율 확보를 최우선으로 하는 공격적인 CEO입니다. 단기 이익 손실을 감수하더라도 경쟁사보다 낮은 가격과 높은 마케팅 비용으로 시장을 지배해야 합니다.",
        "Samsung": "당신은 안정적인 이익률 유지를 최우선으로 하는 보수적인 CEO입니다. 불필요한 가격 경쟁을 피하고, 비용을 효율적으로 사용하여 수익성을 극대화해야 합니다."
    }
    
    # --- 2. 시뮬레이션 환경 및 에이전트 생성 (기존과 동일) ---
    market = MarketSimulator(COMPANY_NAMES, sim_config)
    agents = [AIAgent(name=name, persona=personas[name], use_mock=False) for name in COMPANY_NAMES]
    
    # --- 3. 시뮬레이션 실행 (메인 루프) ---
    for turn in range(1, TOTAL_TURNS + 1):
        print(f"\n{'='*20} Turn {turn}/{TOTAL_TURNS} 시작 {'='*20}")
        market_state = market.get_market_state()

        # [핵심 변경]
        # 1. 두 AI의 결정 함수를 '작업 목록'으로 만듭니다. (아직 실행은 안 함)
        tasks = [agent.decide_action(market_state) for agent in agents]
        
        # 2. asyncio.gather가 두 AI의 작업을 '동시에' 실행하고 결과가 모두 올 때까지 기다립니다.
        decisions_list = await asyncio.gather(*tasks)
        
        # 3. 결과를 시뮬레이터가 이해하는 형태로 변환합니다.
        decisions = {agent.name: decision for agent, decision in zip(agents, decisions_list)}
        
        print(f"AI들의 결정: {decisions}")
        market.process_turn(decisions)
        
    print(f"\n{'='*20} 시뮬레이션 종료 {'='*20}")

    # --- 4 & 5. 결과 저장 및 리포트 생성 (기존과 동일) ---
    history_df = market.get_history_df()
    history_df.to_csv("simulation_results.csv", index=False)
    generate_report("simulation_results.csv")
    print(f"\n시뮬레이션 결과가 'simulation_results.csv' 파일로 저장되었습니다.")


# 비동기 main 함수를 실행하는 공식적인 방법입니다.
if __name__ == "__main__":
    asyncio.run(main())