import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#000000",
        surface: "#12121E",
        "surface-card": "#181828",
        border: "#252538",
        primary: {
          DEFAULT: "#41AA6C",
          hover: "#34925b",
          light: "rgba(65, 170, 108, 0.15)",
        },
        muted: "#94A3B8",
        foreground: "#F8FAFC",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
