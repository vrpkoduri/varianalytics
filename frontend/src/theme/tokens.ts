// Marsh Vantage — Design Tokens
// TypeScript source of truth. CSS variables and Tailwind config must stay in sync.
// Generated from FPA_Variance_Agent_UI.html prototype (136KB, 989 lines)

export const colors = {
  // Backgrounds
  bg: { dark: '#030B1A', light: '#F4F7FC' },
  surface: { dark: '#0A1628', light: '#FFFFFF' },
  card: { dark: '#0F1D32', light: '#FFFFFF' },
  cardAlt: { dark: '#132440', light: '#F0F4FA' },
  border: { dark: '#1A2A42', light: '#D4DCE8' },
  borderHover: { dark: '#243552', light: '#B8C4D6' },

  // Text
  text: { dark: '#E8EDF5', light: '#0A1628' },
  textSecondary: { dark: '#8B9AB5', light: '#5A6B84' },
  textTertiary: { dark: '#5A6B84', light: '#8B9AB5' },

  // Marsh Brand Chrome (same in both themes)
  cobalt: '#002C77',
  cobaltLight: '#003A99',
  teal: '#00A8C7',
  tealLight: '#00BCDB',
  persianBlue: '#016D9E',
  blizzardBlue: '#A7E2F0',

  // Data Semantic (NEVER use for chrome/navigation)
  gold: { dark: '#E3A547', light: '#BF8700' },
  emerald: { dark: '#2DD4A8', light: '#0D9373' },
  coral: { dark: '#F97066', light: '#CF222E' },
  amber: { dark: '#FBBF24', light: '#CA8A04' },
  purple: { dark: '#A78BFA', light: '#7C3AED' },

  // Semantic surfaces (8% opacity tints)
  goldSurface: { dark: 'rgba(227,165,71,.1)', light: 'rgba(191,135,0,.08)' },
  emeraldSurface: { dark: 'rgba(45,212,168,.08)', light: 'rgba(13,147,115,.06)' },
  coralSurface: { dark: 'rgba(249,112,102,.08)', light: 'rgba(207,34,46,.06)' },
  amberSurface: { dark: 'rgba(251,191,36,.08)', light: 'rgba(202,138,4,.06)' },
  purpleSurface: { dark: 'rgba(167,139,250,.08)', light: 'rgba(124,58,237,.06)' },

  // Glass effect
  glass: { dark: 'rgba(15,29,50,.65)', light: 'rgba(255,255,255,.7)' },
  glassBorder: { dark: 'rgba(0,168,199,.12)', light: 'rgba(0,44,119,.08)' },
  glassBlur: { dark: 'blur(16px)', light: 'blur(12px)' },
} as const;

export const typography = {
  fontFamily: {
    body: "'DM Sans', sans-serif",
    display: "'Playfair Display', Georgia, serif",
  },
  fontSize: {
    pageTitle: '22px',
    sectionTitle: '15px',
    cardTitle: '12px',
    kpiNumber: '28px',
    modalBigNum: '30px',
    tableVarNum: '11px',
    body: '13px',
    tableText: '11px',
    label: '10px',
    sectionLabel: '8px',
    badge: '9px',
    micro: '7px',
  },
  fontWeight: {
    regular: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
    heavy: 800,
  },
  lineHeight: {
    tight: '1.2',
    snug: '1.3',
    normal: '1.4',
    relaxed: '1.5',
    loose: '1.6',
  },
  letterSpacing: {
    sectionLabel: '1.2px',
    badge: '0.2px',
    subtitle: '2.5px',
  },
} as const;

