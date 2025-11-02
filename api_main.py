# api_main.py (SoV 곱셈 모델에 맞게 설정값 수정)

import asyncio
import uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict
from fastapi.middleware.cors import CORSMiddleware

from simulator import MarketSimulator
from agent import AIAgent

app = FastAPI(
    title="AI Strategy Lab API (Wargame Mode)",
    description="턴 기반 및 이벤트 주입이 가능한 시뮬레이션 API입니다."
)

# (CORS 설정 - 동일)
origins = ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# (메모리 저장소 - 동일)
active_simulations = {}

# (Pydantic 모델 - 수정)
class CompanyConfig(BaseModel):
    name: str = Field(..., example="Apple")
    persona: str = Field(..., example="시장 점유율 확보를 최우선으로 하는 공격적인 CEO입니다.")
    unit_cost: int = Field(..., example=8500)

class SimulationConfig(BaseModel):
    companies: List[CompanyConfig]
    total_turns: int = Field(30, gt=0)
    market_size: int = Field(10000, gt=0)
    initial_capital: int = Field(25000000)
    
    # [핵심 수정] price_sensitivity를 다시 지수 모델 값 2.0으로 변경
    price_sensitivity: float = Field(2.0, gt=0) 
    
    max_marketing_boost: float = Field(1.0, gt=0) 
    marketing_midpoint: float = Field(5000000, gt=0)
    marketing_steepness: float = Field(0.0000015)
    
    # [핵심 수정] 가중치 합산 모델이 아니므로 가중치 변수 제거
    # price_weight: float = Field(0.6, ge=0, le=1) 
    # marketing_weight: float = Field(0.4, ge=0, le=1)

class EventInject(BaseModel):
    description: str = Field(..., example="공급망 이슈로 원가 20% 상승")
    target_company: str = Field("All", example="Apple")
    effect_type: str = Field(..., example="unit_cost_multiplier")
    impact_value: float = Field(..., example=1.2)
    duration: int = Field(3, gt=0)
# --- (Pydantic 모델 끝) ---


# --- 1. 시뮬레이션 '방' 생성 API (기존과 동일) ---
@app.post("/simulations")
async def create_simulation(config: SimulationConfig):
    sim_id = str(uuid.uuid4())
    ai_company_names = [c.name for c in config.companies]
    sim_config_dict = config.model_dump(exclude={"companies"}) 
    sim_config_dict['unit_costs'] = {c.name: c.unit_cost for c in config.companies}
    personas = {c.name: c.persona for c in config.companies}
    market = MarketSimulator(ai_company_names, sim_config_dict)
    agents = [AIAgent(name=name, persona=personas[name], use_mock=False) for name in ai_company_names]
    active_simulations[sim_id] = {"market": market, "agents": agents}
    print(f"시뮬레이션 생성 완료 (ID: {sim_id})")
    return {"simulation_id": sim_id, "initial_state": market.get_market_state()}

# --- [내부 함수] AI에게 보낼 '분석 리포트' 생성 (기존과 동일) ---
def _get_agent_specific_state(market: MarketSimulator, agent: AIAgent, all_agents: List[AIAgent]):
    market_state_base = market.get_market_state() 
    history = market.history
    turn = market.turn
    
    if turn > 0:
        my_name = agent.name
        ai_company_names = [a.name for a in all_agents]
        opponent_name = next(name for name in ai_company_names if name != my_name) 
        
        summary_window = 5
        recent_history = history[-summary_window:] if turn >= summary_window else history
        
        avg_stats = {}
        for name in market.all_company_names: # "Apple", "Samsung", "Others"
            avg_stats[name] = {
                "profit": sum(h.get(f"{name}_profit", 0) for h in recent_history) / len(recent_history),
                "share": sum(h.get(f"{name}_market_share", 0) for h in recent_history) / len(recent_history)
            }
        
        agent_specific_state = market_state_base.copy()

        last_results = history[-1]
        my_profit = last_results.get(f"{my_name}_profit", 0)
        opponent_profit = last_results.get(f"{opponent_name}_profit", 0)
        agent_specific_state["last_turn_comparison"] = {
            "my_profit": my_profit,
            "opponent_profit": opponent_profit,
            "profit_diff": my_profit - opponent_profit
        }

        agent_specific_state["historical_summary"] = {
            "window_size": len(recent_history),
            "my_avg_profit_5turn": avg_stats[my_name]["profit"],
            "opponent_avg_profit_5turn": avg_stats[opponent_name]["profit"],
            "my_avg_share_5turn": avg_stats[my_name]["share"],
            "others_avg_share_5turn": avg_stats["Others"]["share"] 
        }
        return agent_specific_state
    else: 
        return market_state_base

