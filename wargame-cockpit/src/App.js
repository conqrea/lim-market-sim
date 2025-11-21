import React, { useState, useEffect, useCallback } from 'react';
import SimulationChart from './SimulationChart';
import * as api from './apiService';

const COMPANY_COLORS = {
  GM: '#8884d8',
  Toyota: '#82ca9d',
  Apple: '#aaaaaa',
  Samsung: '#ffc658',
  Sony: '#003791',
  Microsoft: '#107C10',
  Tesla: '#cc0000',
  Netflix: '#E50914',
  Nike: '#F37021',
  Adidas: '#000000',
  "Company A": "#8884d8",
  "Company B": "#82ca9d"
};

// [가이드] 물리 엔진 설정 레퍼런스
const PHYSICS_GUIDE = {
  price_sensitivity: {
    label: "가격 민감도 (price_sensitivity)",
    desc: "고객이 가격 차이에 얼마나 민감하게 반응하는가?",
    levels: [
      { label: "Low (2~3)", desc: "명품, 팬덤 (비싸도 산다)" },
      { label: "Mid (4~5)", desc: "일반 소비재" },
      { label: "High (10+)", desc: "저가 경쟁, 생필품" }
    ]
  },
  marketing_efficiency: {
    label: "마케팅 효율 (marketing_efficiency)",
    desc: "돈을 썼을 때 브랜드 인지도가 오르는 속도",
    levels: [
      { label: "Low (1.0)", desc: "B2B, 기술 중심" },
      { label: "Mid (2.0)", desc: "일반 제품" },
      { label: "High (3.0+)", desc: "패션, 바이럴 제품" }
    ]
  },
  weight_quality: {
    label: "품질 가중치 (weight_quality)",
    desc: "구매 결정 비중 (품질 + 브랜드 + 가격 = 1.0 권장)",
    levels: [
      { label: "Low (0.4)", desc: "디자인/감성 위주" },
      { label: "Mid (0.5~0.6)", desc: "밸런스형" },
      { label: "High (0.8+)", desc: "하이테크, 성능 위주" }
    ]
  },
  weight_brand: {
    label: "브랜드 가중치 (weight_brand)",
    desc: "구매 결정 비중 (품질 + 브랜드 + 가격 = 1.0 권장)",
    levels: [
      { label: "Low (0.1)", desc: "가성비/유틸리티" },
      { label: "Mid (0.3)", desc: "일반 브랜드" },
      { label: "High (0.5+)", desc: "명품, 과시 소비재" }
    ]
  },
  weight_price: {
    label: "가격 가중치 (weight_price)",
    desc: "구매 결정 비중 (품질 + 브랜드 + 가격 = 1.0 권장)",
    levels: [
      { label: "Low (0.05)", desc: "가격 무시 (무료/프리미엄)" },
      { label: "Mid (0.2)", desc: "일반적인 가성비 고려" },
      { label: "High (0.5+)", desc: "무조건 싼 게 팔림" }
    ]
  },
  rd_innovation_impact: {
    label: "R&D 혁신 크기 (rd_innovation_impact)",
    desc: "혁신 성공 시 품질이 오르는 정도 (한 방의 크기)",
    levels: [
      { label: "Low (5~10)", desc: "성숙 산업 (소폭 개선)" },
      { label: "Mid (15~20)", desc: "일반적 신제품" },
      { label: "High (30+)", desc: "파괴적 혁신 (시장 재편)" }
    ]
  },
  rd_innovation_threshold: {
    label: "R&D 혁신 주기 (rd_innovation_threshold)",
    desc: "혁신을 위해 필요한 누적 투자금 (낮을수록 빠름)",
    levels: [
      { label: "Slow (5천만~1억)", desc: "중후장대, 하드웨어" },
      { label: "Mid (3천만)", desc: "가전, 자동차" },
      { label: "Fast (1천만)", desc: "SW, 앱 서비스" }
    ]
  },
  others_overall_competitiveness: {
    label: "기타 경쟁자 강도 (others...)",
    desc: "AI 플레이어 외 '기존 시장 지배자(Others)'의 기초 체력",
    levels: [
      { label: "Low (0.5)", desc: "혁신에 의해 도태되는 중" },
      { label: "Mid (0.8~1.0)", desc: "일반적인 경쟁 상황" },
      { label: "High (1.5+)", desc: "진입 장벽 매우 높음" }
    ]
  }
};

// 입력 필드 한글 라벨 매핑
const FIELD_LABELS = {
  price_sensitivity: "가격 민감도 (Price Sensitivity)",
  marketing_efficiency: "마케팅 효율 (Mkt Efficiency)",
  weight_quality: "품질 가중치 (Weight Quality)",
  weight_brand: "브랜드 가중치 (Weight Brand)",
  weight_price: "가격 가중치 (Weight Price)",
  others_overall_competitiveness: "기타 경쟁자 강도 (Others)",
  rd_innovation_impact: "R&D 혁신 크기 (Impact)",
  rd_innovation_threshold: "R&D 혁신 주기 (Threshold)"
};

// UI 표시 순서 및 그룹 통합
const TUNING_UI_ORDER = [
  'price_sensitivity',            
  'marketing_efficiency',         
  'weight_quality',               
  'weight_brand',                 
  'weight_price',                 
  'rd_innovation_impact',        
  'rd_innovation_threshold',     
  'others_overall_competitiveness'
];

