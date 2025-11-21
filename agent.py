# agent.py

import json
import random
import os
from google import genai
from dotenv import load_dotenv
import re

load_dotenv()

# (Mock API 함수)
def call_mock_llm_api(prompt: str) -> str:
    """LLM API를 모방하는 목(Mock) 함수입니다."""
    print("--- [MOCK] LLM API 호출됨 ---")
    # Mock 응답도 JSON 배열 형태로 반환하도록 수정
    response = [
        {
            "reasoning": "Mock API 응답: R&D(혁신/효율) 누적을 위해 꾸준히 투자하고, 마케팅으로 브랜드를 방어합니다.",
            "probability": 0.6,
            "decision": {
                "price": 10000 + random.randint(-500, 500),
                "marketing_brand_spend": 1000000,
                "marketing_promo_spend": 0,
                "rd_innovation_spend": 2000000,
                "rd_efficiency_spend": 1000000
            }
        },
        {
            "reasoning": "Mock API 응답 (대안): 공격적인 가격 인하로 점유율을 노립니다.",
            "probability": 0.4,
            "decision": {
                "price": 9000,
                "marketing_brand_spend": 500000,
                "marketing_promo_spend": 500000,
                "rd_innovation_spend": 1000000,
                "rd_efficiency_spend": 0
            }
        }
    ]
    return json.dumps(response)

# (JSON 추출 함수)
def extract_and_load_json(text: str) -> dict:
    """LLM 응답 텍스트에서 JSON 블록을 추출하여 파싱합니다."""
    match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if match:
        json_str = match.group(1)
    else:
        json_str = text
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"JSON 파싱 오류: {e}")
        print(f"원본 텍스트: {text[:200]}...") 
        if "{" not in text:
            return None
        return None 

class AIAgent:
    def __init__(self, name: str, persona: str, use_mock: bool = False):
        self.name = name
        self.persona = persona
        self.use_mock = use_mock
        self.model_name = 'gemini-2.0-flash' # 필요에 따라 모델명 변경 (예: gemini-pro)

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
            # 에러 발생 시 안전한 기본값 반환
            error_fallback = [
                {
                    "reasoning": f"API 호출 오류 발생: {e}. 기본 방어 전략을 수행합니다.",
                    "probability": 1.0,
                    "decision": {
                        "price": 10000,
                        "marketing_brand_spend": 100000,
                        "marketing_promo_spend": 0,
                        "rd_innovation_spend": 100000,
                        "rd_efficiency_spend": 0
                    }
                }
            ]
            return json.dumps(error_fallback)

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
            * R&D는 더 이상 '확률 도박'이 아닙니다. **마일스톤(목표 금액)을 달성할 때까지 투자를 '누적'해야 합니다.**
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
        if self.use_mock:
            response_text = call_mock_llm_api(prompt) 
        else:
            response_text = await self.get_gemini_response_async(prompt)

        try:
            # extract_and_load_json은 JSON 배열(list)을 반환해야 함
            choices_list = extract_and_load_json(response_text)

            if choices_list is None or not isinstance(choices_list, list):
                print(f"오류: AI 응답이 JSON 배열이 아닙니다. 응답: {response_text[:100]}...")
                raise json.JSONDecodeError("JSON 파싱 함수가 list를 반환하지 않음", response_text, 0)

            # [호환성 처리] 각 선택지(choice) 내부의 decision 객체 키 확인 및 보정
            for choice in choices_list:
                decision = choice.get("decision", {})
                # 혹시 AI가 구버전 키(marketing_spend 등)를 썼을 경우를 대비해 변환
                if "marketing_spend" in decision and "marketing_brand_spend" not in decision:
                    decision["marketing_brand_spend"] = int(decision.get("marketing_spend", 0))
                    decision["marketing_promo_spend"] = 0
                if "rd_spend" in decision and "rd_innovation_spend" not in decision:
                    decision["rd_innovation_spend"] = int(decision.get("rd_spend", 0))
                    decision["rd_efficiency_spend"] = 0
                choice["decision"] = decision 

            return choices_list 

        except json.JSONDecodeError as e:
            print(f"오류: LLM 응답이 유효한 JSON 배열이 아닙니다. (에러: {e}) 응답: {response_text[:100]}...")
            # 에러 발생 시 기본 선택지 반환
            return [
                {
                    "reasoning": "JSON 파싱 오류. 기본 보수적 전략으로 결정.",
                    "probability": 1.0,
                    "decision": {
                        "price": 10000,
                        "marketing_brand_spend": 100000,
                        "marketing_promo_spend": 0,
                        "rd_innovation_spend": 100000,
                        "rd_efficiency_spend": 0
                    }
                }
            ]