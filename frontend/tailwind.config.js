/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: '#080B11',
        surface: '#0F1523',
        'surface-elevated': '#161F33',
        'surface-hover': '#1D2842',
        border: '#1E293B',
        'border-strong': '#334155',
        'border-subtle': '#151D2C',

        fg: {
          DEFAULT: '#F8FAFC',
          secondary: '#94A3B8',
          tertiary: '#64748B',
          muted: '#475569',
        },

        /**
         * Risk band accents:
         * - CRITICAL uses a light foreground on a deep red field with animated pulse edge.
         * - UNCERTAIN uses violet with dashed border and diagonal hatch.
         */
        band: {
          low: '#10B981',
          'low-glow': 'rgba(16, 185, 129, 0.15)',
          medium: '#F59E0B',
          'medium-glow': 'rgba(245, 158, 11, 0.15)',
          high: '#EF4444',
          'high-glow': 'rgba(239, 68, 68, 0.15)',
          critical: '#FCA5A5',
          'critical-field': '#7F1D1D',
          'critical-edge': '#EF4444',
          'critical-glow': 'rgba(239, 68, 68, 0.25)',
          uncertain: '#A78BFA',
          'uncertain-glow': 'rgba(167, 139, 250, 0.15)',
        },

        accent: {
          DEFAULT: '#6366F1',
          hover: '#4F46E5',
          light: '#818CF8',
          glow: 'rgba(99, 102, 241, 0.15)',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        micro: ['0.625rem', { lineHeight: '0.875rem', letterSpacing: '0.08em' }],
        mini: ['0.6875rem', { lineHeight: '0.9375rem', letterSpacing: '0.04em' }],
      },
      animation: {
        'pulse-edge': 'pulse-edge 2s ease-in-out infinite',
        'pulse-dot': 'pulse-dot 2s ease-in-out infinite',
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
      },
    },
  },
  plugins: [],
};
