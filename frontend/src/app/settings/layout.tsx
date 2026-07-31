import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: '系统设置 - 跨境产品资料中英对照系统',
};

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
