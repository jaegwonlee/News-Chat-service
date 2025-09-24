import { AuthProvider } from "../context/AuthContext";
import "./globals.css";

export const metadata = {
  title: "NewsRound1",
  description: "News-based real-time chat",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
