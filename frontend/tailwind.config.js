/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Core background and surface hierarchy (SignalIQ Paper & Ink)
        background: '#FBFBFA', // SignalIQ off-white paper canvas
        'surface-base': '#FBFBFA',
        surface: '#FFFFFF', // Clean white cards/sections
        'surface-elevated': '#F4F4F2',
        'surface-hover': '#EFEFEA',
        'surface-subtle': '#F8F8F6',

        // Infrastructure Grayscale Borders
        border: '#EBEBEA', // SignalIQ hairline border
        'border-strong': '#DCDCD9',
        'border-subtle': '#F4F4F2',
        'border-hairline': 'rgba(0, 0, 0, 0.06)',

        // Editorial Text Hierarchy
        fg: {
          DEFAULT: '#0A0A0A',
          primary: '#0A0A0A', // Stark Ink
          secondary: '#666666', // SignalIQ secondary neutral
          tertiary: '#888888', // SignalIQ tertiary neutral
          muted: '#A8A8A5',
          subtle: '#DCDCD9',
          inverse: '#FFFFFF',
        },

        /**
         * Semantic Accent States ONLY:
         * Adjusted for legibility on light mode
         */
        state: {
          safe: '#059669', // Emerald 600
          'safe-glow': 'rgba(5, 150, 105, 0.08)',
          medium: '#D97706', // Amber 600
          'medium-glow': 'rgba(217, 119, 6, 0.08)',
          high: '#DC2626', // Red 600
          'high-glow': 'rgba(220, 38, 38, 0.08)',
          critical: '#B91C1C', // Red 700
          'critical-bg': '#FEF2F2', // Red 50
          'critical-glow': 'rgba(185, 28, 28, 0.12)',
          uncertain: '#7C3AED', // Violet 600
          'uncertain-glow': 'rgba(124, 58, 237, 0.08)',
          processing: '#0284C7', // Sky 600
          'processing-glow': 'rgba(2, 132, 199, 0.08)',
          disconnected: '#94A3B8', // Slate 400
        },

        // Backward-compatible risk band keys
        band: {
          low: '#059669',
          'low-glow': 'rgba(5, 150, 105, 0.08)',
          medium: '#D97706',
          'medium-glow': 'rgba(217, 119, 6, 0.08)',
          high: '#DC2626',
          'high-glow': 'rgba(220, 38, 38, 0.08)',
          critical: '#B91C1C',
          'critical-field': '#FEF2F2',
          'critical-edge': '#DC2626',
          'critical-glow': 'rgba(185, 28, 28, 0.12)',
          uncertain: '#7C3AED',
          'uncertain-glow': 'rgba(124, 58, 237, 0.08)',
        },

        accent: {
          DEFAULT: '#000000', // Primary accent is now high contrast black
          hover: '#27272A',
          light: '#52525B',
          glow: 'rgba(0, 0, 0, 0.05)',
        },
      },
      fontFamily: {
        mono: ['-apple-system', 'BlinkMacSystemFont', '"SF Pro Text"', '"SF Pro Display"', '"SF Pro"', '"Plus Jakarta Sans"', '"Inter"', '"Helvetica Neue"', 'Helvetica', 'Arial', 'sans-serif'],
        sans: ['-apple-system', 'BlinkMacSystemFont', '"SF Pro Display"', '"SF Pro Text"', '"SF Pro"', '"Plus Jakarta Sans"', '"Inter"', '"Helvetica Neue"', 'Helvetica', 'Arial', 'sans-serif'],
        serif: ['Instrument Serif', 'Georgia', 'Cambria', 'Times New Roman', 'serif'],
      },
      fontSize: {
        // Micro & Technical Labels
        'micro-label': ['0.625rem', { lineHeight: '0.875rem', letterSpacing: '0.08em' }],
        'technical-label': ['0.6875rem', { lineHeight: '0.9375rem', letterSpacing: '0.05em' }],
        'technical-value': ['0.8125rem', { lineHeight: '1.125rem', letterSpacing: '0.02em' }],

        // Body Scale
        'body-sm': ['0.8125rem', { lineHeight: '1.25rem' }],
        body: ['0.9375rem', { lineHeight: '1.4375rem' }],
        'body-lg': ['1.0625rem', { lineHeight: '1.625rem' }],

        // Section Scale
        'section-index': ['0.75rem', { lineHeight: '1rem', letterSpacing: '0.12em' }],
        'section-title': ['1.25rem', { lineHeight: '1.625rem', letterSpacing: '-0.02em' }],

        // Editorial Display Scale
        'display-md': ['1.875rem', { lineHeight: '2.25rem', letterSpacing: '-0.03em' }],
        'display-lg': ['2.625rem', { lineHeight: '3rem', letterSpacing: '-0.04em' }],
        'display-xl': ['3.75rem', { lineHeight: '4rem', letterSpacing: '-0.05em' }],
        'display-giant': ['clamp(3rem, 7vw, 6rem)', { lineHeight: '1.02', letterSpacing: '-0.045em' }],

        // Legacy compatibility
        micro: ['0.625rem', { lineHeight: '0.875rem', letterSpacing: '0.08em' }],
        mini: ['0.6875rem', { lineHeight: '0.9375rem', letterSpacing: '0.04em' }],
      },
      animation: {
        'pulse-edge': 'pulse-edge 2s ease-in-out infinite',
        'pulse-dot': 'pulse-dot 2s ease-in-out infinite',
        'signal-sweep': 'signal-sweep 3s ease-in-out infinite',
        'fade-in': 'fade-in 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards',
      },
      keyframes: {
        'pulse-edge': {
          '0%, 100%': { borderColor: 'rgba(239, 68, 68, 0.45)', boxShadow: '0 0 15px rgba(239, 68, 68, 0.15)' },
          '50%': { borderColor: 'rgba(239, 68, 68, 0.95)', boxShadow: '0 0 25px rgba(239, 68, 68, 0.35)' },
        },
        'pulse-dot': {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.4', transform: 'scale(0.85)' },
        },
        'signal-sweep': {
          '0%': { transform: 'translateX(-100%)' },
          '50%, 100%': { transform: 'translateX(100%)' },
        },
        'fade-in': {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
};
