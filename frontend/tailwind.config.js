/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Core background and surface hierarchy (Symphony Black & Charcoal)
        background: '#080B11',
        'surface-base': '#080B11',
        surface: '#0F1523',
        'surface-elevated': '#161F33',
        'surface-hover': '#1D2842',
        'surface-subtle': '#0B101A',

        // Infrastructure Grayscale Borders
        border: '#1E293B',
        'border-strong': '#334155',
        'border-subtle': '#151D2C',
        'border-hairline': 'rgba(255, 255, 255, 0.08)',

        // Neutral Text Hierarchy
        fg: {
          DEFAULT: '#F8FAFC',
          primary: '#F8FAFC',
          secondary: '#94A3B8',
          tertiary: '#64748B',
          muted: '#475569',
          subtle: '#334155',
          inverse: '#080B11',
        },

        // Symphony Pure Infrastructure Neutrals
        neutral: {
          950: '#06080D',
          900: '#0D111A',
          850: '#131824',
          800: '#1C2333',
          700: '#2A3449',
          600: '#414E69',
          500: '#62718E',
          400: '#8E9BB4',
          300: '#B6C1D6',
          200: '#D9E0EE',
          100: '#EDF1F7',
          50: '#F8FAFC',
        },

        /**
         * Semantic Accent States ONLY:
         * Accents strictly communicate system state and threat levels.
         */
        state: {
          safe: '#10B981',
          'safe-glow': 'rgba(16, 185, 129, 0.12)',
          medium: '#F59E0B',
          'medium-glow': 'rgba(245, 158, 11, 0.12)',
          high: '#EF4444',
          'high-glow': 'rgba(239, 68, 68, 0.12)',
          critical: '#F87171',
          'critical-bg': '#450A0A',
          'critical-glow': 'rgba(239, 68, 68, 0.25)',
          uncertain: '#A78BFA',
          'uncertain-glow': 'rgba(167, 139, 250, 0.12)',
          processing: '#38BDF8',
          'processing-glow': 'rgba(56, 189, 248, 0.12)',
          disconnected: '#64748B',
        },

        // Backward-compatible risk band keys
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
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
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
