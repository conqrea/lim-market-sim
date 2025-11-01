# simulator.py

import math
import pandas as pd

class MarketSimulator:
    def __init__(self, company_names, config):
        """
        시뮬레이터를 초기화합니다.
        company_names: 회사 이름 리스트 (예: ["Apple", "Samsung"])
        config: 시뮬레이션의 성격을 결정하는 설정 값 딕셔너리
        """
        self.config = config
        self.company_names = company_names
        self.companies = {
            name: {
                "market_share": 1.0 / len(company_names),
                "unit_cost": config.get("unit_costs", {}).get(name, 5000),
                "accumulated_profit": config.get("initial_capital", 0)
            }
            for name in company_names
        }
        self.turn = 0
        self.history = [] # 매 턴의 기록을 저장할 리스트
        print("MarketSimulator가 성공적으로 생성되었습니다!")

    def _calculate_attractiveness(self, decisions):
        """[최종 수정] 현실적인 누적 부채 기반의 재무 페널티 적용"""
        attractiveness = {}
        avg_price = sum(d['price'] for d in decisions.values()) / len(decisions) if decisions else 1

        for name, decision in decisions.items():
            # 1. 가격 매력도 계산
            price_attr = (avg_price / decision['price']) ** self.config['price_sensitivity']
            
            # 2. S-자형 곡선 기반 마케팅 '부스트(Boost)' 계수 계산
            L = self.config['max_marketing_boost']
            k = self.config['marketing_steepness']
            x0 = self.config['marketing_midpoint']
            x = decision['marketing_spend']
            
            marketing_boost = L / (1 + math.exp(-k * (x - x0)))
            
            base_attractiveness = price_attr * (1 + marketing_boost)

            # [핵심 수정] 재무 위기 페널티: '지난 턴 손실'이 아닌 '총 누적 부채'에 기반합니다.
            # 회사의 전반적인 재무 건전성을 반영하여 훨씬 더 현실적입니다.
            financial_distress_multiplier = 1.0
            current_capital = self.companies[name]['accumulated_profit']
            
            if current_capital < 0:
                # 누적 부채가 초기 자본금의 몇 %인지 계산하여 페널티 강도 조절
                debt_ratio = abs(current_capital) / self.config['initial_capital']
                penalty = debt_ratio * 0.5 # 페널티 영향력을 0.5로 설정
                financial_distress_multiplier = max(0.5, 1.0 - penalty) # 매력도가 50% 이하로 떨어지지는 않도록 제한
                
            attractiveness[name] = base_attractiveness * financial_distress_multiplier
            
        return attractiveness

    def process_turn(self, decisions):
        """
        한 턴을 진행하고 시장 상태를 업데이트합니다.
        """
        self.turn += 1

        # --- [개선] 파산 메커니즘 시작 ---
        active_company_names = self.company_names[:]
        bankrupt_company_names = []
        
        for name in self.company_names:
            if self.companies[name]['accumulated_profit'] < 0:
                if name in active_company_names:
                    active_company_names.remove(name)
                    bankrupt_company_names.append(name)

        if not active_company_names:
            print("모든 회사가 파산하여 시뮬레이션을 중단합니다.")
            return self.get_market_state()
        # --- 파산 메커니즘 끝 ---

        # 1단계: '생존한' 기업들의 의사결정만으로 시장 매력도 계산
        active_decisions = {name: decisions[name] for name in active_company_names}
        attractiveness = self._calculate_attractiveness(active_decisions)
        total_attractiveness = sum(attractiveness.values())
        
        current_turn_results = {"turn": self.turn}

        # 2 & 3단계: 점유율 재분배 및 재무 결과 계산
        for name in self.company_names:
            share = 0 # 기본 점유율은 0으로 설정

            # [핵심] 생존한 기업에 대해서만 점유율을 계산하여 재분배
            if name in active_company_names:
                share = attractiveness.get(name, 0) / total_attractiveness if total_attractiveness > 0 else 0
            
            # 파산한 기업은 이 턴부터 점유율이 강제로 0이 됨
            self.companies[name]['market_share'] = share
            
            # 재무 결과 계산
            price = decisions[name]['price']
            marketing_spend = decisions[name]['marketing_spend']
            
            sales_volume = self.config['market_size'] * share
            revenue = sales_volume * price
            
            # 파산한 기업은 마케팅 비용도 0으로 간주 (이미 지출된 것으로 처리하지 않음)
            if name in bankrupt_company_names:
                print(f"!!! 턴 {self.turn}: {name} 파산. 시장에서 퇴출됩니다. (점유율 0, 추가 지출 0 처리)")
                marketing_spend = 0

            profit = revenue - marketing_spend - (sales_volume * self.companies[name]['unit_cost'])
            
            # 누적 이익 업데이트
            self.companies[name]['accumulated_profit'] += profit

            # 턴별 결과 기록
            current_turn_results[f"{name}_price"] = price
            current_turn_results[f"{name}_marketing_spend"] = marketing_spend
            current_turn_results[f"{name}_market_share"] = share
            current_turn_results[f"{name}_profit"] = profit
            current_turn_results[f"{name}_accumulated_profit"] = self.companies[name]['accumulated_profit']

        self.history.append(current_turn_results)
        return self.get_market_state()

    def get_market_state(self):
        """현재 시장 상태를 AI 에이전트에게 전달할 형식으로 반환합니다."""
        state = {
            "turn": self.turn,
            "companies": {}
        }
        for name, data in self.companies.items():
            # [핵심 변경]
            # 이제 시장 점유율 뿐만 아니라,
            # AI 자신의 '원가'와 '누적 이익' 정보도 함께 전달합니다.
            state["companies"][name] = {
                "market_share": data['market_share'],
                "unit_cost": data['unit_cost'],
                "accumulated_profit": data['accumulated_profit']
            }
        
        if self.history:
            state["last_turn_results"] = self.history[-1]
            
        return state

    def get_history_df(self):
        """지금까지의 모든 기록을 Pandas DataFrame으로 반환합니다."""
        return pd.DataFrame(self.history)


# --- 이 파일 단독으로 테스트하기 위한 코드 ---
if __name__ == '__main__':
    # 시뮬레이션의 성격을 결정하는 '튜닝 노브'
    sim_config = {
        'price_sensitivity': 2.0,     # 가격 민감도 (클수록 가격에 민감)
        'marketing_sensitivity': 1.2, # 마케팅 민감도 (클수록 마케팅 효과 큼)
        'market_size': 10000,         # 전체 시장 고객 수
        'unit_costs': {'Apple': 4000, 'Samsung': 4500} # Apple이 원가 경쟁력 우위
    }

    market = MarketSimulator(['Apple', 'Samsung'], sim_config)
    
    print("--- 초기 상태 ---")
    print(market.get_market_state())

    # 1턴: Apple이 공격적으로 가격을 낮춤
    decisions_1 = {
        'Apple': {'price': 9000, 'marketing_spend': 1000000},
        'Samsung': {'price': 10000, 'marketing_spend': 1000000}
    }
    market.process_turn(decisions_1)
    
    print("\n--- 1턴 후 ---")
    # 'last_turn_results'에 1턴의 모든 결과가 담겨 있는지 확인
    print(market.get_market_state()['last_turn_results'])