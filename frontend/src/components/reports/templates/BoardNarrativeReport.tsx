const COBALT = '#002C77'
const TEAL = '#00A8C7'
const RED = '#CF222E'

export function BoardNarrativeReport() {
  return (
    <div
      style={{
        width: 800,
        minHeight: 1060,
        background: '#fff',
        boxShadow: '0 8px 40px rgba(0,0,0,.15)',
        fontFamily: 'sans-serif',
        color: '#1a1a1a',
        fontSize: 12,
        lineHeight: 1.7,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Letterhead */}
      <div style={{ padding: '28px 48px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontFamily: 'serif', fontSize: 11, fontWeight: 700, color: TEAL, letterSpacing: 1.5, textTransform: 'uppercase' }}>
            Marsh Vantage
          </div>
          <div style={{ fontSize: 9, color: '#999', marginTop: 2 }}>Marsh &amp; McLennan Companies</div>
        </div>
        <div style={{ textAlign: 'right', fontSize: 10, color: '#666' }}>
          <div>June 30, 2026</div>
          <div>Board of Directors</div>
        </div>
      </div>
      <div style={{ height: 1, background: '#ddd', margin: '0 48px' }} />

      {/* Title */}
      <div style={{ padding: '24px 48px 0' }}>
        <div style={{ fontFamily: 'serif', fontSize: 22, fontWeight: 700, color: COBALT, marginBottom: 20 }}>
          Financial Performance &mdash; June 2026
        </div>

        {/* Prose */}
        <p style={{ marginBottom: 16, color: '#333' }}>
          The company delivered a strong June, with revenue of $1,842K exceeding budget by 2.2% ($40K favorable).
          This performance was principally driven by volume gains in the Advisory segment, where three new mandates
          closed in the final week of the period, and continued momentum in Reinsurance Brokerage.
        </p>
        <p style={{ marginBottom: 16, color: '#333' }}>
          EBITDA of $521K represented a 6.8% favorable variance to plan, reflecting both top-line outperformance
          and disciplined cost management across operating units. EBITDA margin of 28.3% expanded 180 basis points
          versus budget, marking the third consecutive month of margin expansion.
        </p>

        {/* Callout box */}
        <div
          style={{
            float: 'right',
            width: 200,
            marginLeft: 24,
            marginBottom: 16,
            border: `1px solid ${TEAL}`,
            borderRadius: 6,
            padding: '14px 16px',
            background: '#f7fbfc',
          }}
        >
          <div style={{ fontSize: 9, color: '#888', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 }}>
            Key Figures
          </div>
          {[
            { label: 'Revenue', value: '$1,842K', delta: '+2.2%' },
            { label: 'EBITDA', value: '$521K', delta: '+6.8%' },
            { label: 'Op Income', value: '$488K', delta: '+6.8%' },
          ].map((k) => (
            <div key={k.label} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, marginBottom: 4 }}>
              <span style={{ color: '#666' }}>{k.label}</span>
              <span>
                <strong style={{ color: COBALT }}>{k.value}</strong>{' '}
                <span style={{ color: '#0D9373', fontSize: 9 }}>{k.delta}</span>
              </span>
            </div>
          ))}
        </div>

        {/* Areas of Attention */}
        <div style={{ fontFamily: 'serif', fontSize: 16, fontWeight: 700, color: COBALT, marginTop: 24, marginBottom: 12, clear: 'both' }}>
          Areas of Attention
        </div>

        <div
          style={{
            borderTop: `3px solid ${RED}`,
            padding: '12px 16px',
            background: '#fef5f5',
            borderRadius: '0 0 6px 6px',
            marginBottom: 16,
          }}
        >
          <div style={{ fontWeight: 600, color: COBALT, marginBottom: 4, fontSize: 11 }}>
            Technology Infrastructure Costs
          </div>
          <p style={{ color: '#555', fontSize: 11, marginBottom: 0 }}>
            Technology infrastructure spending exceeded budget for the fourth consecutive month, accumulating a
            year-to-date overspend of $8.4K. The primary driver is unplanned cloud migration costs associated
            with the enterprise platform transition. Management has scheduled a joint Finance-CTO review for
            early July to establish a remediation plan with monthly checkpoints.
          </p>
        </div>

        <div
          style={{
            borderTop: `3px solid ${RED}`,
            padding: '12px 16px',
            background: '#fef5f5',
            borderRadius: '0 0 6px 6px',
            marginBottom: 16,
          }}
        >
          <div style={{ fontWeight: 600, color: COBALT, marginBottom: 4, fontSize: 11 }}>
            EMEA Consulting Pipeline Softness
          </div>
          <p style={{ color: '#555', fontSize: 11, marginBottom: 0 }}>
            The EMEA Consulting pipeline stands 15% below target, with three proposals pending beyond 60 days.
            Engagement team capacity utilization has declined to 72% versus the 85% budget assumption. If
            conversion rates do not improve, approximately $12K of Q3 revenue is at risk. Regional leadership
            has been engaged for a pipeline acceleration initiative.
          </p>
        </div>

        {/* Outlook & Recommendations */}
        <div style={{ fontFamily: 'serif', fontSize: 16, fontWeight: 700, color: COBALT, marginTop: 24, marginBottom: 12 }}>
          Outlook &amp; Recommendations
        </div>

        <ol style={{ paddingLeft: 20, color: '#333', fontSize: 11, lineHeight: 1.8, marginBottom: 24 }}>
          <li style={{ marginBottom: 4 }}>
            Monitor technology infrastructure spending weekly through Q3, with escalation triggers at 10%
            monthly overspend.
          </li>
          <li style={{ marginBottom: 4 }}>
            Engage EMEA Consulting leadership for pipeline acceleration, targeting conversion of two pending
            proposals by mid-July.
          </li>
          <li style={{ marginBottom: 4 }}>
            Accelerate APAC Advisory pipeline development to offset emerging FX headwinds from AUD depreciation.
          </li>
        </ol>

        {/* AI disclosure */}
        <p style={{ fontSize: 9, color: '#bbb', fontStyle: 'italic', marginBottom: 20 }}>
          This narrative was generated by Marsh Vantage AI with RAG-enhanced commentary synthesis.
          All figures reflect approved variance analyses as of June 30, 2026. Reviewed and approved
          by FP&amp;A Director prior to distribution.
        </p>
      </div>

      {/* Footer */}
      <div
        style={{
          padding: '12px 48px',
          borderTop: '1px solid #ddd',
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: 8,
          color: '#999',
          marginTop: 'auto',
        }}
      >
        <span>BOARD CONFIDENTIAL &mdash; Marsh &amp; McLennan Companies</span>
        <span>Page 1 of 1</span>
      </div>
    </div>
  )
}
