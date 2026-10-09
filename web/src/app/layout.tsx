import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  // latin-ext covers Kikamba's ĩ and ũ, so they render in Geist rather than a fallback font.
  subsets: ["latin", "latin-ext"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Understand Kamba — English ⇄ Kikamba translator",
  description:
    "Translate between English and Kikamba, speak Kikamba to transcribe it, and hear translations read aloud.",
};

export const viewport: Viewport = {
  // Matches the butter wash at the top of the page, so mobile browser chrome blends in.
  themeColor: "#fcf6dc",
  colorScheme: "light",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
