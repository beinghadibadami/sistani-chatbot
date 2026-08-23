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
  metadataBase: new URL('https://al-sistani-chat.onrender.com'),
  title: "Sistani Jurisprudence Assistant | Islamic Rulings from Ayatollah Sistani",
  description:
    "Get authentic Islamic rulings from Grand Ayatollah Sistani's official sources. Ask questions about prayer, fasting, hajj, marriage, purity, and daily Islamic practices in English, Hindi, Gujarati, or Urdu.",
  keywords: [
    "Ayatollah Sistani",
    "Islamic rulings",
    "Shia fiqh",
    "Islamic jurisprudence",
    "salat prayer",
    "hajj pilgrimage",
    "wudu ablution",
    "Islamic laws",
    "Sistani fatwa",
    "namaz",
    "roza fasting",
    "halal haram",
    "tahara purity",
    "nikah marriage",
    "zakat",
  ],
  authors: [{ name: "Al-Sistani Chat" }],
  creator: "Al-Sistani Chat",
  publisher: "Al-Sistani Chat",
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://al-sistani-chat.onrender.com',
    title: 'Sistani Jurisprudence Assistant | Islamic Rulings',
    description: 'Get authentic Islamic rulings from Grand Ayatollah Sistani. Free AI-powered assistant for Shia fiqh questions.',
    siteName: 'Sistani Jurisprudence Assistant',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Sistani Jurisprudence Assistant',
    description: 'Ask Islamic law questions, get answers from Ayatollah Sistani\'s sources',
  },
  alternates: {
    canonical: 'https://al-sistani-chat.onrender.com',
  },
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
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "WebApplication",
              "name": "Sistani Jurisprudence Assistant",
              "description": "AI-powered Islamic jurisprudence assistant based on Grand Ayatollah Sistani's rulings",
              "url": "https://al-sistani-chat.onrender.com",
              "applicationCategory": "EducationalApplication",
              "operatingSystem": "All",
              "offers": {
                "@type": "Offer",
                "price": "0",
                "priceCurrency": "USD"
              },
              "author": {
                "@type": "Organization",
                "name": "Al-Sistani Chat"
              },
              "inLanguage": ["en", "hi", "gu", "ur"]
            })
          }}
        />
      </head>
      <body className="font-sans antialiased">
        {children}
        <Analytics />
      </body>
    </html>
  )
}
