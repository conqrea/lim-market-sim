import asyncio
import uuid
import itertools
import time
import json
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from fastapi.middleware.cors import CORSMiddleware

from simulator import MarketSimulator
from agent import AIAgent

QUARTERLY_REPORT_INTERVAL = 4

app = FastAPI(
    title="AI Strategy Lab API (Final Phase: Smart Init & Velocity)",
    description="초기 품질 보정(Smart Init)과 혁신 주기(Threshold) 튜닝을 통해 EV 시나리오의 오차를 획기적으로 줄이는 버전입니다."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_simulations = {}

# --- 데이터 모델 ---
class MarketPhysicsConfig(BaseModel):
    weight_quality: float = Field(0.4)
    weight_brand: float = Field(0.4)
    weight_price: float = Field(0.2)
    price_sensitivity: float = Field(50.0)
    marketing_efficiency: float = Field(1.0)
    others_overall_competitiveness: float = Field(1.0)

class BenchmarkData(BaseModel):
    scenario_name: str
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None 
    turns_data: List[dict]
    physics_override: Optional[Dict[str, Any]] = None

class CompanyConfig(BaseModel):
    name: str = Field(..., example="GM")
    persona: str = Field(..., example="...")
    initial_unit_cost: int = Field(..., example=10000) 
    initial_market_share: float = Field(..., example=0.35)
    initial_product_quality: float = Field(..., example=60.0)
    initial_brand_awareness: float = Field(..., example=70.0)

class SimulationConfig(BaseModel):
    preset_name: Optional[str] = None
    companies: List[CompanyConfig]
    total_turns: int = Field(30)
    
    market_size: int = Field(10000)
    initial_capital: int = Field(1000000000)
    initial_marketing_budget_ratio: float = Field(0.02)
    initial_rd_budget_ratio: float = Field(0.01)
    gdp_growth_rate: float = Field(0.005)
    inflation_rate: float = Field(0.0075)
    
    rd_innovation_threshold: float = Field(5000000)
    rd_innovation_impact: float = Field(5.0)
    rd_efficiency_threshold: float = Field(5000000)
    rd_efficiency_impact: float = Field(0.03)
    
    marketing_cost_base: float = Field(100000.0)
    marketing_cost_multiplier: float = Field(1.12)
    
    quality_decay_rate: float = Field(0.5)
    brand_decay_rate: float = Field(0.2)
    
    physics: MarketPhysicsConfig = Field(default_factory=MarketPhysicsConfig)

class EventInject(BaseModel):
    description: str
    target_company: str
    effect_type: str
    impact_value: float
    duration: int

class AgentFinalDecision(BaseModel):
    price: int
    marketing_brand_spend: int
    marketing_promo_spend: int
    rd_innovation_spend: int
    rd_efficiency_spend: int
    reasoning: str

class ExecuteTurnRequest(BaseModel):
    decisions: Dict[str, AgentFinalDecision]

class PresetSaveRequest(BaseModel):
    filename: str
    preset_name: str
    description: str
    config: Dict[str, Any]

# --- Endpoints ---

@app.get("/presets")
async def get_presets():
    presets_dir = "presets"
    if not os.path.exists(presets_dir):
        os.makedirs(presets_dir)
        return []
    
    presets = []
    for filename in os.listdir(presets_dir):
        if filename.endswith(".json"):
            try:
                with open(os.path.join(presets_dir, filename), "r", encoding="utf-8") as f:
                    data = json.load(f)
                    presets.append({
                        "filename": filename,
                        "name": data.get("preset_name", filename),
                        "description": data.get("description", ""),
                        "config": data.get("config", {}) # <--- [중요] 이 줄이 꼭 있어야 합니다!
                    })
            except Exception as e:
                print(f"Error loading preset {filename}: {e}")
    return presets

@app.post("/admin/save_preset")
async def save_preset(req: PresetSaveRequest):
    presets_dir = "presets"
    if not os.path.exists(presets_dir):
        os.makedirs(presets_dir)
    
    safe_filename = "".join([c for c in req.filename if c.isalnum() or c in ('-', '_')]).strip()
    if not safe_filename:
        safe_filename = f"preset_{int(time.time())}"
    if not safe_filename.endswith(".json"):
        safe_filename += ".json"
        
    file_path = os.path.join(presets_dir, safe_filename)
    
    data_to_save = {
        "preset_name": req.preset_name,
        "description": req.description,
        "config": req.config
    }
    
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        return {"message": f"Preset saved successfully as {safe_filename}", "filename": safe_filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save preset: {str(e)}")

@app.post("/simulations")
async def create_simulation(config: SimulationConfig):
    sim_id = str(uuid.uuid4())
    
    sim_config_dict = config.model_dump(exclude={"companies", "preset_name"}) 
    
    if config.preset_name:
        preset_path = os.path.join("presets", config.preset_name)
        if os.path.exists(preset_path):
            print(f"Loading Preset: {config.preset_name}")
            with open(preset_path, "r", encoding="utf-8") as f:
                preset_data = json.load(f)
                if "config" in preset_data:
                    sim_config_dict.update(preset_data["config"])
        else:
            print(f"Warning: Preset {config.preset_name} not found.")

    sim_config_dict['initial_configs'] = {}
    total_initial_share = sum(c.initial_market_share for c in config.companies)
    
    for c in config.companies:
        sim_config_dict['initial_configs'][c.name] = {
            "unit_cost": c.initial_unit_cost, 
            "market_share": c.initial_market_share / total_initial_share if total_initial_share > 1.0 else c.initial_market_share,
            "product_quality": c.initial_product_quality,
            "brand_awareness": c.initial_brand_awareness
        }

    personas = {c.name: c.persona for c in config.companies}
    
    market = MarketSimulator(company_names=[c.name for c in config.companies], config=sim_config_dict)
    agents = [AIAgent(name=name, persona=personas[name], use_mock=False) for name in [c.name for c in config.companies]]
    active_simulations[sim_id] = {"market": market, "agents": agents}
    
    return {"simulation_id": sim_id, "initial_state": market.get_market_state()}

@app.post("/admin/run_benchmark")
async def run_benchmark_simulation(data: BenchmarkData):
    if not data.turns_data: raise HTTPException(status_code=400, detail="No turn data provided")
    
    override_params = data.physics_override
    market = _initialize_market_for_benchmark(data, override_params=override_params)
    
    results_log = []; total_mae = 0.0
    for turn_data in data.turns_data:
        market.run_benchmark_turn(turn_data)
        last_result = market.history[-1]
        results_log.append(last_result)
        total_mae += last_result.get("total_error_mae", 0)
    avg_mae = total_mae / len(data.turns_data)
    return {"scenario": data.scenario_name, "average_error_mae": avg_mae, "history": results_log, "message": f"Completed. MAE: {avg_mae:.4f}"}

@app.post("/admin/auto_tune")
async def auto_tune_parameters(data: BenchmarkData):
    print(f"\n=== ⚡ Auto-Tuning Started (Deep Search Mode) ===")
    start_time = time.time()
    
    # [개선점 1] 탐색 범위를 매우 촘촘하게(Dense) 설정
    # 기존에 3~4개씩 보던 것을 5~8개 단계로 세분화했습니다.
    search_space = {
        "price_sensitivity": [5.0, 10.0, 20.0, 40.0, 60.0], # 범위 약간 압축 (효율화)
        "marketing_efficiency": [1.0, 3.0, 5.0, 8.0, 10.0],
        "weight_quality": [0.5, 0.7, 0.9, 1.1],
        "weight_brand": [0.1, 0.3, 0.5],
        "others_overall_competitiveness": [0.8, 1.0, 1.5],
        "rd_innovation_impact": [10.0, 30.0, 50.0],
        "quality_decay_rate": [0.05, 0.1, 0.2, 0.3, 0.4],
        "rd_innovation_threshold": [1000000.0, 3000000.0, 5000000.0]
    }
    
    # 모든 조합 생성 (Cartesian Product)
    keys, values = zip(*search_space.items())
    param_combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]
    
    # [개선점 2] 유효성 검사 로직 완화
    # 기존에는 합이 1.0 미만인 경우만 엄격하게 따졌으나, 
    # 시뮬레이터 내부에서 정규화가 일어나므로 범위를 좀 더 유연하게 허용합니다.
    valid_combinations = []
    for params in param_combinations:
        # 품질 + 브랜드 가중치 합계 확인
        current_sum = params["weight_quality"] + params["weight_brand"]
        
        # 합이 너무 크지 않은 경우만 허용 (가격 가중치를 최소 0.05는 남겨두기 위함)
        # 1.5까지 허용하는 이유는, weight_quality가 1.0일 때 브랜드가 0.2일 수도 있기 때문
        if current_sum <= 1.5: 
            # 가격 가중치 자동 계산 (최소 0.05 보장)
            weight_price = max(0.05, round(1.0 - min(1.0, current_sum), 2))
            
            # 만약 합이 1.0을 넘어가면, 시뮬레이터가 알아서 비율대로 처리하겠지만
            # 여기서는 명시적으로 weight_price를 별도로 할당
            params["weight_price"] = weight_price
            valid_combinations.append(params)
    
    total_combos = len(valid_combinations)
    print(f"🧪 Total Dense Combinations to Test: {total_combos}")
    print(f"⏳ 예상 소요 시간: {total_combos * 0.002:.1f}초 (약 {total_combos/500/60:.1f}분)")

    best_mae = float('inf')
    best_params = {}
    
    # 진행 상황 표시를 위한 카운터
    log_interval = max(1, total_combos // 10) 

    for i, params in enumerate(valid_combinations):
        # 벤치마크 실행
        try:
            market = _initialize_market_for_benchmark(data, override_params=params)
            current_total_mae = 0.0
            
            # 턴별 실행 및 오차 계산
            valid_run = True
            for turn_data in data.turns_data:
                market.run_benchmark_turn(turn_data)
                # 결과가 비정상(NaN 등)이면 중단
                last_res = market.history[-1]
                if "total_error_mae" not in last_res:
                    valid_run = False
                    break
                current_total_mae += last_res["total_error_mae"]
            
            if valid_run:
                avg_mae = current_total_mae / len(data.turns_data)
                
                if avg_mae < best_mae:
                    best_mae = avg_mae
                    best_params = params.copy()
                    print(f"  [🔥 New Best! {i+1}/{total_combos}] MAE: {best_mae*100:.2f}% | Sensitivity: {params['price_sensitivity']} | Brand: {params['weight_brand']}")
        
        except Exception as e:
            continue

        # 진행 로그 (너무 자주 찍지 않음)
        if i % log_interval == 0:
             print(f"  .. processing {i}/{total_combos} ({i/total_combos*100:.0f}%) ..")

    elapsed = time.time() - start_time
    print(f"=== 🏁 Deep Tuning Finished in {elapsed:.2f} seconds ===")
    print(f"=== 🏆 Best MAE: {best_mae*100:.2f}% ===")
    
    return {
        "best_params": best_params, 
        "lowest_mae": best_mae, 
        "message": f"Tested {total_combos} scenarios in {elapsed:.1f}s. Best MAE: {best_mae*100:.2f}%"
    }

def _initialize_market_for_benchmark(data: BenchmarkData, override_params: dict = None):
    first_turn = data.turns_data[0]
    company_names = list(first_turn["companies"].keys())
    
    # 1. [기준 정의] 무엇이 '물리 변수(Physics)'인지 키(Key) 목록 정의
    # 이 딕셔너리는 시뮬레이션의 기본 물리값으로도 쓰이고, 
    # 나중에 override_params가 들어왔을 때 분류하는 기준으로도 쓰입니다.
    default_physics = {
        "weight_quality": 0.4, "weight_brand": 0.4, "weight_price": 0.2,
        "price_sensitivity": 50.0, "marketing_efficiency": 1.0,
        "others_overall_competitiveness": 1.0 
    }
    
    # 2. [환경 설정] 기본값 정의 (시장 규모, 초기 자본 등)
    sim_config = {
        "market_size": 50000,           # 기본값
        "initial_capital": 1000000000,  # 기본값
        "marketing_cost_base": 50000.0,
        "inflation_rate": 0.0,
        "gdp_growth_rate": 0.0,
        
        # 튜닝 대상이지만 Physics 안에는 없는 변수들 (Root 레벨)
        "rd_innovation_threshold": 5000000, 
        "rd_innovation_impact": 5.0, 
        "rd_efficiency_threshold": 5000000, 
        "rd_efficiency_impact": 0.03,
        "marketing_cost_multiplier": 1.1,
        "quality_decay_rate": 0.05,
        "brand_decay_rate": 0.2,
        
        # Physics 섹션 초기화
        "physics": default_physics.copy(), 
        "initial_configs": {}
    }

    # 3. [JSON 데이터 주입] 시나리오 파일에 config가 있다면 덮어쓰기
    # 예: 스마트폰 시장이라 market_size를 50000 -> 5000000으로 변경
    if hasattr(data, "config") and data.config:
        # 주의: data.config에 physics 키가 있다면 그것도 덮어씌워질 수 있음
        # 여기서는 Root 레벨 변수(market_size 등) 업데이트가 주 목적
        sim_config.update(data.config)

    # 4. [튜닝 값 적용] Auto-Tune이 넘겨준 파라미터(override_params) 적용
    if override_params:
        for k, v in override_params.items():
            # (1) 물리 변수 목록에 있는 키라면 -> physics 안에 넣음
            if k in default_physics:
                sim_config["physics"][k] = v
            # (2) 그 외(예: quality_decay_rate, rd_threshold) -> Root에 넣음
            else:
                sim_config[k] = v
    
    # 5. [기업 초기 상태 설정] JSON 데이터 기반
    for name in company_names:
        inputs = first_turn["companies"][name]["inputs"]
        actuals = first_turn["companies"][name]["outputs"]
        
        start_quality = inputs.get("initial_quality", 50.0)
        start_brand = inputs.get("initial_brand", 50.0)
        
        sim_config["initial_configs"][name] = {
            "unit_cost": 400, # 벤치마크에서는 원가가 큰 의미 없으므로 고정
            "market_share": actuals.get("actual_market_share", 0.1),
            "product_quality": start_quality, 
            "brand_awareness": start_brand
        }
        
    return MarketSimulator(company_names=company_names, config=sim_config)

# --- Helper Functions ---
def _get_agent_specific_state(market, agent, all_agents): return market.get_market_state()
def _validate_and_clean_ai_decisions(raw, market):
    # 1. 프론트엔드에서 받은 데이터(raw)에서 reasoning만 뽑아서 별도 딕셔너리로 만듦
    reasoning = {}
    for name, data in raw.items():
        # data 안에 있는 'reasoning' 텍스트를 가져오고, 없으면 빈 문자열
        reasoning[name] = data.get("reasoning", "No reasoning provided.")
    
    # 2. (정제된 결정 데이터, 추출한 reasoning 딕셔너리) 순서로 반환
    return raw, reasoning

@app.post("/simulations/{sim_id}/get_choices")
async def get_agent_choices(sim_id: str):
    if sim_id not in active_simulations: raise HTTPException(404, "Not found")
    sim_data = active_simulations[sim_id]
    market = sim_data["market"]; agents = sim_data["agents"]
    if market.turn >= market.config.get("total_turns", 30): raise HTTPException(400, "Ended")
    tasks = []
    for agent in agents:
        state = _get_agent_specific_state(market, agent, agents)
        tasks.append(agent.decide_action(state))
    choices = await asyncio.gather(*tasks)
    return {a.name: c for a, c in zip(agents, choices)}

@app.post("/simulations/{sim_id}/execute_turn")
async def execute_turn(sim_id: str, request: ExecuteTurnRequest):
    if sim_id not in active_simulations: raise HTTPException(404, "Not found")
    market = active_simulations[sim_id]["market"]
    decisions = {n: d.model_dump() for n, d in request.decisions.items()}
    cleaned, reasoning = _validate_and_clean_ai_decisions(decisions, market)
    next_state = market.process_turn(cleaned)
    return {"turn": market.turn, "turn_results": market.history[-1], "ai_reasoning": reasoning, "next_state": next_state}

@app.post("/simulations/{sim_id}/inject_event")
async def inject_event_into_simulation(sim_id: str, event: EventInject):
    if sim_id not in active_simulations: raise HTTPException(404, "Not found")
    active_simulations[sim_id]["market"].inject_event(event.description, event.target_company, event.effect_type, event.impact_value, event.duration)
    return {"message": "Injected"}