# --- [내부 함수] AI 결정을 검증/제한하는 함수 (기존과 동일) ---
def _validate_and_clean_ai_decisions(
    ai_decisions_raw: dict, 
    market: MarketSimulator
) -> (dict, dict):
    ai_decisions_cleaned = {} 
    ai_reasoning = {}         

    for agent_name, decision_data in ai_decisions_raw.items():
        company_data = market.companies[agent_name]
        acc_profit = company_data["accumulated_profit"]
        
        max_marketing_budget = max(1000000, min(acc_profit * 0.1, 20000000))
        if acc_profit <= 0:
            max_marketing_budget = 1000000
            
        try:
            price = int(decision_data.get("price", 10000))
        except (ValueError, TypeError):
            price = 10000 
        price = max(5000, min(price, 20000)) 
        
        try:
            marketing = int(decision_data.get("marketing_spend", 1000000))
        except (ValueError, TypeError):
            marketing = 1000000
        marketing = max(0, min(marketing, max_marketing_budget)) 

        ai_decisions_cleaned[agent_name] = {
            "price": price,
            "marketing_spend": marketing
        }
        ai_reasoning[agent_name] = decision_data.get("reasoning", "No reasoning or invalid data provided.")

    return ai_decisions_cleaned, ai_reasoning


# --- 2. '다음 1턴' 진행 API (기존과 동일) ---
@app.post("/simulations/{sim_id}/next_turn")
async def run_next_turn(sim_id: str):
    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail="시뮬레이션을 찾을 수 없습니다.")
    
    sim_data = active_simulations[sim_id]
    market: MarketSimulator = sim_data["market"]
    agents: List[AIAgent] = sim_data["agents"] 
    sim_config = market.config

    if market.turn >= sim_config.get("total_turns", 30):
        return {"message": "시뮬레이션이 이미 종료되었습니다.", "final_state": market.get_market_state()}

    tasks = []
    for agent in agents:
        agent_state = _get_agent_specific_state(market, agent, agents)
        tasks.append(agent.decide_action(agent_state))

    decisions_list = await asyncio.gather(*tasks)
    ai_decisions_raw = {agent.name: decision for agent, decision in zip(agents, decisions_list)}
    
    ai_decisions_cleaned, ai_reasoning = _validate_and_clean_ai_decisions(ai_decisions_raw, market)

    next_state = market.process_turn(ai_decisions_cleaned)
    
    return {
        "turn": market.turn, 
        "turn_results": market.history[-1], 
        "next_state": next_state,
        "ai_reasoning": ai_reasoning 
    }

# --- 3. 'N턴' 실행 API (기존과 동일) ---
@app.post("/simulations/{sim_id}/run_turns")
async def run_multiple_turns(sim_id: str, turns_to_run: int = 5):
    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail="시뮬레이션을 찾을 수 없습니다.")
    
    sim_data = active_simulations[sim_id]
    market: MarketSimulator = sim_data["market"]
    agents: List[AIAgent] = sim_data["agents"]
    sim_config = market.config
    
    results_history = []
    reasoning_history = []

    for _ in range(turns_to_run):
        if market.turn >= sim_config.get("total_turns", 30):
            break 

        tasks = []
        for agent in agents:
            agent_state = _get_agent_specific_state(market, agent, agents)
            tasks.append(agent.decide_action(agent_state))

        decisions_list = await asyncio.gather(*tasks)
        ai_decisions_raw = {agent.name: decision for agent, decision in zip(agents, decisions_list)}
        
        ai_decisions_cleaned, ai_reasoning = _validate_and_clean_ai_decisions(ai_decisions_raw, market)
        
        next_state = market.process_turn(ai_decisions_cleaned)
        
        results_history.append(market.history[-1])
        reasoning_history.append({"turn": market.turn, "reasoning": ai_reasoning})

    return {
        "turns_ran": len(results_history),
        "results_history": results_history,
        "reasoning_history": reasoning_history,
        "final_state": market.get_market_state()
    }

# --- 4. '이벤트 주입' API (기존과 동일) ---
@app.post("/simulations/{sim_id}/inject_event")
async def inject_event_into_simulation(sim_id: str, event_data: EventInject):
    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail="시뮬레이션을 찾을 수 없습니다.")
    market: MarketSimulator = active_simulations[sim_id]["market"]
    market.inject_event(event_data.model_dump())
    return {"message": f"이벤트 '{event_data.description}'가 다음 턴에 적용되도록 등록되었습니다."}