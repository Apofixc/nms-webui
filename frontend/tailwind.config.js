/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Outfit', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        surface: {
          900: '#12151a',
          850: '#1a1d24',
          800: '#22262e',
          750: '#2a2f3a',
          700: '#343b48',
        },
        accent: {
          DEFAULT: '#22d3ee',
          muted: '#0891b2',
          glow: 'rgba(34, 211, 238, 0.15)',
        },
        success: '#34d399',
        warning: '#fbbf24',
        danger: '#f87171',
      },
      animation: {
        'pulse-soft': 'pulse-soft 2s ease-in-out infinite',
        'fade-in': 'fade-in 0.3s ease-out',
      },
      keyframes: {
        'pulse-soft': {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.7 },
        },
        'fade-in': {
          '0%': { opacity: 0, transform: 'translateY(4px)' },
          '100%': { opacity: 1, transform: 'translateY(0)' },
        },
      },
      boxShadow: {
        'glow': '0 0 20px -5px rgba(34, 211, 238, 0.3)',
        'card': '0 4px 24px -4px rgba(0,0,0,0.4)',
      },
    },
  },
  plugins: [],
}
