import React from 'react';
import styled from '@emotion/styled';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  AreaChart, Area
} from 'recharts';

const ChartWrapper = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-top: 20px;
`;

const ChartBox = styled.div`
  background: #f9f9f9;
  border: 1px solid #eee;
  border-radius: 8px;
  padding: 15px;
`;

const ChartTitle = styled.h3`
  text-align: center;
  margin-top: 0;
`;

const SimulationChart = ({ data }) => {
  return (
    <ChartWrapper>
      {/* 1. 누적 이익 차트 (AreaChart) */}
      <ChartBox>
        <ChartTitle>누적 이익 (Accumulated Profit)</ChartTitle>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="turn" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Area type="monotone" dataKey="Apple_accumulated_profit"  stroke="#007bff" fill="#007bff" fillOpacity={0.3} />
            <Area type="monotone" dataKey="Samsung_accumulated_profit" stroke="#28a745" fill="#28a745" fillOpacity={0.3} />
          </AreaChart>
        </ResponsiveContainer>
      </ChartBox>

      {/* 2. 시장 점유율 차트 (LineChart) */}
      <ChartBox>
        <ChartTitle>시장 점유율 (Market Share)</ChartTitle>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="turn" />
            <YAxis domain={[0, 1]} tickFormatter={(val) => `${(val * 100).toFixed(0)}%`} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="Apple_market_share" stroke="#007bff" strokeWidth={2} />
            <Line type="monotone" dataKey="Samsung_market_share" stroke="#28a745" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </ChartBox>

      {/* 3. 가격 전략 차트 (LineChart) */}
      <ChartBox>
        <ChartTitle>가격 (Price)</ChartTitle>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="turn" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="Apple_price" stroke="#007bff" strokeWidth={2} />
            <Line type="monotone" dataKey="Samsung_price" stroke="#28a745" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </ChartBox>

      {/* 4. 마케팅 지출 차트 (LineChart) */}
      <ChartBox>
        <ChartTitle>마케팅 비용 (Marketing Spend)</ChartTitle>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="turn" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="Apple_marketing_spend" stroke="#007bff" strokeWidth={2} />
            <Line type="monotone" dataKey="Samsung_marketing_spend" stroke="#28a745" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </ChartBox>
    </ChartWrapper>
  );
};

export default SimulationChart;