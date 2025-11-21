import math
import pandas as pd

# 분기 보고서 생성 주기
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
        
        initial_capital = config.get("initial_capital", 0)
        initial_marketing_budget = initial_capital * config.get("initial_marketing_budget_ratio", 0.02)
        initial_rd_budget = initial_capital * config.get("initial_rd_budget_ratio", 0.01)
        
        initial_configs = config.get("initial_configs", {})
        total_initial_share = sum(cfg.get("market_share", 0) for cfg in initial_configs.values())
        
        if total_initial_share > 1.0:
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
                "max_marketing_budget": initial_marketing_budget,
                "max_rd_budget": initial_rd_budget,
                "accumulated_rd_innovation_point": 0.0,
                "accumulated_rd_efficiency_point": 0.0
            }
            
        for name in self.dummy_company_names:
            avg_cost = 10000
            avg_quality = 50.0
            avg_brand = 50.0
            if initial_configs:
                avg_vals = initial_configs.values()
                avg_cost = sum(c.get("unit_cost", 10000) for c in avg_vals) / len(avg_vals)
                avg_quality = sum(c.get("product_quality", 50) for c in avg_vals) / len(avg_vals)
                avg_brand = sum(c.get("brand_awareness", 50) for c in avg_vals) / len(avg_vals)

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
        # print("MarketSimulator Initialized.")

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
        avg_ai_price = 10000
        avg_ai_marketing = 1000000
        if self.history:
            last = self.history[-1]
            prices = [last.get(f"{n}_price", 10000) for n in self.ai_company_names]
            mkts = [last.get(f"{n}_marketing_spend", 1000000) for n in self.ai_company_names]
            if prices: avg_ai_price = sum(prices) / len(prices)
            if mkts: avg_ai_marketing = sum(mkts) / len(mkts)

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

    # [수정됨] 정규화(Normalization) 및 로짓 스케일링 적용
    def _calculate_utility_scores(self, decisions: dict):
        utility_scores = {}
        if not decisions:
            return {}
            
        avg_price = sum(d['price'] for d in decisions.values()) / len(decisions)
        
        physics = self.config.get('physics', {})
        w_quality = physics.get('weight_quality', 0.4)
        w_brand = physics.get('weight_brand', 0.4)
        w_price = physics.get('weight_price', 0.2)
        sensitivity = physics.get('price_sensitivity', 50.0)
        others_competitiveness = physics.get('others_overall_competitiveness', 1.0)

        for name, data in self.companies.items():
            if name not in decisions:
                continue

            # [변경] 품질/브랜드 점수를 0~10 스케일로 정규화 (기존 0~100)
            # 이렇게 해야 exp() 계산 시 값이 너무 커지지 않음
            quality_score = data.get("product_quality", 50.0) / 10.0
            brand_score = data.get("brand_awareness", 50.0) / 10.0
            
            price = decisions[name].get("price", avg_price)
            promo_spend = decisions[name].get("marketing_promo_spend", 0)
            promo_discount_factor = 1.0 - (promo_spend / 100000000) 
            effective_price = price * max(0.9, promo_discount_factor)

            # [변경] 가격 점수 계산: 로그 스케일 사용 (작은 차이도 민감하게)
            # (평균 / 내 가격) 비율이 1.0이면 0점, 1.1이면 +점수
            # sensitivity가 50이면 -> 10% 쌀 때 약 +5점 효용
            if effective_price > 0:
                price_ratio = avg_price / effective_price
                # 로그를 취해 선형적으로 변환 후 민감도 곱함
                price_score = math.log(price_ratio) * (sensitivity / 5.0) # 스케일 조정 (나누기 5)
            else:
                price_score = 0

            # 총 효용 (Utility)
            # 이제 모든 점수가 대략 -5 ~ +10 사이에서 움직임
            utility = (quality_score * w_quality) + \
                      (brand_score * w_brand) + \
                      (price_score * w_price)
            
            if name == "Others":
                # Others 점수 부스트 (1.0이면 그대로, 1.5면 50% 증폭)
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
                price = inputs.get("price", 20000)
                current_share = self.companies[name]['market_share']
                if current_share <= 0: current_share = 0.1 
                estimated_revenue = self.config['market_size'] * current_share * price
                marketing_spend = estimated_revenue * inputs.get("marketing_spend_ratio", 0.02)
                rd_spend = estimated_revenue * inputs.get("rd_spend_ratio", 0.01)
                forced_decisions[name] = {
                    "price": price, "marketing_spend": marketing_spend, "marketing_brand_spend": marketing_spend, 
                    "marketing_promo_spend": 0, "rd_spend": rd_spend, "rd_innovation_spend": rd_spend * 0.5,
                    "rd_efficiency_spend": rd_spend * 0.5
                }
            else:
                forced_decisions[name] = dummy_decisions.get(name, {})
        all_decisions = {**forced_decisions, **dummy_decisions}
        return self._process_turn_internal(all_decisions, is_benchmark=True, benchmark_truth=companies_data)

    def _process_turn_internal(self, all_decisions: dict, is_benchmark: bool = False, benchmark_truth: dict = None):
        quality_decay = self.config.get("quality_decay_rate", 0.5)
        brand_decay = self.config.get("brand_decay_rate", 0.2)
        for name in self.all_company_names:
            self.companies[name]['product_quality'] = max(0, self.companies[name]['product_quality'] - quality_decay)
            self.companies[name]['brand_awareness'] = max(0, self.companies[name]['brand_awareness'] - brand_decay)

        active_ai_company_names = self.ai_company_names[:]
        bankrupt_company_names = []
        for name in self.ai_company_names:
            if self.companies[name]['accumulated_profit'] < - (self.config.get("initial_capital", 0) * 0.5): 
                if name in active_ai_company_names:
                    active_ai_company_names.remove(name)
                    bankrupt_company_names.append(name)
        
        active_all_company_names = active_ai_company_names + self.dummy_company_names
        active_decisions = {n: all_decisions[n] for n in active_all_company_names if n in all_decisions}

        rd_inno_threshold = self.config.get("rd_innovation_threshold", 5000000)
        rd_inno_impact = self.config.get("rd_innovation_impact", 5.0)
        rd_eff_threshold = self.config.get("rd_efficiency_threshold", 5000000)
        rd_eff_impact = self.config.get("rd_efficiency_impact", 0.03)
        physics = self.config.get('physics', {})
        mkt_efficiency = physics.get('marketing_efficiency', 1.0)
        mkt_base = self.config.get("marketing_cost_base", 100000)
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
            cost_per_point_mkt = mkt_base * (mkt_mult ** current_brand)
            points_gained_mkt = (spend_mkt_brand / max(cost_per_point_mkt, 1)) * mkt_efficiency
            self.companies[name]['product_quality'] = min(100, self.companies[name]['product_quality'])
            self.companies[name]['brand_awareness'] = min(100, current_brand + points_gained_mkt)

        utility_scores = self._calculate_utility_scores(active_decisions)
        if utility_scores:
            max_util = max(utility_scores.values())
            # [수정] exp 계산 시 max_util을 빼서 overflow 방지
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
            rd_spend = all_decisions[name].get('rd_spend', 0)
            sales_volume = self.config['market_size'] * share
            revenue = sales_volume * price
            if name in bankrupt_company_names: marketing_spend = 0; rd_spend = 0
            profit = revenue - marketing_spend - rd_spend - (sales_volume * self.companies[name]['unit_cost'])
            profit_margin = profit / revenue if revenue > 0 else 0.0

            if name in self.ai_company_names: self.companies[name]['accumulated_profit'] += profit

            if is_benchmark and benchmark_truth and name in benchmark_truth:
                actual_share = benchmark_truth[name]["outputs"]["actual_market_share"]
                share_error = share - actual_share
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

        for name in self.ai_company_names:
            current_capital = self.companies[name]['accumulated_profit']
            self.companies[name]['max_rd_budget'] = max(500_000, current_capital * 0.01) if current_capital > 0 else 500_000

        if self.turn > 0 and self.turn % QUARTERLY_REPORT_INTERVAL == 0:
            start_index = max(0, self.turn - QUARTERLY_REPORT_INTERVAL)
            quarterly_history = self.history[start_index : self.turn]
            for name in self.ai_company_names:
                last_quarter_profit = sum(h.get(f"{name}_profit", 0) for h in quarterly_history)
                self.companies[name]['max_marketing_budget'] = max(1_000_000, last_quarter_profit * 0.1) if last_quarter_profit > 0 else 1_000_000

        return self.get_market_state()

    def get_company_state(self, name: str) -> dict:
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
                "rd_innovation_threshold": self.config.get("rd_innovation_threshold"),
                "rd_innovation_impact": self.config.get("rd_innovation_impact"),
                "rd_efficiency_threshold": self.config.get("rd_efficiency_threshold"),
                "rd_efficiency_impact": self.config.get("rd_efficiency_impact"),
                "physics": self.config.get("physics", {})
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
                "max_rd_budget": data.get('max_rd_budget', 500000),
                "accumulated_rd_innovation_point": data.get("accumulated_rd_innovation_point", 0.0),
                "accumulated_rd_efficiency_point": data.get("accumulated_rd_efficiency_point", 0.0)
            }
        
        state["active_events"] = [f"{e.description} ({e.duration}턴 남음)" for e in self.active_effects]
        if self.history:
            state["last_turn_results"] = self.history[-1]
            
        return state

    def get_history_df(self):
        return pd.DataFrame(self.history)