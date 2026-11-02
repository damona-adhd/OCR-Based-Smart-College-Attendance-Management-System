/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: '#F4F5F1',
        card: '#FFFFFF',
        forest: {
          900: '#14201C',
          800: '#1C2B26',
          DEFAULT: '#243630',
          700: '#2F463E',
          600: '#465F56',
          500: '#5D7C71',
          100: '#E6ECE9',
          50: '#F0F4F2',
        },
        coral: {
          DEFAULT: '#FF685F',
          hover: '#E55850',
          light: '#FFF0EF',
        },
        cyan: {
          DEFAULT: '#55D5ED',
          light: '#EBFBFE',
        },
        status: {
          present: '#27845B',
          absent: '#D9534F',
          warning: '#E5A23C',
        },
        ink: {
          primary: '#202521',
          secondary: '#737A75',
          border: '#E4E7E1',
        },
        primary: {
          50:  '#F0F4F2',
          100: '#E6ECE9',
          200: '#C5D4CE',
          300: '#9FB6AC',
          400: '#729386',
          500: '#465F56',
          600: '#243630',
          700: '#1C2B26',
          800: '#15211D',
          900: '#0E1613',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
    },
  },
  plugins: [],
}
