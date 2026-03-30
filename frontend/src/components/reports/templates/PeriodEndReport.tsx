const COBALT = '#002C77'
const TEAL = '#00A8C7'
const GREEN = '#0D9373'
const RED = '#CF222E'

const pageStyle: React.CSSProperties = {
  width: 800,
  minHeight: 1060,
  background: '#fff',
  boxShadow: '0 8px 40px rgba(0,0,0,.15)',
  fontFamily: 'sans-serif',
  color: '#1a1a1a',
  fontSize: 12,
  lineHeight: 1.5,
  position: 'relative',
}

const headerStripe: React.CSSProperties = {
  height: 4,
  background: `linear-gradient(90deg, ${COBALT}, ${TEAL})`,
}

const sectionTitle: React.CSSProperties = {
  fontFamily: 'serif',
  fontSize: 18,
  fontWeight: 700,
  color: COBALT,
  marginBottom: 12,
}

const VARIANCES = [
  { account: 'Advisory Revenue', bu: 'Marsh', variance: '+$6.9K', pct: '+15.3%', decomp: [60, 25, 15], status: 'Approved' },
  { account: 'Brokerage Revenue', bu: 'Marsh Re', variance: '+$4.2K', pct: '+8.1%', decomp: [40, 35, 25], status: 'Approved' },
  { account: 'Consulting Fees', bu: 'Oliver Wyman', variance: '-$3.8K', pct: '-12.4%', decomp: [55, 30, 15], status: 'Reviewed' },
  { account: 'Tech Infrastructure', bu: 'Corporate', variance: '-$2.1K', pct: '-18.6%', decomp: [20, 10, 70], status: 'Draft' },
  { account: 'Benefits Revenue', bu: 'Mercer', variance: '+$1.9K', pct: '+5.2%', decomp: [45, 40, 15], status: 'Approved' },
  { account: 'Claims Services', bu: 'Marsh', variance: '-$1.4K', pct: '-9.1%', decomp: [35, 45, 20], status: 'Reviewed' },
  { account: 'Travel & Entertainment', bu: 'Corporate', variance: '-$0.9K', pct: '-22.1%', decomp: [10, 15, 75], status: 'Draft' },
  { account: 'Professional Fees', bu: 'Oliver Wyman', variance: '-$0.7K', pct: '-6.3%', decomp: [50, 30, 20], status: 'Reviewed' },
]

const MARGINS = [
  { label: 'Gross Margin', current: '62.4%', budget: '61.1%', delta: '+1.3pp' },
  { label: 'EBITDA Margin', current: '28.3%', budget: '26.5%', delta: '+1.8pp' },
  { label: 'Operating Margin', current: '26.5%', budget: '24.9%', delta: '+1.6pp' },
  { label: 'Net Margin', current: '18.2%', budget: '17.1%', delta: '+1.1pp' },
]

function DecompBar({ segments }: { segments: number[] }) {
  const colors = [TEAL, COBALT, '#8B9AB5']
  return (
    <div style={{ display: 'flex', height: 6, borderRadius: 3, overflow: 'hidden', width: 80 }}>
      {segments.map((pct, i) => (
        <div key={i} style={{ width: `${pct}%`, background: colors[i] }} />
      ))}
    </div>
  )
}

function PageFooter({ page, total }: { page: number; total: number }) {
  return (
    <div
      style={{
        padding: '12px 40px',
        borderTop: '1px solid #ddd',
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: 8,
        color: '#999',
        marginTop: 'auto',
      }}
    >
      <span>CONFIDENTIAL &mdash; Marsh &amp; McLennan Companies</span>
      <span>
        Page {page} of {total}
      </span>
    </div>
  )
}

