const CONFETTI_COLORS = ['#00A8C7', '#2DD4A8', '#E3A547', '#A78BFA', '#A7E2F0']

/**
 * Fire 20 confetti particles from the center of the screen.
 * Auto-cleans after 1200ms.
 */
export function fireConfetti(): void {
  const container = document.getElementById('confetti-container')
  if (!container) return

  for (let i = 0; i < 20; i++) {
    const el = document.createElement('div')
    const color = CONFETTI_COLORS[i % CONFETTI_COLORS.length]
    const x = Math.random() * 100

    el.style.cssText = `
      position: fixed;
      width: 6px;
      height: 6px;
      border-radius: 2px;
      background: ${color};
      left: ${x}vw;
      top: 60vh;
      z-index: 999;
      pointer-events: none;
      animation: confetti-burst 0.8s ease-out forwards;
      animation-delay: ${Math.random() * 300}ms;
      opacity: 0;
    `
    container.appendChild(el)

    setTimeout(() => {
      el.remove()
    }, 1200)
  }
}

/**
 * Fixed container that holds confetti particles.
 * Mount once at the app root.
 */
export function ConfettiContainer() {
  return (
    <>
      <style>{`
        @keyframes confetti-burst {
          0% { transform: translateY(0) rotate(0deg); opacity: 1; }
          100% { transform: translateY(-60px) rotate(720deg); opacity: 0; }
        }
      `}</style>
      <div
        id="confetti-container"
        className="fixed inset-0 z-[999] pointer-events-none"
      />
    </>
  )
}
