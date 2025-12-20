/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./**/*.py"
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          bg: '#0d0d0d',
          card: '#1a1a1a',
          header: '#111',
          border: '#333'
        },
        primary: {
          blue: '#4a90e2',
          'blue-hover': '#357ae8'
        }
      },
      animation: {
        'fade-in': 'fadeIn 1.2s ease',
        'slide-in': 'slideIn 1s ease',
        'fall-return': 'fallAndReturn 3s infinite ease-in-out',
        'simple-fall': 'simpleFall 5s infinite linear'
      },
      keyframes: {
        fadeIn: {
          'from': { opacity: '0', transform: 'translateY(20px)' },
          'to': { opacity: '1', transform: 'translateY(0)' }
        },
        slideIn: {
          'from': { opacity: '0', transform: 'translateX(-40px)' },
          'to': { opacity: '1', transform: 'translateX(0)' }
        },
        fallAndReturn: {
          '0%, 100%': { transform: 'translateY(-50px) rotateX(90deg)', opacity: '0' },
          '20%, 60%': { transform: 'translateY(0) rotateX(0)', opacity: '1' },
          '80%': { transform: 'translateY(30px) rotateX(-90deg)', opacity: '0' }
        },
        simpleFall: {
          '0%': { transform: 'translateY(-100px)', opacity: '0' },
          '25%': { transform: 'translateY(0)', opacity: '1' },
          '50%': { transform: 'translateY(0)', opacity: '1' },
          '75%': { transform: 'translateY(100px)', opacity: '0' },
          '100%': { transform: 'translateY(-100px)', opacity: '0' }
        }
      }
    }
  },
  plugins: []
}