import { useTheme } from '@/context/ThemeContext'

interface ThemeToggleProps {
  className?: string
}

export default function ThemeToggle({ className }: ThemeToggleProps) {
  const { isDark, toggleTheme } = useTheme()

  return (
    <button
      onClick={toggleTheme}
      className={[
        'w-[30px] h-[30px] rounded-[7px] border border-white/10 bg-white/[.04]',
        'flex items-center justify-center cursor-pointer',
        'hover:bg-white/[.08] transition-colors text-[14px]',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
      aria-label={`Switch to ${isDark ? 'light' : 'dark'} mode`}
    >
      {isDark ? (
        <span className="text-white/50">&#9788;</span>
      ) : (
        <span className="text-white/50">&#9790;</span>
      )}
    </button>
  )
}
