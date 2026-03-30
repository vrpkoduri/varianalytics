import {
  LineChart,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import type { TrendPoint } from '@/mocks/dashboardData'

interface TrendChartProps {
  data: TrendPoint[]
  height?: number
}

function formatDollar(val: number) {
  return `$${val / 1000}K`
}

export function TrendChart({ data, height = 210 }: TrendChartProps) {
  return (
    <div>
      <div className="section-label mb-2">REVENUE TREND</div>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="rgba(0,168,199,.12)" />
              <stop offset="100%" stopColor="rgba(0,168,199,.01)" />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="month"
            tick={{ fontSize: 8, fontFamily: 'DM Sans', fill: 'var(--tx-tertiary)' }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 8, fontFamily: 'DM Sans', fill: 'var(--tx-tertiary)' }}
            tickFormatter={formatDollar}
            axisLine={false}
            tickLine={false}
            width={45}
            domain={['dataMin - 40', 'dataMax + 40']}
          />
          <Tooltip
            content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null
              return (
                <div className="px-3 py-2 rounded-lg text-[9px] shadow-lg"
                     style={{ background: 'var(--card)', border: '1px solid var(--border)', color: 'var(--tx-secondary)' }}>
                  <div className="font-semibold mb-1" style={{ color: 'var(--tx-primary)' }}>{label}</div>
                  {payload.map((p: any, i: number) => (
                    <div key={i}>{p.name}: <b style={{ color: p.color }}>${Math.round(p.value)}K</b></div>
                  ))}
                </div>
              )
            }}
          />
          <Area
            type="monotone"
            dataKey="actual"
            fill="url(#trendFill)"
            stroke="none"
          />
          <Line
            type="monotone"
            dataKey="budget"
            stroke="#016D9E"
            strokeWidth={1.5}
            strokeDasharray="5 3"
            dot={false}
            name="Budget"
          />
          <Line
            type="monotone"
            dataKey="actual"
            stroke="#2DD4A8"
            strokeWidth={2.5}
            dot={{ r: 3, fill: '#2DD4A8', strokeWidth: 0 }}
            name="Actual"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
