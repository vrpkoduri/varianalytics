export function PLHeaderRow() {
  return (
    <div
      className="grid items-center px-3 py-2 border-b-2 border-border"
      style={{
        gridTemplateColumns: 'minmax(230px, 2fr) 70px 70px 70px 65px 50px 50px',
        background: 'var(--card-alt)',
      }}
    >
      <span className="text-[7px] font-bold text-teal uppercase tracking-[0.7px]">Account</span>
      <span className="text-[7px] font-bold text-teal uppercase tracking-[0.7px] text-right">ACT</span>
      <span className="text-[7px] font-bold text-teal uppercase tracking-[0.7px] text-right">BUD</span>
      <span className="text-[7px] font-bold text-teal uppercase tracking-[0.7px] text-right">VAR$</span>
      <span className="text-[7px] font-bold text-teal uppercase tracking-[0.7px] text-right">%</span>
      <span className="text-[7px] font-bold text-teal uppercase tracking-[0.7px] text-center">FAV</span>
      <span className="text-[7px] font-bold text-teal uppercase tracking-[0.7px] text-center">TYPE</span>
    </div>
  )
}
