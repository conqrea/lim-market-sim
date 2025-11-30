// apiService.js

// 백엔드 주소 (FastAPI가 실행되는 주소)
const API_BASE_URL = "http://localhost:8000"; 

// 1. 시뮬레이션 생성 (초기화)
export const createSimulation = async (config) => {
  // [수정됨] 경로: /simulation/create -> /simulations
  const response = await fetch(`${API_BASE_URL}/simulations`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(config),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to create simulation');
  }
  return await response.json();
};

// 2. 현재 턴의 선택지 조회
export const getDecisionChoices = async (simulationId) => {
  // [수정됨] 경로: /simulation/.../choices -> /simulations/.../get_choices
  // [수정됨] 메서드: GET -> POST (백엔드가 @app.post를 사용하므로)
  const response = await fetch(`${API_BASE_URL}/simulations/${simulationId}/get_choices`, {
      method: 'POST', 
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({}) // POST 요청이므로 빈 body라도 보내는 것이 안전함
  });
  
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to fetch choices');
  }
  return await response.json();
};

// 3. 선택(Decision) 전송 및 턴 실행
export const executeTurn = async (simulationId, decisions) => {
  // [수정됨] 경로: /simulation/... -> /simulations/... (이전에 수정한 부분 유지)
  const response = await fetch(`${API_BASE_URL}/simulations/${simulationId}/execute_turn`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    // [중요 수정] 백엔드 스키마(ExecuteTurnRequest)에 맞춰 'decisions' 키로 한 번 감싸야 합니다.
    body: JSON.stringify({ decisions }), 
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to execute turn');
  }
  return await response.json();
};

// --- [신규 추가] 프리셋(Preset) 관련 함수 ---

// 4. 프리셋 목록 불러오기
export const getPresets = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/presets`);
    if (!response.ok) {
      console.warn('Failed to fetch presets'); 
      return [];
    }
    return await response.json();
  } catch (error) {
    console.error("Error fetching presets:", error);
    return [];
  }
};

// 5. 프리셋 저장하기
export const savePreset = async (presetData) => {
  // [수정됨] 경로: /presets (백엔드 경로 확인 필요, /admin/save_preset 일 수도 있음)
  // api_main.py 코드를 보면 @app.post("/admin/save_preset") 입니다.
  const response = await fetch(`${API_BASE_URL}/admin/save_preset`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(presetData),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to save preset');
  }
  return await response.json();
};

// --- [신규 추가] 벤치마크(Track B) 관련 함수 ---

// 6. 벤치마크 실행
export const runBenchmark = async (benchmarkConfig) => {
    // api_main.py 기준 경로: @app.post("/admin/run_benchmark")
    const response = await fetch(`${API_BASE_URL}/admin/run_benchmark`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(benchmarkConfig)
    });
    
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Benchmark failed");
    }
    return await response.json();
};

// 7. 자동 튜닝 (Auto-Tune)
export const autoTuneParams = async (benchmarkConfig) => {
    // api_main.py 기준 경로: @app.post("/admin/auto_tune")
    const response = await fetch(`${API_BASE_URL}/admin/auto_tune`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(benchmarkConfig)
    });
    
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Auto-tune failed");
    }
    return await response.json();
};

// Track C: 시나리오 기반 시뮬레이션 생성
export const createSimulationFromScenario = async (benchmarkData) => {
    const response = await fetch(`${API_BASE_URL}/simulations/create_from_scenario`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(benchmarkData)
    });
    if (!response.ok) throw new Error("Failed to create scenario simulation");
    return await response.json();
};

// Track C: 페르소나 수정 (개입)
export const updatePersona = async (simulationId, companyName, newPersona) => {
    const response = await fetch(`${API_BASE_URL}/simulations/${simulationId}/update_persona`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ company_name: companyName, new_persona: newPersona })
    });
    if (!response.ok) throw new Error("Failed to update persona");
    return await response.json();
};

export const generateScenarioAI = async (topic) => {
    // api_main.py에 새로 만든 엔드포인트 호출
    const response = await fetch(`${API_BASE_URL}/admin/generate_scenario`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic })
    });
    
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Scenario generation failed");
    }
    return await response.json();
};