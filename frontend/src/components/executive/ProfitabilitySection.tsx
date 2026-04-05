/**
 * Profitability section with margin gauges and narrative.
 */

interface ProfitabilitySectionProps {
  narrative: string;
  grossMargin?: number;
  ebitdaMargin?: number;
  netMargin?: number;
}

function MiniGauge({ label, value, color }: { label: string; value: number; color: string }) {
  const radius = 32;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.min(Math.max(value, 0), 100);
  const offset = circumference - (progress / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width="80" height="80" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r={radius} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="6" />
        <circle
          cx="40" cy="40" r={radius} fill="none"
          stroke={color} strokeWidth="6" strokeLinecap="round"
          strokeDasharray={circumference} strokeDashoffset={offset}
          transform="rotate(-90 40 40)"
          className="transition-all duration-1000"
        />
        <text x="40" y="40" textAnchor="middle" dominantBaseline="central"
          className="text-[14px] font-body font-bold" fill="white">
          {value.toFixed(1)}%
        </text>
      </svg>
      <span className="text-[9px] text-text-secondary font-medium">{label}</span>
    </div>
  );
}

export function ProfitabilitySection({ narrative, grossMargin = 0, ebitdaMargin = 0, netMargin = 0 }: ProfitabilitySectionProps) {
  return (
    <div className="glass-card p-4 space-y-3">
      <span className="section-label">PROFITABILITY</span>

      <div className="flex items-center gap-6">
        <div className="flex gap-4">
          <MiniGauge label="Gross Margin" value={grossMargin} color="#2DD4A8" />
          <MiniGauge label="EBITDA Margin" value={ebitdaMargin} color="#00A8C7" />
          <MiniGauge label="Net Margin" value={netMargin} color="#A78BFA" />
        </div>
        <p className="text-[11px] text-text leading-relaxed flex-1">{narrative}</p>
      </div>
    </div>
  );
}
