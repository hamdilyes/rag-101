import type { Metadata } from "next";
import { Newsreader } from "next/font/google";
import "./globals.css";

// Serif used for the greeting and headings, echoing claude.ai's display face.
const serif = Newsreader({
  subsets: ["latin"],
  weight: ["400", "500"],
  style: ["normal", "italic"],
  variable: "--font-serif",
  display: "swap",
});

export const metadata: Metadata = {
  title: "RAG101",
  description: "Chat with your document corpus",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={serif.variable}>
      <body>{children}</body>
    </html>
  );
}
