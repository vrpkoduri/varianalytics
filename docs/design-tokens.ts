// Marsh Vantage — Design Tokens
// Generated from FPA_Variance_Agent_UI.html prototype (136KB, 989 lines)
// Drop this into frontend/src/theme/tokens.ts

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
  amber: { dark: '#FBBF24', light: '#9A6700' },
  purple: { dark: '#A78BFA', light: '#8250DF' },

  // Semantic surfaces (8% opacity tints)
  goldSurface: { dark: 'rgba(227,165,71,.1)', light: 'rgba(191,135,0,.06)' },
  emeraldSurface: { dark: 'rgba(45,212,168,.08)', light: 'rgba(13,147,115,.06)' },
  coralSurface: { dark: 'rgba(249,112,102,.08)', light: 'rgba(207,34,46,.06)' },
  amberSurface: { dark: 'rgba(251,191,36,.08)', light: 'rgba(154,103,0,.06)' },
  purpleSurface: { dark: 'rgba(167,139,250,.08)', light: 'rgba(130,80,223,.06)' },

  // Glass effect
  glass: { dark: 'rgba(15,29,50,.65)', light: 'rgba(255,255,255,.7)' },
  glassBorder: { dark: 'rgba(0,168,199,.12)', light: 'rgba(0,44,119,.08)' },
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
} as const;

export const spacing = {
  pagepadding: '20px 24px',
  cardPadding: '14px 16px',
  cardRadius: '14px',
  cardGap: '10px',
  sectionGap: '22px',
  buttonPadding: '5px 12px',
  buttonPaddingPrimary: '5px 14px',
  buttonRadius: '6px',
  pillRadius: '16px',
  badgeRadius: '10px',
} as const;

export const animation = {
  fadeUp: { duration: '0.45s', easing: 'cubic-bezier(.22,1,.36,1)', staggerMs: 50 },
  slideIn: { duration: '0.25s', easing: 'cubic-bezier(.22,1,.36,1)' },
  fadeIn: { duration: '0.2s', easing: 'ease' },
  expand: { duration: '0.3s', easing: 'cubic-bezier(.22,1,.36,1)' },
  barSlide: { duration: '0.5s', easing: 'cubic-bezier(.22,1,.36,1)', staggerMs: 100 },
  spring: { easing: 'cubic-bezier(.34,1.56,.64,1)' },
  transition: { duration: '0.15s', easing: 'ease' },
} as const;

export const gradients = {
  brand: 'linear-gradient(135deg, #002C77, #00A8C7)',
  header: 'linear-gradient(135deg, #002C77, #001A4D, #002C77)',
  stripe: 'linear-gradient(90deg, #002C77, #00A8C7)',
  button: 'linear-gradient(135deg, #002C77, #00A8C7)',
} as const;

export const shadows = {
  card: '0 8px 24px rgba(0,0,0,.12)',
  button: '0 2px 8px rgba(0,168,199,.2)',
  buttonHover: '0 6px 20px rgba(0,168,199,.3)',
  modal: '0 8px 40px rgba(0,0,0,.4)',
  paper: '0 8px 40px rgba(0,0,0,.4), 0 0 0 1px rgba(255,255,255,.05)',
} as const;

export const breakpoints = {
  tablet: '1100px',
  mobile: '700px',
} as const;

// Persona configuration
export const personas = {
  analyst: { label: 'FP&A Analyst', icon: '▦', narrativeLevel: 'detail' },
  director: { label: 'FP&A Director', icon: '◉', narrativeLevel: 'midlevel' },
  cfo: { label: 'CFO', icon: '◈', narrativeLevel: 'summary' },
  bu: { label: 'BU Leader', icon: '▣', narrativeLevel: 'midlevel', homeBU: 'Marsh' },
} as const;

// Business units (2026 rebrand)
export const businessUnits = ['Marsh', 'Mercer', 'Marsh Re', 'Oliver Wyman', 'Marsh Corporate'] as const;

// Status styling
export const statusStyles = {
  draft: { label: 'AI Draft', bg: 'rgba(255,255,255,.05)', color: 'var(--t3)' },
  reviewed: { label: 'Reviewed', bg: 'var(--gdS)', color: 'var(--gd)' },
  approved: { label: 'Approved', bg: 'var(--emS)', color: 'var(--em)' },
  autoclosed: { label: 'Auto-closed', bg: 'var(--prS)', color: 'var(--pr)' },
} as const;

// Type styling
export const typeStyles = {
  material: { color: 'var(--cr)' },
  netted: { color: 'var(--pr)' },
  trending: { color: 'var(--am)' },
} as const;
