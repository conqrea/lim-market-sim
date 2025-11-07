// wargame-cockpit/src/App.js

import React, { useState } from 'react';
import SimulationChart from './SimulationChart';
import * as api from './apiService'; // apiService 임포트

// 각 회사에 대한 고정 색상
const COMPANY_COLORS = {
  GM: '#8884d8', // 보라색
  Toyota: '#82ca9d', // 녹색
  Apple: '#aaaaaa',
  Samsung: '#ffc658',
};

// [수정] QUARTERLY_REPORT_INTERVAL (L15) 삭제됨 (사용되지 않음)

// [신규] GM vs Toyota 시나리오를 위한 기본 설정값
const defaultGlobalConfig = {
  total_turns: 20,
  market_size: 30000,
  initial_capital: 500000000,
  initial_marketing_budget_ratio: 0.02, // 2%
  initial_rd_budget_ratio: 0.01,       // 1%
  
  // 거시 경제
  gdp_growth_rate: 0.01,  // 분기 1% (IT 버블)
  inflation_rate: 0.005, // 분기 0.5%

  // R&D 도박 (혁신: 품질)
  rd_innovation_cost: 2000000.0,
  rd_innovation_prob: 0.2,
  rd_innovation_impact: 3.0,
  
  // R&D 도박 (효율: 원가)
  rd_efficiency_cost: 2000000.0,
  rd_efficiency_prob: 0.2,
  rd_efficiency_impact: 0.03,

  // 마케팅 수확 체감
  marketing_cost_base: 100000.0,
  marketing_cost_multiplier: 1.12,

  // 자산 감가상각 (핵심 변수)
  quality_decay_rate: 1.0, // 기술 도태 빠름
  brand_decay_rate: 0.5    // 망각 빠름
};

const defaultCompaniesConfig = [
  {
    name: "GM",
    persona: "우리는 시장 1위입니다. 우리의 목표는 'R&D(원가절감)'가 아니라, '공격적인 마케팅'과 '고수익 차종(높은 가격)'을 통해 '누적 이익'을 극대화하는 것입니다. R&D 투자는 최소한으로만 유지합니다.",
    initial_unit_cost: 10000,
    initial_market_share: 0.35, // 35%
    initial_product_quality: 50.0, // (프록시 데이터: J.D. Power 평균)
    initial_brand_awareness: 70.0  // (프록시 데이터: 광고비 우위)
  },
  {
    name: "Toyota",
    persona: "우리는 도전자입니다. 우리의 목표는 'R&D(품질/원가)'에 모든 자원을 투입하여 압도적인 '경쟁력'을 확보하는 것입니다. 이를 바탕으로 '경쟁적인 가격'과 '효율적인 마케팅'을 집행해 1위의 '시장 점유율'을 뺏어오는 것이 최우선입니다.",
    initial_unit_cost: 10000,
    initial_market_share: 0.15, // 15%
    initial_product_quality: 65.0, // (프록시 데이터: J.D. Power 우위)
    initial_brand_awareness: 40.0  // (프록시 데이터: 광고비 열세)
  }
];
// (참고: Others가 나머지 50%의 초기 점유율을 가짐)


