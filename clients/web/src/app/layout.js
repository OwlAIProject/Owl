
import { Inter } from "next/font/google";
import "./globals.css";
import CaptureComponent from "./components/CaptureComponent";

const inter = Inter({ subsets: ["latin"] });

export const metadata = {
  title: "Owl",
  description: "Owl",
};

export default function RootLayout({ children }) {

  return (
    <html lang="en">
      <body className={inter.className}>
         <CaptureComponent />
        {children}
        </body>
    </html>
  );
}
