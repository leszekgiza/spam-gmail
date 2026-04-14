export const metadata = {
  title: 'SPAM Gmail — Poranny przegląd',
  description: 'AI Inbox Cleaner',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pl">
      <body style={{ fontFamily: 'system-ui, sans-serif', margin: 0, padding: 24 }}>
        {children}
      </body>
    </html>
  );
}
