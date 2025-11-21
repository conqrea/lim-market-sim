from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import uuid
import random
import json
import os

app = FastAPI()

# --- [설정] CORS (React 프론트엔드 접속 허용) ---
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- [메모리 DB] 시뮬레이션 상태 저장소 ---
simulations = {}
presets_db = [] # 프리셋 저장소 (메모리)

# 초기 프리셋 데이터 로드 (예시)
if not presets_db:
    presets_db.append({
        "filename": "golden_balance",
        "name": "Golden Balance (Phone War)",
        "description": "A balanced market for high-end smartphones. Profit-focused AI.",
        "config": {
             "total_turns": 20,
             "market_size": 50000,
             "initial_capital": 1000000000,
             "physics": {
                 "price_sensitivity": 3.5,
                 "marketing_efficiency": 2.5,
                 "weight_quality": 0.5,
                 "weight_brand": 0.3,
                 "weight_price": 0.2
             }
        }
    })

# --- [Pydantic 모델] 데이터 검증용 ---
class PhysicsConfig(BaseModel):
    weight_quality: float = 0.5
    weight_brand: float = 0.3
    weight_price: float = 0.2
    price_sensitivity: float = 3.5
    marketing_efficiency: float = 2.5
    others_overall_competitiveness: float = 0.8

class CompanyConfig(BaseModel):
    name: str
    persona: str
    initial_unit_cost: float
    initial_market_share: float
    initial_product_quality: float
    initial_brand_awareness: float

class GlobalConfig(BaseModel):
    total_turns: int = 20
    market_size: float = 50000
    initial_capital: float = 1000000000
    
    gdp_growth_rate: float = 0.02
    inflation_rate: float = 0.005
    
    rd_innovation_threshold: float = 30000000.0
    rd_innovation_impact: float = 15.0
    rd_efficiency_threshold: float = 50000000.0
    rd_efficiency_impact: float = 0.05
    
    marketing_cost_base: float = 3000000.0
    marketing_cost_multiplier: float = 1.5
    
    quality_decay_rate: float = 0.05
    brand_decay_rate: float = 0.1
    
    physics: PhysicsConfig
    companies: List[CompanyConfig]
    preset_name: Optional[str] = None

class DecisionInput(BaseModel):
    price: float
    marketing_brand_spend: float
    marketing_promo_spend: float
    rd_innovation_spend: float
    rd_efficiency_spend: float

class TurnDecisionWrapper(BaseModel):
    price: float
    marketing_brand_spend: float
    marketing_promo_spend: float
    rd_innovation_spend: float
    rd_efficiency_spend: float
    reasoning: Optional[str] = ""

class PresetData(BaseModel):
    filename: str
    preset_name: str
    description: str
    config: Dict[str, Any]

# --- [핵심 로직] 시뮬레이션 엔진 클래스 (간소화 버전) ---
class SimulationEngine:
    def __init__(self, config: GlobalConfig):
        self.id = str(uuid.uuid4())
        self.config = config
        self.turn = 0
        self.history = []
        
        # 회사 초기화
        self.agents = {}
        for comp in config.companies:
            self.agents[comp.name] = {
                "name": comp.name,
                "cash": config.initial_capital,
                "unit_cost": comp.initial_unit_cost,
                "market_share": comp.initial_market_share,
                "product_quality": comp.initial_product_quality,
                "brand_awareness": comp.initial_brand_awareness,
                "accumulated_profit": 0.0,
                "accumulated_rd_innovation_point": 0.0,
                "accumulated_rd_efficiency_point": 0.0
            }
            
        # Others(기타 경쟁자) 초기화
        self.others = {
            "price": 15000.0, # 기본값
            "product_quality": 60.0,
            "brand_awareness": 50.0,
            "market_share": max(0, 1.0 - sum(c.initial_market_share for c in config.companies))
        }

    def get_decision_options(self):
        # AI가 선택할 수 있는 3가지 전략 생성
        choices = {}
        for name, agent in self.agents.items():
            agent_choices = []
            
            # 전략 1: 현상 유지 (Safe)
            agent_choices.append({
                "decision": {
                    "price": agent['unit_cost'] * 1.3, # 30% 마진
                    "marketing_brand_spend": self.config.marketing_cost_base,
                    "marketing_promo_spend": 0,
                    "rd_innovation_spend": 0,
                    "rd_efficiency_spend": 0
                },
                "probability": 0.2,
                "reasoning": "안정적으로 현재 상태를 유지하며 현금을 확보합니다."
            })
            
            # 전략 2: 공격적 투자 (Growth)
            agent_choices.append({
                "decision": {
                    "price": agent['unit_cost'] * 1.1, # 10% 마진 (박리다매)
                    "marketing_brand_spend": self.config.marketing_cost_base * 2,
                    "marketing_promo_spend": self.config.marketing_cost_base,
                    "rd_innovation_spend": self.config.rd_innovation_threshold * 0.1, # 조금씩 투자
                    "rd_efficiency_spend": 0
                },
                "probability": 0.5,
                "reasoning": "시장 점유율 확대를 위해 가격을 낮추고 마케팅을 강화합니다."
            })
            
            # 전략 3: 기술 혁신 올인 (Innovation)
            agent_choices.append({
                "decision": {
                    "price": agent['unit_cost'] * 1.5, # 고가 정책
                    "marketing_brand_spend": 0,
                    "marketing_promo_spend": 0,
                    "rd_innovation_spend": self.config.rd_innovation_threshold * 0.5, # 과감한 투자
                    "rd_efficiency_spend": 0
                },
                "probability": 0.3,
                "reasoning": "단기 이익을 포기하고 R&D에 집중하여 차세대 제품을 준비합니다."
            })
            
            choices[name] = agent_choices
        return choices

    def step(self, decisions: Dict[str, TurnDecisionWrapper]):
        self.turn += 1
        
        turn_result = {"turn": self.turn}
        ai_reasoning = {}
        
        # 1. 의사결정 반영 (비용 지출)
        for name, decision in decisions.items():
            agent = self.agents[name]
            total_spend = (decision.marketing_brand_spend + decision.marketing_promo_spend + 
                           decision.rd_innovation_spend + decision.rd_efficiency_spend)
            
            agent['cash'] -= total_spend
            
            # R&D 누적
            agent['accumulated_rd_innovation_point'] += decision.rd_innovation_spend
            agent['accumulated_rd_efficiency_point'] += decision.rd_efficiency_spend
            
            # 혁신 성공 판정
            if agent['accumulated_rd_innovation_point'] >= self.config.rd_innovation_threshold:
                agent['product_quality'] += self.config.rd_innovation_impact
                agent['accumulated_rd_innovation_point'] = 0 # 초기화 (또는 차감)
                
            # 원가 절감 판정
            if agent['accumulated_rd_efficiency_point'] >= self.config.rd_efficiency_threshold:
                agent['unit_cost'] *= (1.0 - self.config.rd_efficiency_impact)
                agent['accumulated_rd_efficiency_point'] = 0
                
            # 마케팅 효과 (브랜드 상승)
            mkt_effect = (decision.marketing_brand_spend / self.config.marketing_cost_base) * self.config.physics.marketing_efficiency
            agent['brand_awareness'] += mkt_effect
            
            # 추론 저장
            if decision.reasoning:
                ai_reasoning[name] =