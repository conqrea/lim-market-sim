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
    response = {
        "reasoning": "Mock API 응답: R&D(혁신/효율)와 마케팅(브랜드/판촉)에 예산을 배분했습니다.",
        "price": 10000 + random.randint(-500, 500),
        "marketing_brand_spend": 1000000,
        "marketing_promo_spend": 500000,
        "rd_innovation_spend": 2000000,
        "rd_efficiency_spend": 1000000
    }
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
        self.model_name = 'gemini-2.5-pro'

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
            return {
                "reasoning": f"API 호출 오류: {e}",
                "price": 10000,
                "marketing_spend": 100000,
                "rd_spend": 100000
            }

    async def decide_action(self, market_state: dict) -> dict:
        """[신규 엔진 적용] 무형 자산, 자산 감가상각, R&D 도박, 하이브리드 예산 규칙에 따라 행동을 결정합니다."""
        
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

        # --- 4. 현재 시장 상황 (전쟁 안개 적용) ---
        state_for_prompt = market_state.copy()
        state_for_prompt.pop("last_turn_comparison", None)
        state_for_prompt.pop("historical_summary", None)
        state_for_prompt.pop("quarterly_report", None)
        
        if "companies" in state_for_prompt:
            for name in list(state_for_prompt["companies"].keys()):
                if name != self.name:
                    state_for_prompt["companies"][name].pop("max_marketing_budget", None)
                    state_for_prompt["companies"][name].pop("max_rd_budget", None)
                    state_for_prompt["companies"][name].pop("unit_cost", None)
                    state_for_prompt["companies"][name].pop("accumulated_profit", None)
                    state_for_prompt["companies"][name].pop("product_quality", None)
                    state_for_prompt["companies"][name].pop("brand_awareness", None)
                    state_for_prompt["companies"][name].pop("market_share", None)
                else:
                    state_for_prompt["companies"][name].pop("market_share", None)
        
        market_snapshot = json.dumps(state_for_prompt, indent=2)

        # --- 5. 최종 프롬프트 생성 ---
        prompt = f"""
        # [1. 당신의 최종 목표 (가장 중요)]
        당신의 유일하고 궁극적인 목표는 시뮬레이션 종료 시 **'누적 이익(accumulated_profit)'을 극대화**하는 것입니다.

        # [2. 당신의 전략적 성향 (페르소나)]
        **{self.persona}**

        # [3. 현재 시장 상황 (실시간 공개 정보)]
        {market_snapshot}

        # [4. 성과 분석 리포트 (지연/내부 정보)]
        {quarterly_report_info}
        {comparison_info}  
        {summary_info}    
        {constraint_info} 

        # [5. 당신의 임무: 새로운 물리 법칙]
        당신의 **유일한 AI 경쟁자는 '{opponent_name}'**입니다. 'Others'는 시장 배경입니다.
        당신은 **'전쟁 안개'** 속에 있습니다.
        
        **[현실적인 CEO의 조언: 새로운 시장 법칙]**
        
        * **법칙 1: 자산 감가상각 (Asset Decay)**
            * 당신의 핵심 자산인 '제품 품질(product_quality)'과 '브랜드 인지도(brand_awareness)'는 **매 턴 하락(Decay)**합니다. (config의 decay_rate 참조)
            * 지출을 0으로 설정하는 것은 '현상 유지'가 아니라 '시장 도태'를 의미합니다.
            * 당신은 '하락'을 막기 위한 **최소한의 '유지비'**를 R&D와 마케팅에 지출해야 합니다.

        * **법칙 2: R&D 도박 (R&D Gamble)**
            * R&D 예산은 두 가지 '도박'에 사용됩니다.
            * **`rd_innovation_spend`**: '제품 품질'을 높이기 위한 '혁신' 베팅입니다. (config의 prob/cost/impact 참조)
            * **`rd_efficiency_spend`**: '원가(unit_cost)'를 낮추기 위한 '효율' 베팅입니다. (config의 prob/cost/impact 참조)
            * R&D 지출은 '보장된 성공'이 아니며, 확률에 따라 실패할 수 있습니다.

        * **법칙 3: 마케팅 투자 (Marketing Investment)**
            * 마케팅 예산은 두 가지로 사용됩니다.
            * **`marketing_brand_spend`**: '브랜드 인지도' 자산을 쌓는 장기 투자입니다. (수확 체감 적용됨)
            * **`marketing_promo_spend`**: 이번 턴에만 가격을 할인하는 '단기 판촉' 비용입니다.

        * **법칙 4: 시장 점유율 (가치 점수)**
            * 당신의 시장 점유율은 `(제품 품질 x 50%) + (브랜드 인지도 x 30%) + (가격 경쟁력 x 20%)`의 비율로 계산되는 **'가치 점수(Value Score)'**에 의해 결정됩니다.

        * **법칙 5: 하이브리드 예산 (전략적 선택)**
            * [D]의 예산 규칙을 확인하십시오.
            * **R&D 예산(총자본 기반)**은 단기 손실을 봐도 유지될 수 있지만, **마케팅 예산(분기 이익 기반)**은 단기 손실을 보면 삭감될 위험이 있습니다.
        
        [D]의 예산 제약 조건의 한계 내에서, [2. 페르소나]에 맞춰 4가지 지출 항목에 예산을 현명하게 배분하십시오.

        # [6. 응답 형식]
        반드시 5가지 키를 포함한 JSON 형식으로 응답해야 합니다.
        (총합이 [D]의 예산 한도를 넘지 않도록 주의하십시오.)
        {{
            "reasoning": "<1~2줄의 간결한 의사결정 이유. [D]의 예산 한도 내에서 4가지 지출 항목에 예산을 배분.>",
            "price": <가격 (정수)>,
            "marketing_brand_spend": <브랜드 인지도 투자 비용 (정수)>,
            "marketing_promo_spend": <단기 판촉 비용 (정수)>,
            "rd_innovation_spend": <품질 혁신 R&D 베팅 비용 (정수)>,
            "rd_efficiency_spend": <원가 절감 R&D 베팅 비용 (정수)>
        }}
        """
        
        # --- 7. API 호출 및 파싱 ---
        if self.use_mock:
            response_text = call_mock_llm_api(prompt)
        else:
            response_text = await self.get_gemini_response_async(prompt)

        try:
            decision = extract_and_load_json(response_text)
            
            if decision is None:
                print(f"오류: AI 응답에서 JSON을 추출하지 못했습니다. 응답: {response_text[:100]}...")
                if "{" not in response_text:
                    return {"reasoning": response_text, "price": 10000, "marketing_brand_spend": 100000, "marketing_promo_spend": 0, "rd_innovation_spend": 100000, "rd_efficiency_spend": 0}
                raise json.JSONDecodeError("JSON 파싱 함수가 None을 반환", response_text, 0)
            
            # [수정] AI가 구버전으로 응답했을 경우를 대비한 호환성 처리
            if "marketing_spend" in decision:
                decision["marketing_brand_spend"] = int(decision.get("marketing_spend", 0))
                decision["marketing_promo_spend"] = 0
            if "rd_spend" in decision:
                decision["rd_innovation_spend"] = int(decision.get("rd_spend", 0))
                decision["rd_efficiency_spend"] = 0

            return decision
        
        except json.JSONDecodeError as e:
            print(f"오류: LLM 응답이 유효한 JSON이 아닙니다. (에러: {e}) 응답: {response_text[:100]}...")
            return {"reasoning": "JSON 파싱 오류. 기본값으로 결정.", "price": 10000, "marketing_brand_spend": 100000, "marketing_promo_spend": 0, "rd_innovation_spend": 100000, "rd_efficiency_spend": 0}