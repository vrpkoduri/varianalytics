/**
 * GlobalBackground — Radial gradient backdrop per Marsh Vantage spec.
 * Dark: subtle cobalt + teal ellipse gradients on #030B1A.
 * Light: clean gradient on #F4F7FC.
 * Fixed position, z-index -1, covers viewport.
 */
export function GlobalBackground() {
  return (
    <div
      className="fixed inset-0 -z-10 pointer-events-none"
      style={{
        background: `
          radial-gradient(ellipse at 20% 50%, rgba(0,44,119,.15), transparent 60%),
          radial-gradient(ellipse at 80% 20%, rgba(0,168,199,.08), transparent 50%),
          var(--bg)
        `,
      }}
    />
  )
}
