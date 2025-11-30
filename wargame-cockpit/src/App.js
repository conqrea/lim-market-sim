import React, { useState, useEffect, useCallback } from 'react';
import SimulationChart from './SimulationChart';
import * as api from './apiService';

// =================================================================================
// 1. 상수 및 설정 데이터 (Constants & Configs)
// =================================================================================

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

// [가이드] 물리 엔진 설정 레퍼런스 (상세 설명 포함)
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

// 기본 시뮬레이션 설정값 (황금 밸런스 조정판)
const defaultGlobalConfig = {
  total_turns: 20,
  market_size: 50000,
  initial_capital: 1000000000, // 10억
  initial_marketing_budget_ratio: 0.02,
  initial_rd_budget_ratio: 0.01,
  
  gdp_growth_rate: 0.02, // 2% 성장
  inflation_rate: 0.005, // 0.5% 물가

  // R&D 관련 설정
  rd_innovation_threshold: 30000000.0, // 3천만
  rd_innovation_impact: 15.0,
  rd_efficiency_threshold: 50000000.0, // 5천만
  rd_efficiency_impact: 0.05, // 5%

  // 마케팅 관련 설정
  marketing_cost_base: 3000000.0, // 300만
  marketing_cost_multiplier: 1.5, // 비용 체증

  // 감가상각 설정
  quality_decay_rate: 0.05, // 5%
  brand_decay_rate: 0.1, // 10%

  // 물리 엔진 (황금 밸런스)
  physics: {
    weight_quality: 0.4,
    weight_brand: 0.2,
    weight_price: 0.4,
    price_sensitivity: 15.0,
    marketing_efficiency: 2.5,
    others_overall_competitiveness: 0.8
  }
};

// 기본 회사 설정값
const defaultCompaniesConfig = [
  {
    name: "Company A",
    persona: "우리는 시장 1위의 프리미엄 브랜드입니다. 고품질(High Quality) 전략을 유지하되, 시장 점유율이 30% 이하로 떨어지면 즉시 가격을 인하하여 방어해야 합니다. 무조건적인 고가 정책보다는 '이익 총액(Total Profit)' 극대화를 최우선으로 합니다. 경쟁사가 치고 올라오면 마케팅과 가격 대응을 동시에 하십시오.",
    initial_unit_cost: 20000,
    initial_market_share: 0.4,
    initial_product_quality: 85.0,
    initial_brand_awareness: 80.0
  },
  {
    name: "Company B",
    persona: "우리는 가성비로 시장을 공략합니다. 공격적으로 점유율을 늘리되, 절대로 '원가 이하(Below Cost)'로 판매해서는 안 됩니다. 반드시 마진(Margin)을 남겨야 합니다. 점유율이 40%를 넘으면 가격을 조금씩 올려 수익을 실현하십시오. 생존을 위한 순이익(Net Profit) 확보가 점유율보다 중요합니다.",
    initial_unit_cost: 10000,
    initial_market_share: 0.2,
    initial_product_quality: 55.0,
    initial_brand_awareness: 40.0
  }
];

// --- [UI 컴포넌트] 물리 엔진 가이드 패널 ---
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

// =================================================================================
// 2. 메인 App 컴포넌트
// =================================================================================

