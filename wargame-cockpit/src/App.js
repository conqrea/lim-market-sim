import React, { useState } from 'react';
import styled from '@emotion/styled';
// 2단계에서 만든 API 함수들 임포트
import { createSimulation, runNextTurn, injectEvent, runMultipleTurns } from './apiService'
// 4단계에서 만들 차트 컴포넌트 임포트
import SimulationChart from './SimulationChart';

// --- (간단한 스타일링) ---
const Cockpit = styled.div`
  padding: 20px;
  font-family: Arial, sans-serif;
`;
const Header = styled.h1`
  color: #333;
`;
const ControlPanel = styled.div`
  background-color: #f4f4f4;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 20px;
  display: flex;
  gap: 10px;
`;
const Button = styled.button`
  background-color: #007bff;
  color: white;
  border: none;
  padding: 10px 15px;
  border-radius: 5px;
  cursor: pointer;
  font-size: 16px;
  &:hover {
    background-color: #0056b3;
  }
  &:disabled {
    background-color: #ccc;
    cursor: not-allowed;
  }
`;
const LogArea = styled.pre`
  background-color: #222;
  color: #00ff00;
  padding: 15px;
  border-radius: 5px;
  height: 200px;
  overflow-y: scroll;
`;
const EventFormModal = styled.form`
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: white;
  padding: 25px;
  border-radius: 10px;
  box-shadow: 0 5px 20px rgba(0, 0, 0, 0.25);
  z-index: 1000;
  width: 400px;
  display: flex;
  flex-direction: column;
  gap: 12px;

  h3 {
    margin-top: 0;
  }
  
  label {
    font-weight: bold;
    font-size: 14px;
    margin-bottom: -5px;
  }

  input, select {
    padding: 10px;
    font-size: 16px;
    border-radius: 5px;
    border: 1px solid #ccc;
  }
`;
// --- (스타일링 끝) ---

// 1. 시뮬레이션 기본 설정값
const DEFAULT_CONFIG = {
  companies: [
    { name: "Apple", persona: "보수적 CEO: 안정적 이익률 유지가 최우선. 불필요한 경쟁 회피.", unit_cost: 8500 },
    { name: "Samsung", persona: "공격적 CEO: 시장 점유율 확보가 최우선. 단기 손실 감수.", unit_cost: 9000 }
  ],
  total_turns: 30,
  market_size: 10000,
  initial_capital: 25000000,
  
  // --- [핵심 수정] ---
  // (변경 전) price_sensitivity: 2.0,
  // (변경 후) S-curve 모델에 맞는 값으로 수정
  price_sensitivity: 0.0005,
  // ------------------

  max_marketing_boost: 1.0, // (이전 수정안에서 1.0으로 변경했었음)
  marketing_midpoint: 5000000,
  marketing_steepness: 0.0000015,
  price_weight: 0.6,
  marketing_weight: 0.4
};

