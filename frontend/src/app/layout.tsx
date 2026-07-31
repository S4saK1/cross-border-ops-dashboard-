import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: '跨境产品资料中英对照系统',
  description: '不是翻译工具，是跨境卖家的产品资料一致性管理系统',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
