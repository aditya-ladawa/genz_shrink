module.exports = {
  darkMode: 'class',
  content: [
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      borderColor: {
        DEFAULT: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
      },
      colors: {
        primary: {
          DEFAULT: '#673AB7',
          dark: '#512DA8',
          light: '#D1C4E9',
        },
        accent: '#009688',
        text: {
          primary: '#212121',
          secondary: '#757575',
          white: '#FFFFFF',
        },
        divider: '#BDBDBD',
      },
      animation: {
        float: 'float 6s ease-in-out infinite',
        'fade-in': 'fadeIn 0.5s ease-in',
        'slide-up': 'slideUp 0.4s ease-out',
        'pulse-slow': 'pulse 5s infinite',
        'glass-glow': 'glassGlow 8s ease infinite alternate',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        glassGlow: {
          '0%': { 'box-shadow': '0 0 10px rgba(103, 58, 183, 0.3)' },
          '100%': { 'box-shadow': '0 0 20px rgba(103, 58, 183, 0.7)' },
        }
      },
      backdropBlur: {
        xs: '2px',
        sm: '4px',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('tailwindcss-animate'),
  ],
};
