import math
import pandas as pd
import random # [신규] R&D 도박을 위해 추가

# [수정] 분기 보고서 생성 주기 (api_main.py와 동기화)
QUARTERLY_REPORT_INTERVAL = 4

class Event:
    def __init__(self, description, target_company, effect_type, impact_value, duration):
        self.description = description
        self.target_company = target_company
        # [수정] effect_type에 'quality_shock', 'brand_shock' 추가
        self.effect_type = effect_type 
        self.impact_value = impact_value
        self.duration = duration

    def apply(self, company_data):
        if self.effect_type == 'unit_cost_multiplier':
            company_data['unit_cost'] *= self.impact_value
        elif self.effect_type == 'quality_shock': # (예: 신제품 결함)
            company_data['product_quality'] = max(0, company_data['product_quality'] + self.impact_value) # (음수 값으로 전달)
        elif self.effect_type == 'brand_shock': # (예: 스캔들)
            company_data['brand_awareness'] = max(0, company_data['brand_awareness'] + self.impact_value)
        # (다른 이벤트 유형 추가 가능)
        return company_data

    def tick(self):
        self.duration -= 1
        return self.duration > 0


class MarketSimulator:
    def __init__(self, company_names, config):
        self.config = config
        self.ai_company_names = company_names
        self.dummy_company_names = ["Others"]
        self.all_company_names = self.ai_company_names + self.dummy_company_names

        self.companies = {}
        
        # [수정] 1턴에만 사용할 초기 예산을 config에서 읽어옴 (자본 기반)
        initial_capital = config.get("initial_capital", 0)
        initial_marketing_budget = initial_capital * config.get("initial_marketing_budget_ratio", 0.02)
        initial_rd_budget = initial_capital * config.get("initial_rd_budget_ratio", 0.01)
        
        # [수정] config에서 초기 자산 맵을 가져옴
        initial_configs = config.get("initial_configs", {})
        total_initial_share = sum(cfg.get("market_share", 0) for cfg in initial_configs.values())
        
        if total_initial_share > 1.0:
             print("경고: AI 초기 점유율 합계가 1.0을 초과합니다. 1.0으로 정규화됩니다.")
             total_initial_share = 1.0
        
        others_initial_share = 1.0 - total_initial_share

        for name in self.ai_company_names:
            cfg = initial_configs.get(name, {})
            share = cfg.get("market_share", 0)
            if total_initial_share > 1.0 and total_initial_share > 0:
                 share = share / total_initial_share

            self.companies[name] = {
                "market_share": share,
                "unit_cost": cfg.get("unit_cost", 10000),
                "accumulated_profit": initial_capital,
                "product_quality": cfg.get("product_quality", 50.0),
                "brand_awareness": cfg.get("brand_awareness", 50.0),
                "max_marketing_budget": initial_marketing_budget, # 1턴 예산
                "max_rd_budget": initial_rd_budget                # 1턴 예산
            }
            
        for name in self.dummy_company_names:
            # Others는 AI 회사들의 평균 초기값/자산을 가짐
            avg_cost = 10000
            avg_quality = 50.0
            avg_brand = 50.0
            if initial_configs:
                avg_cost = sum(cfg.get("unit_cost", 10000) for cfg in initial_configs.values()) / len(initial_configs)
                avg_quality = sum(cfg.get("product_quality", 50) for cfg in initial_configs.values()) / len(initial_configs)
                avg_brand = sum(cfg.get("brand_awareness", 50) for cfg in initial_configs.values()) / len(initial_configs)

            self.companies[name] = {
                "market_share": others_initial_share,
                "unit_cost": avg_cost,
                "accumulated_profit": 0,
                "product_quality": avg_quality,
                "brand_awareness": avg_brand,
                "max_marketing_budget": initial_marketing_budget / 2,
                "max_rd_budget": 0 
            }
        
        self.turn = 0
        self.history = []
        self.pending_event_queue = [] 
        self.active_effects = []      
        print("MarketSimulator가 성공적으로 생성되었습니다! (Level 3: Probabilistic Asset Model)")

    def inject_event(self, description, target_company, effect_type, impact_value, duration):
        event = Event(description, target_company, effect_type, impact_value, duration)
        self.pending_event_queue.append(event)
        print(f"이벤트 주입됨: {description} (대상: {target_company}, {duration}턴 지속)")

    def _apply_events(self):
        next_active_effects = []
        for event in self.active_effects:
            for name, data in self.companies.items():
                if event.target_company == "All" or event.target_company == name:
                    self.companies[name] = event.apply(data)
            
            if event.tick():
                next_active_effects.append(event)
        self.active_effects = next_active_effects
        self.active_effects.extend(self.pending_event_queue)
        self.pending_event_queue = []

    def _get_dummy_decisions(self):
        decisions = {}
        if not self.ai_company_names:
            return decisions
        avg_ai_price = 10000
        avg_ai_marketing = 1000000
        if self.history:
            last_history = self.history[-1]
            ai_prices = [last_history.get(f"{name}_price", 10000) for name in self.ai_company_names if f"{name}_price" in last_history]
            ai_marketings = [last_history.get(f"{name}_marketing_spend", 1000000) for name in self.ai_company_names if f"{name}_marketing_spend" in last_history]
            if ai_prices:
                avg_ai_price = sum(ai_prices) / len(ai_prices)
            if ai_marketings:
                avg_ai_marketing = sum(ai_marketings) / len(ai_marketings)

        for name in self.dummy_company_names:
            budget = self.companies[name].get('max_marketing_budget', avg_ai_marketing * 0.8)
            decisions[name] = {
                "price": avg_ai_price * 0.95,
                "marketing_spend": min(avg_ai_marketing * 0.8, budget),
                "marketing_brand_spend": min(avg_ai_marketing * 0.8, budget),
                "marketing_promo_spend": 0,
                "rd_spend": 0,
                "rd_innovation_spend": 0,
                "rd_efficiency_spend": 0
            }
        return decisions

    # [수정] _calculate_value_scores (핵심 물리 법칙)
    def _calculate_value_scores(self, decisions: dict):
        value_scores = {}
        
        if not decisions:
            return {}
            
        avg_price = sum(d['price'] for d in decisions.values()) / len(decisions)

        for name, data in self.companies.items():
            if name not in decisions:
                continue

            quality = data.get("product_quality", 50.0)
            brand = data.get("brand_awareness", 50.0)
            price = decisions[name].get("price", avg_price)
            
            # [신규] 프로모션(단기 할인) 효과 적용
            promo_spend = decisions[name].get("marketing_promo_spend", 0)
            # (매우 단순한 예시: 프로모션 100만당 1% 가격 할인 효과)
            promo_discount_factor = 1.0 - (promo_spend / 100000000) # (최대 10% 할인 가정)
            effective_price = price * max(0.9, promo_discount_factor)

            price_competitiveness = (avg_price / max(effective_price, 1)) * 50 
            
            # [수정] 가치 점수 공식 (가중치)
            quality_weight = 0.5
            brand_weight = 0.3
            price_weight = 0.2
            
            value = (quality * quality_weight) + \
                    (brand * brand_weight) + \
                    (price_competitiveness * price_weight)
            
            value_scores[name] = max(0.1, value) # (점수가 0이 되는 것 방지)
            
        return value_scores

    # --- process_turn 함수 (엔진 재설계) ---
    def process_turn(self, ai_decisions: dict):
        self.turn += 1
        print(f"\n--- Turn {self.turn} ---")
        
        # --- 1. 거시 경제 적용 (외부 변수) ---
        inflation = self.config.get("inflation_rate", 0.0)
        gdp_growth = self.config.get("gdp_growth_rate", 0.0)
        
        self.config['market_size'] *= (1 + gdp_growth)
        for name in self.all_company_names:
            self.companies[name]['unit_cost'] *= (1 + inflation)

        # --- 2. 자산 감가상각 (Asset Decay) 적용 ---
        quality_decay = self.config.get("quality_decay_rate", 0.5)
        brand_decay = self.config.get("brand_decay_rate", 0.2)
        for name in self.all_company_names:
            self.companies[name]['product_quality'] = max(0, self.companies[name]['product_quality'] - quality_decay)
            self.companies[name]['brand_awareness'] = max(0, self.companies[name]['brand_awareness'] - brand_decay)

        # --- 3. 이벤트 적용 ---
        self._apply_events() 

        # --- 4. 파산 로직 ---
        active_ai_company_names = self.ai_company_names[:]
        bankrupt_company_names = []
        for name in self.ai_company_names:
            if self.companies[name]['accumulated_profit'] < - (self.config.get("initial_capital", 0) * 0.5): 
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

        # --- 5. AI 지출로 인한 '자산' 업데이트 (R&D 도박 / 마케팅 수확 체감) ---
        
        # R&D 도박 변수
        rd_inno_cost = self.config.get("rd_innovation_cost", 2000000)
        rd_inno_prob = self.config.get("rd_innovation_prob", 0.3)
        rd_inno_impact = self.config.get("rd_innovation_impact", 5.0)
        rd_eff_cost = self.config.get("rd_efficiency_cost", 2000000)
        rd_eff_prob = self.config.get("rd_efficiency_prob", 0.2)
        rd_eff_impact = self.config.get("rd_efficiency_impact", 0.03)

        # 마케팅 수확 체감 변수
        mkt_base = self.config.get("marketing_cost_base", 100000)
        mkt_mult = self.config.get("marketing_cost_multiplier", 1.12)

        for name in active_ai_company_names:
            # (R&D 도박 실행)
            spend_rd_inno = active_decisions[name].get('rd_innovation_spend', 0)
            num_bets_inno = math.floor(spend_rd_inno / rd_inno_cost)
            for _ in range(num_bets_inno):
                if random.random() < rd_inno_prob:
                    self.companies[name]['product_quality'] += rd_inno_impact
                    print(f"*** {name} 품질 R&D 성공! (품질 +{rd_inno_impact}) ***")
            
            spend_rd_eff = active_decisions[name].get('rd_efficiency_spend', 0)
            num_bets_eff = math.floor(spend_rd_eff / rd_eff_cost)
            for _ in range(num_bets_eff):
                if random.random() < rd_eff_prob:
                    self.companies[name]['unit_cost'] *= (1.0 - rd_eff_impact)
                    print(f"*** {name} 원가 R&D 성공! (원가 -{rd_eff_impact*100}%) ***")
            
            # (마케팅 투자 -> 브랜드 상승 - 수확 체감 적용)
            spend_mkt_brand = active_decisions[name].get('marketing_brand_spend', 0)
            current_brand = self.companies[name]['brand_awareness']
            cost_per_point_mkt = mkt_base * (mkt_mult ** current_brand) # 점수가 높을수록 1점 올리기 비쌈
            points_gained_mkt = spend_mkt_brand / max(cost_per_point_mkt, 1)
            
            self.companies[name]['product_quality'] = min(100, self.companies[name]['product_quality'])
            self.companies[name]['brand_awareness'] = min(100, current_brand + points_gained_mkt)

        # --- 6. '가치 점수' 기반 시장 점유율 계산 ---
        value_scores = self._calculate_value_scores(active_decisions)
        total_value = sum(value_scores.values())

        current_turn_results = {"turn": self.turn}

        for name in self.all_company_names:
            
            if name in active_decisions:
                share = value_scores.get(name, 0) / total_value if total_value > 0 else 0
            else:
                share = 0
                
            self.companies[name]['market_share'] = share
            
            if name not in all_decisions:
                current_turn_results[f"{name}_price"] = 0
                current_turn_results[f"{name}_marketing_spend"] = 0
                current_turn_results[f"{name}_rd_spend"] = 0
                current_turn_results[f"{name}_revenue"] = 0
                current_turn_results[f"{name}_profit"] = 0
                current_turn_results[f"{name}_unit_cost"] = self.companies[name]['unit_cost']
                current_turn_results[f"{name}_market_share"] = share
                current_turn_results[f"{name}_accumulated_profit"] = self.companies[name]['accumulated_profit']
                current_turn_results[f"{name}_product_quality"] = self.companies[name]['product_quality']
                current_turn_results[f"{name}_brand_awareness"] = self.companies[name]['brand_awareness']
                current_turn_results[f"{name}_marketing_brand_spend"] = 0
                current_turn_results[f"{name}_marketing_promo_spend"] = 0
                current_turn_results[f"{name}_rd_innovation_spend"] = 0
                current_turn_results[f"{name}_rd_efficiency_spend"] = 0
                continue 

            price = all_decisions[name]['price']
            # (총 지출액 기록)
            marketing_spend = active_decisions[name].get('marketing_spend', 0)
            rd_spend = active_decisions[name].get('rd_spend', 0)

            mkt_brand = all_decisions[name].get('marketing_brand_spend', 0)
            mkt_promo = all_decisions[name].get('marketing_promo_spend', 0)
            rd_inno = all_decisions[name].get('rd_innovation_spend', 0)
            rd_eff = all_decisions[name].get('rd_efficiency_spend', 0)
            
            sales_volume = self.config['market_size'] * share
            revenue = sales_volume * price
            
            if name in bankrupt_company_names:
                print(f"!!! 턴 {self.turn}: {name} 파산. 시장에서 퇴출됩니다.")
                marketing_spend = 0 
                rd_spend = 0

            profit = revenue - marketing_spend - rd_spend - (sales_volume * self.companies[name]['unit_cost'])
            
            if name in self.ai_company_names:
                self.companies[name]['accumulated_profit'] += profit

            current_turn_results[f"{name}_price"] = price
            current_turn_results[f"{name}_marketing_spend"] = marketing_spend
            current_turn_results[f"{name}_rd_spend"] = rd_spend
            current_turn_results[f"{name}_revenue"] = revenue
            current_turn_results[f"{name}_profit"] = profit
            current_turn_results[f"{name}_unit_cost"] = self.companies[name]['unit_cost']
            current_turn_results[f"{name}_market_share"] = share
            current_turn_results[f"{name}_accumulated_profit"] = self.companies[name]['accumulated_profit']
            current_turn_results[f"{name}_product_quality"] = self.companies[name]['product_quality']
            current_turn_results[f"{name}_brand_awareness"] = self.companies[name]['brand_awareness']
            current_turn_results[f"{name}_marketing_brand_spend"] = mkt_brand
            current_turn_results[f"{name}_marketing_promo_spend"] = mkt_promo
            current_turn_results[f"{name}_rd_innovation_spend"] = rd_inno
            current_turn_results[f"{name}_rd_efficiency_spend"] = rd_eff

        self.history.append(current_turn_results)

        # --- 7. (하이브리드 예산 업데이트) ---
        
        # (매 턴, 총 자본 기반 R&D 예산 업데이트)
        for name in self.ai_company_names:
            current_capital = self.companies[name]['accumulated_profit']
            if current_capital > 0:
                self.companies[name]['max_rd_budget'] = max(500_000, current_capital * 0.01) # 총 자본의 1%
            else:
                self.companies[name]['max_rd_budget'] = 500_000 

        # (매 분기 말, 지난 분기 이익 기반 마케팅 예산 업데이트)
        if self.turn > 0 and self.turn % QUARTERLY_REPORT_INTERVAL == 0:
            start_index = max(0, self.turn - QUARTERLY_REPORT_INTERVAL)
            quarterly_history = self.history[start_index : self.turn]
            
            print(f"--- [Turn {self.turn}] 분기 결산 및 다음 분기 마케팅 예산 재조정 ---")

            for name in self.ai_company_names:
                last_quarter_profit = sum(h.get(f"{name}_profit", 0) for h in quarterly_history)
                
                if last_quarter_profit > 0:
                    self.companies[name]['max_marketing_budget'] = max(1_000_000, last_quarter_profit * 0.1) # 분기 이익의 10%
                else:
                    self.companies[name]['max_marketing_budget'] = 1_000_000 
                
                print(f"  [{name}] 지난 분기 이익: {last_quarter_profit:,.0f} -> 다음 분기 Mkt 예산: {self.companies[name]['max_marketing_budget']:,.0f}")
                print(f"  [{name}] (참고) 현재 총 자본: {self.companies[name]['accumulated_profit']:,.0f} -> 다음 턴 R&D 예산: {self.companies[name]['max_rd_budget']:,.0f}")

        return self.get_market_state()
    
    def get_company_state(self, name: str) -> dict:
        """특정 회사의 현재 상태(자산 포함)를 반환합니다. (정보 지연용)"""
        if name in self.companies:
            return self.companies[name]
        return {}

    def get_market_state(self):
        state = {
            "turn": self.turn,
            "config": {
                "market_size": self.config.get("market_size"),
                "gdp_growth_rate": self.config.get("gdp_growth_rate"),
                "inflation_rate": self.config.get("inflation_rate"),
                "quality_decay_rate": self.config.get("quality_decay_rate"),
                "brand_decay_rate": self.config.get("brand_decay_rate"),
                # [신규] R&D 도박 비용/확률 정보 제공
                "rd_innovation_cost": self.config.get("rd_innovation_cost"),
                "rd_innovation_prob": self.config.get("rd_innovation_prob"),
                "rd_efficiency_cost": self.config.get("rd_efficiency_cost"),
                "rd_efficiency_prob": self.config.get("rd_efficiency_prob"),
            },
            "companies": {}
        }
        for name, data in self.companies.items():
            state["companies"][name] = {
                "market_share": data['market_share'],
                "unit_cost": data['unit_cost'],
                "accumulated_profit": data['accumulated_profit'],
                "product_quality": data.get('product_quality', 50.0),
                "brand_awareness": data.get('brand_awareness', 50.0),
                "max_marketing_budget": data.get('max_marketing_budget', 1000000),
                "max_rd_budget": data.get('max_rd_budget', 500000)
            }
        
        state["active_events"] = [
            f"{e.description} ({e.duration}턴 남음)" for e in self.active_effects
        ]
        
        if self.history:
            state["last_turn_results"] = self.history[-1]
            
        return state

    def get_history_df(self):
        return pd.DataFrame(self.history)