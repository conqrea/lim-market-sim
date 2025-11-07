// wargame-cockpit/src/apiService.js

import axios from 'axios';

// FastAPI 서버 주소
const API_BASE_URL = 'http://127.0.0.1:8000';

/**
 * [수정] 새로운 SimulationConfig 객체를 받아 시뮬레이션을 생성합니다.
 * @param {object} config - api_main.py의 SimulationConfig와 일치하는 객체
 */
export const createSimulation = async (config) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/simulations`, config);
    return response.data; // { simulation_id, initial_state } 반환
  } catch (error) {
    console.error("Error creating simulation:", error);
    throw error;
  }
};

// 2. '다음 턴' 진행 API (기존과 동일)
export const runNextTurn = async (simId) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/simulations/${simId}/next_turn`);
    return response.data; // { turn, turn_results, next_state } 반환
  } catch (error) {
    console.error("Error running next turn:", error);
    throw error;
  }
};

// 3. '이벤트' 주입 API (기존과 동일)
export const injectEvent = async (simId, eventData) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/simulations/${simId}/inject_event`, eventData);
    return response.data; // { message } 반환
  } catch (error) {
    console.error("Error injecting event:", error);
    throw error;
  }
};

// 4. '여러 턴' 진행 API (기존과 동일)
/*export const runMultipleTurns = async (simId, turnCount) => {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/simulations/${simId}/run_turns?turns_to_run=${turnCount}`
    );
    return response.data; // { turns_ran, results_history, ... } 반환
  } catch (error) {
    console.error("Error running multiple turns:", error);
    throw error;
  }
};*/

// [신규] 1. AI에게 전략적 선택지를 요청
export const getDecisionChoices = async (simId) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/simulations/${simId}/get_choices`);
    return response.data; // { "GM": [...], "Sony": [...] } 반환
  } catch (error) {
    console.error("Error getting agent choices:", error);
    throw error;
  }
};

// [신규] 2. 사용자가 선택한 결정을 서버로 전송하여 턴 실행
export const executeTurn = async (simId, decisions) => {
  try {
    // decisions = { "GM": {price: ..., reasoning: ...}, "Sony": {...} }
    const response = await axios.post(
      `${API_BASE_URL}/simulations/${simId}/execute_turn`,
      { decisions } // { "decisions": { "GM": ... } } 형태로 래핑하여 전송
    );
    return response.data; // { turn, turn_results, ... } 반환
  } catch (error) {
    console.error("Error executing turn:", error);
    throw error;
  }
};