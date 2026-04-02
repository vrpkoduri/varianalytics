/**
 * P&L Section Narrative Card.
 *
 * Displays a section synthesis (Revenue, COGS, OpEx, etc.) with
 * narrative text and key driver pills.
 */

interface Driver {
  accountName: string;
  amount: number;
  direction: string;
}

interface SectionNarrativeCardProps {
  sectionName: string;
  narrative: string;
  drivers: Driver[];
}

export function SectionNarrativeCard({ sectionName, narrative, drivers }: SectionNarrativeCardProps) {
  return (
    <div className="glass-card p-4 space-y-3">
      <span className="section-label">{sectionName.toUpperCase()}</span>

      <p className="text-[11px] text-text leading-relaxed">{narrative}</p>

      {drivers.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {drivers.map((d, i) => {
            const isFav = d.amount > 0;
            return (
              <span
                key={i}
                className={`text-[9px] px-2 py-0.5 rounded-full border ${
                  isFav
                    ? 'bg-emerald/10 text-emerald border-emerald/20'
                    : 'bg-coral/10 text-coral border-coral/20'
                }`}
              >
                {d.accountName} {isFav ? '+' : ''}${Math.abs(d.amount).toLocaleString()}
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}
