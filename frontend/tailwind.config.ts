import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Warm dark surfaces, in the spirit of claude.ai's dark theme.
        canvas: "#262624",      // main chat area
        sidebar: "#1C1B19",     // left rail
        raised: "#302F2C",      // cards / input
        border: "#3B3A36",
        ink: {
          DEFAULT: "#ECEAE3",   // primary text
          soft: "#BEBBB2",      // secondary text
          faint: "#8B887E",     // tertiary / placeholders
        },
        clay: {
          DEFAULT: "#C9785C",   // Claude coral accent (brightened for dark)
          hover: "#D88E72",
          soft: "#3C2D26",      // user-bubble background (light text on warm dark)
        },
      },
      fontFamily: {
        serif: ["var(--font-serif)", "Georgia", "serif"],
        sans: [
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
      },
      maxWidth: {
        chat: "48rem",
      },
    },
  },
  plugins: [],
};

export default config;