export function PeriodEndReport() {
  return (
    <>
      {/* Page 1 — Cover */}
      <div
        style={{
          ...pageStyle,
          background: `linear-gradient(135deg, ${COBALT}, #001A4D)`,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          textAlign: 'center',
          color: '#fff',
        }}
      >
        <div style={{ fontSize: 10, letterSpacing: 3, textTransform: 'uppercase', color: TEAL, marginBottom: 16 }}>
          Marsh Vantage
        </div>
        <div style={{ fontFamily: 'serif', fontSize: 28, fontWeight: 700, maxWidth: 500, lineHeight: 1.3 }}>
          Period-End Variance Analysis
        </div>
        <div style={{ fontSize: 14, color: 'rgba(255,255,255,.7)', marginTop: 12 }}>
          June 2026 &middot; MTD vs Budget
        </div>
        <div style={{ marginTop: 40, fontSize: 10, color: 'rgba(255,255,255,.5)', lineHeight: 2 }}>
          <div>Generated: June 30, 2026 at 09:15 AM EST</div>
          <div>Engine Run: 2.3s &middot; 5.5-pass materiality-first</div>
          <div>Coverage: 847 intersections &middot; 25 material variances</div>
        </div>
        <div
          style={{
            marginTop: 60,
            border: '1px solid rgba(255,255,255,.3)',
            padding: '6px 20px',
            fontSize: 10,
            letterSpacing: 2,
            textTransform: 'uppercase',
            borderRadius: 4,
          }}
        >
          Confidential
        </div>
      </div>

      {/* Page 2 — Financial Summary */}
      <div style={{ ...pageStyle, display: 'flex', flexDirection: 'column' }}>
        <div style={headerStripe} />
        <div style={{ padding: '28px 40px 0' }}>
          <div style={sectionTitle}>Financial Summary</div>

          {/* KPI grid */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 10, marginBottom: 24 }}>
            {[
              { label: 'Revenue', value: '$1,842K', delta: '+2.2%', color: GREEN },
              { label: 'EBITDA', value: '$521K', delta: '+6.8%', color: GREEN },
              { label: 'Op Income', value: '$488K', delta: '+6.8%', color: GREEN },
              { label: 'Net Income', value: '$335K', delta: '+4.1%', color: GREEN },
            ].map((kpi) => (
              <div key={kpi.label} style={{ border: '1px solid #e8e8e8', borderRadius: 6, padding: '10px 14px' }}>
                <div style={{ fontSize: 8, color: '#888', textTransform: 'uppercase', letterSpacing: 0.8 }}>{kpi.label}</div>
                <div style={{ fontFamily: 'serif', fontSize: 20, fontWeight: 700, color: COBALT, marginTop: 2 }}>{kpi.value}</div>
                <div style={{ fontSize: 10, fontWeight: 600, color: kpi.color }}>{kpi.delta}</div>
              </div>
            ))}
          </div>

          {/* Narrative */}
          <div
            style={{
              borderLeft: `3px solid ${TEAL}`,
              padding: '10px 16px',
              background: '#f7fbfc',
              borderRadius: '0 6px 6px 0',
              fontSize: 11,
              lineHeight: 1.7,
              color: '#333',
              marginBottom: 24,
            }}
          >
            June results reflect continued momentum in Advisory and Brokerage lines, offset by persistent Tech
            Infrastructure overspend and softness in EMEA Consulting. Revenue exceeded budget by $40K (+2.2%),
            primarily driven by volume gains. Cost discipline delivered EBITDA margin expansion of 180bps vs budget.
            Management action required on two trending items flagged by the engine.
          </div>

          {/* Margin Analysis */}
          <div style={{ fontFamily: 'serif', fontSize: 14, fontWeight: 700, color: COBALT, marginBottom: 8 }}>
            Margin Analysis
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 10, marginBottom: 24 }}>
            <thead>
              <tr style={{ borderBottom: `2px solid ${COBALT}` }}>
                {['Metric', 'Actual', 'Budget', 'Delta'].map((h) => (
                  <th
                    key={h}
                    style={{
                      textAlign: 'left',
                      padding: '6px 10px',
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
              {MARGINS.map((m) => (
                <tr key={m.label} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: '6px 10px', fontWeight: 500 }}>{m.label}</td>
                  <td style={{ padding: '6px 10px', fontFamily: 'serif', fontWeight: 600 }}>{m.current}</td>
                  <td style={{ padding: '6px 10px', color: '#888' }}>{m.budget}</td>
                  <td style={{ padding: '6px 10px', fontWeight: 600, color: GREEN }}>{m.delta}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <PageFooter page={2} total={4} />
      </div>

      {/* Page 3 — Variance Detail */}
      <div style={{ ...pageStyle, display: 'flex', flexDirection: 'column' }}>
        <div style={headerStripe} />
        <div style={{ padding: '28px 40px 0' }}>
          <div style={sectionTitle}>Material Variances</div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 10, marginBottom: 20 }}>
            <thead>
              <tr style={{ borderBottom: `2px solid ${COBALT}` }}>
                {['Account', 'BU', 'Variance', '%', 'Decomposition', 'Status'].map((h) => (
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
              {VARIANCES.map((v, i) => {
                const isNeg = v.variance.startsWith('-')
                return (
                  <tr key={i} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={{ padding: '6px 8px', fontWeight: 500 }}>{v.account}</td>
                    <td style={{ padding: '6px 8px', color: '#666' }}>{v.bu}</td>
                    <td style={{ padding: '6px 8px', fontWeight: 600, color: isNeg ? RED : GREEN }}>{v.variance}</td>
                    <td style={{ padding: '6px 8px', fontWeight: 600, color: isNeg ? RED : GREEN }}>{v.pct}</td>
                    <td style={{ padding: '6px 8px' }}>
                      <DecompBar segments={v.decomp} />
                    </td>
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
                )
              })}
            </tbody>
          </table>

          {/* Narrative excerpts */}
          <div style={{ fontFamily: 'serif', fontSize: 14, fontWeight: 700, color: COBALT, marginBottom: 8 }}>
            Narrative Excerpts
          </div>
          {[
            { title: 'Advisory Revenue (+$6.9K)', text: 'Volume-driven outperformance. 3 new mandates closed in final week. Price realization +2.1% above budget rate card. Mix shift toward higher-margin strategic advisory engagements.' },
            { title: 'Consulting Fees (-$3.8K)', text: 'Pipeline conversion below target. Two major engagements delayed to Q3. Utilization at 72% vs 85% budget. EMEA region accounts for 65% of shortfall.' },
            { title: 'Tech Infrastructure (-$2.1K)', text: 'Fourth consecutive month of overspend. Unplanned cloud migration costs ($1.4K) and license true-up ($0.7K). CTO review scheduled for July.' },
          ].map((n) => (
            <div key={n.title} style={{ marginBottom: 12, fontSize: 10, lineHeight: 1.6 }}>
              <div style={{ fontWeight: 600, color: COBALT, marginBottom: 2 }}>{n.title}</div>
              <div style={{ color: '#555' }}>{n.text}</div>
            </div>
          ))}
        </div>
        <PageFooter page={3} total={4} />
      </div>

      {/* Page 4 — Risk & Appendix */}
      <div style={{ ...pageStyle, display: 'flex', flexDirection: 'column' }}>
        <div style={headerStripe} />
        <div style={{ padding: '28px 40px 0' }}>
          <div style={sectionTitle}>Risk Assessment</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 28 }}>
            {[
              { severity: 'HIGH', title: 'Tech Infrastructure Overspend', text: 'Cumulative YTD overspend of $8.4K with no remediation plan. Cloud migration timeline extended by 2 months.' },
              { severity: 'MEDIUM', title: 'EMEA Consulting Pipeline', text: 'Revenue at risk for Q3: $12K if conversion rates do not improve. 3 proposals pending > 60 days.' },
              { severity: 'LOW', title: 'FX Impact — APAC', text: 'AUD depreciation creating $0.4K drag on APAC revenue. Hedging strategy under review.' },
            ].map((r) => (
              <div
                key={r.title}
                style={{
                  borderLeft: `3px solid ${r.severity === 'HIGH' ? RED : r.severity === 'MEDIUM' ? '#BF8700' : '#8B9AB5'}`,
                  padding: '8px 14px',
                  background: r.severity === 'HIGH' ? '#fef5f5' : r.severity === 'MEDIUM' ? '#fef8e7' : '#f8f9fa',
                  borderRadius: '0 6px 6px 0',
                  fontSize: 10,
                }}
              >
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 2 }}>
                  <span
                    style={{
                      fontSize: 7,
                      fontWeight: 700,
                      padding: '1px 5px',
                      borderRadius: 4,
                      background: r.severity === 'HIGH' ? RED : r.severity === 'MEDIUM' ? '#BF8700' : '#8B9AB5',
                      color: '#fff',
                    }}
                  >
                    {r.severity}
                  </span>
                  <strong>{r.title}</strong>
                </div>
                <div style={{ color: '#555' }}>{r.text}</div>
              </div>
            ))}
          </div>

          <div style={sectionTitle}>Recommendations</div>
          <ol style={{ paddingLeft: 20, fontSize: 11, lineHeight: 1.8, color: '#333', marginBottom: 28 }}>
            <li>Convene finance + CTO review of Tech Infrastructure budget before July close. Establish remediation plan with monthly checkpoints.</li>
            <li>Engage EMEA Consulting leadership for pipeline acceleration workshop. Target: convert 2 of 3 pending proposals by mid-July.</li>
            <li>Accelerate APAC Advisory pipeline to offset FX headwind. Consider selective pricing adjustments for AUD-denominated engagements.</li>
            <li>Validate Q3 forecast assumptions against June actuals. Update rolling forecast by July 10.</li>
          </ol>

          <div style={{ fontFamily: 'serif', fontSize: 14, fontWeight: 700, color: COBALT, marginBottom: 8 }}>
            Methodology
          </div>
          <div style={{ fontSize: 9, color: '#888', lineHeight: 1.7, marginBottom: 20 }}>
            This report was generated using the Marsh Vantage 5.5-pass materiality-first computation engine.
            Variances are calculated at the MTD atomic grain across 847 intersections (5 hierarchy dimensions x
            account structure). Materiality thresholds: absolute &gt; $1K OR percentage &gt; 5% OR trending (3+
            consecutive months). Decomposition applied: Revenue (Volume x Price x Mix x FX), COGS (Rate x Volume
            x Mix), OpEx (Rate x Volume x Timing x One-time). Narratives generated via RAG-enhanced LLM with
            approved commentary few-shot examples.
          </div>
        </div>
        <PageFooter page={4} total={4} />
      </div>
    </>
  )
}
