# agent.py (공식 문서의 Client 패턴을 정확히 반영한 최종 버전)

import json
import random
import os
import google.genai as genai
from dotenv import load_dotenv
import re

# .env 파일은 스크립트 시작 시 한 번만 로드합니다.
# 라이브러리는 'GOOGLE_API_KEY' 환경 변수를 자동으로 찾습니다.
# 만약 .env 파일에 'GEMINI_API_KEY'로 저장했다면, 아래와 같이 이름을 맞춰주세요.
# os.environ['GOOGLE_API_KEY'] = os.getenv('GEMINI_API_KEY')
load_dotenv()


# --- 1. 가짜 API 함수 (기존과 동일) ---
def call_mock_llm_api(prompt: str) -> str:
    print("--- (Mock API 호출됨, 비용 0원) ---")
    price = random.randint(8000, 12000)
    marketing_spend = random.randint(300000, 700000)
    decision = {"price": price, "marketing_spend": marketing_spend}
    return json.dumps(decision)

def extract_and_load_json(text: str):
        # 정규표현식 패턴
        # 패턴 설명:
        # 1. (\{.*\}): 중괄호 `{}`로 시작하고 끝나는 문자열 (JSON 객체)
        # 2. |: OR 연산자
        # 3. (\[.*\]): 대괄호 `[]`로 시작하고 끝나는 문자열 (JSON 배열)
        # re.DOTALL: `.`이 줄바꿈 문자(\n)까지 포함하도록 설정 (여러 줄에 걸친 JSON 파싱 가능)
        
        # 이 패턴은 가장 바깥쪽의 { ... } 또는 [ ... ] 구조를 찾습니다.
        json_pattern = re.compile(r'(\{.*\})|(\[.*\])', re.DOTALL)
        
        # 문자열에서 패턴과 일치하는 첫 번째 항목을 검색
        match = json_pattern.search(text)
        
        if match:
            # 매치된 텍스트 중 공백을 제거하여 실제 JSON 문자열 추출
            # match.group(0)은 전체 매치된 문자열입니다.
            json_string = match.group(0).strip()
            
            try:
                # JSON 문자열을 파이썬 객체로 변환
                data = json.loads(json_string)
                return data
            except json.JSONDecodeError as e:
                # 추출된 문자열이 유효한 JSON이 아닌 경우
                print(f"오류: 추출된 텍스트는 유효한 JSON이 아닙니다. ({e})")
                print(f"추출된 텍스트: {repr(json_string[:50])}...")
                return None
        else:
            # JSON 구조를 찾지 못한 경우
            print("오류: 입력 문자열에서 JSON 구조를 찾지 못했습니다 ({} 또는 []).")
            return None

class AIAgent:
    def __init__(self, name: str, persona: str, use_mock: bool = True):
        self.name = name
        self.persona = persona
        self.use_mock = use_mock
        self.model_name = 'gemini-2.5-pro'

        # [핵심 변경]
        # genai.configure() 호출을 완전히 제거했습니다.
        # Client()가 환경 변수를 자동으로 읽어 인증을 처리합니다.
        # 따라서, 생성자에서는 아무런 설정 코드가 필요 없습니다.
        if not self.use_mock and not os.getenv("GOOGLE_API_KEY") and not os.getenv("GEMINI_API_KEY"):
             raise ValueError("GOOGLE_API_KEY 또는 GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")

        print(f"AI 에이전트 '{self.name}' 생성 완료. Mock 모드: {self.use_mock}")


    # --- 2. 최신 비동기 API 호출 함수 ---
    async def get_gemini_response_async(self, prompt: str) -> str:
        """
        최신 google-genai SDK의 비동기 클라이언트를 사용하여 API를 호출합니다.
        """
        try:
            print(f"--- (실제 Gemini API 비동기 호출 시작: {self.name}) ---")
            # Client() 객체는 API 키를 자동으로 환경 변수에서 가져옵니다.
            async with genai.Client().aio as client:
                response = await client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
            return response.text
        except Exception as e:
            print(f"!!! Gemini API 비동기 호출 중 오류 발생 ({self.name}): {e} !!!")
            return '{"price": 10000, "marketing_spend": 100000}' # 오류 시 기본값 반환

    

    # --- 3. 비동기 행동 결정 함수 (변경 없음) ---
    async def decide_action(self, market_state: dict) -> dict:
        """시장 상황을 보고 다음 행동을 비동기적으로 결정합니다."""
        prompt = f"""
        # 역할
        당신은 '{self.name}' 회사의 CEO입니다. 당신의 페르소나는 다음과 같습니다:
        {self.persona}

        # 현재 시장 및 우리 회사 재무 상황
        {json.dumps(market_state, indent=2)}

        # 임무
        위 상황을 종합적으로 분석하여, 다음 턴의 'price'와 'marketing_spend'를 결정하세요.
        단순히 점유율만 쫓아서는 안 됩니다. **지출 대비 수익(ROI)을 신중하게 고려하여,
        회사의 장기적인 '누적 이익(accumulated_profit)'을 극대화하는 방향으로 결정해야 합니다.**
        파산하지 않도록 재무 상태를 반드시 확인하십시오.

        # 응답 형식
        반드시 아래와 같은 JSON 형식으로만 응답해야 합니다. 다른 말은 절대 추가하지 마십시오.
        {{
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
            return decision
        except json.JSONDecodeError:
            print("오류: LLM 응답이 유효한 JSON이 아닙니다. 응답:", response_text)
            return {"price": 10000, "marketing_spend": 100000}