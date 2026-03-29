import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  ResponsiveContainer,
} from 'recharts'
import type { WaterfallStep } from '@/mocks/dashboardData'

interface WaterfallChartProps {
  data: WaterfallStep[]
  height?: number
}

const BAR_COLORS = {
  total: '#00A8C7',
  positive: '#2DD4A8',
  negative: '#F97066',
}

function formatDollar(val: number) {
  return `$${val}K`
}

export function WaterfallChart({ data, height = 210 }: WaterfallChartProps) {
  // Transform data for stacked bar approach: invisible base + visible segment
  const chartData = data.map((step) => {
    if (step.type === 'total') {
      return { name: step.name, invisible: 0, visible: step.value, type: step.type }
    }
    const base = step.value >= 0
      ? step.cumulative - step.value
      : step.cumulative
    const vis = Math.abs(step.value)
    return { name: step.name, invisible: base, visible: vis, type: step.type }
  })

  return (
    <div>
      <div className="section-label mb-2">EBITDA BRIDGE</div>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <XAxis
            dataKey="name"
            tick={{ fontSize: 7, fontFamily: 'DM Sans', fill: 'var(--tx-tertiary)' }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 8, fontFamily: 'DM Sans', fill: 'var(--tx-tertiary)' }}
            tickFormatter={formatDollar}
            axisLine={false}
            tickLine={false}
            width={45}
          />
          <Tooltip
            formatter={(val: number, name: string) => {
              if (name === 'invisible') return [null, null]
              return [formatDollar(val), 'Value']
            }}
            contentStyle={{
              background: 'var(--card)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              fontSize: 10,
              color: 'var(--tx-primary)',
            }}
          />
          <Bar dataKey="invisible" stackId="stack" fill="transparent" radius={0} />
          <Bar dataKey="visible" stackId="stack" radius={[4, 4, 0, 0]}>
            {chartData.map((entry, index) => (
              <Cell
                key={index}
                fill={BAR_COLORS[entry.type as keyof typeof BAR_COLORS]}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
