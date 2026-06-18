import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Warm cream surfaces, in the spirit of claude.ai.
        canvas: "#FAF9F5",      // main chat area
        sidebar: "#F0EEE6",     // left rail
        raised: "#FFFFFF",      // cards / input
        border: "#E5E2D6",
        ink: {
          DEFAULT: "#1F1E1C",   // primary text
          soft: "#46443E",      // secondary text
          faint: "#8A877C",     // tertiary / placeholders
        },
        clay: {
          DEFAULT: "#C2603F",   // Claude coral accent
          hover: "#AB5236",
          soft: "#EBD9CE",
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