function App() {
  const [simulationId, setSimulationId] = useState(null);
  const [history, setHistory] = useState([]);
  const [companyNames, setCompanyNames] = useState([]);
  const [currentTurn, setCurrentTurn] = useState(0);
  const [totalTurns, setTotalTurns] = useState(defaultGlobalConfig.total_turns);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [aiReasoning, setAiReasoning] = useState([]);
  
  const [showConfig, setShowConfig] = useState(true); 
  const [globalConfig, setGlobalConfig] = useState(defaultGlobalConfig);
  const [companiesConfig, setCompaniesConfig] = useState(defaultCompaniesConfig);

  const [choiceOptions, setChoiceOptions] = useState(null);
  const [selectedDecisions, setSelectedDecisions] = useState({});
  const [isWaitingForChoice, setIsWaitingForChoice] = useState(false);

  // 차트 라인 생성
  // [수정] 1: 함수 시그니처를 (dataKeySuffix) -> (names)로 변경
  const getChartLines = (names) => { 
    const lines = {
      accumulated_profit: [],
      market_share: [],
      price: [],

      // [신규] 마케팅 상세
      marketing_brand_spend: [],
      marketing_promo_spend: [],

      // [신규] R&D 상세
      rd_innovation_spend: [],
      rd_efficiency_spend: [],

      unit_cost: [],
      product_quality: [],
      brand_awareness: [],
    };

    // [수정] 2: state (companyNames) 대신 파라미터 (names)를 사용
    names.forEach((name, index) => { 
      const color = COMPANY_COLORS[name] || '#000';
      lines.accumulated_profit.push({ dataKey: `${name}_accumulated_profit`, stroke: color });
      lines.market_share.push({ dataKey: `${name}_market_share`, stroke: color });
      lines.price.push({ dataKey: `${name}_price`, stroke: color });

      // [신규] 상세 변수 추가
      lines.marketing_brand_spend.push({ dataKey: `${name}_marketing_brand_spend`, stroke: color });
      lines.marketing_promo_spend.push({ dataKey: `${name}_marketing_promo_spend`, stroke: color });
      lines.rd_innovation_spend.push({ dataKey: `${name}_rd_innovation_spend`, stroke: color });
      lines.rd_efficiency_spend.push({ dataKey: `${name}_rd_efficiency_spend`, stroke: color });

      lines.unit_cost.push({ dataKey: `${name}_unit_cost`, stroke: color });
      lines.product_quality.push({ dataKey: `${name}_product_quality`, stroke: color });
      lines.brand_awareness.push({ dataKey: `${name}_brand_awareness`, stroke: color });
    });
    return lines;
  };
  
  // [수정] 3: 'getAllCompetitorLines' (L160-L177) 함수 전체 삭제 (사용되지 않음)
  
  // 설정값 변경 핸들러
  const handleGlobalConfigChange = (e) => {
    const { name, value } = e.target;
    setGlobalConfig(prev => ({ ...prev, [name]: parseFloat(value) || 0 }));
  };
  
  const handleCompanyConfigChange = (index, e) => {
    const { name, value } = e.target;
    const newCompanies = [...companiesConfig];
    newCompanies[index] = {
      ...newCompanies[index],
      [name]: (name === 'name' || name === 'persona') ? value : parseFloat(value) || 0
    };
    setCompaniesConfig(newCompanies);
  };


  // 시뮬레이션 생성 핸들러
  const handleCreateSimulation = async () => {
    setIsLoading(true);
    setError(null);
    setHistory([]);
    setAiReasoning([]);
    setCurrentTurn(0);

    const config = {
      ...globalConfig,
      companies: companiesConfig
    };
    
    const totalShare = config.companies.reduce((sum, c) => sum + c.initial_market_share, 0);
    if (totalShare > 1.0) {
      setError("오류: AI 회사들의 초기 점유율 합계가 1.0 (100%)을 초과할 수 없습니다.");
      setIsLoading(false);
      return;
    }

    try {
      const data = await api.createSimulation(config);
      setSimulationId(data.simulation_id);
      const aiNames = config.companies.map(c => c.name);
      setCompanyNames(aiNames);
      setTotalTurns(config.total_turns);
      setShowConfig(false); 
      console.log("시뮬레이션 생성 완료:", data.simulation_id);
    } catch (err) {
      setError("시뮬레이션 생성 실패: " + err.message);
    }
    setIsLoading(false);
  };

  // 턴 실행 핸들러
  // [수정] '다음 1턴' 버튼이 이 함수를 호출
  const handleGetChoices = async () => {
    if (!simulationId || isLoading) return;

    setIsLoading(true);
    setError(null);
    try {
      // 1. API를 호출해 선택지를 받아옴
      const choices = await api.getDecisionChoices(simulationId);
      setChoiceOptions(choices); // { "GM": [...], "Sony": [...] }
      setIsWaitingForChoice(true); // 선택 대기 모드 활성화
      setSelectedDecisions({}); // 이전 선택 초기화
    } catch (err) {
      setError(`선택지 요청 실패: ` + err.message);
    }
    setIsLoading(false);
  };

  const handleExecuteTurn = async () => {
    if (!simulationId || isLoading || !isWaitingForChoice) return;

    setIsLoading(true);
    setError(null);
    try {
      // 1. 선택된 결정들을 { "GM": {...}, "Sony": {...} } 형태로 모음
      const decisionsToExecute = {};
      companyNames.forEach(name => {
        if (selectedDecisions[name]) {
          // 'decision' 객체와 'reasoning'을 함께 넘김
          decisionsToExecute[name] = {
            ...selectedDecisions[name].decision,
            reasoning: selectedDecisions[name].reasoning
          };
        }
      });

      // 2. API로 전송하여 턴 실행
      const data = await api.executeTurn(simulationId, decisionsToExecute);

      // 3. (기존 runMultipleTurns의 성공 로직과 동일)
      setHistory(prevHistory => [...prevHistory, data.turn_results]);
      setCurrentTurn(data.turn);

      setAiReasoning(prev => [...prev, {
        turn: data.turn,
        reasons: Object.entries(data.ai_reasoning).map(([name, reason]) => `[${name}]: ${reason}`)
      }]);

      // 4. 선택 모드 종료 및 초기화
      setIsWaitingForChoice(false);
      setChoiceOptions(null);
      setSelectedDecisions({});

    } catch (err) {
      setError(`턴 실행 실패: ` + err.message);
    }
    setIsLoading(false);
  };

  // [신규] 사용자가 특정 AI의 특정 선택지를 클릭할 때 호출됨
  const handleSelectChoice = (agentName, choice) => {
    setSelectedDecisions(prev => ({
      ...prev,
      [agentName]: choice // choice = { reasoning, probability, decision }
    }));
  };
  
  // [수정] CSV 다운로드 핸들러 추가
  const handleDownloadCSV = () => {
    if (history.length === 0) {
      alert("다운로드할 데이터가 없습니다.");
      return;
    }

    try {
      // 1. 헤더 생성 (history의 첫 번째 객체 키 사용)
      const headers = Object.keys(history[0]);
      const headerString = headers.join(',');

      // 2. 데이터 행 생성
      const rows = history.map(turnData => {
        return headers.map(header => turnData[header]).join(',');
      });

      // 3. CSV 문자열 결합 (헤더 + 데이터)
      // \uFEFF는 Excel에서 한글(UTF-8)이 깨지지 않도록 하는 BOM(Byte Order Mark)입니다.
      const csvString = '\uFEFF' + [headerString, ...rows].join('\n');

      // 4. Blob 생성 및 다운로드 링크 클릭
      const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      
      link.setAttribute('href', url);
      link.setAttribute('download', 'simulation_history.csv');
      link.style.visibility = 'hidden';
      
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

    } catch (err) {
      console.error("CSV 다운로드 오류:", err);
      setError("CSV 다운로드 중 오류가 발생했습니다: " + err.message);
    }
  };
  
  // 설정 UI 렌더링 함수
  const renderConfigUI = () => (
    <div style={{ padding: '20px', border: '1px solid #ccc', borderRadius: '8px', marginBottom: '20px', backgroundColor: '#f9f9f9' }}>
      <h3>🌍 1. 글로벌 시장 설정</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '10px' }}>
        {Object.entries(globalConfig).map(([key, value]) => (
          <div key={key}>
            <label style={{ fontSize: '0.9em', display: 'block' }}>{key}</label>
            <input
              type="number"
              name={key}
              value={value}
              onChange={handleGlobalConfigChange}
              style={{ width: '100%', padding: '5px' }}
            />
          </div>
        ))}
      </div>
      
      <h3 style={{ marginTop: '20px' }}>🏢 2. AI 회사 설정 (GM vs Toyota)</h3>
      {companiesConfig.map((company, index) => (
        <div key={index} style={{ borderTop: '1px solid #eee', paddingTop: '10px', marginTop: '10px' }}>
          <h4>회사 {index + 1}</h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '10px' }}>
            <div>
              <label>name</label>
              <input type="text" name="name" value={company.name} onChange={e => handleCompanyConfigChange(index, e)} style={{ width: '100%' }} />
            </div>
            <div>
              <label>initial_unit_cost</label>
              <input type="number" name="initial_unit_cost" value={company.initial_unit_cost} onChange={e => handleCompanyConfigChange(index, e)} style={{ width: '100%' }} />
            </div>
            <div>
              <label>initial_market_share (0.0 ~ 1.0)</label>
              <input type="number" step="0.01" name="initial_market_share" value={company.initial_market_share} onChange={e => handleCompanyConfigChange(index, e)} style={{ width: '100%' }} />
            </div>
            <div>
              <label>initial_product_quality (0-100)</label>
              <input type="number" name="initial_product_quality" value={company.initial_product_quality} onChange={e => handleCompanyConfigChange(index, e)} style={{ width: '100%' }} />
            </div>
            <div>
              <label>initial_brand_awareness (0-100)</label>
              <input type="number" name="initial_brand_awareness" value={company.initial_brand_awareness} onChange={e => handleCompanyConfigChange(index, e)} style={{ width: '100%' }} />
            </div>
          </div>
          <div>
            <label style={{ marginTop: '10px', display: 'block' }}>persona</label>
            <textarea
              name="persona"
              value={company.persona}
              onChange={e => handleCompanyConfigChange(index, e)}
              style={{ width: '100%', height: '60px', fontSize: '0.9em' }}
            />
          </div>
        </div>
      ))}
      <button onClick={handleCreateSimulation} disabled={isLoading} style={{ marginTop: '20px', padding: '10px 20px', fontSize: '1.1em', backgroundColor: 'green', color: 'white' }}>
        🚀 시뮬레이션 생성
      </button>
    </div>
  );

  // [수정] 4: 함수를 호출할 때 정의된 파라미터(companyNames)를 전달
  const chartLines = getChartLines(companyNames);

  return (
    <div style={{ fontFamily: 'sans-serif', padding: '20px', maxWidth: '1600px', margin: 'auto' }}>
      <h1 style={{ textAlign: 'center', color: '#333' }}>🤖 AI 전략 워게임 시뮬레이터 (v2: Dynamic Asset Model)</h1>

      {/* 설정/제어 버튼 */}
      <button onClick={() => setShowConfig(prev => !prev)} style={{ marginBottom: '10px' }}>
        {showConfig ? '▼ 설정창 닫기' : '► 설정창 열기'}
      </button>
      
      {/* 1. 설정 UI */}
      {showConfig && renderConfigUI()}

      {/* 2. 실행 제어 UI */}
      {!showConfig && simulationId && !isWaitingForChoice && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', padding: '10px', border: '1px solid #ccc', borderRadius: '8px' }}>
          <button onClick={handleGetChoices} disabled={isLoading || currentTurn >= totalTurns}>
            다음 1턴 결정 보기 (Turn: {currentTurn}/{totalTurns})
          </button>
          
          {/* [수정] CSV 다운로드 버튼 추가 */}
          <button 
            onClick={handleDownloadCSV} 
            disabled={history.length === 0 || isLoading}
            style={{ backgroundColor: '#28a745', color: 'white', marginLeft: 'auto' }}>
            결과 다운로드 (CSV)
          </button>

          {isLoading && <div style={{ color: 'blue' }}>(시뮬레이션 진행 중...)</div>}
          {error && <div style={{ color: 'red' }}>[오류] {error}</div>}
        </div>
      )}

      {/* [신규] 2.5. 결정 선택 UI */}
      {isWaitingForChoice && choiceOptions && (
        <div style={{ marginTop: '20px', padding: '10px', border: '1px solid #007bff', borderRadius: '8px' }}>
          <h3 style={{ textAlign: 'center' }}>결정 대기 중: {currentTurn + 1}턴 </h3>
          <div style={{ display: 'grid', gridTemplateColumns: `repeat(${companyNames.length}, 1fr)`, gap: '10px' }}>
              {companyNames.map(name => (
              <div key={name} style={{ border: '1px solid #ccc', padding: '10px' }}>
                <h4 style={{ color: COMPANY_COLORS[name] || '#000' }}>{name}의 전략</h4>
                {choiceOptions[name] && choiceOptions[name].map((choice, index) => {
                  const isSelected = selectedDecisions[name] === choice;
                  return (
                    <button 
                      key={index}
                      onClick={() => handleSelectChoice(name, choice)}
                      style={{ 
                        display: 'block', width: '100%', marginBottom: '5px', 
                        backgroundColor: isSelected ? '#007bff' : '#f0f0f0',
                        color: isSelected ? 'white' : 'black',
                        border: '1px solid #ccc', padding: '8px', textAlign: 'left'
                      }}>
                      <strong>전략 {index + 1} (확률: {(choice.probability * 100).toFixed(0)}%)</strong>
                      <p style={{ fontSize: '0.9em', margin: '4px 0' }}>{choice.reasoning}</p>
                    </button>
                  );
                })}
              </div>
            ))}

          </div>
          <button 
            onClick={handleExecuteTurn} 
            disabled={isLoading || Object.keys(selectedDecisions).length < companyNames.length}
            style={{ width: '100%', padding: '15px', fontSize: '1.2em', backgroundColor: 'green', color: 'white', marginTop: '10px' }}>
            선택 완료 및 {currentTurn + 1}턴 실행
          </button>
        </div>
      )}

      {/* 3. AI 결정 로그 */}
      {aiReasoning.length > 0 && (
        <div style={{ 
          marginTop: '20px', padding: '10px', border: '1px solid #eee', borderRadius: '8px', 
          height: '150px', overflowY: 'scroll', backgroundColor: '#282c34', 
          color: '#e6e6e6', fontSize: '0.9em'
        }}>
          <strong>[AI 결정 로그]</strong>
          {aiReasoning.slice().reverse().map((entry, idx) => (
            <div key={idx} style={{ borderTop: '1px dashed #555', paddingTop: '5px', marginTop: '5px' }}>
              <strong>--- {entry.turn}턴 결정 ---</strong>
              {entry.reasons.map((reason, rIdx) => <div key={rIdx}>{reason}</div>)}
            </div>
          ))}
        </div>
      )}

      {/* 4. 차트 그리드 (새로운 자산 변수 표시) */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(5, 1fr)',
        gap: '20px', 
        marginTop: '20px' 
      }}>
          {/* 1. [신규] 제품 품질 */}
          <SimulationChart data={history} lines={chartLines.accumulated_profit} title="누적 이익" />
          <SimulationChart data={history} lines={chartLines.market_share} title="시장 점유율" format={(v) => `${(v * 100).toFixed(1)}%`} />
          <SimulationChart data={history} lines={chartLines.price} title="제품 가격" />
          <SimulationChart data={history} lines={chartLines.marketing_brand_spend} title="마케팅 (브랜드) 지출" />
          <SimulationChart data={history} lines={chartLines.marketing_promo_spend} title="마케팅 (판촉) 지출" />
          <SimulationChart data={history} lines={chartLines.rd_innovation_spend} title="R&D (품질 혁신) 지출" />
          <SimulationChart data={history} lines={chartLines.rd_efficiency_spend} title="R&D (원가 절감) 지출" />

          <SimulationChart data={history} lines={chartLines.unit_cost} title="단위 원가" />
          <SimulationChart data={history} lines={chartLines.product_quality} title="제품 품질" />
          <SimulationChart data={history} lines={chartLines.brand_awareness} title="브랜드 인지도" />
      </div>
    </div>
  );
}

export default App;