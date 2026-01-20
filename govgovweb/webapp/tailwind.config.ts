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
        background: "var(--background)",
        foreground: "var(--foreground)",
        govgov: {
          // Exact colors from the logo
          'cyan-light': '#6DD4E8',     // Top right - light cyan/turquoise
          'blue-main': '#2FA9DB',      // Top left - medium blue
          'blue-deep': '#0077C8',      // Bottom right - deep blue
          'navy-dark': '#1A1F4D',      // Bottom left - dark navy
        },
      },
      fontFamily: {
        inter: ["var(--font-inter)", "sans-serif"],
        jakarta: ["var(--font-plus-jakarta-sans)", "sans-serif"],
        noto: ["var(--font-noto-sans-jp)", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
