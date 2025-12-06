# agent.py

import json
import random
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
import re

load_dotenv()

class CompanyInputs(BaseModel):
    price: int = Field(description="제품 가격 (정수)")
    marketing_spend_ratio: float = Field(description="매출 대비 마케팅비 비율 (0.05~0.3)")
    rd_spend_ratio: float = Field(description="매출 대비 R&D비 비율 (0.05~0.2)")
    initial_quality: float = Field(description="제품 품질 점수 (0~100)")
    initial_brand: float = Field(description="브랜드 인지도 점수 (0~100)")
    unit_cost: int = Field(description="단위 원가 (정수, 가격의 70~90% 수준)")

class CompanyOutputs(BaseModel):
    actual_market_share: float = Field(description="당시 시장 점유율 (0.0~1.0)")
    actual_accumulated_profit: int = Field(description="누적 이익 (추정치)")

class CompanyData(BaseModel):
    persona: str = Field(description="[1.정체성(매 턴 복사)] [2.상황] [3.지침] 구조의 텍스트")
    inputs: CompanyInputs
    outputs: CompanyOutputs

class TurnData(BaseModel):
    turn: int
    turn_description: str = Field(description="해당 턴의 핵심 사건 요약")
    companies: Dict[str, CompanyData] 

class PhysicsConfig(BaseModel):
    price_sensitivity: float = Field(description="가격 민감도 (20~50)")
    marketing_efficiency: float = Field(description="마케팅 효율 (1.5~3.0)")
    weight_quality: float
    weight_brand: float
    weight_price: float
    others_overall_competitiveness: float

class ScenarioConfig(BaseModel):
    total_turns: int
    market_size: int
    initial_capital: int
    physics: PhysicsConfig
    # [핵심] 자본금 규모에 비례하도록 유도
    marketing_cost_base: float = Field(description="마케팅 기준가 (예상 매출의 10% 수준)")
    rd_innovation_threshold: float = Field(description="R&D 기준가 (예상 매출의 20% 수준)")
    rd_efficiency_threshold: float = Field(description="R&D 효율 기준가 (예상 매출의 20% 수준)")

class ScenarioOutput(BaseModel):
    scenario_name: str
    description: str
    config: ScenarioConfig
    turns_data: List[TurnData]

# (Mock API 함수)
def call_mock_llm_api(prompt: str) -> str:
    print("--- [MOCK] LLM API 호출됨 ---")
    response = [
        {
            "reasoning": "Mock Response: 유지 보수 전략",
            "probability": 1.0,
            "decision": {
                "price": 0, # 0으로 두면 아래 로직에서 원가 기반 자동 설정됨
                "marketing_brand_spend": 0,
                "marketing_promo_spend": 0,
                "rd_innovation_spend": 0,
                "rd_efficiency_spend": 0
            }
        }
    ]
    return json.dumps(response)

# (JSON 추출 함수)
def extract_and_load_json(text: str):
    """
    LLM 응답 텍스트에서 JSON 배열 또는 객체를 추출해서 파싱합니다.
    ```json ... ``` 코드블록이 있으면 그 안을 우선 사용합니다.
    """
    # 0. 우선 전체를 한 번 정리
    raw = text.strip()

    # 1. ```json ... ``` 코드 블록 내부만 추출 (있으면)
    code_block = re.search(r"```json(.*?)```", raw, re.DOTALL | re.IGNORECASE)
    if code_block:
        candidate = code_block.group(1).strip()
    else:
        candidate = raw

    # 2. 앞쪽 잡소리(설명 텍스트) 제거: 가장 먼저 나오는 '[' 또는 '{' 기준으로 자르기
    first_brace = candidate.find('{')
    first_bracket = candidate.find('[')

    if first_brace == -1 and first_bracket == -1:
        print(f"JSON 파싱 오류: 중괄호/대괄호를 찾을 수 없습니다. (Text: {candidate[:80]}...)")
        return None

    if first_bracket != -1 and (first_bracket < first_brace or first_brace == -1):
        # 배열이 먼저 나오는 경우: [ ... ] 전체를 노림
        start = first_bracket
        end = candidate.rfind(']')
    else:
        # 객체가 먼저 나오는 경우: { ... } 전체를 노림
        start = first_brace
        end = candidate.rfind('}')

    if end == -1 or end <= start:
        print(f"JSON 파싱 오류: 닫는 괄호를 찾지 못했습니다. (Text: {candidate[:80]}...)")
        return None

    json_str = candidate[start:end+1]

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"JSON 파싱 오류: {e}")
        print(f"추출된 텍스트(일부): {json_str[:200]}...")
        return None

