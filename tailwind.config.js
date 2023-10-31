/** @type {import('tailwindcss').Config} */
const defaultTheme = require('tailwindcss/defaultTheme')
module.exports = {
  content: ["./templates/*.html", "./static/css/*.css"],
  theme: {
    extend: {
      ...defaultTheme
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
  safelist: [
    'invisible',
  ]
}