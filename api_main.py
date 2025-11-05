import asyncio
import uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict
from fastapi.middleware.cors import CORSMiddleware

from simulator import MarketSimulator
from agent import AIAgent

# [수정] 분기 보고서 생성 주기 (simulator.py와 동기화)
QUARTERLY_REPORT_INTERVAL = 4

app = FastAPI(
    title="AI Strategy Lab API (Level 3: Probabilistic Asset Model)",
    description="무형 자산(품질/브랜드), 자산 감가상각, R&D 도박(확률), 하이브리드 예산 법칙이 적용된 최종 엔진입니다."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 인메모리 저장소 ---
active_simulations = {}

# --- Pydantic 모델 수정 ---
class CompanyConfig(BaseModel):
    name: str = Field(..., example="GM")
    persona: str = Field(..., example="R&D는 최소화하고 마케팅/고수익에 집중합니다.")
    
    # [수정] '프록시 데이터' 기반 초기값
    initial_unit_cost: int = Field(..., example=10000) 
    initial_market_share: float = Field(..., ge=0, le=1.0, example=0.35)
    initial_product_quality: float = Field(..., ge=0, le=100.0, example=60.0, description="초기 제품 품질 (프록시 데이터 기반, 0-100점)")
    initial_brand_awareness: float = Field(..., ge=0, le=100.0, example=70.0, description="초기 브랜드 인지도 (프록시 데이터 기반, 0-100점)")

class SimulationConfig(BaseModel):
    companies: List[CompanyConfig]
    total_turns: int = Field(30, gt=0)
    market_size: int = Field(10000, gt=0)
    initial_capital: int = Field(1000000000)
    
    # [수정] 1턴에만 사용할 초기 예산 '비율' (자본 기반)
    initial_marketing_budget_ratio: float = Field(0.02, gt=0, description="초기 자본 대비 1턴 마케팅 예산 비율 (예: 2%)")
    initial_rd_budget_ratio: float = Field(0.01, gt=0, description="초기 자본 대비 1턴 R&D 예산 비율 (예: 1%)")

    # [수정] 거시 경제 (외부 변수)
    gdp_growth_rate: float = Field(0.005, description="턴(분기)당 시장 규모 성장률 (예: 0.5% = 연 2%)")
    inflation_rate: float = Field(0.0075, description="턴(분기)당 원가 상승률 (예: 0.75% = 연 3%)")
    
    # [수정] 'R&D 도박' 변수 (R&D Gamble)
    rd_innovation_cost: float = Field(2000000, description="품질(Innovation) R&D 1회 '베팅' 비용")
    rd_innovation_prob: float = Field(0.3, description="품질 R&D '베팅' 1회당 성공 확률 (예: 30%)")
    rd_innovation_impact: float = Field(5.0, description="품질 R&D 성공 시 상승하는 '제품 품질' 점수")
    
    rd_efficiency_cost: float = Field(2000000, description="원가(Efficiency) R&D 1회 '베팅' 비용")
    rd_efficiency_prob: float = Field(0.2, description="원가 R&D '베팅' 1회당 성공 확률 (예: 20%)")
    rd_efficiency_impact: float = Field(0.03, description="원가 R&D 성공 시 하락하는 '원가' 비율 (예: 3%)")

    # [수정] 마케팅 '수확 체감' 변수
    marketing_cost_base: float = Field(100000.0, description="브랜드 인지도 1포인트를 올리는 기본 비용")
    marketing_cost_multiplier: float = Field(1.12, description="브랜드 점수가 1 오를 때마다 비용이 증가하는 비율")

    # [수정] 자산 감가상각 (Decay)
    quality_decay_rate: float = Field(0.5, description="턴(분기)당 하락하는 제품 품질 점수 (기술 도태)")
    brand_decay_rate: float = Field(0.2, description="턴(분기)당 하락하는 브랜드 인지도 점수 (망각)")

class EventInject(BaseModel):
    description: str = Field(..., example="공급망 이슈로 원가 20% 상승")
    target_company: str = Field("All", example="Apple")
    effect_type: str = Field(..., example="unit_cost_multiplier") # 'quality_shock', 'brand_shock' 등
    impact_value: float = Field(..., example=1.2)
    duration: int = Field(3, gt=0)
# --- (Pydantic 모델 끝) ---


@app.post("/simulations")
async def create_simulation(config: SimulationConfig):
    sim_id = str(uuid.uuid4())
    ai_company_names = [c.name for c in config.companies]
    
    sim_config_dict = config.model_dump(exclude={"companies"}) 
    
    sim_config_dict['initial_configs'] = {}
    total_initial_share = sum(c.initial_market_share for c in config.companies)
    
    if total_initial_share > 1.0:
        print("경고: AI 초기 점유율 합계가 1.0을 초과합니다. 1.0으로 정규화됩니다.")
    
    for c in config.companies:
        sim_config_dict['initial_configs'][c.name] = {
            "unit_cost": c.initial_unit_cost,
            "market_share": c.initial_market_share / total_initial_share if total_initial_share > 1.0 else c.initial_market_share,
            "product_quality": c.initial_product_quality,
            "brand_awareness": c.initial_brand_awareness
        }

    personas = {c.name: c.persona for c in config.companies}
    
    market = MarketSimulator(ai_company_names, sim_config_dict)
    agents = [AIAgent(name=name, persona=personas[name], use_mock=False) for name in ai_company_names]
    active_simulations[sim_id] = {"market": market, "agents": agents}
    print(f"시뮬레이션 생성 완료 (ID: {sim_id})")
    return {"simulation_id": sim_id, "initial_state": market.get_market_state()}

# [수정] _get_agent_specific_state (전쟁 안개, 정보 지연)
def _get_agent_specific_state(market: MarketSimulator, agent: AIAgent, all_agents: List[AIAgent]):
    market_state_base = market.get_market_state() 
    history = market.history
    turn = market.turn
    
    my_name = agent.name
    ai_company_names = [a.name for a in all_agents]
    opponent_name = next((name for name in ai_company_names if name != my_name), ai_company_names[0]) 
    
    agent_specific_state = market_state_base.copy()
    agent_specific_state["opponent_name"] = opponent_name

    # [전쟁 안개]
    if "companies" in agent_specific_state:
        companies_data = agent_specific_state["companies"]
        for name, data in companies_data.items():
            data.pop("market_share", None)
            
            if name != my_name: # 내 정보가 아닌 경우
                data.pop("unit_cost", None)
                data.pop("accumulated_profit", None)
                data.pop("product_quality", None)
                data.pop("brand_awareness", None)
                data.pop("max_marketing_budget", None) 
                data.pop("max_rd_budget", None)      

    # [정보 지연] 턴별/분기별 리포트 생성
    if turn > 0:
        last_results = history[-1]
        agent_specific_state["last_turn_comparison"] = {
            "my_profit": last_results.get(f"{my_name}_profit", 0)
        }
        
        summary_window = QUARTERLY_REPORT_INTERVAL
        recent_history = history[-summary_window:] if turn >= summary_window else history
        agent_specific_state["historical_summary"] = {
            "window_size": len(recent_history),
            "my_avg_profit_4turn": sum(h.get(f"{my_name}_profit", 0) for h in recent_history) / len(recent_history),
        }

    if turn > 0 and turn % QUARTERLY_REPORT_INTERVAL == 0:
        start_index = max(0, turn - QUARTERLY_REPORT_INTERVAL)
        quarterly_history = history[start_index : turn] 
        
        report_data = {}
        companies_to_report = [my_name, opponent_name, "Others"]
        
        for name in companies_to_report:
            if not quarterly_history:
                report_data[name] = {"total_profit": 0, "total_rd_spend": 0, "total_marketing_spend": 0, "end_of_quarter_market_share": 0, "end_of_quarter_product_quality": 0, "end_of_quarter_brand_awareness": 0}
                continue

            total_profit = sum(h.get(f"{name}_profit", 0) for h in quarterly_history)
            total_rd = sum(h.get(f"{name}_rd_spend", 0) for h in quarterly_history)
            total_marketing = sum(h.get(f"{name}_marketing_spend", 0) for h in quarterly_history)
            final_share = quarterly_history[-1].get(f"{name}_market_share", 0.0)
            
            end_of_quarter_state = market.get_company_state(name)
            final_quality = end_of_quarter_state.get("product_quality", 0)
            final_brand = end_of_quarter_state.get("brand_awareness", 0)

            report_data[name] = {
                "total_profit": total_profit,
                "total_rd_spend": total_rd,
                "total_marketing_spend": total_marketing,
                "end_of_quarter_market_share": final_share,
                "end_of_quarter_product_quality": final_quality,
                "end_of_quarter_brand_awareness": final_brand
            }
        
        agent_specific_state["quarterly_report"] = {
            "turn_range": (start_index + 1, turn),
            "data": report_data
        }
    else:
        agent_specific_state["quarterly_report"] = None

    return agent_specific_state


# [수정] _validate_and_clean_ai_decisions (하이브리드 예산 준수)
def _validate_and_clean_ai_decisions(
    ai_decisions_raw: dict, 
    market: MarketSimulator
) -> (dict, dict):
    ai_decisions_cleaned = {} 
    ai_reasoning = {}         

    for agent_name, decision_data in ai_decisions_raw.items():
        company_data = market.companies.get(agent_name)
        if not company_data:
            print(f"경고: {agent_name}에 대한 회사 데이터를 찾을 수 없습니다. 결정을 건너뜁니다.")
            continue
            
        max_marketing_budget = company_data.get('max_marketing_budget', 1000000)
        max_rd_budget = company_data.get('max_rd_budget', 500000)
            
        try:
            price = int(decision_data.get("price", 10000))
        except (ValueError, TypeError):
            price = 10000 
        price = max(1000, min(price, 50000))
        
        # [수정] AI는 이제 'R&D 지출'과 '마케팅 지출'을 결정
        # (AI가 보낸 총액을 검증)
        try:
            marketing = int(decision_data.get("marketing_spend", 1000000))
        except (ValueError, TypeError):
            marketing = 1000000
        marketing = max(0, min(marketing, max_marketing_budget)) 

        try:
            rd_spend = int(decision_data.get("rd_spend", 500000))
        except (ValueError, TypeError):
            rd_spend = 500000
        rd_spend = max(0, min(rd_spend, max_rd_budget))
        
        # [수정] AI가 세분화된 지출을 보냈는지 확인 (에이전트 v3)
        marketing_brand_spend = int(decision_data.get("marketing_brand_spend", marketing))
        marketing_promo_spend = int(decision_data.get("marketing_promo_spend", 0))
        rd_innovation_spend = int(decision_data.get("rd_innovation_spend", rd_spend))
        rd_efficiency_spend = int(decision_data.get("rd_efficiency_spend", 0))

        # (총액이 예산을 넘지 않도록 검증)
        if (marketing_brand_spend + marketing_promo_spend) > max_marketing_budget:
             marketing_brand_spend = max_marketing_budget
             marketing_promo_spend = 0
             
        if (rd_innovation_spend + rd_efficiency_spend) > max_rd_budget:
            rd_innovation_spend = max_rd_budget
            rd_efficiency_spend = 0

        ai_decisions_cleaned[agent_name] = {
            "price": price,
            # [수정] 총액과 세부 항목을 모두 전달
            "marketing_spend": marketing_brand_spend + marketing_promo_spend,
            "marketing_brand_spend": marketing_brand_spend,
            "marketing_promo_spend": marketing_promo_spend,
            "rd_spend": rd_innovation_spend + rd_efficiency_spend,
            "rd_innovation_spend": rd_innovation_spend,
            "rd_efficiency_spend": rd_efficiency_spend
        }
        ai_reasoning[agent_name] = decision_data.get("reasoning", "No reasoning or invalid data provided.")

    return ai_decisions_cleaned, ai_reasoning


@app.post("/simulations/{sim_id}/next_turn")
async def run_next_turn(sim_id: str):
    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail="시뮬레이션을 찾을 수 없습니다.")
    
    sim_data = active_simulations[sim_id]
    market: MarketSimulator = sim_data["market"]
    agents: List[AIAgent] = sim_data["agents"] 
    sim_config = market.config
    
    if market.turn >= sim_config.get("total_turns", 30):
        raise HTTPException(status_code=400, detail="시뮬레이션이 이미 종료되었습니다.")

    tasks = []
    for agent in agents:
        agent_state = _get_agent_specific_state(market, agent, agents)
        tasks.append(agent.decide_action(agent_state))
    
    ai_decisions_raw_list = await asyncio.gather(*tasks)
    ai_decisions_raw = {agent.name: decision for agent, decision in zip(agents, ai_decisions_raw_list)}
    
    ai_decisions_cleaned, ai_reasoning = _validate_and_clean_ai_decisions(ai_decisions_raw, market)
    
    next_state = market.process_turn(ai_decisions_cleaned)
    turn_results = market.history[-1] if market.history else {}
    
    return {
        "turn": market.turn,
        "turn_results": turn_results,
        "ai_reasoning": ai_reasoning,
        "next_state": next_state
    }


