import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans, IBM_Plex_Sans_Devanagari } from "next/font/google";
import { Providers } from "@/components/Providers";
import { AppShell } from "@/components/shell/AppShell";
import "./globals.css";

const plexSans = IBM_Plex_Sans({
  variable: "--font-plex-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});
const plexDeva = IBM_Plex_Sans_Devanagari({
  variable: "--font-plex-deva",
  subsets: ["devanagari"],
  weight: ["400", "500", "600"],
});
const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: { default: "FinSight", template: "%s · FinSight" },
  description:
    "FinSight reads an IPO's offer document, pulls out the numbers that matter, and shows the exact page each one came from.",
};

// Runs before first paint so there is no flash of the wrong theme.
const THEME_SCRIPT = `try{var s=JSON.parse(localStorage.getItem("fs_ui")||"null");var t=s&&s.state&&s.state.theme;if(!t){t=matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"}document.documentElement.dataset.theme=t;var l=s&&s.state&&s.state.lang;if(l==="hi")document.documentElement.lang="hi"}catch(e){}`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      data-theme="light"
      suppressHydrationWarning
      className={`${plexSans.variable} ${plexDeva.variable} ${plexMono.variable} h-full`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="flex min-h-full flex-col">
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