function App() {
  // -------------------------------------------------------------------------------
  // [State] 탭 및 화면 관리
  // -------------------------------------------------------------------------------
  const [activeTab, setActiveTab] = useState('setup'); // 'setup' | 'battle' | 'lab'
  
  // -------------------------------------------------------------------------------
  // [State] 시뮬레이션 공통 데이터
  // -------------------------------------------------------------------------------
  const [simulationId, setSimulationId] = useState(null);
  const [history, setHistory] = useState([]);
  const [companyNames, setCompanyNames] = useState([]);
  const [currentTurn, setCurrentTurn] = useState(0);
  const [totalTurns, setTotalTurns] = useState(defaultGlobalConfig.total_turns);
  
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [aiReasoning, setAiReasoning] = useState([]);
  
  // -------------------------------------------------------------------------------
  // [State] 설정 및 게임 플레이
  // -------------------------------------------------------------------------------
  const [showGuide, setShowGuide] = useState(false);
  const [globalConfig, setGlobalConfig] = useState(defaultGlobalConfig);
  const [companiesConfig, setCompaniesConfig] = useState(defaultCompaniesConfig);

  const [choiceOptions, setChoiceOptions] = useState(null);
  const [selectedDecisions, setSelectedDecisions] = useState({});
  const [isWaitingForChoice, setIsWaitingForChoice] = useState(false);
  
  const [isAutoRun, setIsAutoRun] = useState(false);
  const [isLooping, setIsLooping] = useState(false);

  // -------------------------------------------------------------------------------
  // [State] Track B (Tuning)
  // -------------------------------------------------------------------------------
  const [benchmarkResult, setBenchmarkResult] = useState(null);
  const [uploadedBenchmarkData, setUploadedBenchmarkData] = useState(null);
  const [tunedParams, setTunedParams] = useState(null);
  const [presets, setPresets] = useState([]);
  const [selectedPreset, setSelectedPreset] = useState("");
  const [benchmarkFileName, setBenchmarkFileName] = useState("");

  // -------------------------------------------------------------------------------
  // [State] Track C (Laboratory)
  // -------------------------------------------------------------------------------
  const [labMode, setLabMode] = useState('playback'); // 'playback' (과거) | 'simulation' (미래)
  const [actualHistory, setActualHistory] = useState([]); // JSON 전체 데이터
  const [targetCompanyForEdit, setTargetCompanyForEdit] = useState("");
  const [originalPersona, setOriginalPersona] = useState(""); // 변경 전 페르소나 저장
  const [currentPersona, setCurrentPersona] = useState("");   // 현재 편집 중인 페르소나
  const [interventionLog, setInterventionLog] = useState(null); // 개입 기록 { turn: 5, company: "GM", old: "...", new: "..." }
  const [personaSourceTurn, setPersonaSourceTurn] = useState(null);

  const [genTopic, setGenTopic] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);

  // [App.js 핸들러 함수 추가]
  const handleGenerateScenario = async () => {
      if (!genTopic) return alert("생성할 시나리오의 주제를 입력해주세요.\n(예: 전기차 전쟁 - 테슬라 vs BYD)");
      
      setIsGenerating(true);
      try {
          // 1. AI에게 생성 요청
          const data = await api.generateScenarioAI(genTopic);
          
          // 2. 생성된 데이터를 즉시 로드 (업로드한 것과 동일한 효과)
          setUploadedBenchmarkData(data);
          setBenchmarkFileName(`🤖 AI_Gen: ${genTopic}`);
          
          // 3. 그래프 확인을 위해 벤치마크 실행
          await executeBenchmark(data);
          
          alert(`✅ 시나리오 생성 완료!\n주제: ${data.scenario_name}\n\nTrack C(실험실)로 이동하여 페르소나를 확인해보세요.`);
          
      } catch (err) {
          alert("생성 실패: " + err.message);
      }
      setIsGenerating(false);
  };

  const handleDownloadScenario = () => {
    if (!uploadedBenchmarkData) return alert("다운로드할 시나리오 데이터가 없습니다.");
    
    // JSON 문자열로 변환 (보기 좋게 들여쓰기 2칸)
    const jsonString = JSON.stringify(uploadedBenchmarkData, null, 2);
    const blob = new Blob([jsonString], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    
    // 가상 링크 생성 및 클릭
    const link = document.createElement('a');
    link.href = url;
    // 파일명: 설정된 이름이 있으면 쓰고, 없으면 타임스탬프
    link.download = benchmarkFileName || `scenario_${new Date().getTime()}.json`;
    document.body.appendChild(link);
    link.click();
    
    // 뒷정리
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // -------------------------------------------------------------------------------
  // [Effect] 초기화 및 프리셋 로드
  // -------------------------------------------------------------------------------
  const loadPresets = async () => {
      try {
        const data = await api.getPresets();
        setPresets(data);
      } catch (err) {
        console.error("Failed to load presets", err);
      }
  };

  useEffect(() => {
    loadPresets();
  }, []);

  // -------------------------------------------------------------------------------
  // [Helper] 홈 리셋 기능
  // -------------------------------------------------------------------------------
  const handleGoHome = () => {
    if (window.confirm("홈으로 돌아가시겠습니까? 현재 진행 중인 시뮬레이션 데이터는 모두 초기화됩니다.")) {
        setActiveTab('setup');
        setSimulationId(null);
        setHistory([]);
        setAiReasoning([]);
        setBenchmarkResult(null);
        setIsAutoRun(false);
        setIsLooping(false);
        setError(null);
        setCurrentTurn(0);
    }
  };

  // -------------------------------------------------------------------------------
  // [Helper] 차트 데이터 라인 생성기
  // -------------------------------------------------------------------------------
  const getChartLines = (names, isBenchmark = false) => {
    const lines = {
      accumulated_profit: [], market_share: [], price: [],
      marketing_brand_spend: [], marketing_promo_spend: [],
      rd_innovation_spend: [], rd_efficiency_spend: [],
      unit_cost: [], product_quality: [], brand_awareness: [],
      accumulated_rd_innovation: [], accumulated_rd_efficiency: [], error: []
    };

    names.forEach((name) => {
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

  // -------------------------------------------------------------------------------
  // [Handler] 설정 변경 핸들러
  // -------------------------------------------------------------------------------
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
        // 물리 엔진 병합
        const newPhysics = {
            ...globalConfig.physics,
            ...(selectedData.config.physics || {})
        };
        // 나머지 설정 병합
        const { physics, ...otherConfigs } = selectedData.config;
        
        setGlobalConfig(prev => ({
            ...prev,
            ...otherConfigs,
            physics: newPhysics
        }));
    }
  };

  // -------------------------------------------------------------------------------
  // [Track B] 벤치마크 & 튜닝 기능
  // -------------------------------------------------------------------------------
  const executeBenchmark = async (jsonData) => {
    setIsLoading(true);
    setError(null);
    setBenchmarkResult(null);
    
    try {
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
    } catch (err) {
        setError("벤치마크 실행 실패: " + err.message);
    } finally {
        setIsLoading(false);
    }
  };

  const handleBenchmarkFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setBenchmarkFileName(file.name);

    const reader = new FileReader();
    reader.onload = async (evt) => {
      try {
        const jsonData = JSON.parse(evt.target.result);
        
        // 현재 설정값들을 override 파라미터로 주입하여 테스트
        jsonData.physics_override = {
            ...globalConfig.physics,
            rd_innovation_impact: globalConfig.rd_innovation_impact,
            rd_innovation_threshold: globalConfig.rd_innovation_threshold
        };

        setUploadedBenchmarkData(jsonData);
        await executeBenchmark(jsonData);
      } catch (err) {
        setError("파일 파싱 실패: " + err.message);
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
    } catch (err) {
      setError("자동 튜닝 실패: " + err.message);
    }
    setIsLoading(false);
  };

  const applyTunedParams = async () => {
    if (!tunedParams || !uploadedBenchmarkData) return;
    
    const bestParams = tunedParams.best_params;
    const newPhysics = { ...globalConfig.physics, ...bestParams };
    let newGlobal = { ...globalConfig };
    
    // Root 레벨 변수 처리
    if (bestParams.rd_innovation_impact) {
        newGlobal.rd_innovation_impact = bestParams.rd_innovation_impact;
        delete newPhysics.rd_innovation_impact;
    }
    if (bestParams.rd_innovation_threshold) {
        newGlobal.rd_innovation_threshold = bestParams.rd_innovation_threshold;
        delete newPhysics.rd_innovation_threshold;
    }
    
    newGlobal.physics = newPhysics;
    setGlobalConfig(newGlobal);
    
    // 설정 적용 후 즉시 재테스트
    const retestData = {
        ...uploadedBenchmarkData,
        physics_override: {
            ...newPhysics,
            rd_innovation_impact: newGlobal.rd_innovation_impact,
            rd_innovation_threshold: newGlobal.rd_innovation_threshold
        }
    };
    
    await executeBenchmark(retestData);
  };

  const handleSavePreset = async () => {
      if (!tunedParams) return alert("No tuned parameters to save.");
      const name = prompt("Enter Preset Name (e.g., 'Console War 2014'):", "New Preset");
      if (!name) return;
      
      const presetData = {
          filename: name.replace(/\s+/g, '_').toLowerCase(),
          preset_name: name,
          description: `Auto-tuned MAE: ${(tunedParams.lowest_mae*100).toFixed(2)}%`,
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

  // -------------------------------------------------------------------------------
  // [Track A] 일반 전투 (Battle Mode)
  // -------------------------------------------------------------------------------
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
      
      // 서버에서 확정된 초기 상태를 클라이언트에 반영
      if (data.initial_state.config.physics) {
          setGlobalConfig(prev => ({ ...prev, physics: data.initial_state.config.physics }));
      }
      if (data.initial_state.config.rd_innovation_threshold) {
          setGlobalConfig(prev => ({ ...prev, rd_innovation_threshold: data.initial_state.config.rd_innovation_threshold }));
      }
      
      setCompanyNames(config.companies.map(c => c.name));
      setTotalTurns(config.total_turns);
      
      // 시뮬레이션 생성 성공 시 탭 이동
      setActiveTab('battle');
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

  const handleExecuteTurn = useCallback(async () => {
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

      const data = await api.executeTurn(simulationId, decisionsToExecute);
      
      setHistory(prevHistory => [...prevHistory, data.turn_results]);
      setCurrentTurn(data.turn);

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

      setIsWaitingForChoice(false); 
      setChoiceOptions(null); 
      setSelectedDecisions({});
      setIsLoading(false); 

    } catch (err) {
      console.error("Turn Execution Error:", err);
      setError(`턴 실행 실패: ` + err.message);
      setIsAutoRun(false); 
      setIsLooping(false); 
      setIsLoading(false);
    }

  }, [simulationId, isLoading, isWaitingForChoice, companyNames, selectedDecisions]);

  // 자동 주행(Looping) 드라이버
  useEffect(() => {
    if (isLooping && !isLoading && !isWaitingForChoice && simulationId && currentTurn < totalTurns) {
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
      try { await handleGetChoices(); } catch (err) { console.error("1턴 로딩 실패:", err); }
      setIsLoading(false);
  };

  const handleRunAllTurns = useCallback(async () => {
    if (isLoading || currentTurn >= totalTurns || isLooping) return;
    setIsLooping(true); 
    setIsAutoRun(true); 
    setIsLoading(true);
    try {
      await handleGetChoices();
      setIsLoading(false);
    } catch (err) {
      setError("첫 턴 로딩 오류: " + err.message);
      setIsLooping(false); 
      setIsAutoRun(false);
      setIsLoading(false);
    }
  }, [isLoading, currentTurn, totalTurns, isLooping, handleGetChoices]);

  const handleSelectChoice = (agentName, choice) => {
    setSelectedDecisions(prev => ({ ...prev, [agentName]: choice }));
  };

  // 자동 선택 (Auto Pick) 로직
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

  // 자동 실행 (Auto Execute) 로직
  useEffect(() => {
    if (isLoading || !isWaitingForChoice || Object.keys(selectedDecisions).length < companyNames.length) return;
    if (isLooping || isAutoRun) {
        handleExecuteTurn();
    }
  }, [isLooping, isAutoRun, isWaitingForChoice, selectedDecisions, isLoading, companyNames, handleExecuteTurn]);
  
  const handleDownloadCSV = () => {
    if (history.length === 0) return alert("다운로드할 데이터가 없습니다.");
    try {
      const headers = Object.keys(history[0]);
      const headerString = headers.join(',');
      const rows = history.map(turnData => headers.map(header => turnData[header]).join(','));
      const csvString = '\uFEFF' + [headerString, ...rows].join('\n');
      const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.setAttribute('href', url);
      link.setAttribute('download', 'simulation_history.csv');
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      setError("CSV 다운로드 중 오류: " + err.message);
    }
  };

  // -------------------------------------------------------------------------------
  // [Track C] 실험실 (Laboratory)
  // -------------------------------------------------------------------------------
  // --- [Track C] 1. 실험실 시작 (초기화) ---
  const canGoToBattle = simulationId && activeTab !== 'lab';
  const canGoToLab = (actualHistory.length > 0) || (simulationId && activeTab === 'lab');

  const handleStartTrackC = () => {
    if (!uploadedBenchmarkData) {
        alert("벤치마크(시나리오) 파일을 먼저 업로드해주세요.");
        return;
    }
    
    // JSON 데이터 로드 및 초기화
    const data = uploadedBenchmarkData.turns_data;
    setActualHistory(data); 
    
    setSimulationId(null); // 아직 시뮬레이션 연결 안 함
    setHistory([]);        // 화면 그래프 초기화
    setCurrentTurn(0);
    setTotalTurns(data.length);
    setLabMode('playback'); // '재생 모드'로 시작
    setInterventionLog(null);
    setAiReasoning([]);
    
    if (data.length > 0) {
        setCompanyNames(Object.keys(data[0].companies));
        setTargetCompanyForEdit("");
    }

    setActiveTab('lab');
    alert("🧪 실험실 모드 시작.\n\n[1턴 진행] 버튼을 눌러 과거 역사를 재생하다가,\n원하는 시점에서 [개입(Intervention)]하여 역사를 바꾸십시오.");
  };

  // --- [Track C] 2. 다음 턴 진행 (재생 vs 시뮬레이션 분기) ---
  const handleNextTurnLab = async () => {
      if (labMode === 'playback') {
          if (currentTurn >= actualHistory.length) {
              alert("준비된 시나리오(JSON)가 끝났습니다.");
              return;
          }

          const turnData = actualHistory[currentTurn];
          const formattedTurnResult = { turn: turnData.turn };
          
          Object.keys(turnData.companies).forEach(name => {
              const comp = turnData.companies[name];
              const outputs = comp.outputs || {}; 
              const inputs = comp.inputs || {};   

              formattedTurnResult[`${name}_market_share`] = outputs.actual_market_share;
              // 누적 이익 매핑 (키 이름 다양성 대응)
              formattedTurnResult[`${name}_accumulated_profit`] = outputs.actual_accumulated_profit ?? outputs.accumulated_profit ?? 0;
              
              formattedTurnResult[`${name}_product_quality`] = inputs.initial_quality || 50; 
              formattedTurnResult[`${name}_price`] = inputs.price;
              formattedTurnResult[`${name}_brand_awareness`] = inputs.initial_brand || 50;
              
              // [핵심 수정] 원가(unit_cost)가 JSON에 없으면 가격의 80%로 추정해서라도 채워넣음
              // 이렇게 해야 개입 시 이 값을 물려받을 수 있음
              let estimatedCost = 0;
              if (inputs.unit_cost) estimatedCost = inputs.unit_cost;
              else if (inputs.price) estimatedCost = inputs.price * 0.8; // 마진 20% 가정
              
              formattedTurnResult[`${name}_unit_cost`] = estimatedCost;

              // 나머지 0 처리
              formattedTurnResult[`${name}_marketing_brand_spend`] = 0;
              formattedTurnResult[`${name}_marketing_promo_spend`] = 0;
              formattedTurnResult[`${name}_rd_innovation_spend`] = 0;
              formattedTurnResult[`${name}_rd_efficiency_spend`] = 0;
          });

          setHistory(prev => [...prev, formattedTurnResult]);
          setCurrentTurn(prev => prev + 1);

      } else {
          if (isWaitingForChoice) return;
          await handleGetOneTurnChoices(); 
      }
  };

  // --- [Track C] 3. 개입 적용 및 시뮬레이션 생성 (Hot Start) ---
  const handleApplyIntervention = async () => {
      if (!targetCompanyForEdit || !currentPersona) return;
      if (currentTurn === 0) {
          alert("최소 1턴 이상 진행 후에 개입할 수 있습니다.");
          return;
      }

      setIsLoading(true);
      try {
          // 현재 시점(currentTurn)의 상태 스냅샷
          const lastState = history[history.length - 1]; 
          
          const hotStartCompanies = companyNames.map(name => {
             // [안전 장치] 데이터 가져오기 및 타입 변환
             // 1. 원가는 반드시 정수(int)여야 함 -> Math.round 사용
             const rawCost = lastState[`${name}_unit_cost`];
             const safeCost = (rawCost !== undefined && rawCost !== null) ? rawCost : 100;
             const finalCost = Math.round(safeCost);

             // 2. 나머지 실수형(float) 데이터 처리
             const rawShare = lastState[`${name}_market_share`];
             const finalShare = (rawShare !== undefined) ? rawShare : 0.1;

             const rawQuality = lastState[`${name}_product_quality`];
             const finalQuality = (rawQuality !== undefined) ? rawQuality : 50.0;

             const rawBrand = lastState[`${name}_brand_awareness`];
             const finalBrand = (rawBrand !== undefined) ? rawBrand : 50.0;

             const rawProfit = lastState[`${name}_accumulated_profit`];
             const finalProfit = (rawProfit !== undefined) ? rawProfit : 0;

             return {
                 name: name,
                 persona: (name === targetCompanyForEdit) ? currentPersona : "Standard AI Persona",
                 
                 initial_unit_cost: finalCost, // [중요] 정수형 전달
                 initial_market_share: finalShare,
                 initial_product_quality: finalQuality,
                 initial_brand_awareness: finalBrand,
                 initial_accumulated_profit: finalProfit
             };
          });

          // [안전 장치] globalConfig에서 physics가 누락되지 않도록 보장
          const safePhysics = globalConfig.physics || {
              weight_quality: 0.4, weight_brand: 0.4, weight_price: 0.2,
              price_sensitivity: 50.0, marketing_efficiency: 1.0, others_overall_competitiveness: 1.0
          };

          const hotStartConfig = {
              ...globalConfig,
              companies: hotStartCompanies,
              start_turn: currentTurn,
              total_turns: totalTurns + 10,
              physics: safePhysics // 물리 엔진 설정 명시적 전달
          };

          console.log("Sending Config:", hotStartConfig); // 디버깅용 로그

          const data = await api.createSimulation(hotStartConfig);
          setSimulationId(data.simulation_id);

          setLabMode('simulation');
          setInterventionLog({
              turn: currentTurn,
              company: targetCompanyForEdit,
              old: originalPersona,
              new: currentPersona
          });
          
          alert(`⚡ 역사가 바뀌었습니다!\n지금부터(${currentTurn}턴) AI가 새로운 페르소나로 시뮬레이션을 이어갑니다.`);
          
      } catch (err) {
          console.error(err);
          setError("개입 적용 실패(422 등): " + err.message);
      }
      setIsLoading(false);
  };

  // [UI Helper] 회사 선택 시 기존 페르소나 표시용
  useEffect(() => {
    if (activeTab === 'lab' && targetCompanyForEdit && actualHistory.length > 0) {
        
        let foundPersona = "기본 이윤 추구형 AI (데이터 없음)";
        let sourceInfo = "Unknown"; 

        // 1. 역추적 (Backtracking) 로직
        // 현재 턴(currentTurn)이 아직 진행 전이라면 0턴부터 찾음
        // 시뮬레이션 중이라면 마지막 턴부터 찾음
        const searchIndex = Math.min(currentTurn, actualHistory.length - 1);

        for (let i = searchIndex; i >= 0; i--) {
            const turnData = actualHistory[i];
            if (turnData && turnData.companies && turnData.companies[targetCompanyForEdit]) {
                const p = turnData.companies[targetCompanyForEdit].persona;
                if (p && p.length > 0) {
                    foundPersona = p;
                    sourceInfo = `Turn ${i} (History)`;
                    break; // 찾았으면 중단
                }
            }
        }

        // 2. 개입 기록 확인 (덮어쓰기)
        if (interventionLog && interventionLog.company === targetCompanyForEdit) {
            const logTurn = interventionLog.turn;
            // 개입한 턴이 역사 데이터보다 최신이거나 같으면 적용
            // (단순화: 개입 기록이 있으면 무조건 우선순위 높게 표시)
            foundPersona = interventionLog.new;
            sourceInfo = `Turn ${logTurn} (Intervention)`;
        }

        setOriginalPersona(foundPersona);
        setPersonaSourceTurn(sourceInfo);
        
        // 편집창 초기화 (사용자가 입력 중이 아닐 때만)
        if (!currentPersona) setCurrentPersona(foundPersona);
    }
  }, [targetCompanyForEdit, activeTab, actualHistory, currentTurn, interventionLog, currentPersona]);
    
  // -------------------------------------------------------------------------------
  // [UI Component] 결정 패널 (Decision Panel) - 재사용 가능
  // -------------------------------------------------------------------------------
  const renderDecisionPanel = () => {
    if (!isWaitingForChoice || !choiceOptions) return null;

    return (
        <div style={{ marginTop: '20px', padding: '20px', border: '1px solid #007bff', borderRadius: '8px', backgroundColor: '#eaf4ff' }}>
          <h3 style={{ textAlign: 'center', color: '#0056b3', marginTop: 0 }}>🧠 AI 전략 수립 완료: {currentTurn + 1}턴 </h3>
          
          <div style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.min(companyNames.length, 3)}, 1fr)`, gap: '15px' }}>
              {companyNames.map(name => (
              <div key={name} style={{ border: '1px solid #ccc', padding: '15px', backgroundColor: '#fff', borderRadius: '8px', boxShadow: '0 2px 5px rgba(0,0,0,0.05)' }}>
                <h4 style={{ color: COMPANY_COLORS[name] || '#000', borderBottom: '2px solid #eee', paddingBottom: '10px', marginTop: 0 }}>{name}의 전략</h4>
                {choiceOptions[name] && choiceOptions[name].map((choice, index) => {
                  const isSelected = selectedDecisions[name] === choice;
                  return (
                    <button 
                      key={index}
                      onClick={() => handleSelectChoice(name, choice)}
                      style={{ 
                          display: 'block', width: '100%', marginBottom: '10px', 
                          backgroundColor: isSelected ? '#007bff' : 'white', 
                          color: isSelected ? 'white' : '#333', 
                          border: isSelected ? '1px solid #0056b3' : '1px solid #ddd', 
                          padding: '12px', textAlign: 'left', cursor: 'pointer', borderRadius: '6px', 
                          boxShadow: isSelected ? '0 2px 5px rgba(0,123,255,0.3)' : 'none', 
                          transition: 'all 0.2s' 
                      }}
                    >
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
    );
  };

  // =================================================================================
  // 3. 메인 렌더링 (JSX)
  // =================================================================================
  return (
    <div style={{ fontFamily: 'sans-serif', padding: '20px', maxWidth: '1600px', margin: 'auto' }}>
      
      {/* --- 1. Header (Home Button) --- */}
      <h1 
        onClick={handleGoHome} 
        style={{ textAlign: 'center', color: '#333', cursor: 'pointer', userSelect: 'none', borderBottom: '1px solid #eee', paddingBottom: '15px' }}
        title="홈으로 돌아가기 (Reset)"
      >
        🤖 AI 전략 워게임 (Integrated Platform)
      </h1>

      {/* --- 2. Tab Navigation --- */}
      <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '20px', gap: '10px' }}>
          <button 
            onClick={() => setActiveTab('setup')} 
            style={{ 
                padding: '12px 24px', fontSize: '1.1em', fontWeight: 'bold', border: 'none', borderRadius: '8px', cursor: 'pointer', 
                backgroundColor: activeTab === 'setup' ? '#ffc107' : '#f0f0f0', 
                color: activeTab === 'setup' ? '#000' : '#888',
                boxShadow: activeTab === 'setup' ? '0 2px 5px rgba(0,0,0,0.2)' : 'none'
            }}
          >
            🛠️ 설정 및 튜닝
          </button>
          <button 
            onClick={() => setActiveTab('battle')} 
            disabled={!canGoToBattle} // ▼▼▼ [변수 연결] ▼▼▼
            style={{ 
              padding: '12px 24px', fontSize: '1.1em', fontWeight: 'bold', border: 'none', borderRadius: '8px', cursor: 'pointer', 
              backgroundColor: activeTab === 'battle' ? '#28a745' : '#f0f0f0', 
              color: activeTab === 'battle' ? '#fff' : '#888', 
              opacity: (!canGoToBattle) ? 0.5 : 1 // ▼▼▼ [변수 연결] ▼▼▼
            }}
          >
            ⚔️ 일반 시뮬레이션
          </button>
          <button 
            onClick={() => setActiveTab('lab')} 
            disabled={!canGoToLab} // ▼▼▼ [변수 연결] ▼▼▼
            style={{ padding: '12px 24px', fontSize: '1.1em', fontWeight: 'bold', border: 'none', borderRadius: '8px', cursor: 'pointer', 
            backgroundColor: activeTab === 'lab' ? '#6f42c1' : '#f0f0f0', 
            color: activeTab === 'lab' ? '#fff' : '#888', 
            opacity: (!canGoToLab) ? 0.5 : 1 // ▼▼▼ [변수 연결] ▼▼▼
          }}
        >
          🧪 실험실 (Track C)
        </button>
      </div>

      {/* --- TAB 1: SETUP (Config & Track B) --- */}
      {activeTab === 'setup' && (
        <>
            {/* Track B: 벤치마크 & 튜닝 섹션 */}
            <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: '#fff3cd', border: '1px solid #ffeeba', borderRadius: '5px' }}>
                <h3 style={{ marginTop: 0, color: '#856404' }}>🛠️ Track B: 관리자 튜닝 모드 (Benchmark & Auto-Tune)</h3>
                
                {/* ▼▼▼ [신규 추가] AI 시나리오 생성기 UI ▼▼▼ */}
                <div style={{ marginBottom: '15px', paddingBottom: '15px', borderBottom: '1px dashed #d39e00' }}>
                    <label style={{ fontWeight: 'bold', display: 'block', marginBottom: '5px', color: '#6f42c1' }}>✨ AI 시나리오 메이커 (Auto-Generator)</label>
                    <div style={{ display: 'flex', gap: '10px' }}>
                        <input 
                            type="text" 
                            placeholder="주제를 입력하세요 (예: 2007년 아이폰 출시와 노키아의 몰락)" 
                            value={genTopic}
                            onChange={(e) => setGenTopic(e.target.value)}
                            disabled={isGenerating}
                            style={{ flex: 1, padding: '10px', borderRadius: '4px', border: '1px solid #ccc' }}
                        />
                        <button 
                            onClick={handleGenerateScenario} 
                            disabled={isGenerating}
                            style={{ 
                                padding: '10px 20px', backgroundColor: '#6f42c1', color: 'white', 
                                border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold', minWidth: '120px'
                            }}
                        >
                            {isGenerating ? "생성 중..." : "🔮 생성하기"}
                        </button>

                        {/* ▼▼▼ [신규 추가] 다운로드 버튼 ▼▼▼ */}
                        {uploadedBenchmarkData && (
                            <button 
                                onClick={handleDownloadScenario}
                                title="현재 로드된 시나리오를 JSON 파일로 저장합니다"
                                style={{ 
                                    padding: '10px 20px', backgroundColor: '#28a745', color: 'white', 
                                    border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' 
                                }}
                            >
                                📥 JSON 저장
                            </button>
                        )}
                    </div>
                    <p style={{ fontSize: '0.8em', color: '#666', marginTop: '5px', margin: 0 }}>
                        * 역사적 사실을 기반으로 [정체성+상황+전술]이 포함된 정교한 JSON 시나리오를 자동 생성합니다.
                    </p>
                </div>

                <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                    <label 
                        htmlFor="benchmark-upload" 
                        style={{ padding: '8px 12px', backgroundColor: '#fff', border: '1px solid #ccc', borderRadius: '4px', cursor: 'pointer', fontSize: '0.9em', display: 'flex', alignItems: 'center', gap: '5px' }}
                    >
                        📂 시나리오(.json) 업로드
                    </label>
                    <input id="benchmark-upload" type="file" accept=".json" onChange={handleBenchmarkFileUpload} disabled={isLoading} style={{ display: 'none' }} />
                    
                    <span style={{ fontSize: '0.9em', color: benchmarkFileName ? '#28a745' : '#666', fontWeight: benchmarkFileName ? 'bold' : 'normal' }}>
                        {benchmarkFileName ? `✅ ${benchmarkFileName}` : '(선택된 파일 없음)'}
                    </span>
                    
                    <button 
                        onClick={handleAutoTune} 
                        disabled={isLoading || !uploadedBenchmarkData} 
                        style={{ marginLeft: 'auto', padding: '8px 16px', backgroundColor: '#ffc107', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}
                    >
                        ⚡ 자동 튜닝 시작
                    </button>
                </div>
                
                {isLoading && <span style={{ marginLeft: '10px', fontWeight: 'bold', color: 'blue' }}>작업 진행 중...</span>}
                {error && <div style={{ color: 'red', marginTop: '10px' }}>Error: {error}</div>}
                
                {tunedParams && (
                <div style={{ marginTop: '15px', padding: '15px', backgroundColor: 'white', borderRadius: '5px', border: '1px solid #ffeeba' }}>
                    <h4 style={{ marginTop: 0, color: '#856404' }}>🎯 튜닝 결과</h4>
                    <div style={{ marginBottom: '10px' }}>
                        <strong>최소 오차(MAE): </strong>
                        <span style={{ color: 'green', fontSize: '1.2em', fontWeight: 'bold' }}>{(tunedParams.lowest_mae * 100).toFixed(2)}%</span>
                    </div>
                    
                    <div style={{ marginBottom: '15px', padding: '10px', backgroundColor: '#f8f9fa', borderRadius: '4px', fontSize: '0.9em', color: '#333', border: '1px solid #ddd' }}>
                        <strong>🔍 발견된 최적 파라미터:</strong>
                        <pre style={{ whiteSpace: 'pre-wrap', marginTop: '5px', fontFamily: 'monospace' }}>
                            {JSON.stringify(tunedParams.best_params, null, 2)}
                        </pre>
                    </div>

                    <div style={{ display: 'flex', gap: '10px' }}>
                        <button onClick={applyTunedParams} style={{ padding: '8px 15px', backgroundColor: '#28a745', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>✅ 설정 적용 (재테스트)</button>
                        <button onClick={handleSavePreset} style={{ padding: '8px 15px', backgroundColor: '#17a2b8', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>💾 프리셋 저장</button>
                    </div>
                </div>
                )}
                
                {/* Track C 진입 버튼 */}
                <div style={{ marginTop: '10px', borderTop: '1px dashed #d39e00', paddingTop: '10px' }}>
                    <h4 style={{ margin: '0 0 5px 0', color: '#856404' }}>🧪 Track C: The Laboratory (What-if 분석)</h4>
                    <p style={{ fontSize: '0.9em', margin: '0 0 10px 0', color: '#666' }}>업로드된 벤치마크 데이터를 '실제 역사'로 설정하고, 페르소나를 수정하며 시뮬레이션 결과와 비교합니다.</p>
                    <button 
                        onClick={handleStartTrackC} 
                        disabled={isLoading || !uploadedBenchmarkData} 
                        style={{ padding: '10px 20px', backgroundColor: '#6f42c1', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer', fontWeight: 'bold', opacity: (!uploadedBenchmarkData) ? 0.6 : 1 }}
                    >
                        🧪 실험실 입장
                    </button>
                </div>
            </div>

            {/* 메인 설정 폼 */}
            <div style={{ padding: '20px', border: '1px solid #ccc', borderRadius: '8px', marginBottom: '20px', backgroundColor: '#f9f9f9' }}>
                <div style={{ marginBottom: '15px', padding: '10px', backgroundColor: '#e9ecef', borderRadius: '5px' }}>
                    <label style={{ fontWeight: 'bold', marginRight: '10px' }}>📂 시장 환경(Preset) 선택:</label>
                    <select value={selectedPreset} onChange={handlePresetChange} style={{ padding: '5px', fontSize: '1em', minWidth: '300px' }}>
                        <option value="">(기본값 - 사용자 설정)</option>
                        {presets.map(p => (<option key={p.filename} value={p.filename}>{p.name} - {p.description}</option>))}
                    </select>
                </div>

                <h3>🌍 1. 글로벌 시장 설정 (거시 경제)</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '15px', marginBottom: '15px' }}>
                    <div>
                        <label style={{fontWeight:'bold', color:'#007bff'}}>총 턴 수</label>
                        <input type="number" name="total_turns" value={globalConfig.total_turns} onChange={handleGlobalConfigChange} style={{width:'100%', padding:'8px', border:'2px solid #007bff', borderRadius:'5px'}} />
                    </div>
                    <div>
                        <label style={{fontWeight:'bold', color:'#28a745'}}>시장 규모</label>
                        <input type="number" name="market_size" value={globalConfig.market_size} onChange={handleGlobalConfigChange} style={{width:'100%', padding:'8px', border:'2px solid #28a745', borderRadius:'5px'}} />
                    </div>
                    <div>
                        <label style={{fontWeight:'bold', color:'#dc3545'}}>초기 자본금</label>
                        <input type="number" name="initial_capital" value={globalConfig.initial_capital} onChange={handleGlobalConfigChange} style={{width:'100%', padding:'8px', border:'2px solid #dc3545', borderRadius:'5px'}} />
                    </div>
                </div>

                <details style={{ marginBottom: '20px', backgroundColor: '#f1f3f5', padding: '10px', borderRadius: '5px', border: '1px solid #dee2e6' }}>
                    <summary style={{ cursor: 'pointer', fontWeight: 'bold', color: '#495057' }}>🔽 고급 시장 역학 설정 (마케팅, R&D, 감가상각)</summary>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '15px', marginTop: '15px' }}>
                        {Object.entries(globalConfig).map(([key, value]) => {
                            if (['total_turns', 'market_size', 'initial_capital', 'physics', 'rd_innovation_impact', 'rd_innovation_threshold'].includes(key)) return null;
                            return (
                                <div key={key} style={{ backgroundColor: 'white', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}>
                                    <label style={{ fontSize: '0.9em', fontWeight: 'bold' }}>{key}</label>
                                    <input type="number" step={value < 1 ? "0.001" : "1000"} name={key} value={value} onChange={handleGlobalConfigChange} style={{ width: '100%', padding: '5px' }} />
                                </div>
                            );
                        })}
                    </div>
                </details>

                <div style={{ marginTop: '20px', borderTop: '1px dashed #ccc', paddingTop: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
                        <h4 style={{ margin: 0 }}>⚙️ Engine Tuning (Physics)</h4>
                        <button onClick={() => setShowGuide(!showGuide)} style={{ padding: '6px 12px', fontSize: '0.85em', cursor: 'pointer', backgroundColor: showGuide ? '#5a6268' : '#17a2b8', color: 'white', border: 'none', borderRadius: '20px' }}>
                            {showGuide ? '▲ 가이드 접기' : 'ℹ️ 설정 도우미'}
                        </button>
                    </div>
                    
                    {showGuide && <PhysicsGuidePanel />}
                    
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '15px', backgroundColor: '#eef' , padding: '15px', borderRadius: '5px', border: '1px solid #dde'}}>
                        {TUNING_UI_ORDER.map((key) => {
                            const isRD = key.startsWith('rd_');
                            const value = isRD ? globalConfig[key] : globalConfig.physics[key];
                            const onChange = isRD ? handleGlobalConfigChange : handlePhysicsConfigChange;
                            return (
                                <div key={key}>
                                    <label style={{ fontSize: '0.85em', display: 'block', fontWeight: 'bold' }}>{FIELD_LABELS[key] || key}</label>
                                    <input type="number" name={key} value={value} onChange={onChange} style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px' }} />
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
                        <div><label>name</label><input type="text" name="name" value={company.name} onChange={e => handleCompanyConfigChange(index, e)} style={{ width: '100%' }} /></div>
                        <div><label>initial_unit_cost</label><input type="number" name="initial_unit_cost" value={company.initial_unit_cost} onChange={e => handleCompanyConfigChange(index, e)} style={{ width: '100%' }} /></div>
                        <div><label>initial_market_share</label><input type="number" step="0.01" name="initial_market_share" value={company.initial_market_share} onChange={e => handleCompanyConfigChange(index, e)} style={{ width: '100%' }} /></div>
                        <div><label>initial_quality</label><input type="number" name="initial_product_quality" value={company.initial_product_quality} onChange={e => handleCompanyConfigChange(index, e)} style={{ width: '100%' }} /></div>
                        <div><label>initial_brand</label><input type="number" name="initial_brand_awareness" value={company.initial_brand_awareness} onChange={e => handleCompanyConfigChange(index, e)} style={{ width: '100%' }} /></div>
                    </div>
                    <div><label style={{ marginTop: '10px', display: 'block' }}>persona</label><textarea name="persona" value={company.persona} onChange={e => handleCompanyConfigChange(index, e)} style={{ width: '100%', height: '60px', padding: '5px' }} /></div>
                    </div>
                ))}
                
                <button onClick={handleCreateSimulation} disabled={isLoading} style={{ marginTop: '20px', padding: '15px', width: '100%', fontSize: '1.2em', backgroundColor: '#28a745', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer', fontWeight: 'bold' }}>
                    🚀 시뮬레이션 시작
                </button>
            </div>

            {/* 벤치마크 결과 그래프 (Setup 화면 하단) */}
            {benchmarkResult && (
                <div style={{ marginTop: '20px', padding: '20px', border: '2px solid #856404', borderRadius: '8px', backgroundColor: '#fff3cd' }}>
                    <h2 style={{ color: '#856404' }}>📊 벤치마크 결과: {benchmarkResult.scenario}</h2>
                    <div style={{ fontSize: '1.2em', marginBottom: '20px' }}>
                        <strong>평균 오차(MAE): </strong>
                        <span style={{ color: benchmarkResult.average_error_mae > 0.1 ? 'red' : 'green' }}>{(benchmarkResult.average_error_mae * 100).toFixed(2)}%p</span>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '20px', minHeight: '400px' }}>
                        <SimulationChart data={benchmarkResult.history} lines={getChartLines(companyNames, true).error} title="점유율 오차" format={(v) => `${(v * 100).toFixed(1)}%p`} />
                        <SimulationChart data={benchmarkResult.history} lines={getChartLines(companyNames, true).market_share} title="시뮬레이션 점유율" format={(v) => `${(v * 100).toFixed(1)}%`} />
                        <SimulationChart data={benchmarkResult.history} lines={getChartLines(companyNames, true).product_quality} title="품질 변화" />
                        <SimulationChart data={benchmarkResult.history} lines={getChartLines(companyNames, true).unit_cost} title="원가 변화" />
                    </div>
                </div>
            )}
        </>
      )}

      {/* --- TAB 2: BATTLE MODE (Normal Sim) --- */}
      {activeTab === 'battle' && simulationId && !benchmarkResult && (
        <>
            {/* 게임 컨트롤 패널 */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', padding: '15px', border: '1px solid #ccc', borderRadius: '8px', alignItems: 'center', backgroundColor: 'white', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
                <button onClick={handleGetOneTurnChoices} disabled={isLoading || (isAutoRun && isLooping)} style={{ backgroundColor: '#007bff', color: 'white', border: 'none', padding: '10px 15px', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>▶ 다음 1턴 결정 보기</button>
                <button onClick={handleRunAllTurns} disabled={isLoading || (isAutoRun && isLooping)} style={{ backgroundColor: '#28a745', color: 'white', border: 'none', padding: '10px 15px', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>⏩ 남은 턴 모두 실행</button>
                <div style={{ marginLeft: '15px', display: 'flex', alignItems: 'center', backgroundColor: '#f1f1f1', padding: '8px 12px', borderRadius: '20px' }}>
                    <input type="checkbox" id="autoRunCheck" checked={isAutoRun} onChange={(e) => { const checked = e.target.checked; setIsAutoRun(checked); if (!checked) { setIsLooping(false); } }} disabled={isLoading} style={{ marginRight: '8px', width: '18px', height: '18px', cursor: 'pointer' }} />
                    <label htmlFor="autoRunCheck" style={{ cursor: 'pointer', userSelect: 'none', fontWeight: 'bold', color: '#333' }}>{isLooping ? (isAutoRun ? '■ 자동 반복 중...' : '■ 수동 반복 중...') : '최고 확률 자동 선택'}</label>
                </div>
                <button onClick={handleDownloadCSV} disabled={history.length === 0 || isLoading} style={{ backgroundColor: (history.length === 0 || isLoading) ? '#ccc' : '#17a2b8', color: 'white', marginLeft: 'auto', border: 'none', padding: '10px 15px', borderRadius: '4px', cursor: 'pointer' }}>📥 결과 다운로드 (CSV)</button>
            </div>

            {/* 결정 패널 호출 */}
            {renderDecisionPanel()}

            {/* AI 생각 로그 */}
            {aiReasoning.length > 0 && (
                <div style={{ marginTop: '20px', padding: '10px', border: '1px solid #eee', borderRadius: '8px', height: '150px', overflowY: 'scroll', backgroundColor: '#282c34', color: '#e6e6e6', fontSize: '0.9em' }}>
                <strong>[AI 결정 로그]</strong>
                {aiReasoning.slice().reverse().map((entry, idx) => (
                    <div key={idx} style={{ borderTop: '1px dashed #555', paddingTop: '5px', marginTop: '5px' }}><strong>T{entry.turn}:</strong> {entry.reasons.join(" | ")}</div>
                ))}
                </div>
            )}

            {/* 시뮬레이션 결과 차트들 (11개) */}
            {history.length > 0 && (
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
        </>
      )}

      {activeTab === 'lab' && (
        <div style={{ marginTop: '20px', padding: '20px', border: '2px solid #6f42c1', borderRadius: '8px', backgroundColor: '#f3e5f5' }}>
            <h2 style={{ color: '#4a148c', textAlign: 'center' }}>🧪 The Laboratory: Time Machine</h2>
            
            <div style={{ display: 'flex', gap: '15px', marginBottom: '20px', padding: '15px', backgroundColor: 'white', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
                {/* 1. 진행 컨트롤 (Playback & Simulation 통합 버튼) */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', minWidth: '250px', borderRight: '1px solid #eee', paddingRight: '15px' }}>
                    <div style={{ fontWeight: 'bold', color: '#333', marginBottom: '5px' }}>
                        현재 모드: {labMode === 'playback' ? <span style={{color:'blue'}}>📼 과거 재생 (Playback)</span> : <span style={{color:'red'}}>🔥 라이브 시뮬레이션</span>}
                    </div>
                    
                    <button 
                        onClick={handleNextTurnLab} 
                        disabled={isLoading || isWaitingForChoice || (labMode === 'playback' && currentTurn >= actualHistory.length)} 
                        style={{ padding: '12px', backgroundColor: labMode === 'playback' ? '#007bff' : '#dc3545', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold', fontSize: '1.1em' }}
                    >
                        {labMode === 'playback' ? `▶ ${currentTurn+1}턴 재생 (Load JSON)` : `🎲 ${currentTurn+1}턴 실행 (Run AI)`}
                    </button>
                    
                    <div style={{fontSize: '0.9em', color: '#666', marginTop: '5px'}}>
                        진행 상황: <strong>{currentTurn} / {totalTurns} Turn</strong>
                    </div>
                    
                    {interventionLog && (
                        <div style={{ marginTop: '10px', padding: '8px', backgroundColor: '#fff3cd', border: '1px solid #ffeeba', borderRadius: '4px', fontSize: '0.85em' }}>
                            ⚠️ <strong>{interventionLog.turn}턴</strong>에 개입 발생!<br/>
                            ({interventionLog.company}의 전략 수정됨)
                        </div>
                    )}
                </div>
                
                {/* 2. 페르소나 뷰어 및 개입 패널 */}
                <div style={{ flex: 1, paddingLeft: '15px' }}>
                    <h4 style={{ margin: '0 0 10px 0', color: '#d63384' }}>⚡ 전략 개입 (Persona Intervention)</h4>
                    
                    <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}>
                        <select 
                            onChange={(e) => setTargetCompanyForEdit(e.target.value)} 
                            value={targetCompanyForEdit} 
                            disabled={labMode === 'simulation'} // 시뮬레이션 중에는 수정 불가 (단순화)
                            style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ccc', minWidth: '200px' }}
                        >
                            <option value="">-- 개입할 회사 선택 --</option>
                            {companyNames.map(name => (<option key={name} value={name}>{name}</option>))}
                        </select>
                        
                        {targetCompanyForEdit && labMode === 'playback' && (
                            <button 
                                onClick={handleApplyIntervention} 
                                disabled={isLoading || !currentPersona}
                                style={{ padding: '8px 20px', backgroundColor: '#d63384', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}
                            >
                                ⚡ 이 시점에서 개입하기 (Change History)
                            </button>
                        )}
                    </div>

                    {targetCompanyForEdit && (
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                            
                            {/* [좌측] 현재 적용 중인 페르소나 (Read-Only) */}
                            <div style={{ backgroundColor: '#f8f9fa', padding: '10px', borderRadius: '5px', border: '1px solid #ddd' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', alignItems: 'center' }}>
                                    <div style={{ fontSize: '0.85em', color: '#495057', fontWeight: 'bold' }}>📄 현재 적용 중인 전략 (Current Status)</div>
                                    
                                    {/* 출처 배지 (Source Badge) */}
                                    <div style={{ 
                                        fontSize: '0.75em', 
                                        padding: '3px 8px', 
                                        borderRadius: '12px', 
                                        fontWeight: 'bold',
                                        // 현재 턴과 출처 턴의 차이가 3턴 이상이면 '오래됨(노란색)' 경고 표시
                                        backgroundColor: (personaSourceTurn && typeof personaSourceTurn === 'string' && personaSourceTurn.includes('Turn') && (currentTurn - parseInt(personaSourceTurn.replace(/[^0-9]/g,'')||0)) > 2) ? '#ffc107' : '#e9ecef',
                                        color: '#333',
                                        border: '1px solid #ccc'
                                    }}>
                                        출처: {personaSourceTurn}
                                    </div>
                                </div>
                                <div style={{ fontSize: '0.9em', color: '#333', fontStyle: 'italic', whiteSpace: 'pre-wrap', lineHeight: '1.5', maxHeight: '150px', overflowY: 'auto' }}>
                                    {originalPersona}
                                </div>
                            </div>
                            
                            {/* [우측] 페르소나 수정 (Editor) */}
                            <div style={{ backgroundColor: '#fff0f6', padding: '10px', borderRadius: '5px', border: '1px solid #fcc2d7' }}>
                                <div style={{ fontSize: '0.85em', color: '#d63384', fontWeight: 'bold', marginBottom: '8px' }}>✏️ 전략 수정 (Modify Strategy)</div>
                                <div style={{ fontSize: '0.8em', color: '#666', marginBottom: '5px' }}>
                                    💡 Tip: 기존 정체성을 지우지 말고, 그 뒤에 <strong>"이번 턴의 구체적 전술"</strong>을 덧붙이세요.
                                </div>
                                <textarea 
                                    value={currentPersona} 
                                    onChange={(e) => setCurrentPersona(e.target.value)}
                                    disabled={labMode === 'simulation'} // 시뮬레이션 중에는 수정 불가
                                    placeholder="기존 전략 뒤에 새로운 지시사항을 추가하세요..."
                                    style={{ width: '100%', height: '100px', padding: '10px', borderRadius: '4px', border: '1px solid #ffdeeb', fontSize: '0.9em', fontFamily: 'sans-serif' }} 
                                />
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* 시뮬레이션 모드일 때만 결정 패널 표시 */}
            {labMode === 'simulation' && renderDecisionPanel()}

            {/* 그래프 영역 (JSON 데이터 + 시뮬레이션 데이터 연속 표시) */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '30px', marginTop: '30px' }}>
                
                {/* 섹션 1: 시뮬레이션 결과 (가상 역사) - 사용자가 개입한 결과 */}
                <div style={{ padding: '20px', backgroundColor: '#fff', borderRadius: '8px', border: '2px solid #6f42c1' }}>
                    <h3 style={{ margin: '0 0 20px 0', color: '#6f42c1' }}>🧪 [Experiment] 가상 시뮬레이션 결과 ({history.length} Turns)</h3>
                    {history.length > 0 ? (
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '20px' }}>
                            <SimulationChart data={history} lines={getChartLines(companyNames).market_share} title="[Sim] 시장 점유율" format={(v) => `${(v * 100).toFixed(1)}%`} />
                            <SimulationChart data={history} lines={getChartLines(companyNames).accumulated_profit} title="[Sim] 누적 이익" />
                            <SimulationChart data={history} lines={getChartLines(companyNames).price} title="[Sim] 가격 정책" />
                            <SimulationChart data={history} lines={getChartLines(companyNames).product_quality} title="[Sim] 품질 변화" />
                        </div>
                    ) : (
                        <div style={{ textAlign: 'center', color: '#999', padding: '20px' }}>데이터 없음 (1턴 진행을 눌러주세요)</div>
                    )}
                </div>

                {/* 섹션 2: 실제 역사 (원본 데이터) - 비교군 */}
                <div style={{ padding: '20px', backgroundColor: '#f8f9fa', borderRadius: '8px', border: '2px dashed #999', opacity: 0.8 }}>
                    <h3 style={{ margin: '0 0 20px 0', color: '#666' }}>📼 [History] 실제 역사 기록 (Original Data)</h3>
                    {/* 차트 헬퍼 함수: 실제 역사 데이터 전용 라인 생성기 필요 */}
                    {actualHistory.length > 0 ? (
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '20px' }}>
                            {/* 실제 역사 데이터를 차트 포맷으로 변환하여 전달해야 함 */}
                            <SimulationChart 
                                data={actualHistory.map(t => {
                                    const row = { turn: t.turn };
                                    Object.keys(t.companies).forEach(c => {
                                        row[`${c}_market_share`] = t.companies[c].outputs.actual_market_share;
                                        row[`${c}_accumulated_profit`] = t.companies[c].outputs.actual_accumulated_profit;
                                        row[`${c}_price`] = t.companies[c].inputs.price;
                                        row[`${c}_product_quality`] = t.companies[c].inputs.initial_quality || 50;
                                    });
                                    return row;
                                })} 
                                lines={getChartLines(companyNames).market_share} 
                                title="[Actual] 시장 점유율" 
                                format={(v) => `${(v * 100).toFixed(1)}%`} 
                            />
                            <SimulationChart 
                                data={actualHistory.map(t => {
                                    const row = { turn: t.turn };
                                    Object.keys(t.companies).forEach(c => {
                                        row[`${c}_accumulated_profit`] = t.companies[c].outputs.actual_accumulated_profit;
                                    });
                                    return row;
                                })} 
                                lines={getChartLines(companyNames).accumulated_profit} 
                                title="[Actual] 누적 이익" 
                            />
                            <SimulationChart 
                                data={actualHistory.map(t => {
                                    const row = { turn: t.turn };
                                    Object.keys(t.companies).forEach(c => {
                                        row[`${c}_price`] = t.companies[c].inputs.price;
                                    });
                                    return row;
                                })} 
                                lines={getChartLines(companyNames).price} 
                                title="[Actual] 가격 정책" 
                            />
                            <SimulationChart 
                                data={actualHistory.map(t => {
                                    const row = { turn: t.turn };
                                    Object.keys(t.companies).forEach(c => {
                                        row[`${c}_product_quality`] = t.companies[c].inputs.initial_quality || 50;
                                    });
                                    return row;
                                })} 
                                lines={getChartLines(companyNames).product_quality} 
                                title="[Actual] 품질 변화" 
                            />
                        </div>
                    ) : (
                        <div style={{ textAlign: 'center', color: '#999' }}>파일을 로드해주세요.</div>
                    )}
                </div>
            </div>
        </div>
      )}
    </div>
  );
}

export default App;