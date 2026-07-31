'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getToken } from '@/lib/api';
import Sidebar from '@/components/Sidebar';
import { Package, BookOpen, AlertTriangle, CheckCircle } from 'lucide-react';

export default function Dashboard() {
  const router = useRouter();
  const [stats, setStats] = useState({ products: 0, terms: 0, errors: 0, passed: 0 });

  useEffect(() => {
    if (!getToken()) { router.push('/login'); return; }
    fetch('/api/v1/products?page_size=1', { headers: { Authorization: `Bearer ${getToken()}` } })
      .then(r => r.json()).then(d => setStats(s => ({ ...s, products: d.total || 0 }))).catch(() => {});
    fetch('/api/v1/terms?page_size=1', { headers: { Authorization: `Bearer ${getToken()}` } })
      .then(r => r.json()).then(d => setStats(s => ({ ...s, terms: d.total || 0 }))).catch(() => {});
  }, []);

  const cards = [
    { label: '产品总数', value: stats.products, icon: Package, color: 'bg-blue-500' },
    { label: '术语词典', value: stats.terms, icon: BookOpen, color: 'bg-green-500' },
    { label: '一致性问题', value: stats.errors, icon: AlertTriangle, color: 'bg-yellow-500' },
    { label: '已通过检测', value: stats.passed, icon: CheckCircle, color: 'bg-emerald-500' },
  ];

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <h1 className="text-2xl font-bold mb-6">仪表盘</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {cards.map(card => {
            const Icon = card.icon;
            return (
              <div key={card.label} className="bg-white rounded-xl shadow-sm p-6 flex items-center gap-4">
                <div className={`${card.color} p-3 rounded-lg text-white`}><Icon size={24} /></div>
                <div>
                  <p className="text-sm text-gray-500">{card.label}</p>
                  <p className="text-2xl font-bold">{card.value}</p>
                </div>
              </div>
            );
          })}
        </div>
      </main>
    </div>
  );
}
