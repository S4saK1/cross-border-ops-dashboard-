'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Package, BookOpen, Download, Upload, FileText, Users, LayoutDashboard, LogOut, type LucideIcon } from 'lucide-react';
import { useState, useEffect } from 'react';

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

interface SidebarProps {
  className?: string;
  userRole?: 'admin' | 'editor' | 'reviewer' | 'viewer';
}

export default function Sidebar({ className, userRole }: SidebarProps) {
  const pathname = usePathname();
  const [role, setRole] = useState<string>(userRole || 'viewer');

  useEffect(() => {
    if (!userRole && typeof window !== 'undefined') {
      try {
        const stored = localStorage.getItem('user');
        if (stored) {
          const user = JSON.parse(stored);
          if (user.role) setRole(user.role);
        }
      } catch {}
    }
  }, [userRole]);

  const filteredNavItems = navItems.filter(item => {
    if (item.href === '/settings/users' && role !== 'admin') {
      return false;
    }
    return true;
  });

  return (
    <aside className={`w-60 bg-white border-r border-gray-200 min-h-screen flex flex-col ${className || ''}`}>
      <div className="p-4 border-b border-gray-200">
        <h2 className="font-bold text-lg text-blue-600">Bilingual CMS</h2>
        <p className="text-xs text-gray-500">产品资料一致性管理</p>
      </div>
      <nav className="flex-1 p-3 space-y-1">
        {filteredNavItems.map(item => {
          const Icon = item.icon;
          const active = pathname === item.href;
          return (
            <Link key={item.href} href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition ${
                active ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-600 hover:bg-gray-100'
              }`}>
              <Icon size={18} />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="p-3 border-t border-gray-200">
        <button onClick={() => { localStorage.clear(); window.location.href = '/login'; }}
          className="flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">
          <LogOut size={18} /> 退出登录
        </button>
      </div>
    </aside>
  );
}

const navItems: NavItem[] = [
  { href: '/', label: '仪表盘', icon: LayoutDashboard },
  { href: '/products', label: '产品管理', icon: Package },
  { href: '/terms', label: '术语词典', icon: BookOpen },
  { href: '/export', label: 'CSV 导出', icon: Download },
  { href: '/products/import', label: '批量导入', icon: Upload },
  { href: '/audit', label: '审计日志', icon: FileText },
  { href: '/settings/users', label: '用户管理', icon: Users },
];
