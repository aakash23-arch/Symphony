/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: '#0B0F19',
        surface: '#111827',
        'surface-elevated': '#161E2E',
        border: '#232B3B',
        'border-strong': '#374151',

        fg: {
          DEFAULT: '#F3F4F6',
          secondary: '#9CA3AF',
          tertiary: '#6B7280',
        },

        /**
         * Risk band accents. Two deliberate departures from the obvious choice:
         *
         *  - `critical` is a LIGHT foreground on a deep field. A darker red than
         *    `high` would make the worst band read as less urgent than the one
         *    below it.
         *  - `uncertain` is violet, not grey. Grey is the universal "inactive"
         *    colour and would read as "nothing to see here" - exactly the
         *    misreading this band exists to prevent.
         */
        band: {
          low: '#34D399',
          medium: '#FBBF24',
          high: '#F87171',
          critical: '#FCA5A5',
          'critical-field': '#7F1D1D',
          'critical-edge': '#EF4444',
          uncertain: '#C4B5FD',
        },

        accent: '#818CF8',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        micro: ['0.625rem', { lineHeight: '0.875rem', letterSpacing: '0.08em' }],
      },
      animation: {
        'pulse-edge': 'pulse-edge 2s ease-in-out infinite',
        'pulse-dot': 'pulse-dot 2s ease-in-out infinite',
      },
      keyframes: {
        'pulse-edge': {
          '0%, 100%': { borderColor: 'rgba(239, 68, 68, 0.55)' },
          '50%': { borderColor: 'rgba(239, 68, 68, 1)' },
        },
        'pulse-dot': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.35' },
        },
      },
    },
  },
  plugins: [],
};
