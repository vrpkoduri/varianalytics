import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Layout (CSS variable references for theme switching)
        bg: 'var(--bg)',
        surface: 'var(--surface)',
        card: 'var(--card)',
        'card-alt': 'var(--card-alt)',
        border: 'var(--border)',
        'border-hover': 'var(--border-hover)',
        'tx-primary': 'var(--tx-primary)',
        'tx-secondary': 'var(--tx-secondary)',
        'tx-tertiary': 'var(--tx-tertiary)',
        // Brand chrome (fixed — same in both themes)
        cobalt: { DEFAULT: '#002C77', light: '#003A99' },
        teal: { DEFAULT: '#00A8C7', light: '#00BCDB' },
        persian: '#016D9E',
        blizzard: '#A7E2F0',
        // Data semantics (CSS variable references for theme switching)
        gold: { DEFAULT: 'var(--gold)', surface: 'var(--gold-surface)' },
        emerald: { DEFAULT: 'var(--emerald)', surface: 'var(--emerald-surface)' },
        coral: { DEFAULT: 'var(--coral)', surface: 'var(--coral-surface)' },
        amber: { DEFAULT: 'var(--amber)', surface: 'var(--amber-surface)' },
        purple: { DEFAULT: 'var(--purple)', surface: 'var(--purple-surface)' },
        // Glass
        glass: 'var(--glass)',
        'glass-border': 'var(--glass-border)',
      },
      fontFamily: {
        body: ['"DM Sans"', 'sans-serif'],
        display: ['"Playfair Display"', 'Georgia', 'serif'],
      },
      fontSize: {
        'page-title': ['22px', { lineHeight: '1.3', fontWeight: '700' }],
        'section-title': ['15px', { lineHeight: '1.4', fontWeight: '700' }],
        'card-title': ['12px', { lineHeight: '1.4', fontWeight: '700' }],
        'kpi': ['28px', { lineHeight: '1.2', fontWeight: '700' }],
        'modal-big': ['30px', { lineHeight: '1.2', fontWeight: '700' }],
        'table-var': ['11px', { lineHeight: '1.4', fontWeight: '700' }],
        'body-md': ['13px', { lineHeight: '1.6', fontWeight: '400' }],
        'table-sm': ['11px', { lineHeight: '1.5', fontWeight: '400' }],
        'label-sm': ['10px', { lineHeight: '1.4', fontWeight: '600' }],
        'section-label': ['8px', { lineHeight: '1.4', fontWeight: '700', letterSpacing: '1.2px' }],
        'badge-xs': ['9px', { lineHeight: '1.4', fontWeight: '600', letterSpacing: '0.2px' }],
        'micro': ['7px', { lineHeight: '1.4', fontWeight: '700' }],
      },
      borderRadius: {
        card: '14px',
        button: '6px',
        pill: '16px',
        badge: '10px',
      },
      spacing: {
        'page-x': '24px',
        'page-y': '20px',
        'card-px': '16px',
        'card-py': '14px',
        'sidebar': '210px',
        'header-1': '58px',
        'header-2': '40px',
        'modal-w': '500px',
      },
      maxWidth: {
        content: '1300px',
      },
      screens: {
        mobile: '700px',
        tablet: '1100px',
        desktop: '1300px',
      },
      boxShadow: {
        card: '0 2px 8px rgba(0,0,0,.08)',
        'card-hover': '0 8px 24px rgba(0,0,0,.12)',
        modal: '0 16px 48px rgba(0,0,0,.25)',
        paper: '0 8px 40px rgba(0,0,0,.15)',
        glow: '0 0 16px rgba(0,168,199,.3)',
      },
      keyframes: {
        fadeUp: {
          from: { opacity: '0', transform: 'translateY(16px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        slideIn: {
          from: { transform: 'translateX(100%)' },
          to: { transform: 'translateX(0)' },
        },
        fadeIn: {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        pulse: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.4' },
        },
        expandIn: {
          from: { maxHeight: '0', opacity: '0', paddingTop: '0', paddingBottom: '0' },
          to: { maxHeight: '600px', opacity: '1' },
        },
        blink: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
        slideDown: {
          from: { opacity: '0', transform: 'translateY(-8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        glow: {
          '0%, 100%': { filter: 'drop-shadow(0 0 8px rgba(0,168,199,.4))' },
          '50%': { filter: 'drop-shadow(0 0 16px rgba(0,168,199,.6))' },
        },
        headerGrad: {
          '0%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
          '100%': { backgroundPosition: '0% 50%' },
        },
        confetti: {
          '0%': { transform: 'translateY(0) rotate(0)', opacity: '1' },
          '100%': { transform: 'translateY(-60px) rotate(720deg)', opacity: '0' },
        },
        borderPulse: {
          '0%, 100%': { opacity: '0.6' },
          '50%': { opacity: '1' },
        },
        breathe: {
          '0%, 100%': { boxShadow: '0 0 0 rgba(0,168,199,.4)' },
          '50%': { boxShadow: '0 0 6px rgba(0,168,199,.6)' },
        },
        typingBounce: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-4px)' },
        },
        barSlide: {
          from: { width: '0' },
          to: { width: 'var(--bar-w)' },
        },
        shimmer: {
          from: { backgroundPosition: '-200% 0' },
          to: { backgroundPosition: '200% 0' },
        },
      },
      animation: {
        'fade-up': 'fadeUp 0.45s cubic-bezier(.22,1,.36,1) both',
        'slide-in': 'slideIn 0.25s cubic-bezier(.22,1,.36,1) both',
        'fade-in': 'fadeIn 0.2s ease both',
        'pulse': 'pulse 2s infinite',
        'expand-in': 'expandIn 0.3s cubic-bezier(.22,1,.36,1) both',
        'blink': 'blink 0.8s infinite',
        'slide-down': 'slideDown 0.2s ease both',
        'glow': 'glow 3s ease infinite',
        'header-grad': 'headerGrad 8s ease infinite',
        'confetti': 'confetti 0.8s ease-out both',
        'border-pulse': 'borderPulse 2s ease infinite',
        'breathe': 'breathe 1.5s ease infinite',
        'typing-bounce': 'typingBounce 1.2s ease infinite',
        'bar-slide': 'barSlide 0.5s cubic-bezier(.22,1,.36,1) both',
        'shimmer': 'shimmer 2s linear infinite',
      },
    },
  },
  plugins: [],
}

export default config
