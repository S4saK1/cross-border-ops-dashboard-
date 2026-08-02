'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { authHeaders } from '@/lib/api';
import { useRequireAuth } from '@/lib/auth';
import Sidebar from '@/components/Sidebar';
import { Search, Plus } from 'lucide-react';

const CATEGORIES = ['全部', '通用属性', '服装鞋帽', '3C电子', '家居家具', '美妆个护', '户外运动', '母婴用品', '汽车配件', '珠宝饰品', '办公文具', '宠物用品'];

export default function TermsPage() {
  const router = useRouter();
  const { status } = useRequireAuth(router);
  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState('全部');
  const [search, setSearch] = useState('');

  const fetchTerms = async (p: number, cat: string, q: string) => {
    const params: Record<string, string> = { page: String(p), page_size: '20' };
    if (cat !== '全部') params.category = cat;
    if (q) params.q = q;
    const res = await fetch(`/api/v1/terms?${new URLSearchParams(params)}`, {
      headers: authHeaders(),
    });
    const data = await res.json();
    setItems(data.items || []);
    setTotal(data.total || 0);
  };

  /* eslint-disable react-hooks/exhaustive-deps -- search 由 Enter 键显式触发，避免输入时逐键请求 */
  useEffect(() => {
    if (status !== 'authenticated') return;
    fetchTerms(page, category, search);
  }, [page, category, status]);
  /* eslint-enable react-hooks/exhaustive-deps */

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">术语词典</h1>
          <span className="text-sm text-gray-500">共 {total} 条术语</span>
        </div>

        <div className="flex gap-2 mb-4 overflow-x-auto pb-2">
          {CATEGORIES.map(c => (
            <button key={c} onClick={() => { setCategory(c); setPage(1); }}
              className={`px-3 py-1.5 rounded-full text-sm whitespace-nowrap ${
                category === c ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}>{c}</button>
          ))}
        </div>

        <div className="flex gap-3 mb-4">
          <div className="relative flex-1">
            <Search size={18} className="absolute left-3 top-2.5 text-gray-400" />
            <input value={search} onChange={e => setSearch(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') { setPage(1); fetchTerms(1, category, search); } }}
              className="w-full pl-10 pr-4 py-2 border rounded-lg" placeholder="搜索中英文术语..." />
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 text-left text-sm text-gray-500">
              <tr>
                <th className="px-4 py-3">中文</th>
                <th className="px-4 py-3">英文</th>
                <th className="px-4 py-3">品类</th>
                <th className="px-4 py-3">同义词</th>
                <th className="px-4 py-3">Amazon</th>
                <th className="px-4 py-3">阿里</th>
                <th className="px-4 py-3">来源</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {items.map(t => (
                <tr key={t.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-medium">{t.zh}</td>
                  <td className="px-4 py-3 text-sm">{t.en}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{t.category}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {t.synonyms?.length > 0 ? t.synonyms.join(', ') : '-'}
                  </td>
                  <td className="px-4 py-3 text-sm">{t.platform_amazon || '-'}</td>
                  <td className="px-4 py-3 text-sm">{t.platform_alibaba || '-'}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      t.is_builtin ? 'bg-blue-100 text-blue-700' : 'bg-green-100 text-green-700'
                    }`}>{t.is_builtin ? '内置' : '自定义'}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
