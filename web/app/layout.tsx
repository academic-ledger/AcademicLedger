import type { Metadata } from "next";
import "./globals.css";

const favicon =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='22' fill='%23111'/%3E%3Ctext x='51' y='70' text-anchor='middle' fill='white' font-family='Georgia,serif' font-size='58'%3E%3Ctspan font-style='italic'%3Ea%3C/tspan%3E%3Ctspan%3EL%3C/tspan%3E%3C/text%3E%3C/svg%3E";

export const metadata: Metadata = {
  title: "academic Ledger — QaL",
  description:
    "Quality as a Ledger (QaL): a calibrated, continuously updated estimate of a paper's eventual standing in its field, built on the open scholarly record.",
  icons: { icon: favicon },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