function App() {
  // --- 3. React 상태 관리 ---
  const [simId, setSimId] = useState(null); // 현재 시뮬레이션 ID
  const [history, setHistory] = useState([]); // 차트에 그릴 턴별 누적 데이터
  const [logs, setLogs] = useState(["시뮬레이션을 시작하세요..."]); // 로그 출력
  const [isLoading, setIsLoading] = useState(false); // 로딩 상태 (AI 응답 대기)
  const [currentTurn, setCurrentTurn] = useState(0);
  const [showEventModal, setShowEventModal] = useState(false);
  const [eventForm, setEventForm] = useState({
    description: "원자재 가격 10% 상승",
    target_company: "All",
    effect_type: "unit_cost_multiplier",
    impact_value: 1.1,
    duration: 4
  });

  // --- 4. API 호출 핸들러 ---

  // '시뮬레이션 생성' 버튼 클릭 시
  const handleCreateSimulation = async () => {
    setIsLoading(true);
    setLogs(["(1/3) 시뮬레이션 생성 중..."]);
    try {
      const data = await createSimulation(DEFAULT_CONFIG);
      setSimId(data.simulation_id);
      setCurrentTurn(0);
      setHistory([]); // 기록 초기화
      setLogs(prev => [...prev, `(2/3) 시뮬레이션 생성 완료! ID: ${data.simulation_id}`, `(3/3) '다음 턴 진행' 버튼을 누르세요.`]);
    } catch (error) {
      setLogs(prev => [...prev, "!! 시뮬레이션 생성 실패 !!", error.message]);
    }
    setIsLoading(false);
  };

  // '다음 턴 진행' 버튼 클릭 시
  const handleNextTurn = async () => {
    if (!simId) return;

    setIsLoading(true);
    setLogs(prev => [...prev, `--- Turn ${currentTurn + 1} 진행 중 (AI 응답 대기)... ---`]);
    try {
      const data = await runNextTurn(simId);
      
      // 차트 데이터를 위해 history에 턴 결과 추가
      setHistory(prevHistory => [...prevHistory, data.turn_results]);
      setCurrentTurn(data.turn);

      // 로그 업데이트
      setLogs(prev => [
        ...prev, 
        `Turn ${data.turn} 완료.`,
        `[Apple 결정] ${data.ai_reasoning.Apple}`,
        `[Samsung 결정] ${data.ai_reasoning.Samsung}`,
        `[이벤트] ${data.next_state.active_events.length > 0 ? data.next_state.active_events.join(', ') : '없음'}`
      ]);

      if (data.message === "시뮬레이션이 이미 종료되었습니다.") {
         setLogs(prev => [...prev, "--- 모든 턴이 종료되었습니다. ---"]);
         setIsLoading(false);
         setSimId(null); // 종료
      }

    } catch (error) {
      setLogs(prev => [...prev, "!! 턴 진행 실패 !!", error.message]);
    }
    setIsLoading(false);
  };

  // '이벤트 주입' 버튼 클릭 시
  const handleInjectEvent = async (e) => {
    e.preventDefault(); // 폼 제출 기본 동작 방지
    if (!simId) return;

    setIsLoading(true);
    setLogs(prev => [...prev, `[이벤트 주입 시도] "${eventForm.description}"`]);
    try {
      // [수정] 하드코딩된 EXAMPLE_EVENT 대신 폼 상태(eventForm)를 사용
      const data = await injectEvent(simId, eventForm);
      setLogs(prev => [...prev, `[이벤트 주입 성공] ${data.message}`]);
    } catch (error) {
      setLogs(prev => [...prev, "!! 이벤트 주입 실패 !!", error.message]);
    }
    setShowEventModal(false); // 모달 닫기
    setIsLoading(false);
  };

  const handleEventFormChange = (e) => {
    const { name, value } = e.target;
    setEventForm(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleRunMultipleTurns = async (turnCount) => {
    if (!simId) return;
    setIsLoading(true);
    setLogs(prev => [...prev, `--- ${turnCount}턴 연속 진행 시작... ---`]);
    
    const data = await runMultipleTurns(simId, turnCount);
    
    // [수정] N개의 턴 결과를 history에 한 번에 추가
    setHistory(prevHistory => [...prevHistory, ...data.results_history]);
    setCurrentTurn(data.final_state.turn);
    
    // [수정] 마지막 턴의 로그만 간단히 표시
    const lastReasoning = data.reasoning_history[data.reasoning_history.length - 1];
    setLogs(prev => [
      ...prev, 
      `--- ${data.turns_ran}턴 진행 완료. (현재 ${data.final_state.turn}턴) ---`,
      `[Apple 결정] ${lastReasoning.reasoning.Apple}`,
      `[Samsung 결정] ${lastReasoning.reasoning.Samsung}`,
    ]);
    setIsLoading(false);
  };

  return (
    <Cockpit>
      <Header>🚀 AI 전략 워게임 조종석</Header>
      
      <ControlPanel>
        <Button onClick={handleCreateSimulation} disabled={isLoading || simId}>
          1. 시뮬레이션 생성
        </Button>
        <Button onClick={handleNextTurn} disabled={isLoading || !simId}>
          다음 1턴 (Turn: {currentTurn})
        </Button>
        {/* [신규] 5턴 진행 버튼 */}
        <Button onClick={() => handleRunMultipleTurns(5)} disabled={isLoading || !simId}>
          다음 5턴
        </Button>
        <Button onClick={() => setShowEventModal(true)} disabled={isLoading || !simId}>
          [난입] 커스텀 이벤트
        </Button>
      </ControlPanel>

      {showEventModal && (
        <EventFormModal onSubmit={handleInjectEvent}>
          <h3>커스텀 이벤트 주입</h3>
          <label>설명:</label>
          <input name="description" value={eventForm.description} onChange={handleEventFormChange} />
          
          <label>대상:</label>
          <select name="target_company" value={eventForm.target_company} onChange={handleEventFormChange}>
            <option value="All">All</option>
            <option value="Apple">Apple</option>
            <option value="Samsung">Samsung</option>
          </select>
          
          <label>효과:</label>
          <select name="effect_type" value={eventForm.effect_type} onChange={handleEventFormChange}>
            <option value="unit_cost_multiplier">원가 (배율)</option>
            {/* (나중에 R&D, 마케팅 효율 등 추가) */}
          </select>
          
          <label>영향 값:</label>
          <input name="impact_value" type="number" step="0.1" value={eventForm.impact_value} onChange={handleEventFormChange} />
          
          <label>지속 턴:</label>
          <input name="duration" type="number" step="1" value={eventForm.duration} onChange={handleEventFormChange} />

          <Button type="submit" disabled={isLoading}>주입하기</Button>
          <Button type="button" onClick={() => setShowEventModal(false)}>취소</Button>
        </EventFormModal>
      )}
      
      <LogArea>
        {logs.map((log, index) => (
          <div key={index}>{log}</div>
        ))}
      </LogArea>

      {/* 4단계: 차트 컴포넌트 렌더링 */}
      <Header>📊 시뮬레이션 결과</Header>
      <SimulationChart data={history} />

    </Cockpit>
  );
}

export default App;