// [수정됨] 황금 밸런스 + 안정적인 마진 구조 기본값
const defaultGlobalConfig = {
  total_turns: 20,
  market_size: 50000,
  initial_capital: 1000000000, // 10억
  initial_marketing_budget_ratio: 0.02,
  initial_rd_budget_ratio: 0.01,
  
  gdp_growth_rate: 0.02, // 2% 성장
  inflation_rate: 0.005, // 0.5% 물가

  // R&D
  rd_innovation_threshold: 30000000.0, // 3천만
  rd_innovation_impact: 15.0,
  
  rd_efficiency_threshold: 50000000.0, // 5천만
  rd_efficiency_impact: 0.05, // 5%

  // 마케팅
  marketing_cost_base: 3000000.0, // 300만
  marketing_cost_multiplier: 1.5, // 비용 체증

  // 감가상각
  quality_decay_rate: 0.05, // 5%
  brand_decay_rate: 0.1, // 10%

  // 물리 엔진 (황금 밸런스 조정판)
  physics: {
    weight_quality: 0.4, // 품질 쏠림 완화
    weight_brand: 0.2,
    weight_price: 0.4, // 가격 중요도 복구
    price_sensitivity: 15.0, // 적당한 민감도
    marketing_efficiency: 2.5,
    others_overall_competitiveness: 0.8
  }
};

const defaultCompaniesConfig = [
  {
    name: "Company A",
    persona: "우리는 시장 1위의 프리미엄 브랜드입니다. 고품질(High Quality) 전략을 유지하되, 시장 점유율이 30% 이하로 떨어지면 즉시 가격을 인하하여 방어해야 합니다. 무조건적인 고가 정책보다는 '이익 총액(Total Profit)' 극대화를 최우선으로 합니다. 경쟁사가 치고 올라오면 마케팅과 가격 대응을 동시에 하십시오.",
    initial_unit_cost: 20000, // 원가 인하 (마진 확보용)
    initial_market_share: 0.4,
    initial_product_quality: 85.0,
    initial_brand_awareness: 80.0
  },
  {
    name: "Company B",
    persona: "우리는 가성비로 시장을 공략합니다. 공격적으로 점유율을 늘리되, 절대로 '원가 이하(Below Cost)'로 판매해서는 안 됩니다. 반드시 마진(Margin)을 남겨야 합니다. 점유율이 40%를 넘으면 가격을 조금씩 올려 수익을 실현하십시오. 생존을 위한 순이익(Net Profit) 확보가 점유율보다 중요합니다.",
    initial_unit_cost: 10000, // 원가 인하 (마진 확보용)
    initial_market_share: 0.2,
    initial_product_quality: 55.0,
    initial_brand_awareness: 40.0
  }
];

