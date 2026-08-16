/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        vault: {
          bg: "#0b0f14",
          panel: "#121820",
          border: "#232b36",
          accent: "#22d3ee",
          danger: "#f87171",
          success: "#34d399",
          warn: "#fbbf24",
        },
      },
    },
  },
  plugins: [],
};