@app.post("/simulations/{sim_id}/run_turns")
async def run_multiple_turns(sim_id: str, turns_to_run: int = 1):
    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail="시뮬레이션을 찾을 수 없습니다.")
    
    sim_data = active_simulations[sim_id]
    market: MarketSimulator = sim_data["market"]
    agents: List[AIAgent] = sim_data["agents"] 
    sim_config = market.config
    
    results_history = []
    reasoning_history = []
    turns_ran = 0

    for _ in range(turns_to_run):
        if market.turn >= sim_config.get("total_turns", 30):
            break
            
        tasks = []
        for agent in agents:
            agent_state = _get_agent_specific_state(market, agent, agents)
            tasks.append(agent.decide_action(agent_state))
        
        ai_decisions_raw_list = await asyncio.gather(*tasks)
        ai_decisions_raw = {agent.name: decision for agent, decision in zip(agents, ai_decisions_raw_list)}
        
        ai_decisions_cleaned, ai_reasoning = _validate_and_clean_ai_decisions(ai_decisions_raw, market)
        
        next_state = market.process_turn(ai_decisions_cleaned)
        
        results_history.append(market.history[-1])
        reasoning_history.append({"turn": market.turn, "reasoning": ai_reasoning})
        turns_ran += 1

    return {
        "turns_ran": turns_ran,
        "final_turn": market.turn,
        "results_history": results_history,
        "reasoning_history": reasoning_history,
        "final_state": market.get_market_state()
    }


@app.post("/simulations/{sim_id}/inject_event")
async def inject_event_into_simulation(sim_id: str, event: EventInject):
    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail="시뮬레이션을 찾을 수 없습니다.")
    
    market: MarketSimulator = active_simulations[sim_id]["market"]
    
    try:
        market.inject_event(
            description=event.description,
            target_company=event.target_company,
            effect_type=event.effect_type,
            impact_value=event.impact_value,
            duration=event.duration
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": f"이벤트 '{event.description}'가 {event.target_company}에 주입되었습니다."}