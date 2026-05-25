import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { SwRegister } from "@/components/sw-register";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Yoel",
  description: "Mesin editorial konten horor. Review, approve, skrip.",
  manifest: "/manifest.webmanifest",
  icons: { icon: "/favicon.svg", apple: "/icon.svg" },
  appleWebApp: { capable: true, title: "Yoel", statusBarStyle: "black-translucent" },
};

export const viewport: Viewport = {
  themeColor: "#0a0a0a",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="id"
      className={`${geistSans.variable} ${geistMono.variable} h-full`}
      suppressHydrationWarning
    >
      <body className="min-h-dvh">
        <script
          dangerouslySetInnerHTML={{
            __html: `try{if(localStorage.getItem('yoel_theme')==='light')document.documentElement.classList.add('light')}catch(e){}`,
          }}
        />
        {children}
        <SwRegister />
      </body>
    </html>
  );
}
