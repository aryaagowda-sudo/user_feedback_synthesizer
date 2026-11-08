/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        canvas: '#080B11',
        surface: {
          DEFAULT: '#0E131F',
          raised: '#141A29',
          hover: '#1A2234',
          subtle: '#0B0F17',
        },
        border: {
          subtle: 'rgba(255, 255, 255, 0.06)',
          muted: '#1E2638',
          focus: '#3B4863',
        },
        brand: {
          violet: '#7C3AED',
          indigo: '#6366F1',
          cyan: '#06B6D4',
          emerald: '#10B981',
          rose: '#F43F5E',
          amber: '#F59E0B'
        }
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'Inter', 'system-ui', 'sans-serif'],
        body: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'card': '0 1px 3px 0 rgba(0, 0, 0, 0.4), 0 1px 2px -1px rgba(0, 0, 0, 0.4)',
        'card-hover': '0 4px 6px -1px rgba(0, 0, 0, 0.5), 0 2px 4px -2px rgba(0, 0, 0, 0.5)',
        'modal': '0 20px 25px -5px rgba(0, 0, 0, 0.7), 0 8px 10px -6px rgba(0, 0, 0, 0.7)',
        'glow-subtle': '0 0 15px -3px rgba(124, 58, 237, 0.15)',
      }
    },
  },
  plugins: [],
}
