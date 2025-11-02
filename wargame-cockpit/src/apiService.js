import axios from 'axios';

// FastAPI 서버 주소
const API_BASE_URL = 'http://127.0.0.1:8000';

// 1. 시뮬레이션 '방' 생성 API
export const createSimulation = async (config) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/simulations`, config);
    return response.data; // { simulation_id, initial_state } 반환
  } catch (error) {
    console.error("Error creating simulation:", error);
    throw error;
  }
};

// 2. '다음 턴' 진행 API
export const runNextTurn = async (simId) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/simulations/${simId}/next_turn`);
    return response.data; // { turn, turn_results, next_state } 반환
  } catch (error) {
    console.error("Error running next turn:", error);
    throw error;
  }
};

// 3. '이벤트' 주입 API
export const injectEvent = async (simId, eventData) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/simulations/${simId}/inject_event`, eventData);
    return response.data; // { message } 반환
  } catch (error) {
    console.error("Error injecting event:", error);
    throw error;
  }
};

export const runMultipleTurns = async (simId, turnCount) => {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/simulations/${simId}/run_turns?turns_to_run=${turnCount}`
    );
    return response.data; // { turns_ran, results_history, ... } 반환
  } catch (error) {
    console.error("Error running multiple turns:", error);
    throw error;
  }
};