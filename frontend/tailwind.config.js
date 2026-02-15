/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Urbanist', 'sans-serif'],
        heading: ['Outfit', 'sans-serif'],
      },
      colors: {
        accent: "rgb(71, 208, 208)",
        dark: "#070707",
      }
    },
  },
  plugins: [],
}