import './globals.css';
import React from 'react';

export const metadata = {
  title: 'Blumetara AI — Admin Console',
  description: 'Manage and monitor laboratory OCRs, RAG embeddings, and active user metrics.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
