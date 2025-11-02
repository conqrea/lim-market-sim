# agent.py ('Others' 인지, R&D 제거, 최종본)

import json
import random
import os
from google import genai
from dotenv import load_dotenv
import re

load_dotenv()

# (call_mock_llm_api, extract_and_load_json 함수는 기존과 동일)
def call_mock_llm_api(prompt: str) -> str:
    print("--- (Mock API 호출됨, 비용 0원) ---")
    price = random.randint(8000, 12000)
    marketing_spend = random.randint(300000, 700000)
    decision = {"price": price, "marketing_spend": marketing_spend}
    return json.dumps(decision)

def extract_and_load_json(text: str):
    json_pattern = re.compile(r'(\{.*\})|(\[.*\])', re.DOTALL)
    match = json_pattern.search(text)
    if match:
        json_string = match.group(0).strip()
        try:
            data = json.loads(json_string)
            return data
        except json.JSONDecodeError as e:
            print(f"오류: 추출된 텍스트는 유효한 JSON이 아닙니다. ({e})")
            print(f"추출된 텍스트: {repr(json_string[:50])}...")
            return None
    else:
        print("오류: 입력 문자열에서 JSON 구조를 찾지 못했습니다 ({} 또는 []).")
        return None

# (AIAgent 클래스)
class AIAgent:
    def __init__(self, name: str, persona: str, use_mock: bool = True):
        self.name = name
        self.persona = persona
        self.use_mock = use_mock
        self.model_name = 'gemini-2.5-pro' 

        if not self.use_mock and not os.getenv("GOOGLE_API_KEY") and not os.getenv("GEMINI_API_KEY"):
             raise ValueError("GOOGLE_API_KEY 또는 GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")

        print(f"AI 에이전트 '{self.name}' 생성 완료. Mock 모드: {self.use_mock}")

    # (get_gemini_response_async 함수는 기존과 동일)
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
            return '{"price": 10000, "marketing_spend": 100000}'

    # [핵심 수정] decide_action 함수
    async def decide_action(self, market_state: dict) -> dict:
        """시장 상황을 보고 다음 행동을 비동기적으로 결정합니다."""
        
        event_info = ""
        if market_state.get("active_events"):
            event_info = f"""
            # !! 중요: 현재 발동 중인 시장 이벤트 !!
            {json.dumps(market_state["active_events"], indent=2)}
            """

        comparison_info = ""
        if market_state.get("last_turn_comparison"):
            comp = market_state["last_turn_comparison"]
            comparison_info = f"""
            # [A. 지난 턴 성과 (단기)]
            * 나의 이익: {comp['my_profit']:,.0f}
            * (주요경쟁사) 이익: {comp['opponent_profit']:,.0f}
            """

        summary_info = ""
        if market_state.get("historical_summary"):
            summary = market_state["historical_summary"]
            summary_info = f"""
            # [B. 최근 {summary['window_size']}턴 평균 성과 (중기 추세)]
            * 나의 평균 이익: {summary['my_avg_profit_5turn']:,.0f}
            * 나의 평균 점유율: {summary['my_avg_share_5turn']:.2%}
            * (시장 평균) 'Others'의 평균 점유율: {summary['others_avg_share_5turn']:.2%}
            """

        constraint_info = ""
        my_company_data = market_state.get("companies", {}).get(self.name, {})
        my_accumulated_profit = my_company_data.get("accumulated_profit", 0)
        
        max_marketing_budget = max(1000000, min(my_accumulated_profit * 0.1, 20000000))
        if my_accumulated_profit <= 0:
            max_marketing_budget = 1000000

        constraint_info = f"""
        # [C. 기업 생존 및 예산 제약 (현실)]
        * 현재 총 누적 이익(자본): {my_accumulated_profit:,.0f} 원
        * 이번 턴 최대 마케팅 예산: {max_marketing_budget:,.0f} 원
        * **'marketing_spend' 값은 이 예산을 절대 초과할 수 없습니다.**
        * **파산(누적 이익 < 0)은 CEO로서 최악의 실패입니다.**
        """

        prompt = f"""
        # [1. 당신의 최종 목표 (가장 중요)]
        당신의 유일하고 궁극적인 목표는 시뮬레이션 종료 시 **'누적 이익(accumulated_profit)'을 극대화**하는 것입니다.

        # [2. 당신의 전략적 성향 (페르소나)]
        당신은 이 목표를 달성하기 위해 다음과 같은 성향을 가진 CEO입니다.
        **{self.persona}**
        * 이 페르소나는 당신의 '스타일'이며, 최종 목표(누적 이익)를 훼손하면서까지 맹목적으로 따라서는 안 됩니다.

        # [3. 현재 시장 상황]
        # [수정] 이제 'Others'가 포함된 3개 회사의 정보가 제공됩니다.
        # 'Others'는 시장 평균가를 따르는 규칙 기반의 더미 경쟁자입니다.
        {json.dumps(market_state, indent=2)}
        {event_info} 
        
        # [4. 성과 분석 리포트]
        {comparison_info}  
        {summary_info}    
        {constraint_info} 

        # [5. 당신의 임무]
        당신의 경쟁자는 'Samsung'(주요 AI 경쟁자)과 'Others'(시장 평균)입니다.
        [1. 최종 목표]를 달성하기 위해, [2. 페르소나] 스타일을 참고하여,
        [3. 시장 상황]과 [4. 성과 리포트]를 종합적으로 분석하십시오.
        
        **[현실적인 CEO의 조언]**
        * **제로섬 게임이 아님:** 이제 당신의 점유율은 'Others'로부터 뺏어올 수도, 'Others'에게 뺏길 수도 있습니다.
        * **균형:** 이익과 점유율 중 하나를 완전히 포기하지 마십시오.
        * **마케팅:** 'Others'와의 경쟁에서 밀리지 않으려면(점유율 방어), '보수적' CEO도 최소한의 방어적 마케팅은 집행해야 합니다.
        
        [C. 예산 제약 조건]의 한계 내에서 합리적인 결정을 내리십시오.

        # [6. 응답 형식]
        반드시 2가지 키를 포함한 JSON 형식으로 응답해야 합니다.
        {{
            "reasoning": "<1~2줄의 간결한 의사결정 이유. *가격, 마케팅*을 어떻게 균형 잡았는지 설명.>",
            "price": <가격 (정수)>,
            "marketing_spend": <마케팅 비용 (정수)>
        }}
        """
        
        if self.use_mock:
            response_text = call_mock_llm_api(prompt)
        else:
            response_text = await self.get_gemini_response_async(prompt)

        try:
            decision = extract_and_load_json(response_text)
            if decision is None:
                raise json.JSONDecodeError("JSON 파싱 함수가 None을 반환", response_text, 0)
            
            return decision
        except json.JSONDecodeError:
            print("오류: LLM 응답이 유효한 JSON이 아닙니다. 응답:", response_text)
            return {"price": 10000, "marketing_spend": 100000}