class AIAgent:
    def __init__(self, name: str, persona: str, use_mock: bool = False):
        self.name = name
        self.persona = persona
        self.use_mock = use_mock
        self.model_name = 'gemini-2.5-pro' # 필요에 따라 모델명 변경 (예: gemini-pro)

        if not self.use_mock and not os.getenv("GOOGLE_API_KEY") and not os.getenv("GEMINI_API_KEY"):
             raise ValueError("GOOGLE_API_KEY 또는 GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")

    async def get_gemini_response_async(self, prompt: str) -> str:
        try:
            print(f"--- (실제 Gemini API 비동기 호출 시작: {self.name}) ---")
            async with genai.Client().aio as client:
                response = await client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
            return response.text
        except Exception as e:
            print(f"!!! Gemini API 비동기 호출 중 오류 발생 ({self.name}): {e} !!!")
            # [수정] 여기서 하드코딩된 JSON을 리턴하지 않고 에러를 던져서
            # decide_action의 try-except 블록이 '현재 상태 기반 Fallback'을 쓰게 유도함
            raise e

    def _create_fallback_decision(self, market_state: dict, reason: str):
        my_data = market_state.get("companies", {}).get(self.name, {})
        current_cost = my_data.get("unit_cost", 100) # 원가 없으면 100
        safe_price = int(current_cost * 1.1) # 10% 마진
        
        current_capital = my_data.get("accumulated_profit", 0)
        safe_budget = max(0, int(current_capital * 0.01))

        print(f"🛡️ [Fallback] {self.name} 안전 모드! 원가({current_cost}) -> 가격({safe_price})")

        return [
            {
                "reasoning": f"시스템 오류({reason})로 인한 안전 모드. 원가({current_cost:.1f}) 기반 방어적 가격 설정.",
                "probability": 1.0,
                "decision": {
                    "price": safe_price,
                    "marketing_brand_spend": int(safe_budget * 0.5),
                    "marketing_promo_spend": 0,
                    "rd_innovation_spend": int(safe_budget * 0.5),
                    "rd_efficiency_spend": 0
                }
            }
        ]

    async def decide_action(self, market_state: dict) -> dict:
        """[Phase 1] R&D 누적 시스템, 물리 엔진 튜닝, 하이브리드 예산 규칙에 따라 행동을 결정합니다."""
        
        opponent_name = market_state.get("opponent_name", "경쟁사")

        # --- 1. 분기 보고서 정보 포맷팅 ---
        quarterly_report_info = ""
        report = market_state.get("quarterly_report")
        if report:
            quarterly_report_info = f"""
            # [A. 지난 분기({report['turn_range'][0]}~{report['turn_range'][1]}턴) 재무제표 (공개 정보)]
            {json.dumps(report['data'], indent=2)}
            """
        else:
            quarterly_report_info = """
            # [A. 지난 분기 재무제표]
            # (이번 턴에는 분기 보고서가 없습니다. '전쟁 안개' 상태입니다.)
            """

        # --- 2. 턴별 요약 정보 포맷팅 ---
        comparison_info = ""
        if market_state.get("last_turn_comparison"):
            comp = market_state["last_turn_comparison"]
            comparison_info = f"""
            # [B. 지난 턴 나의 성과 (단기)]
            * 나의 이익: {comp['my_profit']:,.0f}
            """
        
        summary_info = ""
        if market_state.get("historical_summary"):
            summary = market_state["historical_summary"]
            summary_info = f"""
            # [C. 최근 {summary['window_size']}턴 나의 평균 이익 (중기 추세)]
            * 나의 평균 이익: {summary['my_avg_profit_4turn']:,.0f}
            """

        # --- 3. 예산 제약 조건 포맷팅 (하이브리드 예산) ---
        constraint_info = ""
        my_company_data = market_state.get("companies", {}).get(self.name, {})
        current_unit_cost = my_company_data.get("unit_cost", 0)
        
        # 지난 턴 나의 결정(가격)을 확인 (없으면 기본값)
        last_turn_results = market_state.get("last_turn_results", {})
        last_price = last_turn_results.get(f"{self.name}_price", current_unit_cost * 1.1)
        
        # 단위당 마진 계산
        unit_margin = last_price - current_unit_cost
        margin_rate = (unit_margin / last_price * 100) if last_price > 0 else 0
        
        cfo_warning = ""
        if unit_margin < 0:
            cfo_warning = f"""
            🚨 [CFO 긴급 경고: 역마진(Negative Margin) 발생 중!] 🚨
            * 현재 당신은 물건을 하나 팔 때마다 {abs(unit_margin):,.0f}원씩 손해를 보고 있습니다!
            * 원가({current_unit_cost:,.0f}원) > 판매가({last_price:,.0f}원) 상태입니다.
            * 이 상태가 지속되면 점유율이 높을수록 더 빨리 파산합니다.
            * 즉시 가격을 원가 이상(최소 {current_unit_cost * 1.05:,.0f}원 권장)으로 인상하십시오.
            """
        elif margin_rate < 5.0:
            cfo_warning = f"""
            ⚠️ [CFO 경고: 이익률 위험 수준]
            * 현재 대당 마진이 {unit_margin:,.0f}원 ({margin_rate:.1f}%)에 불과합니다.
            * 마케팅/R&D 비용을 감당하기에 턱없이 부족합니다. 가격 인상을 고려하십시오.
            """
        else:
            cfo_warning = f"""
            ✅ [CFO 보고: 재무 건전성 양호]
            * 현재 대당 마진: {unit_margin:,.0f}원 ({margin_rate:.1f}%)
            * 안정적인 수익 구조를 유지하고 있습니다.
            """
        my_accumulated_profit = my_company_data.get("accumulated_profit", 0)
        
        max_marketing_budget = my_company_data.get('max_marketing_budget', 1000000)
        max_rd_budget = my_company_data.get('max_rd_budget', 500000)
            
        constraint_info = f"""
        # [D. 기업 생존 및 예산 제약 (현실)]
        * (참고) 현재 총 누적 이익(자본): {my_accumulated_profit:,.0f} 원
        
        **[중요: 하이브리드 예산 한도]**
        * **1. 최대 R&D 예산 (전략): {max_rd_budget:,.0f} 원**
            * (이 예산은 매 턴 '총 누적 이익(자본)'에 비례하여 갱신됩니다.)
        * **2. 최대 마케팅 예산 (운영): {max_marketing_budget:,.0f} 원**
            * (이 예산은 4턴(1분기)마다 '지난 분기 이익'을 바탕으로 갱신됩니다.)

        * **'rd_...' 지출 총합은 '최대 R&D 예산'을 초과할 수 없습니다.**
        * **'marketing_...' 지출 총합은 '최대 마케팅 예산'을 초과할 수 없습니다.**
        * **파산(누적 이익 < 0)은 CEO로서 최악의 실패입니다.**
        """

        # --- [신규] 3.5. R&D 누적 현황 정보 (Phase 1 추가) ---
        # simulator.py에서 보내준 누적 포인트와 설정값(threshold)을 읽어옵니다.
        acc_rd_inno = my_company_data.get("accumulated_rd_innovation_point", 0)
        acc_rd_eff = my_company_data.get("accumulated_rd_efficiency_point", 0)
        
        config = market_state.get("config", {})
        thresh_inno = config.get("rd_innovation_threshold", 5000000)
        thresh_eff = config.get("rd_efficiency_threshold", 5000000)
        
        # 달성률 계산 (0으로 나누기 방지)
        percent_inno = (acc_rd_inno / thresh_inno * 100) if thresh_inno > 0 else 0
        percent_eff = (acc_rd_eff / thresh_eff * 100) if thresh_eff > 0 else 0

        rd_status_info = f"""
        # [E. R&D 프로젝트 진행 현황 (누적 시스템)]
        * **혁신(품질) 프로젝트:** 현재 누적 {acc_rd_inno:,.0f} / 목표 {thresh_inno:,.0f} (진척률 {percent_inno:.1f}%)
        * **효율(원가) 프로젝트:** 현재 누적 {acc_rd_eff:,.0f} / 목표 {thresh_eff:,.0f} (진척률 {percent_eff:.1f}%)
        * (목표 금액을 채우면 즉시 기술적 성과(품질 향상 또는 원가 절감)가 발생하고, 누적 포인트는 차감됩니다.)
        """

        # --- 4. 현재 시장 상황 (전쟁 안개 적용) ---
        state_for_prompt = market_state.copy()
        # 프롬프트 토큰 절약을 위해 중복/불필요 정보 제거
        state_for_prompt.pop("last_turn_comparison", None)
        state_for_prompt.pop("historical_summary", None)
        state_for_prompt.pop("quarterly_report", None)
        
        # 상대방의 민감한 정보(예산, 원가 등) 숨기기
        if "companies" in state_for_prompt:
            for name in list(state_for_prompt["companies"].keys()):
                if name != self.name:
                    state_for_prompt["companies"][name].pop("max_marketing_budget", None)
                    state_for_prompt["companies"][name].pop("max_rd_budget", None)
                    state_for_prompt["companies"][name].pop("unit_cost", None)
                    state_for_prompt["companies"][name].pop("accumulated_profit", None)
                    # 품질/브랜드 점수도 가끔은 숨겨질 수 있으나, 지금은 공개 정보로 가정
                    # state_for_prompt["companies"][name].pop("product_quality", None)
                    # state_for_prompt["companies"][name].pop("brand_awareness", None)
                    state_for_prompt["companies"][name].pop("market_share", None)
                    # 상대방 R&D 진행 상황도 숨김 (비밀 프로젝트)
                    state_for_prompt["companies"][name].pop("accumulated_rd_innovation_point", None)
                    state_for_prompt["companies"][name].pop("accumulated_rd_efficiency_point", None)
                else:
                    # 내 정보에서는 점유율만 제거 (결과로 확인하므로)
                    state_for_prompt["companies"][name].pop("market_share", None)
        
        market_snapshot = json.dumps(state_for_prompt, indent=2)

        # --- 5. 최종 프롬프트 생성 (Phase 1 로직 반영) ---
        prompt = f"""
        # [1. 당신의 최종 목표]
        당신의 목표는 경쟁사를 이기고 시뮬레이션 종료 시 **'누적 이익(accumulated_profit)'을 극대화**하는 것입니다.

        # [2. 당신의 전략적 성향 (페르소나)]
        **{self.persona}**

        # [3. 현재 시장 상황 (실시간 공개 정보)]
        {market_snapshot}

        # [3-1. CFO의 재무 분석 리포트 (가장 중요)]
        {cfo_warning}

        # [4. 성과 및 제약 리포트]
        {quarterly_report_info}
        {comparison_info}  
        {summary_info}    
        {constraint_info}
        {rd_status_info} 

        # [5. 새로운 시장 물리 법칙 (Phase 1: 축적과 물리 엔진)]
        당신은 불확실한 도박이 아닌, **'축적의 시간'**을 보내고 있습니다.
        
        * **법칙 1: 자산 감가상각 (Asset Decay)**
            * 품질(Quality)과 브랜드(Brand)는 가만히 있으면 매 턴 하락(Decay)합니다.
            * 현상 유지를 위해서라도 꾸준한 투자가 필요합니다.

        * **법칙 2: R&D 누적 (Accumulation System)**
            * R&D는 마일스톤(목표 금액)을 달성할 때까지 투자를 '누적'해야 합니다.**
            * [E. R&D 프로젝트 진행 현황]을 참고하여, 조금씩 꾸준히 투자할지, 아니면 한 번에 큰돈을 부어 기술 격차를 벌릴지 결정하십시오.
            * `rd_innovation_spend`: 품질 향상 프로젝트에 누적됩니다. (제품 경쟁력 상승)
            * `rd_efficiency_spend`: 원가 절감 프로젝트에 누적됩니다. (이익률 개선)

        * **법칙 3: 마케팅 효율 (Marketing Physics)**
            * 마케팅은 브랜드 자산을 쌓습니다.
            * `marketing_brand_spend`: 장기적인 브랜드 인지도를 높입니다.
            * `marketing_promo_spend`: 이번 턴에만 적용되는 가격 할인(판촉) 효과를 냅니다.

        * **법칙 4: 하이브리드 예산**
            * R&D 예산은 '총자본'에서 나오므로 장기적인 계획이 가능합니다.
            * 마케팅 예산은 '분기 이익'에서 나오므로 실적이 나쁘면 예산이 삭감됩니다.

        위 정보를 바탕으로, [2. 페르소나]에 맞춰 4가지 지출 항목에 예산을 현명하게 배분하십시오.

        # [6. 응답 형식]
        반드시 3가지의 논리적인 전략적 선택지를 포함한 JSON 배열 형식으로 응답해야 합니다.
        각 선택지는 'reasoning', 'probability', 'decision' 키를 포함해야 합니다.
        'probability'의 총합은 1.0이어야 합니다.
        예시는 다음과 같습니다.
        [
            {{
                "reasoning": "경쟁사의 기술 추격을 따돌리기 위해 혁신 R&D에 집중 투자하여 마일스톤을 달성합니다.",
                "probability": 0.6,
                "decision": {{
                "price": 20000,
                "marketing_brand_spend": 1000000,
                "marketing_promo_spend": 0,
                "rd_innovation_spend": 3000000,
                "rd_efficiency_spend": 0
                }}
            }},
            {{
                "reasoning": "R&D 투자를 잠시 줄이고 마케팅 판촉에 집중하여 단기 점유율을 방어합니다.",
                "probability": 0.4,
                "decision": {{
                "price": 19000,
                "marketing_brand_spend": 2000000,
                "marketing_promo_spend": 1500000,
                "rd_innovation_spend": 500000,
                "rd_efficiency_spend": 0
                }}
            }}
        ]
        """
        
        # --- 7. API 호출 및 파싱 ---
        try:
            if self.use_mock:
                response_text = call_mock_llm_api(prompt) 
            else:
                response_text = await self.get_gemini_response_async(prompt)
            
            # extract_and_load_json은 JSON 배열(list)을 반환해야 함
            choices_list = extract_and_load_json(response_text)

            if choices_list is None or not isinstance(choices_list, list):
                print(f"오류: AI 응답이 JSON 배열이 아닙니다. 응답: {response_text[:100]}...")
                raise json.JSONDecodeError("JSON 파싱 함수가 list를 반환하지 않음", response_text, 0)

            # [호환성 처리 및 안전장치]
            for choice in choices_list:
                decision = choice.get("decision", {})
                
                # 가격이 0이거나 터무니없이 작으면 원가 기반 보정
                price = decision.get("price", 0)
                my_cost = market_state.get("companies", {}).get(self.name, {}).get("unit_cost", 100)
                if price <= 0:
                     decision["price"] = int(my_cost * 1.1)
                
                # 키 이름 보정 (구버전 호환)
                if "marketing_spend" in decision and "marketing_brand_spend" not in decision:
                    decision["marketing_brand_spend"] = int(decision.get("marketing_spend", 0))
                if "rd_spend" in decision and "rd_innovation_spend" not in decision:
                    decision["rd_innovation_spend"] = int(decision.get("rd_spend", 0))
                
                choice["decision"] = decision 

            return choices_list 

        except Exception as e:
            # [핵심] 모든 에러(API, 파싱 등)를 잡아서 안전 모드 가동
            return self._create_fallback_decision(market_state, str(e))
        
