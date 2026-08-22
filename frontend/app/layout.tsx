import type React from "react"
import type { Metadata } from "next"
import { Amiri, Cormorant_Garamond, Inter, Spectral } from "next/font/google"
import { Analytics } from "@vercel/analytics/next"
import "./globals.css"

// Display face for the title and headings: high-contrast, calligraphic feel.
const cormorant = Cormorant_Garamond({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-cormorant",
  display: "swap",
})

// Reading face for answers. A serif signals scholarly prose rather than chatbot output.
const spectral = Spectral({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-spectral",
  display: "swap",
})

// UI chrome stays sans for legibility at small sizes.
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
})

// Arabic passages (the greeting, quoted text) need a proper Arabic face.
const amiri = Amiri({
  subsets: ["arabic"],
  weight: ["400", "700"],
  variable: "--font-amiri",
  display: "swap",
})

export const metadata: Metadata = {
  title: "Sistani Jurisprudence Assistant",
  description:
    "Ask questions on Islamic jurisprudence, answered from the rulings of Ayatullah al-Sistani with exact citations.",
  icons: {
    icon: [{ url: "/icon.jpg" }],
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${spectral.variable} ${cormorant.variable} ${amiri.variable}`}
      suppressHydrationWarning
    >
      <body className="font-sans antialiased">
        {children}
        <Analytics />
      </body>
    </html>
  )
}
