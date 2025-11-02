# simulator.py (SoV 곱셈 모델 + IndexError 수정)

import math
import pandas as pd

# (Event 클래스는 동일)
class Event:
    def __init__(self, description, target_company, effect_type, impact_value, duration):
        self.description = description
        self.target_company = target_company
        self.effect_type = effect_type
        self.impact_value = impact_value
        self.duration = duration

class MarketSimulator:
    def __init__(self, company_names, config):
        self.config = config
        self.ai_company_names = company_names
        self.dummy_company_names = ["Others"]
        self.all_company_names = self.ai_company_names + self.dummy_company_names

        self.companies = {}
        for name in self.ai_company_names:
            self.companies[name] = {
                "market_share": 1.0 / len(self.all_company_names),
                "base_unit_cost": config.get("unit_costs", {}).get(name, 5000), 
                "unit_cost": config.get("unit_costs", {}).get(name, 5000),      
                "accumulated_profit": config.get("initial_capital", 0)
            }
        for name in self.dummy_company_names:
            self.companies[name] = {
                "market_share": 1.0 / len(self.all_company_names),
                "base_unit_cost": config.get("unit_costs", {}).get(company_names[0], 5000), 
                "unit_cost": config.get("unit_costs", {}).get(company_names[0], 5000),
                "accumulated_profit": 0
            }
        
        self.turn = 0
        self.history = []
        self.pending_event_queue = [] 
        self.active_effects = []      
        print("MarketSimulator가 성공적으로 생성되었습니다! ('Others' 경쟁자 포함, SoV 곱셈 모델)")

    # (inject_event)
    def inject_event(self, event_data: dict):
        try:
            event = Event(
                description=event_data['description'],
                target_company=event_data['target_company'],
                effect_type=event_data['effect_type'],
                impact_value=event_data['impact_value'],
                duration=event_data['duration']
            )
            self.pending_event_queue.append(event)
            print(f"[이벤트 주입] 턴 {self.turn+1}에 '{event.description}' 이벤트가 등록되었습니다.")
        except Exception as e:
            print(f"[이벤트 오류] 잘못된 이벤트 데이터입니다: {e}")

    # (_apply_events)
    def _apply_events(self):
        for name in self.all_company_names:
            if name in self.companies:
                self.companies[name]['unit_cost'] = self.companies[name]['base_unit_cost']
        
        while self.pending_event_queue:
            event = self.pending_event_queue.pop(0)
            self.active_effects.append(event)
            print(f"[이벤트 발생] 턴 {self.turn}: '{event.description}' 효과가 적용됩니다!")
        
        temp_active_effects = []
        for effect in self.active_effects:
            if effect.effect_type == "unit_cost_multiplier":
                target_list = [effect.target_company] if effect.target_company != "All" else self.all_company_names
                for name in target_list:
                    if name in self.companies:
                        self.companies[name]['unit_cost'] *= effect.impact_value 
            
            effect.duration -= 1
            if effect.duration > 0:
                temp_active_effects.append(effect)
            else:
                print(f"[이벤트 종료] 턴 {self.turn}: '{effect.description}' 효과가 종료되었습니다.")
        self.active_effects = temp_active_effects

    # --- [버그 수정 1] 'Others'의 결정을 생성하는 규칙 기반 로직 ---
    def _get_dummy_decisions(self):
        """'Others'의 결정을 생성하는 규칙 기반 로직"""
        
        others_price = 10000 
        others_marketing = self.config['marketing_midpoint'] / 2 
        
        # [수정] self.history 리스트에 데이터가 1개라도 있는지 확인합니다.
        if self.history: 
            last_history = self.history[-1]
            avg_price = 0
            count = 0
            for name in self.all_company_names:
                avg_price += last_history.get(f"{name}_price", 10000)
                count += 1
            others_price = avg_price / count

        return {"Others": {"price": others_price, "marketing_spend": others_marketing}}

    # --- [핵심 수정] _calculate_attractiveness 함수 (Share of Voice 곱셈 모델) ---
    def _calculate_attractiveness(self, decisions):
        """
        [밸런싱 수정] 'Share of Voice' (상대적 마케팅 점유율) 모델을 적용합니다.
        """
        attractiveness = {}
        
        # --- 1단계: 각 회사의 '마케팅 유효성(Effectiveness)' 계산 ---
        marketing_effectiveness = {}
        total_effectiveness = 0.0
        
        for name, decision in decisions.items():
            L = self.config['max_marketing_boost'] # 1.0 (최대 효율)
            k = self.config['marketing_steepness']
            x0 = self.config['marketing_midpoint']
            x = decision['marketing_spend']

            effectiveness = L / (1 + math.exp(-k * (x - x0)))
            start_point_effectiveness = L / (1 + math.exp(-k * (0 - x0)))
            effectiveness = max(0, effectiveness - start_point_effectiveness)
            
            effectiveness += 0.01 # 최소 인지도 0.01

            marketing_effectiveness[name] = effectiveness
            total_effectiveness += effectiveness

        # --- 2단계: 'Share of Voice' 및 최종 매력도 계산 ---
        if not decisions:
             return {}
        avg_price = sum(d['price'] for d in decisions.values()) / len(decisions)
        price_sensitivity = self.config.get('price_sensitivity', 2.0) # [수정] 다시 2.0 (지수)로 변경

        for name, decision in decisions.items():
            # 1. 가격 매력도 (지수 모델)
            # [수정] 0으로 나누기 방지
            price_attr = (avg_price / max(1, decision['price'])) ** price_sensitivity
            
            # 2. 마케팅 매력도 (Share of Voice)
            marketing_boost = marketing_effectiveness[name] / total_effectiveness if total_effectiveness > 0 else 0

            # 3. [핵심 수정] 최종 매력도는 '가격'과 '마케팅'의 곱
            base_attractiveness = price_attr * marketing_boost
            
            # 4. 재무 페널티 (AI 회사에만 적용)
            financial_distress_multiplier = 1.0
            if name in self.ai_company_names:
                current_capital = self.companies[name]['accumulated_profit']
                if current_capital < 0:
                    debt_ratio = abs(current_capital) / self.config['initial_capital']
                    penalty = debt_ratio * 0.5 
                    financial_distress_multiplier = max(0.5, 1.0 - penalty) 
                
            attractiveness[name] = base_attractiveness * financial_distress_multiplier
            
        return attractiveness

    # --- (process_turn 함수 - 기존과 동일) ---
    def process_turn(self, ai_decisions: dict):
        self.turn += 1
        print(f"\n--- Turn {self.turn} ---")
        self._apply_events() 

        active_ai_company_names = self.ai_company_names[:]
        bankrupt_company_names = []
        for name in self.ai_company_names:
            if self.companies[name]['accumulated_profit'] < 0:
                if name in active_ai_company_names:
                    active_ai_company_names.remove(name)
                    bankrupt_company_names.append(name)
        
        active_all_company_names = active_ai_company_names + self.dummy_company_names

        dummy_decisions = self._get_dummy_decisions()
        all_decisions = {**ai_decisions, **dummy_decisions}
        
        active_decisions = {
            name: all_decisions[name] 
            for name in active_all_company_names 
            if name in all_decisions
        }
        
        attractiveness = self._calculate_attractiveness(active_decisions) 
        total_attractiveness = sum(attractiveness.values())
        
        current_turn_results = {"turn": self.turn}

        for name in self.all_company_names:
            share = 0 
            if name in active_decisions:
                share = attractiveness.get(name, 0) / total_attractiveness if total_attractiveness > 0 else 0
            
            self.companies[name]['market_share'] = share
            
            if name not in all_decisions:
                continue 

            price = all_decisions[name]['price']
            marketing_spend = all_decisions[name]['marketing_spend']
            
            sales_volume = self.config['market_size'] * share
            revenue = sales_volume * price
            
            if name in bankrupt_company_names:
                print(f"!!! 턴 {self.turn}: {name} 파산. 시장에서 퇴출됩니다.")
                marketing_spend = 0 

            profit = revenue - marketing_spend - (sales_volume * self.companies[name]['unit_cost'])
            
            if name in self.ai_company_names:
                self.companies[name]['accumulated_profit'] += profit

            current_turn_results[f"{name}_price"] = price
            current_turn_results[f"{name}_marketing_spend"] = marketing_spend
            current_turn_results[f"{name}_market_share"] = share
            current_turn_results[f"{name}_profit"] = profit
            current_turn_results[f"{name}_unit_cost"] = self.companies[name]['unit_cost']
            if name in self.ai_company_names:
                current_turn_results[f"{name}_accumulated_profit"] = self.companies[name]['accumulated_profit']

        self.history.append(current_turn_results)
        return self.get_market_state()

    # --- (get_market_state 함수 - 기존과 동일) ---
    def get_market_state(self):
        state = {
            "turn": self.turn,
            "companies": {}
        }
        for name, data in self.companies.items():
            state["companies"][name] = {
                "market_share": data['market_share'],
                "unit_cost": data['unit_cost'],
                "accumulated_profit": data['accumulated_profit']
            }
        
        state["active_events"] = [
            f"{e.description} ({e.duration}턴 남음)" for e in self.active_effects
        ]
        
        if self.history:
            state["last_turn_results"] = self.history[-1]
            
        return state

    def get_history_df(self):
        return pd.DataFrame(self.history)