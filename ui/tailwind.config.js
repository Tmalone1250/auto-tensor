/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          bg: "#020617", // Slate-950
          success: "#10b981", // Emerald-500
          warning: "#f59e0b", // Amber-500
          danger: "#f43f5e", // Rose-500
          accent: "#334155", // Slate-700
        }
      },
      fontFamily: {
        mono: ["Fira Code", "JetBrains Mono", "monospace"],
      }
    },
  },
  plugins: [],
}
