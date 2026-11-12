import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Providers } from "@/components/Providers";
import { AppShell } from "@/components/shell/AppShell";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
});

export const metadata: Metadata = {
  openGraph: {
    title: "Vidura",
    description: "Read the fine print of an IPO. Vidura finds the risks in an offer document and shows the page each one came from.",
    images: [{ url: "/images/og.webp", width: 1200, height: 630, alt: "Stacks of printed prospectuses on a desk with a city skyline at dawn behind them." }],
    type: "website",
  },
  twitter: { card: "summary_large_image", images: ["/images/og.webp"] },
  title: { default: "Vidura", template: "%s · Vidura" },
  description:
    "Read the fine print of an IPO. Vidura finds the risks in an offer document and shows the page each one came from.",
};

// Runs before first paint so there is no flash of the wrong theme.
const THEME_SCRIPT = `try{var s=JSON.parse(localStorage.getItem("vd_ui")||localStorage.getItem("fs_ui")||"null");var t=s&&s.state&&s.state.theme;if(!t){t="light"}document.documentElement.dataset.theme=t}catch(e){}`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      data-theme="light"
      suppressHydrationWarning
      className={`${inter.variable} h-full`}
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