export const spacing = {
  pagepadding: '20px 24px',
  pagePaddingX: '24px',
  pagePaddingY: '20px',
  cardPadding: '14px 16px',
  cardPaddingX: '16px',
  cardPaddingY: '14px',
  cardRadius: '14px',
  cardGap: '10px',
  sectionGap: '22px',
  buttonPadding: '5px 12px',
  buttonPaddingPrimary: '5px 14px',
  buttonRadius: '6px',
  pillRadius: '16px',
  badgeRadius: '10px',
  sidebarWidth: '210px',
  headerHeight1: '58px',
  headerHeight2: '40px',
  modalWidth: '500px',
  maxContentWidth: '1300px',
} as const;

export const animation = {
  fadeUp: {
    duration: '0.45s',
    easing: 'cubic-bezier(.22,1,.36,1)',
    staggerMs: 50,
    keyframes: { from: { opacity: 0, transform: 'translateY(16px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
  },
  slideIn: {
    duration: '0.25s',
    easing: 'cubic-bezier(.22,1,.36,1)',
    keyframes: { from: { transform: 'translateX(100%)' }, to: { transform: 'translateX(0)' } },
  },
  fadeIn: {
    duration: '0.2s',
    easing: 'ease',
    keyframes: { from: { opacity: 0 }, to: { opacity: 1 } },
  },
  pulse: {
    duration: '2s',
    easing: 'ease',
    infinite: true,
    keyframes: { '0%, 100%': { opacity: 1 }, '50%': { opacity: 0.4 } },
  },
  expandIn: {
    duration: '0.3s',
    easing: 'cubic-bezier(.22,1,.36,1)',
    keyframes: { from: { maxHeight: '0', opacity: 0 }, to: { maxHeight: '600px', opacity: 1 } },
  },
  blink: {
    duration: '0.8s',
    easing: 'ease',
    infinite: true,
    keyframes: { '0%, 100%': { opacity: 1 }, '50%': { opacity: 0 } },
  },
  slideDown: {
    duration: '0.2s',
    easing: 'ease',
    keyframes: { from: { opacity: 0, transform: 'translateY(-8px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
  },
  glow: {
    duration: '3s',
    easing: 'ease',
    infinite: true,
    keyframes: { '0%, 100%': { filter: 'drop-shadow(0 0 8px rgba(0,168,199,.4))' }, '50%': { filter: 'drop-shadow(0 0 16px rgba(0,168,199,.6))' } },
  },
  headerGrad: {
    duration: '8s',
    easing: 'ease',
    infinite: true,
    keyframes: { '0%': { backgroundPosition: '0% 50%' }, '50%': { backgroundPosition: '100% 50%' }, '100%': { backgroundPosition: '0% 50%' } },
  },
  confetti: {
    duration: '0.8s',
    easing: 'ease-out',
    keyframes: { '0%': { transform: 'translateY(0) rotate(0)', opacity: 1 }, '100%': { transform: 'translateY(-60px) rotate(720deg)', opacity: 0 } },
  },
  borderPulse: {
    duration: '2s',
    easing: 'ease',
    infinite: true,
    keyframes: { '0%, 100%': { opacity: 0.6 }, '50%': { opacity: 1 } },
  },
  breathe: {
    duration: '1.5s',
    easing: 'ease',
    infinite: true,
    keyframes: { '0%, 100%': { boxShadow: '0 0 0 rgba(0,168,199,.4)' }, '50%': { boxShadow: '0 0 6px rgba(0,168,199,.6)' } },
  },
  typingBounce: {
    duration: '1.2s',
    easing: 'ease',
    infinite: true,
    keyframes: { '0%, 100%': { transform: 'translateY(0)' }, '50%': { transform: 'translateY(-4px)' } },
  },
  barSlide: {
    duration: '0.5s',
    easing: 'cubic-bezier(.22,1,.36,1)',
    staggerMs: 100,
    keyframes: { from: { width: '0' }, to: { width: 'var(--bar-w)' } },
  },
  shimmer: {
    duration: '2s',
    easing: 'linear',
    infinite: true,
    keyframes: { from: { backgroundPosition: '-200% 0' }, to: { backgroundPosition: '200% 0' } },
  },
  spring: { easing: 'cubic-bezier(.34,1.56,.64,1)' },
  transition: { duration: '0.15s', easing: 'ease' },
} as const;

export const glassmorphism = {
  dark: {
    background: 'rgba(15,29,50,.65)',
    backdropFilter: 'blur(16px)',
    border: '1px solid rgba(0,168,199,.12)',
    borderRadius: '14px',
    hoverBorderColor: 'rgba(0,168,199,.2)',
  },
  light: {
    background: 'rgba(255,255,255,.7)',
    backdropFilter: 'blur(12px)',
    border: '1px solid rgba(0,44,119,.08)',
    borderRadius: '14px',
    hoverBorderColor: 'rgba(0,44,119,.15)',
  },
  gradientStripe: {
    background: 'linear-gradient(90deg, #002C77, #00A8C7)',
    height: '2px',
    opacity: 0.6,
  },
} as const;

export const gradients = {
  brand: 'linear-gradient(135deg, #002C77, #00A8C7)',
  header: 'linear-gradient(135deg, #002C77, #001A4D, #002C77)',
  stripe: 'linear-gradient(90deg, #002C77, #00A8C7)',
  button: 'linear-gradient(135deg, #002C77, #00A8C7)',
  activeTab: 'linear-gradient(135deg, #00A8C7, #016D9E)',
  background: {
    dark: `radial-gradient(ellipse at 20% 50%, rgba(0,44,119,.15), transparent 60%),
           radial-gradient(ellipse at 80% 20%, rgba(0,168,199,.08), transparent 50%),
           #030B1A`,
    light: `radial-gradient(ellipse at 20% 50%, rgba(0,44,119,.06), transparent 60%),
            radial-gradient(ellipse at 80% 20%, rgba(0,168,199,.04), transparent 50%),
            #F4F7FC`,
  },
} as const;

export const shadows = {
  card: '0 2px 8px rgba(0,0,0,.08)',
  cardHover: '0 8px 24px rgba(0,0,0,.12)',
  button: '0 2px 8px rgba(0,168,199,.2)',
  buttonHover: '0 6px 20px rgba(0,168,199,.3)',
  modal: '0 16px 48px rgba(0,0,0,.25)',
  paper: '0 8px 40px rgba(0,0,0,.15)',
  glow: '0 0 16px rgba(0,168,199,.3)',
} as const;

export const breakpoints = {
  mobile: '700px',
  tablet: '1100px',
  desktop: '1300px',
} as const;

// Persona configuration
export const personas = {
  analyst: { label: 'FP&A Analyst', icon: '\u25A6', narrativeLevel: 'detail' },
  director: { label: 'FP&A Director', icon: '\u25C9', narrativeLevel: 'midlevel' },
  cfo: { label: 'CFO', icon: '\u25C8', narrativeLevel: 'summary' },
  bu: { label: 'BU Leader', icon: '\u25A3', narrativeLevel: 'midlevel', homeBU: 'Marsh' },
} as const;

// Business units (2026 rebrand)
export const businessUnits = ['Marsh', 'Mercer', 'Marsh Re', 'Oliver Wyman', 'Marsh Corporate'] as const;

// Status styling
export const statusStyles = {
  draft: { label: 'AI Draft', bg: 'rgba(255,255,255,.05)', color: 'var(--tx-tertiary)' },
  reviewed: { label: 'Reviewed', bg: 'var(--gold-surface)', color: 'var(--gold)' },
  approved: { label: 'Approved', bg: 'var(--emerald-surface)', color: 'var(--emerald)' },
  autoclosed: { label: 'Auto-closed', bg: 'var(--purple-surface)', color: 'var(--purple)' },
} as const;

// Type styling
export const typeStyles = {
  material: { color: 'var(--coral)' },
  netted: { color: 'var(--purple)' },
  trending: { color: 'var(--amber)' },
} as const;
