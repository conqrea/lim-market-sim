import math
import pandas as pd

QUARTERLY_REPORT_INTERVAL = 4

class Event:
    def __init__(self, description, target_company, effect_type, impact_value, duration):
        self.description = description
        self.target_company = target_company
        self.effect_type = effect_type 
        self.impact_value = impact_value
        self.duration = duration

    def apply(self, company_data):
        if self.effect_type == 'unit_cost_multiplier':
            company_data['unit_cost'] *= self.impact_value
        elif self.effect_type == 'quality_shock':
            company_data['product_quality'] = max(0, company_data['product_quality'] + self.impact_value)
        elif self.effect_type == 'brand_shock':
            company_data['brand_awareness'] = max(0, company_data['brand_awareness'] + self.impact_value)
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
        
        # 1. 초기 자본금 및 시장 규모 가져오기
        initial_capital = config.get("initial_capital", 0)
        market_size = config.get("market_size", 10000)
        
        # 2. [핵심 수정] 하드코딩 제거 & 동적 스케일링
        # Config에 값이 없으면, 자본금의 일정 비율로 '물리 상수'를 자동 설정합니다.
        if not self.config.get("marketing_cost_base"):
            self.config["marketing_cost_base"] = initial_capital * 0.00005 if initial_capital > 0 else 1000
            
        if not self.config.get("rd_innovation_threshold"):
            self.config["rd_innovation_threshold"] = initial_capital * 0.005 if initial_capital > 0 else 50000

        if not self.config.get("rd_efficiency_threshold"):
            self.config["rd_efficiency_threshold"] = initial_capital * 0.005 if initial_capital > 0 else 50000

        # 초기 예산 설정 (자본금 비례)
        initial_marketing_budget = initial_capital * config.get("initial_marketing_budget_ratio", 0.02)
        initial_rd_budget = initial_capital * config.get("initial_rd_budget_ratio", 0.01)
        
        initial_configs = config.get("initial_configs", {})
        total_initial_share = sum(cfg.get("market_share", 0) for cfg in initial_configs.values())
        
        if total_initial_share > 1.0:
             total_initial_share = 1.0
        others_initial_share = 1.0 - total_initial_share

        # AI 기업 초기화
        for name in self.ai_company_names:
            cfg = initial_configs.get(name, {})
            share = cfg.get("market_share", 0)
            if total_initial_share > 1.0 and total_initial_share > 0:
                 share = share / total_initial_share

            # [수정] 원가(unit_cost) 기본값을 10000이 아니라 자본금 비례로 작게 설정
            default_cost = initial_capital * 0.0000001 if initial_capital > 0 else 100
            if default_cost < 1: default_cost = 100 

            self.companies[name] = {
                "market_share": share,
                "unit_cost": cfg.get("unit_cost", default_cost),
                "accumulated_profit": initial_capital,
                "product_quality": cfg.get("product_quality", 50.0),
                "brand_awareness": cfg.get("brand_awareness", 50.0),
                "max_marketing_budget": initial_marketing_budget,
                "max_rd_budget": initial_rd_budget,
                "accumulated_rd_innovation_point": 0.0,
                "accumulated_rd_efficiency_point": 0.0
            }
            
        # Others(더미) 기업 초기화 - 평균 원가 기반
        avg_cost = 100
        avg_quality = 50.0
        avg_brand = 50.0

        if self.ai_company_names:
            ai_count = len(self.ai_company_names)
            avg_cost = sum(self.companies[n]["unit_cost"] for n in self.ai_company_names) / ai_count
            avg_quality = sum(self.companies[n]["product_quality"] for n in self.ai_company_names) / ai_count
            avg_brand = sum(self.companies[n]["brand_awareness"] for n in self.ai_company_names) / ai_count

        for name in self.dummy_company_names:
            self.companies[name] = {
                "market_share": others_initial_share,
                "unit_cost": avg_cost,
                "accumulated_profit": 0,
                "product_quality": avg_quality, 
                "brand_awareness": avg_brand,
                "max_marketing_budget": initial_marketing_budget / 2,
                "max_rd_budget": 0,
                "accumulated_rd_innovation_point": 0.0,
                "accumulated_rd_efficiency_point": 0.0
            }
        
        self.turn = 0
        self.history = []
        self.pending_event_queue = [] 
        self.active_effects = []

    def inject_event(self, description, target_company, effect_type, impact_value, duration):
        event = Event(description, target_company, effect_type, impact_value, duration)
        self.pending_event_queue.append(event)

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
        
        # [수정] 더미 의사결정도 '현재 시장 상황'에 비례하도록 수정 (10000원 하드코딩 제거)
        avg_cost = sum(self.companies[n]["unit_cost"] for n in self.ai_company_names) / len(self.ai_company_names)
        
        # 기본 가격은 원가의 1.2배 (20% 마진)
        estimated_market_price = avg_cost * 1.2 
        
        # 기록이 있다면 지난 턴 AI 평균 가격을 참고
        if self.history:
            last = self.history[-1]
            prices = [last.get(f"{n}_price", 0) for n in self.ai_company_names if last.get(f"{n}_price", 0) > 0]
            if prices: 
                estimated_market_price = sum(prices) / len(prices)

        # 마케팅비는 AI 평균 예산의 80% 수준
        avg_ai_budget = self.companies[self.ai_company_names[0]]['max_marketing_budget']

        for name in self.dummy_company_names:
            budget = self.companies[name].get('max_marketing_budget', avg_ai_budget * 0.8)
            decisions[name] = {
                "price": estimated_market_price * 0.95, # AI보다 약간 싸게 팜
                "marketing_spend": budget,
                "marketing_brand_spend": budget,
                "marketing_promo_spend": 0,
                "rd_spend": 0,
                "rd_innovation_spend": 0,
                "rd_efficiency_spend": 0
            }
        return decisions

    def _calculate_utility_scores(self, decisions: dict):
        utility_scores = {}
        if not decisions:
            return {}
            
        avg_price = sum(d['price'] for d in decisions.values()) / len(decisions)
        if avg_price == 0: avg_price = 1 # 0 나누기 방지
        
        physics = self.config.get('physics', {})
        w_quality = physics.get('weight_quality', 0.4)
        w_brand = physics.get('weight_brand', 0.4)
        w_price = physics.get('weight_price', 0.2)
        sensitivity = physics.get('price_sensitivity', 50.0)
        others_competitiveness = physics.get('others_overall_competitiveness', 1.0)

        for name, data in self.companies.items():
            if name not in decisions:
                continue

            # 정규화 (0~10 스케일)
            quality_score = data.get("product_quality", 50.0) / 10.0
            brand_score = data.get("brand_awareness", 50.0) / 10.0
            
            price = decisions[name].get("price", avg_price)
            if price <= 0: price = avg_price

            promo_spend = decisions[name].get("marketing_promo_spend", 0)
            # 마케팅 효율 베이스 값 (하드코딩 방지)
            mkt_base = self.config.get("marketing_cost_base", 1000)
            promo_discount_factor = 1.0 - (promo_spend / (mkt_base * 2000)) # 스케일링 조정
            effective_price = price * max(0.9, promo_discount_factor)

            if effective_price > 0:
                price_ratio = avg_price / effective_price
                price_score = math.log(price_ratio) * (sensitivity / 5.0) 
            else:
                price_score = 0

            utility = (quality_score * w_quality) + \
                      (brand_score * w_brand) + \
                      (price_score * w_price)
            
            if name == "Others":
                utility *= others_competitiveness

            utility_scores[name] = utility
            
        return utility_scores

    def process_turn(self, ai_decisions: dict):
        dummy_decisions = self._get_dummy_decisions()
        all_decisions = {**ai_decisions, **dummy_decisions}
        self.turn += 1
        print(f"\n--- Turn {self.turn} (Standard) ---")
        inflation = self.config.get("inflation_rate", 0.0)
        gdp_growth = self.config.get("gdp_growth_rate", 0.0)
        self.config['market_size'] *= (1 + gdp_growth)
        for name in self.all_company_names: self.companies[name]['unit_cost'] *= (1 + inflation)
        self._apply_events()
        return self._process_turn_internal(all_decisions, is_benchmark=False)

    def run_benchmark_turn(self, turn_data: dict):
        self.turn = turn_data["turn"]
        macro = turn_data.get("macro", {})
        gdp_growth = macro.get("gdp_growth", 0.0)
        inflation = macro.get("inflation", 0.0)
        self.config['market_size'] *= (1 + gdp_growth)
        for name in self.all_company_names: self.companies[name]['unit_cost'] *= (1 + inflation)
        self._apply_events()
        
        forced_decisions = {}
        companies_data = turn_data.get("companies", {})
        dummy_decisions = self._get_dummy_decisions()
        
        for name in self.ai_company_names:
            if name in companies_data:
                inputs = companies_data[name]["inputs"]
                price = inputs.get("price", 0)
                
                # [수정] 벤치마크 데이터에 가격이 누락되었을 경우 하드코딩(20000) 대신 원가 기반 추정
                if price <= 0:
                    current_cost = self.companies[name]['unit_cost']
                    price = current_cost * 1.2 if current_cost > 0 else 100

                current_share = self.companies[name]['market_share']
                if current_share <= 0: current_share = 0.1 
                estimated_revenue = self.config['market_size'] * current_share * price
                marketing_spend = estimated_revenue * inputs.get("marketing_spend_ratio", 0.02)
                rd_spend = estimated_revenue * inputs.get("rd_spend_ratio", 0.01)
                
                forced_decisions[name] = {
                    "price": price, 
                    "marketing_spend": marketing_spend, "marketing_brand_spend": marketing_spend, 
                    "marketing_promo_spend": 0, "rd_spend": rd_spend, 
                    "rd_innovation_spend": rd_spend * 0.5, "rd_efficiency_spend": rd_spend * 0.5
                }
            else:
                forced_decisions[name] = dummy_decisions.get(name, {})
        all_decisions = {**forced_decisions, **dummy_decisions}
        return self._process_turn_internal(all_decisions, is_benchmark=True, benchmark_truth=companies_data)

    def _process_turn_internal(self, all_decisions: dict, is_benchmark: bool = False, benchmark_truth: dict = None):
        quality_decay = self.config.get("quality_decay_rate", 0.05)
        brand_decay = self.config.get("brand_decay_rate", 0.2)
        for name in self.all_company_names:
            self.companies[name]['product_quality'] = max(0, self.companies[name]['product_quality'] - quality_decay)
            self.companies[name]['brand_awareness'] = max(0, self.companies[name]['brand_awareness'] - brand_decay)

        active_ai_company_names = self.ai_company_names[:]
        bankrupt_company_names = []
        limit = - (self.config.get("initial_capital", 0) * 0.5)
        for name in self.ai_company_names:
            if self.companies[name]['accumulated_profit'] < limit: 
                if name in active_ai_company_names:
                    active_ai_company_names.remove(name)
                    bankrupt_company_names.append(name)
        
        active_all_company_names = active_ai_company_names + self.dummy_company_names
        active_decisions = {n: all_decisions[n] for n in active_all_company_names if n in all_decisions}

        # [수정] Config에서 동적으로 설정된 임계값 사용 (하드코딩 제거)
        rd_inno_threshold = self.config.get("rd_innovation_threshold", 50000)
        rd_eff_threshold = self.config.get("rd_efficiency_threshold", 50000)
        
        rd_inno_impact = self.config.get("rd_innovation_impact", 5.0)
        rd_eff_impact = self.config.get("rd_efficiency_impact", 0.03)
        
        physics = self.config.get('physics', {})
        mkt_efficiency = physics.get('marketing_efficiency', 1.0)
        
        mkt_base = self.config.get("marketing_cost_base", 1000)
        mkt_mult = self.config.get("marketing_cost_multiplier", 1.12)

        for name in active_ai_company_names:
            spend_rd_inno = active_decisions[name].get('rd_innovation_spend', 0)
            self.companies[name]['accumulated_rd_innovation_point'] += spend_rd_inno
            if self.companies[name]['accumulated_rd_innovation_point'] >= rd_inno_threshold:
                self.companies[name]['product_quality'] += rd_inno_impact
                self.companies[name]['accumulated_rd_innovation_point'] -= rd_inno_threshold
                if not is_benchmark: print(f"*** {name} 품질 혁신 달성! ***")

            spend_rd_eff = active_decisions[name].get('rd_efficiency_spend', 0)
            self.companies[name]['accumulated_rd_efficiency_point'] += spend_rd_eff
            if self.companies[name]['accumulated_rd_efficiency_point'] >= rd_eff_threshold:
                self.companies[name]['unit_cost'] *= (1.0 - rd_eff_impact)
                self.companies[name]['accumulated_rd_efficiency_point'] -= rd_eff_threshold
                if not is_benchmark: print(f"*** {name} 원가 혁신 달성! ***")
            
            spend_mkt_brand = active_decisions[name].get('marketing_brand_spend', 0)
            current_brand = self.companies[name]['brand_awareness']
            cost_per_point_mkt = mkt_base * (mkt_mult ** (current_brand/10)) # 스케일링 조정
            points_gained_mkt = (spend_mkt_brand / max(cost_per_point_mkt, 1)) * mkt_efficiency
            self.companies[name]['product_quality'] = min(100, self.companies[name]['product_quality'])
            self.companies[name]['brand_awareness'] = min(100, current_brand + points_gained_mkt)

        utility_scores = self._calculate_utility_scores(active_decisions)
        if utility_scores:
            max_util = max(utility_scores.values())
            exp_scores = {k: math.exp(v - max_util) for k, v in utility_scores.items()}
            total_exp = sum(exp_scores.values())
        else:
            exp_scores = {}; total_exp = 0

        current_turn_results = {"turn": self.turn}
        total_composite_error = 0.0
        sim_ranks = []; real_ranks = []

        for name in self.all_company_names:
            if name in active_decisions and total_exp > 0:
                share = exp_scores[name] / total_exp
            else: share = 0
            self.companies[name]['market_share'] = share
            
            if name not in all_decisions: continue 

            price = all_decisions[name]['price']
            marketing_spend = all_decisions[name].get('marketing_spend', 0)
            if marketing_spend == 0:
                marketing_spend = all_decisions[name].get('marketing_brand_spend', 0) + all_decisions[name].get('marketing_promo_spend', 0)
                
            rd_spend = all_decisions[name].get('rd_spend', 0)
            if rd_spend == 0:
                rd_spend = all_decisions[name].get('rd_innovation_spend', 0) + all_decisions[name].get('rd_efficiency_spend', 0)

            sales_volume = self.config['market_size'] * share
            revenue = sales_volume * price
            
            if name in bankrupt_company_names: 
                marketing_spend = 0; rd_spend = 0
            
            profit = revenue - marketing_spend - rd_spend - (sales_volume * self.companies[name]['unit_cost'])
            profit_margin = profit / revenue if revenue > 0 else 0.0

            if name in self.ai_company_names: self.companies[name]['accumulated_profit'] += profit

            if is_benchmark and benchmark_truth and name in benchmark_truth:
                actual_share = benchmark_truth[name]["outputs"]["actual_market_share"]
                share_error = share - actual_share
                
                # [수정] 벤치마크 결과에 실제 이익 데이터도 포함 (프론트엔드 그래프용)
                current_turn_results[f"{name}_actual_accumulated_profit"] = benchmark_truth[name]["outputs"].get("actual_accumulated_profit", 0)
                
                actual_margin = benchmark_truth[name]["outputs"].get("actual_profit_margin", None)
                margin_error = 0.0
                if actual_margin is not None: margin_error = profit_margin - actual_margin
                composite_error = (abs(share_error) * 0.7) + (abs(margin_error) * 0.3)
                total_composite_error += composite_error
                current_turn_results[f"{name}_error"] = share_error
                sim_ranks.append((name, share))
                real_ranks.append((name, actual_share))

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
            current_turn_results[f"{name}_marketing_brand_spend"] = all_decisions[name].get('marketing_brand_spend', 0)
            current_turn_results[f"{name}_marketing_promo_spend"] = all_decisions[name].get('marketing_promo_spend', 0)
            current_turn_results[f"{name}_rd_innovation_spend"] = all_decisions[name].get('rd_innovation_spend', 0)
            current_turn_results[f"{name}_rd_efficiency_spend"] = all_decisions[name].get('rd_efficiency_spend', 0)
            current_turn_results[f"{name}_accumulated_rd_innovation_point"] = self.companies[name]['accumulated_rd_innovation_point']
            current_turn_results[f"{name}_accumulated_rd_efficiency_point"] = self.companies[name]['accumulated_rd_efficiency_point']

        if is_benchmark and sim_ranks:
            sim_ranks.sort(key=lambda x: x[1], reverse=True)
            real_ranks.sort(key=lambda x: x[1], reverse=True)
            if sim_ranks[0][0] != real_ranks[0][0]: total_composite_error += 0.1
            current_turn_results["total_error_mae"] = total_composite_error / len(sim_ranks)

        self.history.append(current_turn_results)

        # 예산 갱신
        for name in self.ai_company_names:
            current_capital = self.companies[name]['accumulated_profit']
            # 자본금 비례 최소 예산 설정 (1000원 아님)
            base_budget = max(100, current_capital * 0.01) if current_capital > 0 else 100
            self.companies[name]['max_rd_budget'] = base_budget
            self.companies[name]['max_marketing_budget'] = base_budget * 2

        if self.turn > 0 and self.turn % QUARTERLY_REPORT_INTERVAL == 0:
            pass 

        return self.get_market_state()

    def get_company_state(self, name: str) -> dict:
        if name in self.companies:
            return self.companies[name]
        return {}

    def get_market_state(self):
        state = {
            "turn": self.turn,
            "config": self.config,
            "companies": {}
        }
        for name, data in self.companies.items():
            state["companies"][name] = data.copy()
        
        state["active_events"] = [f"{e.description} ({e.duration}턴 남음)" for e in self.active_effects]
        if self.history:
            state["last_turn_results"] = self.history[-1]
            
        return state

    def get_history_df(self):
        return pd.DataFrame(self.history)