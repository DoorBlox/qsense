import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Q-SENSE | Queue Sensing & Evaluation System",
  description:
    "Q-SENSE is an IoT-based cafeteria queue monitoring and analytics proof of concept.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
