import type { Metadata } from "next";
import "@fontsource-variable/inter";
import "./globals.css";

import { Providers } from "@/components/providers";

export const metadata: Metadata = {
  title: {
    default: "EDSS",
    template: "%s | EDSS",
  },
  description: "Executive Decision Support System for university leadership",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
