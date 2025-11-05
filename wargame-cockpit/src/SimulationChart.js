// wargame-cockpit/src/SimulationChart.js

import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';

const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#00C49F'];

const SimulationChart = ({ title, data, yLabel, lines }) => {
  
  // 숫자를 천 단위 콤마(,)로 포맷팅 (예: 누적 이익, 가격, 원가)
  const formatNumber = (tick) => {
    if (tick >= 1000000) {
      return `${(tick / 1000000).toFixed(1)}M`;
    }
    if (tick >= 1000) {
      return `${(tick / 1000).toFixed(0)}K`;
    }
    return tick.toLocaleString();
  };

  // 1.0 -> 100% (점유율 포맷팅)
  const formatPercent = (tick) => {
    if (tick <= 1.0 && tick >= 0.0) {
        return `${(tick * 100).toFixed(0)}%`;
    }
    return tick.toLocaleString();
  };
  
  // 0-100점 (품질, 브랜드 포맷팅)
  const formatScore = (tick) => {
    return `${tick.toFixed(0)}점`;
  };

  // [수정] Y축 레이블(yLabel)에 따라 적절한 포맷터 함수를 동적으로 선택
  let yAxisFormatter = formatNumber;
  if (yLabel.includes("점유율")) {
    yAxisFormatter = formatPercent;
  } else if (yLabel.includes("품질") || yLabel.includes("브랜드")) {
    yAxisFormatter = formatScore;
  }

  return (
    <div style={{ border: '1px solid #ddd', padding: '15px', borderRadius: '8px', backgroundColor: '#f9f9f9' }}>
      <h4 style={{ textAlign: 'center', marginTop: 0 }}>{title}</h4>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart
          data={data}
          margin={{
            top: 5,
            right: 20,
            left: 20,
            bottom: 5,
          }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="turn" label={{ value: '턴(Turn)', position: 'insideBottom', offset: -5 }} />
          <YAxis 
            tickFormatter={yAxisFormatter} 
            label={{ value: yLabel, angle: -90, position: 'insideLeft', offset: -10 }}
            domain={yLabel.includes("점유율") ? [0, 1] : ['auto', 'auto']} // 점유율 차트 Y축을 0-100%로 고정
          />
          <Tooltip formatter={yAxisFormatter} />
          <Legend />
          {lines.map((line, index) => (
            <Line
              key={line.dataKey}
              type="monotone"
              dataKey={line.dataKey}
              name={line.name}
              stroke={line.color || COLORS[index % COLORS.length]}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 6 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default SimulationChart;