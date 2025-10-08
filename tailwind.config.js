/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: ["./app/templates/**/*.html"],
  theme: {
    extend: {
      screens: {
        'xs': '475px',
      },
    },
  },
  plugins: [],
}