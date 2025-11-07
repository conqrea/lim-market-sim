import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

// [수정] App.js와 동일한 색상 맵 (불일치 방지)
const COMPANY_COLORS = {
  GM: '#8884d8',
  Toyota: '#82ca9d',
  Apple: '#aaaaaa',
  Samsung: '#ffc658',
  // 'Others' 또는 기본 색상 추가
  Others: '#cccccc', 
  default: '#ff7300',
};

const SimulationChart = ({ data, lines, title, format }) => {

  const yAxisFormatter = (value) => {
    // [수정] title이 undefined일 때를 대비해 'title &&' 추가
    if (title && title.includes('시장 점유율')) {
      return format ? format(value) : `${(value * 100).toFixed(0)}%`;
    }
    // 기본 숫자 포맷 (e.g., 1000000 -> 1M)
    if (value >= 1000000) return `${(value / 1000000).toFixed(0)}M`;
    if (value >= 1000) return `${(value / 1000).toFixed(0)}K`;
    if (value <= -1000000) return `${(value / 1000000).toFixed(0)}M`;
    if (value <= -1000) return `${(value / 1000).toFixed(0)}K`;
    return value;
  };

  const tooltipFormatter = (value, name) => {
    let formattedValue = value;
    let formattedName = name;

    // [수정] name이 undefined일 때를 대비해 'name &&' 추가
    if (name && name.includes('market_share')) {
      formattedValue = `${(value * 100).toFixed(1)}%`;
    } else if (typeof value === 'number') {
      formattedValue = value.toLocaleString(); // 숫자에 콤마 추가
    }
    
    // dataKey에서 회사 이름 추출 (e.g., "GM_price" -> "GM")
    // [수정] name이 undefined일 때를 대비
    if (name) {
      const nameParts = name.split('_');
      if (nameParts.length > 0) {
        formattedName = nameParts[0]; // "GM"
      }
    }

    return [formattedValue, formattedName];
  };

  return (
    <div style={{ width: '100%', height: 200, marginBottom: '20px' }}>
      <h4 style={{ textAlign: 'center' }}>{title}</h4>
      <ResponsiveContainer>
        <LineChart
          data={data}
          margin={{
            top: 5,
            right: 30,
            left: 20,
            bottom: 5,
          }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="turn" />
          <YAxis tickFormatter={yAxisFormatter} />
          <Tooltip formatter={tooltipFormatter} />
          <Legend />
          {lines && lines.map((line, index) => {
            // [수정] App.js의 COMPANY_COLORS를 참조하도록 로직 강화
            const name = line.dataKey.split('_')[0];
            const color = COMPANY_COLORS[name] || COMPANY_COLORS.default;
            
            return (
              <Line
                key={line.dataKey}
                type="monotone"
                dataKey={line.dataKey}
                stroke={line.stroke || color} // App.js에서 받은 stroke 우선
                strokeWidth={2}
                name={name} // 범례와 툴팁에 표시될 이름
                dot={false}
              />
            );
          })}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default SimulationChart;