// --- 컴포넌트: 물리 엔진 가이드 패널 ---
const PhysicsGuidePanel = () => (
  <div style={{ backgroundColor: '#f8f9fa', padding: '15px', border: '1px solid #dee2e6', borderRadius: '8px', marginTop: '10px', marginBottom: '20px', fontSize: '0.9em' }}>
    <h4 style={{ marginTop: 0, color: '#495057' }}>📚 물리 엔진 설정 레퍼런스 (Cheat Sheet)</h4>
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '15px' }}>
      {Object.entries(PHYSICS_GUIDE).map(([key, info]) => (
        <div key={key} style={{ backgroundColor: 'white', padding: '10px', borderRadius: '5px', border: '1px solid #eee' }}>
          <div style={{ fontWeight: 'bold', color: '#007bff', marginBottom: '5px' }}>{info.label}</div>
          <div style={{ fontSize: '0.85em', color: '#555', marginBottom: '8px', fontStyle: 'italic' }}>{info.desc}</div>
          <table style={{ width: '100%', fontSize: '0.85em', borderCollapse: 'collapse' }}>
            <tbody>
              {info.levels.map((lvl, idx) => (
                <tr key={idx} style={{ borderBottom: idx < 2 ? '1px dashed #eee' : 'none' }}>
                  <td style={{ padding: '3px', fontWeight: 'bold', color: '#333', width: '35%' }}>{lvl.label}</td>
                  <td style={{ padding: '3px', color: '#666' }}>{lvl.desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  </div>
);

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
  const [showGuide, setShowGuide] = useState(false);
  const [globalConfig, setGlobalConfig] = useState(defaultGlobalConfig);
  const [companiesConfig, setCompaniesConfig] = useState(defaultCompaniesConfig);

  const [choiceOptions, setChoiceOptions] = useState(null);
  const [selectedDecisions, setSelectedDecisions] = useState({});
  const [isWaitingForChoice, setIsWaitingForChoice] = useState(false);
  const [isAutoRun, setIsAutoRun] = useState(false);
  const [isLooping, setIsLooping] = useState(false);

  // Track B States
  const [benchmarkResult, setBenchmarkResult] = useState(null);
  const [uploadedBenchmarkData, setUploadedBenchmarkData] = useState(null);
  const [tunedParams, setTunedParams] = useState(null);
  const [presets, setPresets] = useState([]);
  const [selectedPreset, setSelectedPreset] = useState("");

  const loadPresets = async () => {
      const data = await api.getPresets();
      setPresets(data);
  };

  useEffect(() => {
    loadPresets();
  }, []);

  const getChartLines = (names, isBenchmark = false) => {
    const lines = {
      accumulated_profit: [], market_share: [], price: [],
      marketing_brand_spend: [], marketing_promo_spend: [],
      rd_innovation_spend: [], rd_efficiency_spend: [],
      unit_cost: [], product_quality: [], brand_awareness: [],
      accumulated_rd_innovation: [], accumulated_rd_efficiency: [], error: []
    };

    names.forEach((name, index) => {
      const color = COMPANY_COLORS[name] || '#'+(Math.random()*0xFFFFFF<<0).toString(16);
      lines.accumulated_profit.push({ dataKey: `${name}_accumulated_profit`, stroke: color });
      lines.market_share.push({ dataKey: `${name}_market_share`, stroke: color });
      lines.price.push({ dataKey: `${name}_price`, stroke: color });
      lines.marketing_brand_spend.push({ dataKey: `${name}_marketing_brand_spend`, stroke: color });
      lines.marketing_promo_spend.push({ dataKey: `${name}_marketing_promo_spend`, stroke: color });
      lines.rd_innovation_spend.push({ dataKey: `${name}_rd_innovation_spend`, stroke: color });
      lines.rd_efficiency_spend.push({ dataKey: `${name}_rd_efficiency_spend`, stroke: color });
      lines.unit_cost.push({ dataKey: `${name}_unit_cost`, stroke: color });
      lines.product_quality.push({ dataKey: `${name}_product_quality`, stroke: color });
      lines.brand_awareness.push({ dataKey: `${name}_brand_awareness`, stroke: color });
      
      lines.accumulated_rd_innovation.push({ dataKey: `${name}_accumulated_rd_innovation_point`, stroke: color });
      lines.accumulated_rd_efficiency.push({ dataKey: `${name}_accumulated_rd_efficiency_point`, stroke: color });

      if (isBenchmark) {
        lines.error.push({ dataKey: `${name}_error`, stroke: color });
      }
    });
    return lines;
  };
  
  const handleGlobalConfigChange = (e) => {
    const { name, value } = e.target;
    setGlobalConfig(prev => ({ ...prev, [name]: parseFloat(value) || 0 }));
  };

  const handlePhysicsConfigChange = (e) => {
    const { name, value } = e.target;
    setGlobalConfig(prev => ({
      ...prev,
      physics: {
        ...prev.physics,
        [name]: parseFloat(value) || 0
      }
    }));
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

  const handlePresetChange = (e) => {
    const filename = e.target.value;
    setSelectedPreset(filename);

    if (!filename) return;

    const selectedData = presets.find(p => p.filename === filename);

    if (selectedData && selectedData.config) {
        const newPhysics = {
            ...globalConfig.physics,
            ...(selectedData.config.physics || {})
        };

        const { physics, ...otherConfigs } = selectedData.config;
        
        setGlobalConfig(prev => ({
            ...prev,
            ...otherConfigs,
            physics: newPhysics
        }));
    }
  };

  // --- Track B: Admin Functions ---
  const handleBenchmarkFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (evt) => {
      try {
        const jsonData = JSON.parse(evt.target.result);
        jsonData.physics_override = {
            ...globalConfig.physics,
            rd_innovation_impact: globalConfig.rd_innovation_impact,
            rd_innovation_threshold: globalConfig.rd_innovation_threshold
        };

        setUploadedBenchmarkData(jsonData);
        setIsLoading(true);
        setError(null);
        setBenchmarkResult(null);
        
        const result = await api.runBenchmark(jsonData);
        setBenchmarkResult(result);
        
        if (result.history.length > 0) {
          const keys = Object.keys(result.history[0]);
          const extractedNames = [];
          keys.forEach(k => {
            if (k.endsWith('_market_share')) {
              extractedNames.push(k.replace('_market_share', ''));
            }
          });
          setCompanyNames([...new Set(extractedNames)]);
        }
        setIsLoading(false);
      } catch (err) {
        setError("벤치마크 실행 실패: " + err.message);
        setIsLoading(false);
      }
      e.target.value = null;
    };
    reader.readAsText(file);
  };

  const handleAutoTune = async () => {
    if (!uploadedBenchmarkData) {
      alert("먼저 벤치마크 파일(.json)을 업로드해주세요.");
      return;
    }
    setIsLoading(true);
    try {
      const result = await api.autoTuneParams(uploadedBenchmarkData);
      setTunedParams(result);
      alert(`튜닝 완료! 최소 오차: ${(result.lowest_mae*100).toFixed(2)}%p\n(화면의 '적용' 버튼을 눌러 반영하세요)`);
    } catch (err) {
      setError("자동 튜닝 실패: " + err.message);
    }
    setIsLoading(false);
  };

  const applyTunedParams = () => {
    if (!tunedParams) return;
    
    const newPhysics = { ...globalConfig.physics, ...tunedParams.best_params };
    let newGlobal = { ...globalConfig };
    
    if (tunedParams.best_params.rd_innovation_impact) {
        newGlobal.rd_innovation_impact = tunedParams.best_params.rd_innovation_impact;
        delete newPhysics.rd_innovation_impact;
    }
    if (tunedParams.best_params.rd_innovation_threshold) {
        newGlobal.rd_innovation_threshold = tunedParams.best_params.rd_innovation_threshold;
        delete newPhysics.rd_innovation_threshold;
    }
    
    newGlobal.physics = newPhysics;
    setGlobalConfig(newGlobal);
    
    alert("최적 파라미터가 설정에 적용되었습니다. 다시 벤치마크를 실행해보세요!");
  };

  const handleSavePreset = async () => {
      if (!tunedParams) return alert("No tuned parameters to save.");
      const name = prompt("Enter Preset Name (e.g., 'Console War 2014'):", "New Preset");
      if (!name) return;
      
      const presetData = {
          filename: name.replace(/\s+/g, '_').toLowerCase(),
          preset_name: name,
          description: `Auto-tuned from ${benchmarkResult?.scenario || 'benchmark'}. MAE: ${(tunedParams.lowest_mae*100).toFixed(2)}%`,
          config: {
              ...globalConfig,
              physics: tunedParams.best_params
          }
      };

      try {
          await api.savePreset(presetData);
          alert("Preset Saved!");
          loadPresets();
      } catch (err) {
          alert("Save Failed: " + err.message);
      }
  };

  // --- Track A: Battle Functions ---
  const handleCreateSimulation = async () => {
    setIsLoading(true);
    setError(null);
    setHistory([]);
    setAiReasoning([]);
    setCurrentTurn(0);
    setBenchmarkResult(null);

    const config = {
      ...globalConfig,
      companies: companiesConfig,
      preset_name: selectedPreset || null
    };
    
    try {
      const data = await api.createSimulation(config);
      setSimulationId(data.simulation_id);
      
      if (data.initial_state.config.physics) {
          setGlobalConfig(prev => ({ ...prev, physics: data.initial_state.config.physics }));
      }
      if (data.initial_state.config.rd_innovation_threshold) {
          setGlobalConfig(prev => ({ ...prev, rd_innovation_threshold: data.initial_state.config.rd_innovation_threshold }));
      }
      if (data.initial_state.config.rd_innovation_impact) {
          setGlobalConfig(prev => ({ ...prev, rd_innovation_impact: data.initial_state.config.rd_innovation_impact }));
      }
      
      setCompanyNames(config.companies.map(c => c.name));
      setTotalTurns(config.total_turns);
      setShowConfig(false);
    } catch (err) {
      setError("시뮬레이션 생성 실패: " + err.message);
    }
    setIsLoading(false);
  };

  const handleGetChoices = useCallback(async () => {
    if (!simulationId) return;
    setError(null);
    try {
      const choices = await api.getDecisionChoices(simulationId);
      setChoiceOptions(choices);
      setIsWaitingForChoice(true);
      setSelectedDecisions({});
    } catch (err) {
      setError(`선택지 요청 실패: ` + err.message);
      setIsAutoRun(false); setIsLooping(false); setIsLoading(false);
      throw err;
    }
  }, [simulationId]);

  // [수정됨] 재귀 호출 제거하고, 오직 1턴 실행만 담당
  const handleExecuteTurn = useCallback(async () => {
    // (이전 조건문 유지)
    if (!simulationId || isLoading || !isWaitingForChoice) return;
    
    setIsLoading(true); 
    setError(null);
    
    try {
      const decisionsToExecute = {};
      companyNames.forEach(name => {
        if (selectedDecisions[name]) {
          decisionsToExecute[name] = {
            ...selectedDecisions[name].decision,
            reasoning: selectedDecisions[name].reasoning
          };
        }
      });

      // API 호출
      const data = await api.executeTurn(simulationId, decisionsToExecute);
      
      // 상태 업데이트
      setHistory(prevHistory => [...prevHistory, data.turn_results]);
      setCurrentTurn(data.turn);

      // 로그 처리
      let formattedReasons = [];
      if (data.ai_reasoning && typeof data.ai_reasoning === 'object') {
          formattedReasons = Object.entries(data.ai_reasoning).map(([name, reason]) => `[${name}]: ${reason}`);
      } else {
          formattedReasons = ["(No AI Log)"];
      }

      setAiReasoning(prev => [...prev, {
        turn: data.turn,
        reasons: formattedReasons
      }]);

      // 다음 턴 준비
      setIsWaitingForChoice(false); 
      setChoiceOptions(null); 
      setSelectedDecisions({});

      // [중요 수정] 루핑 여부와 상관없이, 이번 턴의 실행(통신)이 끝났으므로 로딩을 반드시 꺼야 합니다.
      // 그래야 useEffect(Loop Driver)가 '로딩 끝났네? 다음 턴 진행하자'라고 인식합니다.
      setIsLoading(false); 

    } catch (err) {
      console.error("❌ Turn Execution Error:", err);
      setError(`턴 실행 실패: ` + err.message);
      // 에러 발생 시에는 루프도 멈추는 것이 안전합니다.
      setIsAutoRun(false); 
      setIsLooping(false); 
      setIsLoading(false);
    }

  }, [simulationId, isLoading, isWaitingForChoice, companyNames, selectedDecisions]);

  // [신규] 자동 주행(Looping)을 관리하는 Driver
  useEffect(() => {
    if (isLooping && !isLoading && !isWaitingForChoice && simulationId && currentTurn < totalTurns) {
        
        console.log(`🕒 ${currentTurn}턴 완료. 1초 후 다음 턴 요청...`);
        
        // 속도 조절: 1초(1000ms) 딜레이
        const timer = setTimeout(() => {
            handleGetChoices();
        }, 1000); 

        return () => clearTimeout(timer);
    }
    
    if (isLooping && currentTurn >= totalTurns) {
        setIsLooping(false);
        setIsLoading(false);
        alert("시뮬레이션 종료!");
    }
  }, [isLooping, isLoading, isWaitingForChoice, simulationId, currentTurn, totalTurns, handleGetChoices]);


  const handleGetOneTurnChoices = async () => {
      if (isLoading || isLooping) return;
      setIsLoading(true);
      try { await handleGetChoices(); } catch (err) { console.error("1턴 선택지 로딩 실패:", err); }
      setIsLoading(false);
  };

  const handleRunAllTurns = useCallback(async () => {
    if (isLoading || currentTurn >= totalTurns || isLooping) return;
    
    // [중요 수정] 루핑 시작 시 '자동 선택(AutoRun)'도 강제로 켭니다.
    setIsLooping(true); 
    setIsAutoRun(true); 
    setIsLoading(true);
    
    // 첫 턴의 선택지 가져오기 트리거
    try {
      await handleGetChoices();
      // handleGetChoices는 내부적으로 isLoading을 끄지 않으므로 여기서 꺼줍니다.
      setIsLoading(false);
    } catch (err) {
      setError("첫 턴 선택지 로딩 중 오류: " + err.message);
      setIsLooping(false); 
      setIsAutoRun(false);
      setIsLoading(false);
    }
  }, [isLoading, currentTurn, totalTurns, isLooping, handleGetChoices]);

  const handleSelectChoice = (agentName, choice) => {
    setSelectedDecisions(prev => ({ ...prev, [agentName]: choice }));
  };

  // 자동 선택 (Auto Run)
  useEffect(() => {
    if (!isAutoRun || !isWaitingForChoice || !choiceOptions || isLoading) return;
    const selectedForState = {};
    let allAgentsHaveChoices = true;
    companyNames.forEach(name => {
      const choices = choiceOptions[name];
      if (!choices || choices.length === 0) { allAgentsHaveChoices = false; return; }
      const bestChoice = choices.reduce((max, current) => current.probability > max.probability ? current : max, choices[0]);
      selectedForState[name] = bestChoice;
    });
    if (allAgentsHaveChoices) setSelectedDecisions(selectedForState);
    else setIsAutoRun(false);
  }, [isAutoRun, isWaitingForChoice, isLoading, choiceOptions, companyNames]);

  // 자동 실행 (결정이 다 되면 실행)
  useEffect(() => {
    if (isLoading || !isWaitingForChoice || Object.keys(selectedDecisions).length < companyNames.length) return;
    // 루핑 중이거나, 자동 실행 모드일 때만 자동 클릭
    if (isLooping || isAutoRun) {
        handleExecuteTurn();
    }
  }, [isLooping, isAutoRun, isWaitingForChoice, selectedDecisions, isLoading, companyNames, handleExecuteTurn]);
  
  const handleDownloadCSV = () => {
    if (history.length === 0) {
      alert("다운로드할 데이터가 없습니다.");
      return;
    }
    try {
      const headers = Object.keys(history[0]);
      const headerString = headers.join(',');
      const rows = history.map(turnData => {
        return headers.map(header => turnData[header]).join(',');
      });
      const csvString = '\uFEFF' + [headerString, ...rows].join('\n');
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
      setError("CSV 다운로드 중 오류: " + err.message);
    }
  };
  
  return (
    <div style={{ fontFamily: 'sans-serif', padding: '20px', maxWidth: '1600px', margin: 'auto' }}>
      <h1 style={{ textAlign: 'center', color: '#333' }}>🤖 AI 전략 워게임 (Integrated Platform)</h1>
      
      <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: '#fff3cd', border: '1px solid #ffeeba', borderRadius: '5px' }}>
        <h3 style={{ marginTop: 0, color: '#856404' }}>🛠️ Track B: 관리자 튜닝 모드 (Benchmark & Auto-Tune)</h3>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <input 
              type="file" 
              accept=".json" 
              onChange={handleBenchmarkFileUpload}
              disabled={isLoading}
            />
            
            <button 
                onClick={handleAutoTune} 
                disabled={isLoading || !uploadedBenchmarkData}
                style={{ padding: '8px 16px', backgroundColor: '#ffc107', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}
            >
                ⚡ 자동 튜닝 시작
            </button>
        </div>

        {tunedParams && (
            <div style={{ marginTop: '15px', padding: '10px', backgroundColor: 'white', border: '1px solid #ddd' }}>
                <strong>🎯 튜닝 결과 (추천 값):</strong>
                <pre style={{ fontSize: '0.9em', backgroundColor: '#f5f5f5', padding: '5px' }}>
                    {JSON.stringify(tunedParams.best_params, null, 2)}
                </pre>
                <p style={{ margin: '5px 0', color: 'green' }}>예상 오차(MAE): {(tunedParams.lowest_mae * 100).toFixed(2)}%p</p>
                <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
                    <button 
                        onClick={applyTunedParams}
                        style={{ padding: '5px 10px', backgroundColor: '#28a745', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                    >
                        ✅ 설정에 적용하기
                    </button>
                    
                    <button 
                        onClick={handleSavePreset}
                        style={{ padding: '5px 10px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                    >
                        💾 프리셋으로 저장
                    </button>
                </div>
            </div>
        )}
        
        {isLoading && <span style={{ marginLeft: '10px', fontWeight: 'bold', color: 'blue' }}>작업 진행 중...</span>}
        {error && <div style={{ color: 'red', marginTop: '10px' }}>Error: {error}</div>}
      </div>

      {showConfig && (
        <div style={{ padding: '20px', border: '1px solid #ccc', borderRadius: '8px', marginBottom: '20px', backgroundColor: '#f9f9f9' }}>
            <div style={{ marginBottom: '15px', padding: '10px', backgroundColor: '#e9ecef', borderRadius: '5px' }}>
                <label style={{ fontWeight: 'bold', marginRight: '10px' }}>📂 시장 환경(Preset) 선택:</label>
                <select 
                    value={selectedPreset} 
                    onChange={handlePresetChange}
                    style={{ padding: '5px', fontSize: '1em', minWidth: '300px' }}
                >
                    <option value="">(기본값 - 사용자 설정)</option>
                    {presets.map(p => (
                        <option key={p.filename} value={p.filename}>{p.name} - {p.description}</option>
                    ))}
                </select>
                <div style={{marginTop: '5px', fontSize: '0.85em', color: '#666'}}>* 선택 시 아래 물리 엔진 설정값이 자동으로 변경됩니다.</div>
            </div>

            <h3>🌍 1. 글로벌 시장 설정 (거시 경제)</h3>
            
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '15px', marginBottom: '15px' }}>
                <div>
                   <label style={{fontWeight:'bold', color:'#007bff'}}>총 턴 수 (Total Turns)</label>
                   <input type="number" name="total_turns" value={globalConfig.total_turns} onChange={handleGlobalConfigChange} style={{width:'100%', padding:'8px', border:'2px solid #007bff', borderRadius:'5px'}} />
                </div>
                <div>
                   <label style={{fontWeight:'bold', color:'#28a745'}}>시장 규모 (Market Size)</label>
                   <input type="number" name="market_size" value={globalConfig.market_size} onChange={handleGlobalConfigChange} style={{width:'100%', padding:'8px', border:'2px solid #28a745', borderRadius:'5px'}} />
                </div>
                <div>
                   <label style={{fontWeight:'bold', color:'#dc3545'}}>초기 자본금 (Initial Capital)</label>
                   <input type="number" name="initial_capital" value={globalConfig.initial_capital} onChange={handleGlobalConfigChange} style={{width:'100%', padding:'8px', border:'2px solid #dc3545', borderRadius:'5px'}} />
                </div>
            </div>

            <details style={{ marginBottom: '20px', backgroundColor: '#f1f3f5', padding: '10px', borderRadius: '5px', border: '1px solid #dee2e6' }}>
                <summary style={{ cursor: 'pointer', fontWeight: 'bold', color: '#495057' }}>🔽 고급 시장 역학 설정 (마케팅 비용, 감가상각, R&D 효율 등)</summary>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '15px', marginTop: '15px' }}>
                    {Object.entries(globalConfig).map(([key, value]) => {
                        if (['total_turns', 'market_size', 'initial_capital', 'physics', 'rd_innovation_impact', 'rd_innovation_threshold'].includes(key)) return null;
                        
                        let label = key;
                        let desc = "";
                        if (key === 'gdp_growth_rate') { label = "GDP 성장률"; desc = "매 턴 시장 크기 증가율 (0.01 = 1%)"; }
                        else if (key === 'inflation_rate') { label = "물가 상승률"; desc = "매 턴 비용 상승률 (0.005 = 0.5%)"; }
                        else if (key === 'marketing_cost_base') { label = "마케팅 기초 비용"; desc = "마케팅 시작 시 드는 기본 비용 (진입장벽)"; }
                        else if (key === 'marketing_cost_multiplier') { label = "마케팅 비용 체증률"; desc = "투입량 대비 비용 증가 가속도 (1.0=선형, >1.0=체증)"; }
                        else if (key === 'rd_efficiency_threshold') { label = "원가절감 필요 투자금"; desc = "이 금액이 모여야 원가가 절감됨"; }
                        else if (key === 'rd_efficiency_impact') { label = "원가절감 비율"; desc = "성공 시 원가가 줄어드는 비율 (0.05 = 5%)"; }
                        else if (key === 'quality_decay_rate') { label = "품질 노후화 속도"; desc = "시간이 지날수록 품질이 떨어지는 비율 (0.1 = 10%)"; }
                        else if (key === 'brand_decay_rate') { label = "브랜드 망각 속도"; desc = "시간이 지날수록 브랜드가 잊혀지는 비율"; }

                        return (
                            <div key={key} style={{ backgroundColor: 'white', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}>
                                <label style={{ fontSize: '0.9em', fontWeight: 'bold', display: 'block' }}>{label}</label>
                                <div style={{ fontSize: '0.75em', color: '#666', marginBottom: '4px' }}>{key}</div>
                                <input
                                    type="number"
                                    step={value < 1 ? "0.001" : "1000"} 
                                    name={key}
                                    value={value}
                                    onChange={handleGlobalConfigChange}
                                    style={{ width: '100%', padding: '5px', border: '1px solid #ccc' }}
                                />
                                <div style={{ fontSize: '0.75em', color: '#888', marginTop: '2px' }}>💡 {desc}</div>
                            </div>
                        );
                    })}
                </div>
            </details>

            <div style={{ marginTop: '20px', borderTop: '1px dashed #ccc', paddingTop: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
                    <h4 style={{ margin: 0 }}>⚙️ Engine Tuning (Market Physics + R&D)</h4>
                    <button 
                        onClick={() => setShowGuide(!showGuide)}
                        style={{ padding: '6px 12px', fontSize: '0.85em', cursor: 'pointer', backgroundColor: showGuide ? '#5a6268' : '#17a2b8', color: 'white', border: 'none', borderRadius: '20px', transition: 'all 0.2s' }}
                    >
                        {showGuide ? '▲ 가이드 접기' : 'ℹ️ 설정 도우미 (Cheat Sheet)'}
                    </button>
                </div>
                
                {showGuide && <PhysicsGuidePanel />}

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '15px', backgroundColor: '#eef' , padding: '15px', borderRadius: '5px', border: '1px solid #dde'}}>
                    {TUNING_UI_ORDER.map((key) => {
                        const isRD = key.startsWith('rd_');
                        const value = isRD ? globalConfig[key] : globalConfig.physics[key];
                        const onChange = isRD ? handleGlobalConfigChange : handlePhysicsConfigChange;
                        const label = FIELD_LABELS[key] || key;

                        return (
                            <div key={key}>
                                <label style={{ fontSize: '0.85em', display: 'block', color: '#333', fontWeight: 'bold', marginBottom: '3px' }}>
                                    {label}
                                </label>
                                <input
                                    type="number"
                                    name={key}
                                    value={value}
                                    onChange={onChange}
                                    style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px' }}
                                />
                            </div>
                        );
                    })}
                </div>
            </div>
            
            <h3 style={{ marginTop: '20px' }}>🏢 2. AI 회사 설정</h3>
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
                        <label>initial_market_share</label>
                        <input type="number" step="0.01" name="initial_market_share" value={company.initial_market_share} onChange={e => handleCompanyConfigChange(index, e)} style={{ width: '100%' }} />
                    </div>
                    <div>
                        <label>initial_quality</label>
                        <input type="number" name="initial_product_quality" value={company.initial_product_quality} onChange={e => handleCompanyConfigChange(index, e)} style={{ width: '100%' }} />
                    </div>
                    <div>
                        <label>initial_brand</label>
                        <input type="number" name="initial_brand_awareness" value={company.initial_brand_awareness} onChange={e => handleCompanyConfigChange(index, e)} style={{ width: '100%' }} />
                    </div>
                </div>
                <div>
                    <label style={{ marginTop: '10px', display: 'block' }}>persona (AI 전략 성향)</label>
                    <textarea
                        name="persona"
                        value={company.persona}
                        onChange={e => handleCompanyConfigChange(index, e)}
                        style={{ width: '100%', height: '60px', fontSize: '0.9em', padding: '5px', marginTop: '5px' }}
                    />
                </div>
                </div>
            ))}
            <button onClick={handleCreateSimulation} disabled={isLoading} style={{ marginTop: '20px', padding: '15px', width: '100%', fontSize: '1.2em', backgroundColor: '#28a745', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer', fontWeight: 'bold', boxShadow: '0 2px 5px rgba(0,0,0,0.2)' }}>
                🚀 시뮬레이션 시작 (Battle Start)
            </button>
        </div>
      )}

      {benchmarkResult && (
        <div style={{ marginTop: '20px', padding: '20px', border: '2px solid #856404', borderRadius: '8px', backgroundColor: '#fff3cd' }}>
          <h2 style={{ color: '#856404' }}>📊 벤치마크 결과: {benchmarkResult.scenario}</h2>
          <div style={{ fontSize: '1.2em', marginBottom: '20px' }}>
            <strong>평균 오차(MAE): </strong> 
            <span style={{ color: benchmarkResult.average_error_mae > 0.1 ? 'red' : 'green' }}>
              {(benchmarkResult.average_error_mae * 100).toFixed(2)}%p
            </span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '20px', minHeight: '400px', paddingBottom: '20px' }}>
              <SimulationChart data={benchmarkResult.history} lines={getChartLines(companyNames, true).error} title="점유율 오차 (Error)" format={(v) => `${(v * 100).toFixed(1)}%p`} />
              <SimulationChart data={benchmarkResult.history} lines={getChartLines(companyNames, true).market_share} title="시뮬레이션 점유율" format={(v) => `${(v * 100).toFixed(1)}%`} />
              <SimulationChart data={benchmarkResult.history} lines={getChartLines(companyNames, true).product_quality} title="제품 품질 변화" />
              <SimulationChart data={benchmarkResult.history} lines={getChartLines(companyNames, true).unit_cost} title="단위 원가 변화" />
          </div>
        </div>
      )}

      {!showConfig && simulationId && !isWaitingForChoice && !benchmarkResult && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', padding: '15px', border: '1px solid #ccc', borderRadius: '8px', alignItems: 'center', backgroundColor: 'white', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
          <button onClick={handleGetOneTurnChoices} disabled={isLoading || (isAutoRun && isLooping)} style={{ backgroundColor: '#007bff', color: 'white', border: 'none', padding: '10px 15px', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>
            다음 1턴 결정 보기
          </button>
          <button onClick={handleRunAllTurns} disabled={isLoading || (isAutoRun && isLooping)} style={{ backgroundColor: '#28a745', color: 'white', border: 'none', padding: '10px 15px', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>
            🚀 남은 턴 모두 실행
          </button>
          <div style={{ marginLeft: '15px', display: 'flex', alignItems: 'center', backgroundColor: '#f1f1f1', padding: '8px 12px', borderRadius: '20px' }}>
            <input type="checkbox" id="autoRunCheck" checked={isAutoRun} onChange={(e) => { const checked = e.target.checked; setIsAutoRun(checked); if (!checked) { setIsLooping(false); } }} disabled={isLoading} style={{ marginRight: '8px', width: '18px', height: '18px', cursor: 'pointer' }} />
            <label htmlFor="autoRunCheck" style={{ cursor: 'pointer', userSelect: 'none', fontWeight: 'bold', color: '#333' }}>{isLooping ? (isAutoRun ? '■ 자동 반복 중...' : '■ 수동 반복 중...') : '최고 확률 자동 선택'}</label>
          </div>
          <button onClick={handleDownloadCSV} disabled={history.length === 0 || isLoading} style={{ backgroundColor: (history.length === 0 || isLoading) ? '#ccc' : '#17a2b8', color: 'white', marginLeft: 'auto', border: 'none', padding: '10px 15px', borderRadius: '4px', cursor: 'pointer' }}>
            📥 결과 다운로드 (CSV)
          </button>
          {isLoading && <div style={{ color: '#0056b3', marginLeft: '15px', fontWeight: 'bold' }}>⏳ AI 생각 중...</div>}
          {error && <div style={{ color: 'red', marginLeft: '15px' }}>⚠️ [오류] {error}</div>}
        </div>
      )}

      {isWaitingForChoice && choiceOptions && !benchmarkResult && (
        <div style={{ marginTop: '20px', padding: '20px', border: '1px solid #007bff', borderRadius: '8px', backgroundColor: '#eaf4ff' }}>
          <h3 style={{ textAlign: 'center', color: '#0056b3', marginTop: 0 }}>🧠 AI 전략 수립 완료: {currentTurn + 1}턴 </h3>
          <div style={{ display: 'grid', gridTemplateColumns: `repeat(${companyNames.length}, 1fr)`, gap: '15px' }}>
              {companyNames.map(name => (
              <div key={name} style={{ border: '1px solid #ccc', padding: '15px', backgroundColor: '#fff', borderRadius: '8px', boxShadow: '0 2px 5px rgba(0,0,0,0.05)' }}>
                <h4 style={{ color: COMPANY_COLORS[name] || '#000', borderBottom: '2px solid #eee', paddingBottom: '10px', marginTop: 0 }}>{name}의 전략</h4>
                {choiceOptions[name] && choiceOptions[name].map((choice, index) => {
                  const isSelected = selectedDecisions[name] === choice;
                  return (
                    <button 
                      key={index}
                      onClick={() => handleSelectChoice(name, choice)}
                      style={{ display: 'block', width: '100%', marginBottom: '10px', backgroundColor: isSelected ? '#007bff' : 'white', color: isSelected ? 'white' : '#333', border: isSelected ? '1px solid #0056b3' : '1px solid #ddd', padding: '12px', textAlign: 'left', cursor: 'pointer', borderRadius: '6px', boxShadow: isSelected ? '0 2px 5px rgba(0,123,255,0.3)' : 'none', transition: 'all 0.2s' }}>
                      <div style={{display:'flex', justifyContent:'space-between', marginBottom:'5px', alignItems: 'center'}}>
                        <strong style={{fontSize:'1.1em'}}>전략 {index + 1}</strong>
                        <span style={{backgroundColor: isSelected?'rgba(255,255,255,0.3)':'#f1f1f1', padding:'3px 8px', borderRadius:'12px', fontSize:'0.85em', fontWeight: 'bold'}}>확률: {(choice.probability * 100).toFixed(0)}%</span>
                      </div>
                      <p style={{ fontSize: '0.95em', margin: '8px 0', lineHeight: '1.5' }}>{choice.reasoning}</p>
                      <div style={{fontSize: '0.85em', color: isSelected?'#e0e0e0':'#666', marginTop:'8px', borderTop: isSelected ? '1px solid rgba(255,255,255,0.2)' : '1px solid #eee', paddingTop: '5px'}}>
                        🏷️ 가격: {choice.decision.price.toLocaleString()} | 📢 마케팅: {(choice.decision.marketing_brand_spend/10000).toFixed(0)}만 | 🔬 R&D: {(choice.decision.rd_innovation_spend/10000).toFixed(0)}만
                      </div>
                    </button>
                  );
                })}
              </div>
            ))}
          </div>
          <button onClick={handleExecuteTurn} disabled={isLoading || Object.keys(selectedDecisions).length < companyNames.length} style={{ width: '100%', padding: '15px', fontSize: '1.2em', backgroundColor: '#28a745', color: 'white', marginTop: '15px', border: 'none', borderRadius: '5px', cursor: 'pointer', fontWeight: 'bold', boxShadow: '0 3px 6px rgba(0,0,0,0.2)' }}>
            ✅ 선택 완료 및 턴 실행
          </button>
        </div>
      )}

      {!benchmarkResult && aiReasoning.length > 0 && (
        <div style={{ marginTop: '20px', padding: '10px', border: '1px solid #eee', borderRadius: '8px', height: '150px', overflowY: 'scroll', backgroundColor: '#282c34', color: '#e6e6e6', fontSize: '0.9em' }}>
          <strong>[AI 결정 로그]</strong>
          {aiReasoning.slice().reverse().map((entry, idx) => (
            <div key={idx} style={{ borderTop: '1px dashed #555', paddingTop: '5px', marginTop: '5px' }}>
              <strong>--- {entry.turn}턴 결정 ---</strong>
              {entry.reasons.map((reason, rIdx) => <div key={rIdx}>{reason}</div>)}
            </div>
          ))}
        </div>
      )}

      {!benchmarkResult && history.length > 0 && (
         <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(450px, 1fr))', gap: '25px', marginTop: '30px' }}>
            <SimulationChart data={history} lines={getChartLines(companyNames).market_share} title="시장 점유율 (%)" format={(v) => `${(v * 100).toFixed(1)}%`} />
            <SimulationChart data={history} lines={getChartLines(companyNames).accumulated_profit} title="누적 이익 (원)" />
            <SimulationChart data={history} lines={getChartLines(companyNames).product_quality} title="제품 품질 (점수)" />
            <SimulationChart data={history} lines={getChartLines(companyNames).price} title="제품 가격 (원)" />
            <SimulationChart data={history} lines={getChartLines(companyNames).marketing_brand_spend} title="마케팅 (브랜드) 지출" />
            <SimulationChart data={history} lines={getChartLines(companyNames).marketing_promo_spend} title="마케팅 (판촉) 지출" />
            <SimulationChart data={history} lines={getChartLines(companyNames).rd_innovation_spend} title="R&D (품질 혁신) 지출" />
            <SimulationChart data={history} lines={getChartLines(companyNames).rd_efficiency_spend} title="R&D (원가 절감) 지출" />
            <SimulationChart data={history} lines={getChartLines(companyNames).unit_cost} title="단위 원가 (원)" />
            <SimulationChart data={history} lines={getChartLines(companyNames).brand_awareness} title="브랜드 인지도" />
            <SimulationChart data={history} lines={getChartLines(companyNames).accumulated_rd_innovation} title="R&D 혁신 누적" format={(v) => `${(v / 1000000).toFixed(1)}M`} />
         </div>
      )}
    </div>
  );
}

export default App;