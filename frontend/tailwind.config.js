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
                    dim: '#10131a',
                    bright: '#363941',
                    'container-lowest': '#0b0e15',
                    'container-low': '#191c22',
                    container: '#1d2027',
                    'container-high': '#272a31',
                    'container-highest': '#32353c',
                    variant: '#32353c',
                },
                'on-surface': '#e0e2ec',
                'on-surface-variant': '#bbc9cd',
                background: '#10131a',
                'on-background': '#e0e2ec',
                primary: {
                    DEFAULT: '#8aebff',
                    container: '#22d3ee',
                },
                'on-primary': '#00363e',
                'on-primary-container': '#005763',
                secondary: {
                    DEFAULT: '#c0c6d7',
                    container: '#424957',
                },
                'on-secondary': '#2a313d',
                'on-secondary-container': '#b2b8c9',
                tertiary: {
                    DEFAULT: '#61f6b9',
                    container: '#3dd99e',
                },
                outline: '#859397',
                'outline-variant': '#3c494c',
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
