/** @type {import('tailwindcss').Config} */
export default {
    darkMode: 'class',
    content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
    theme: {
        extend: {
            fontFamily: {
                sans: ['Outfit', 'system-ui', 'sans-serif'],
                mono: ['JetBrains Mono', 'monospace'],
            },
            colors: {
                surface: {
                    900: 'rgb(var(--color-surface-900) / <alpha-value>)',
                    850: 'rgb(var(--color-surface-850) / <alpha-value>)',
                    800: 'rgb(var(--color-surface-800) / <alpha-value>)',
                    750: 'rgb(var(--color-surface-750) / <alpha-value>)',
                    700: 'rgb(var(--color-surface-700) / <alpha-value>)',
                    dim: 'rgb(var(--color-surface-dim) / <alpha-value>)',
                    bright: 'rgb(var(--color-surface-bright) / <alpha-value>)',
                    'container-lowest': 'rgb(var(--color-surface-container-lowest) / <alpha-value>)',
                    'container-low': 'rgb(var(--color-surface-container-low) / <alpha-value>)',
                    container: 'rgb(var(--color-surface-container) / <alpha-value>)',
                    'container-high': 'rgb(var(--color-surface-container-high) / <alpha-value>)',
                    'container-highest': 'rgb(var(--color-surface-container-highest) / <alpha-value>)',
                    variant: 'rgb(var(--color-surface-variant) / <alpha-value>)',
                },
                'on-surface': 'rgb(var(--color-on-surface) / <alpha-value>)',
                'on-surface-variant': 'rgb(var(--color-on-surface-variant) / <alpha-value>)',
                background: 'rgb(var(--color-background) / <alpha-value>)',
                'on-background': 'rgb(var(--color-on-background) / <alpha-value>)',
                primary: {
                    DEFAULT: 'rgb(var(--color-primary) / <alpha-value>)',
                    container: 'rgb(var(--color-primary-container) / <alpha-value>)',
                },
                'on-primary': 'rgb(var(--color-on-primary) / <alpha-value>)',
                'on-primary-container': 'rgb(var(--color-on-primary-container) / <alpha-value>)',
                secondary: {
                    DEFAULT: 'rgb(var(--color-secondary) / <alpha-value>)',
                    container: 'rgb(var(--color-secondary-container) / <alpha-value>)',
                },
                'on-secondary': 'rgb(var(--color-on-secondary) / <alpha-value>)',
                'on-secondary-container': 'rgb(var(--color-on-secondary-container) / <alpha-value>)',
                tertiary: {
                    DEFAULT: 'rgb(var(--color-tertiary) / <alpha-value>)',
                    container: 'rgb(var(--color-tertiary-container) / <alpha-value>)',
                },
                outline: 'rgb(var(--color-outline) / <alpha-value>)',
                'outline-variant': 'rgb(var(--color-outline-variant) / <alpha-value>)',
                accent: {
                    DEFAULT: 'rgb(var(--color-accent) / <alpha-value>)',
                    muted: 'rgb(var(--color-accent-muted) / <alpha-value>)',
                    glow: 'var(--color-accent-glow)',
                },
                success: 'rgb(var(--color-success) / <alpha-value>)',
                warning: 'rgb(var(--color-warning) / <alpha-value>)',
                danger: 'rgb(var(--color-danger) / <alpha-value>)',
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