SCENARIO_DESIGNER_SYSTEM_PROMPT = """
당신은 정교한 '비즈니스 워게임 시뮬레이션 설계자'입니다.
사용자 주제를 바탕으로 JSON 시나리오를 작성하되, **AI 에이전트가 시뮬레이션 변수(점유율, 이익 등)를 보고 판단할 수 있는 "구체적이고 실전적인 페르소나"**를 작성해야 합니다.
문장을 길게 쓰지 말고 **핵심만 짧게** 쓰십시오.

### 1. 페르소나 작성 규칙 (Simulation-Friendly)
각 회사의 `persona`는 아래 3단 구조를 따르며, **시뮬레이션 변수(Market Share, Profit, R&D, Cost)**를 직접 언급해야 합니다.

* **[1. 정체성 (Identity)]**: 회사의 궁극적 목표 (1턴부터 10턴까지 **동일한 문장 복사**)
    * 예: "우리는 **고마진(High Profit)**과 **프리미엄 브랜드(High Brand)**를 추구하는 럭셔리 기업입니다."

* **[2. 상황 (Context)]**: 현재 수치적 상황 요약
    * 예: "**점유율(Market Share)** 안정적 / **매출 성장(Revenue Growth)** 정체."

* **[3. 지침 (Directive)]**: 구체적인 행동 전략 (우선순위 설정)
    * 상황에 따라 **'선택과 집중'** 혹은 **'균형 유지'**를 명확히 지시하십시오.
    * **Type A (공격/위기):** "~를 희생해서라도 ~를 달성하라." (Trade-off)
        * 예: "가격을 낮춰 **단기 이익(Profit)** 희생/**점유율(Share)** 방어."
    * **Type B (안정/성장):** "~와 ~의 균형을 맞춰라." (Balance)
        * 예: "안정적인 선에서 **R&D 혁신(Innovation)** 투자 증가."

### 2. 분량 및 구조
* **총 10턴(Turns)**으로 구성하십시오.
* `turn_description`: 1문장 요약.
* 시나리오에서 시장의 판도를 가장 크게 바꾸는 턴을 **핵심 턴**이라 규정합니다.
* **핵심 턴**은 반드시 전체 턴(10턴)의 중앙(4~5턴)이어야 합니다.

### 3. 경제 데이터 (Realistic Data)
* `unit_cost`: 판매가(`price`) 대비 마진(10~30%)을 고려하여 **반드시 정수(Integer)**로 기입.
* `marketing_cost_base` 등은 자본금 규모에 맞춰 현실적으로 설정.

### 4. 출력 형식
* 오직 **순수한 JSON 문자열**만 출력하십시오.
* `companies` 내부 데이터는 반드시 `inputs`과 `outputs` 객체로 분리해야 합니다. **구조 평탄화 금지.**

---
**[JSON 출력 예시 (Strictly Follow)]**
{
  "scenario_name": "Smartphone Wars 2010",
  "description": "Apple vs Samsung competition...",
  "config": {
    "total_turns": 10,
    "market_size": 1000000,
    "initial_capital": 5000000000,
    "physics": { "price_sensitivity": 30.0, "marketing_efficiency": 2.0, "weight_quality": 0.5, "weight_brand": 0.3, "weight_price": 0.2, "others_overall_competitiveness": 0.5 },
    "marketing_cost_base": 2000000,
    "rd_innovation_threshold": 100000000
  },
  "turns_data": [
    {
      "turn": 0,
      "turn_description": "Galaxy S 출시로 인한 경쟁 본격화.",
      "companies": {
        "Apple": {
          "persona": "[1.정체성] 우리는 **고마진(High Profit)**과 **프리미엄 브랜드(High Brand)**를 최우선으로 추구합니다. 점유율보다 대당 순이익을 중시합니다. [2.상황] 독점적 지위가 흔들림. [3.지침] **가격(Price) 방어**, **이익(Profit) 우선**, **마케팅(Marketing) 집중**.",
          "inputs": { 
            "price": 800, "unit_cost": 400, 
            "marketing_spend_ratio": 0.2, "rd_spend_ratio": 0.1, 
            "initial_quality": 90, "initial_brand": 95 
          },
          "outputs": { "actual_market_share": 0.45, "actual_accumulated_profit": 100000000 }
        },
        "Samsung": {
          "persona": "[1.정체성] 우리는 **시장 점유율(Market Share)** 극대화와 **가격 경쟁력(Price Competitiveness)**을 핵심 가치로 삼습니다. [2.상황] 시장 진입 초기. [3.지침] **이익(Profit) 희생**, **점유율(Share) 확대**, **저가 정책(Low Price)**.",
          "inputs": { 
            "price": 600, "unit_cost": 350, 
            "marketing_spend_ratio": 0.3, "rd_spend_ratio": 0.1, 
            "initial_quality": 80, "initial_brand": 60 
          },
          "outputs": { "actual_market_share": 0.25, "actual_accumulated_profit": 50000000 }
        }
      }
    },
    {
      "turn": 1,
      "turn_description": "보급형 모델 확산으로 삼성 점유율 상승.",
      "companies": {
        "Apple": {
          "persona": "[1.정체성] 우리는 **고마진(High Profit)**과 **프리미엄 브랜드(High Brand)**를 최우선으로 추구합니다. 점유율보다 대당 순이익을 중시합니다. (복사됨) [2.상황] 경쟁사 추격 허용. [3.지침] **가격(Price) 동결**, **R&D 품질 혁신(Innovation)**, **격차 유지**.",
          "inputs": { 
            "price": 800, "unit_cost": 390, 
            "marketing_spend_ratio": 0.2, "rd_spend_ratio": 0.15,
            "initial_quality": 92, "initial_brand": 94
          },
          "outputs": { 
            "actual_market_share": 0.42, 
            "actual_accumulated_profit": 250000000 
          }
        },
        "Samsung": {
          "persona": "[1.정체성] 우리는 **시장 점유율(Market Share)** 극대화와 **가격 경쟁력(Price Competitiveness)**을 핵심 가치로 삼습니다. (복사됨) [2.상황] 점유율 확대 성공. [3.지침] **마진(Margin) 최소화**, **물량 공세(Volume)**, **판촉 강화**.",
          "inputs": { 
            "price": 550, "unit_cost": 340, 
            "marketing_spend_ratio": 0.25, "rd_spend_ratio": 0.1,
            "initial_quality": 82, "initial_brand": 65
          },
          "outputs": { 
            "actual_market_share": 0.30, 
            "actual_accumulated_profit": 130000000 
          }
        }
      }
    }
  ]
}
"""

