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

const QUARTERLY_REPORT_INTERVAL = 4;

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

  // 차트 라인 생성
  const getChartLines = (dataKeySuffix) => {
    return companyNames.map((name) => ({
      name: name,
      dataKey: `${name}${dataKeySuffix}`,
      color: COMPANY_COLORS[name] || '#ff7300'
    }));
  };
  
  // 'Others'를 포함한 모든 경쟁사 라인 생성
  const getAllCompetitorLines = (dataKeySuffix) => {
    if (history.length === 0) return [];
    
    const allNames = new Set();
    Object.keys(history[0]).forEach(key => {
      if (key !== 'turn' && key.includes('_')) {
        allNames.add(key.split('_')[0]);
      }
    });
    
    return Array.from(allNames).map((name, index) => ({
      name: name,
      dataKey: `${name}${dataKeySuffix}`,
      color: COMPANY_COLORS[name] || (['#8884d8', '#82ca9d', '#ffc658', '#ff7300'][index % 4])
    }));
  };
  
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
  const handleRunTurns = async (turns) => {
    if (!simulationId || isLoading) return;

    setIsLoading(true);
    setError(null);

    try {
      const data = await api.runMultipleTurns(simulationId, turns);
      
      setHistory(prevHistory => [...prevHistory, ...data.results_history]);
      setCurrentTurn(data.final_state.turn);
      
      setAiReasoning(prev => [...prev, ...data.reasoning_history.map(r => ({
        turn: r.turn,
        reasons: Object.entries(r.reasoning).map(([name, reason]) => `[${name}]: ${reason}`)
      }))]);

    } catch (err) {
      setError(`턴 ${turns}회 진행 실패: ` + err.message);
    }
    setIsLoading(false);
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
      {!showConfig && simulationId && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', padding: '10px', border: '1px solid #ccc', borderRadius: '8px' }}>
          <button onClick={() => handleRunTurns(1)} disabled={isLoading || currentTurn >= totalTurns}>
            다음 1턴 (Turn: {currentTurn}/{totalTurns})
          </button>
          <button onClick={() => handleRunTurns(QUARTERLY_REPORT_INTERVAL)} disabled={isLoading || currentTurn >= totalTurns}>
            다음 1분기 ({QUARTERLY_REPORT_INTERVAL}턴)
          </button>
          <button onClick={() => handleRunTurns(totalTurns - currentTurn)} disabled={isLoading || currentTurn >= totalTurns}>
            전체 실행
          </button>
          
          {/* [수정] CSV 다운로드 버튼 추가 */}
          <button 
            onClick={handleDownloadCSV} 
            disabled={history.length === 0 || isLoading}
            style={{ backgroundColor: '#28a745', color: 'white', marginLeft: 'auto' }}
          >
            결과 다운로드 (CSV)
          </button>

          {isLoading && <div style={{ color: 'blue' }}>(시뮬레이션 진행 중...)</div>}
          {error && <div style={{ color: 'red' }}>[오류] {error}</div>}
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
        gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
        gap: '20px', 
        marginTop: '20px' 
      }}>
        {/* 1. [신규] 제품 품질 */}
        <SimulationChart
          title="제품 품질 (Product Quality)"
          data={history}
          yLabel="제품 품질 (점)"
          lines={getAllCompetitorLines('_product_quality')}
        />
        {/* 2. [신규] 브랜드 인지도 */}
        <SimulationChart
          title="브랜드 인지도 (Brand Awareness)"
          data={history}
          yLabel="브랜드 인지도 (점)"
          lines={getAllCompetitorLines('_brand_awareness')}
        />
        {/* 3. 시장 점유율 */}
        <SimulationChart
          title="시장 점유율 (Market Share)"
          data={history}
          yLabel="시장 점유율 (%)"
          lines={getAllCompetitorLines('_market_share')}
        />
        {/* 4. 누적 이익 */}
        <SimulationChart
          title="누적 이익 (Accumulated Profit)"
          data={history}
          yLabel="누적 이익"
          lines={getChartLines('_accumulated_profit')}
        />
        {/* 5. 가격 */}
        <SimulationChart
          title="가격 (Price)"
          data={history}
          yLabel="가격"
          lines={getAllCompetitorLines('_price')}
        />
        {/* 6. 단위 원가 */}
        <SimulationChart
          title="단위 원가 (Unit Cost)"
          data={history}
          yLabel="단위 원가"
          lines={getAllCompetitorLines('_unit_cost')}
        />
      </div>
    </div>
  );
}

export default App;