
import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "AEGIS | Intelligence Workspace",
    template: "%s | AEGIS",
  },
  description:
    "AEGIS is an intelligent workspace for task execution, tool orchestration, memory, and adaptive research.",
  applicationName: "AEGIS",
  keywords: [
    "AEGIS",
    "AI Agent",
    "Intelligent Workspace",
    "Task Automation",
    "Tool Orchestration",
    "Adaptive Learning",
  ],
  authors: [{ name: "Asad Yar" }],
  openGraph: {
    title: "AEGIS | Intelligence Workspace",
    description:
      "An intelligent workspace for task execution, memory, and adaptive research.",
    siteName: "AEGIS",
    type: "website",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#f8f7fc",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