async def generate_scenario_async(topic: str, model_name: str = 'gemini-2.5-pro') -> dict:
    """
    LLM을 사용하여 주제(topic)에 맞는 시나리오 JSON을 생성합니다.
    """
    if not os.getenv("GOOGLE_API_KEY") and not os.getenv("GEMINI_API_KEY"):
        print("!!! API Key not found. Returning MOCK Scenario. !!!")
        return _generate_mock_scenario(topic)

    prompt = f"""
    주제: "{topic}"
    위 주제로 시뮬레이션 시나리오 JSON을 작성해줘.
    """

    try:
        print(f"--- (Scenario Generation Start: {topic}) ---")
        
        async with genai.Client().aio as client:
            response = await client.models.generate_content(
                model=model_name,
                contents=prompt,
                # [핵심 수정] Native JSON Mode 활성화 & 토큰 한도 최대치
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    # response_schema=ScenarioOutput,
                    system_instruction=SCENARIO_DESIGNER_SYSTEM_PROMPT,
                    max_output_tokens=8192, 
                    temperature=0.7,
                )
            )
        
        scenario_json = json.loads(response.text)
        
        # Native JSON 모드는 마크다운 없이 순수 JSON만 주므로 바로 파싱 가능
        try:
            config = scenario_json.get("config", {})
            market_size = config.get("market_size", 1000000)
            
            # 대표 가격 찾기 (첫 턴의 첫 회사 가격 참조)
            first_turn = scenario_json.get("turns_data", [])[0]
            first_company = list(first_turn.get("companies", {}).values())[0]
            price = first_company.get("inputs", {}).get("price", 100)
            
            # 예상 시장 총 매출 (Total Addressable Market Revenue)
            estimated_revenue = market_size * price
            
            # 밸런싱 공식 적용
            # - 마케팅 기준가: 매출의 10% (이 정도 써야 브랜드 점수 오름)
            # - R&D 임계값: 매출의 20% (이 정도 써야 기술 혁신 일어남)
            new_mkt_base = int(estimated_revenue * 0.1)
            new_rd_threshold = int(estimated_revenue * 0.2)
            
            print(f"🔧 [Auto-Balance] Revenue: {estimated_revenue:,}")
            print(f"   -> Marketing Base: {new_mkt_base:,} (Was: {config.get('marketing_cost_base', 'N/A')})")
            print(f"   -> R&D Threshold:  {new_rd_threshold:,}")

            # 값 덮어쓰기
            scenario_json["config"]["marketing_cost_base"] = new_mkt_base
            scenario_json["config"]["rd_innovation_threshold"] = new_rd_threshold
            scenario_json["config"]["rd_efficiency_threshold"] = new_rd_threshold

        except json.JSONDecodeError:
            # 혹시라도 실패하면 기존 추출 함수 시도
            print(f"⚠️ Auto-balancing skipped due to error: {e}")
            scenario_json = extract_and_load_json(response.text)
        
        if not scenario_json:
            print(f"Truncated Text Check: ...{response.text[-200:]}")
            raise ValueError("LLM이 유효한 JSON을 반환하지 않았습니다.")
            
        return scenario_json

    except Exception as e:
        print(f"!!! Scenario Generation Error: {e} !!!")
        raise e

def _generate_mock_scenario(topic: str) -> dict:
    """API 키가 없을 때 반환할 더미 데이터"""
    return {
        "scenario_name": f"Mock Scenario: {topic}",
        "description": "API 키가 없어 생성된 테스트 데이터입니다.",
        "config": {
            "total_turns": 5,
            "market_size": 100000,
            "initial_capital": 1000000000,
            "physics": {"price_sensitivity": 20}
        },
        "turns_data": []
    }