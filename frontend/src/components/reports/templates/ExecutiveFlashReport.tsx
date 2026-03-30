const COBALT = '#002C77'
const TEAL = '#00A8C7'
const GREEN = '#0D9373'
const RED = '#CF222E'

const VARIANCES = [
  { account: 'Advisory Revenue', bu: 'Marsh', variance: '+$6.9K', pct: '+15.3%', status: 'Approved', color: GREEN },
  { account: 'Brokerage Revenue', bu: 'Marsh Re', variance: '+$4.2K', pct: '+8.1%', status: 'Approved', color: GREEN },
  { account: 'Consulting Fees', bu: 'Oliver Wyman', variance: '-$3.8K', pct: '-12.4%', status: 'Reviewed', color: RED },
  { account: 'Tech Infrastructure', bu: 'Corporate', variance: '-$2.1K', pct: '-18.6%', status: 'Draft', color: RED },
  { account: 'Benefits Revenue', bu: 'Mercer', variance: '+$1.9K', pct: '+5.2%', status: 'Approved', color: GREEN },
  { account: 'Claims Services', bu: 'Marsh', variance: '-$1.4K', pct: '-9.1%', status: 'Reviewed', color: RED },
]

export function ExecutiveFlashReport() {
  return (
    <div
      style={{
        width: 800,
        minHeight: 1000,
        background: '#fff',
        boxShadow: '0 8px 40px rgba(0,0,0,.15)',
        fontFamily: 'sans-serif',
        color: '#1a1a1a',
        fontSize: 12,
        lineHeight: 1.5,
      }}
    >
      {/* Cobalt header stripe */}
      <div style={{ height: 4, background: `linear-gradient(90deg, ${COBALT}, ${TEAL})` }} />

      {/* Logo area */}
      <div style={{ padding: '28px 40px 16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ fontFamily: 'serif', fontSize: 11, fontWeight: 700, color: TEAL, letterSpacing: 1.5, textTransform: 'uppercase' }}>
              Marsh Vantage
            </div>
            <div style={{ fontFamily: 'serif', fontSize: 22, fontWeight: 700, color: COBALT, marginTop: 4 }}>
              Executive Flash Report
            </div>
          </div>
          <div style={{ textAlign: 'right', fontSize: 10, color: '#666' }}>
            <div>June 2026</div>
            <div>MTD vs Budget</div>
          </div>
        </div>
        <div style={{ height: 1, background: '#ddd', marginTop: 16 }} />
      </div>

      {/* KPI grid */}
      <div style={{ padding: '0 40px 24px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        {[
          { label: 'Revenue', value: '$1,842K', delta: '+2.2%', color: GREEN },
          { label: 'EBITDA', value: '$521K', delta: '+6.8%', color: GREEN },
          { label: 'Operating Income', value: '$488K', delta: '+6.8%', color: GREEN },
          { label: 'Material Variances', value: '25', delta: 'flagged', color: COBALT },
        ].map((kpi) => (
          <div
            key={kpi.label}
            style={{
              border: '1px solid #e8e8e8',
              borderRadius: 6,
              padding: '12px 16px',
            }}
          >
            <div style={{ fontSize: 9, color: '#888', textTransform: 'uppercase', letterSpacing: 1 }}>{kpi.label}</div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginTop: 4 }}>
              <span style={{ fontFamily: 'serif', fontSize: 22, fontWeight: 700, color: COBALT }}>{kpi.value}</span>
              <span style={{ fontSize: 11, fontWeight: 600, color: kpi.color }}>{kpi.delta}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Executive Summary */}
      <div style={{ padding: '0 40px 24px' }}>
        <div style={{ fontFamily: 'serif', fontSize: 14, fontWeight: 700, color: COBALT, marginBottom: 8 }}>
          Executive Summary
        </div>
        <div
          style={{
            borderLeft: `3px solid ${TEAL}`,
            padding: '10px 16px',
            background: '#f7fbfc',
            borderRadius: '0 6px 6px 0',
            fontSize: 11,
            lineHeight: 1.7,
            color: '#333',
          }}
        >
          June close: Revenue +2.2% ($40K favorable), driven by Advisory outperformance in Marsh (+$6.9K) and strong Brokerage
          volumes in Marsh Re. EBITDA +6.8% ($33K favorable) reflecting disciplined cost management. Key watch items: Tech
          Infrastructure overspend persists for 4th consecutive month; EMEA Consulting pipeline 15% below target. 25 material
          variances identified, 18 approved for distribution.
        </div>
      </div>

      {/* Top Material Variances */}
      <div style={{ padding: '0 40px 24px' }}>
        <div style={{ fontFamily: 'serif', fontSize: 14, fontWeight: 700, color: COBALT, marginBottom: 8 }}>
          Top Material Variances
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 10 }}>
          <thead>
            <tr style={{ borderBottom: `2px solid ${COBALT}` }}>
              {['Account', 'BU', 'Variance', '%', 'Status'].map((h) => (
                <th
                  key={h}
                  style={{
                    textAlign: 'left',
                    padding: '6px 8px',
                    fontSize: 9,
                    fontWeight: 700,
                    color: COBALT,
                    textTransform: 'uppercase',
                    letterSpacing: 0.8,
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {VARIANCES.map((v, i) => (
              <tr key={i} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: '6px 8px', fontWeight: 500 }}>{v.account}</td>
                <td style={{ padding: '6px 8px', color: '#666' }}>{v.bu}</td>
                <td style={{ padding: '6px 8px', fontWeight: 600, color: v.color }}>{v.variance}</td>
                <td style={{ padding: '6px 8px', fontWeight: 600, color: v.color }}>{v.pct}</td>
                <td style={{ padding: '6px 8px' }}>
                  <span
                    style={{
                      fontSize: 8,
                      fontWeight: 600,
                      padding: '2px 6px',
                      borderRadius: 8,
                      background: v.status === 'Approved' ? '#e6f7f2' : v.status === 'Reviewed' ? '#fef8e7' : '#f5f5f5',
                      color: v.status === 'Approved' ? GREEN : v.status === 'Reviewed' ? '#BF8700' : '#888',
                    }}
                  >
                    {v.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Risk Flags */}
      <div style={{ padding: '0 40px 32px' }}>
        <div style={{ fontFamily: 'serif', fontSize: 14, fontWeight: 700, color: COBALT, marginBottom: 8 }}>
          Risk Flags
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div
            style={{
              borderLeft: `3px solid ${RED}`,
              padding: '8px 14px',
              background: '#fef5f5',
              borderRadius: '0 6px 6px 0',
              fontSize: 11,
              color: '#333',
            }}
          >
            <strong>Tech Infrastructure:</strong> 4 consecutive months above budget. Cumulative YTD overspend of $8.4K.
            Root cause: unplanned cloud migration costs. Recommend finance review with CTO.
          </div>
          <div
            style={{
              borderLeft: `3px solid ${RED}`,
              padding: '8px 14px',
              background: '#fef5f5',
              borderRadius: '0 6px 6px 0',
              fontSize: 11,
              color: '#333',
            }}
          >
            <strong>EMEA Consulting:</strong> Pipeline 15% below target. Revenue at risk for Q3 if conversion rates
            do not improve. Engagement team capacity utilization at 72% vs 85% target.
          </div>
        </div>
      </div>

      {/* Footer */}
      <div
        style={{
          padding: '12px 40px',
          borderTop: '1px solid #ddd',
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: 8,
          color: '#999',
        }}
      >
        <span>CONFIDENTIAL &mdash; Marsh &amp; McLennan Companies</span>
        <span>Page 1 of 1</span>
      </div>
    </div>
  )
}
