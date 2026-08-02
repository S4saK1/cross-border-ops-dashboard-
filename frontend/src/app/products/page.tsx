'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { authHeaders } from '@/lib/api';
import { useRequireAuth } from '@/lib/auth';
import Sidebar from '@/components/Sidebar';
import { Plus, Search, Trash2, Eye } from 'lucide-react';

const statusColors: Record<string, string> = {
  unchecked: 'bg-gray-100 text-gray-500',
  passed: 'bg-green-100 text-green-700',
  warning: 'bg-yellow-100 text-yellow-700',
  error: 'bg-red-100 text-red-700',
};
const statusLabels: Record<string, string> = {
  unchecked: '未检测', passed: '通过', warning: '警告', error: '错误',
};

export default function ProductsPage() {
  const router = useRouter();
  const { status } = useRequireAuth(router);
  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchProducts = async (p: number, q: string) => {
    setLoading(true);
    try {
      const params: Record<string, string> = { page: String(p), page_size: '20' };
      if (q) params.search = q;
      const res = await fetch(`/api/v1/products?${new URLSearchParams(params)}`, {
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error("Request failed");
      const data = await res.json();
      setItems(data.items || []);
      setTotal(data.total || 0);
    } catch (err) { console.error("Failed to fetch products:", err) }
    setLoading(false);
  };

  /* eslint-disable react-hooks/exhaustive-deps -- search 由搜索按钮显式触发，避免输入时逐键请求 */
  useEffect(() => {
    if (status !== 'authenticated') return;
    fetchProducts(page, search);
  }, [page, status]);
  /* eslint-enable react-hooks/exhaustive-deps */

  const handleSearch = () => { setPage(1); fetchProducts(1, search); };

  const handleDelete = async (id: string) => {
    if (!confirm('确认删除此产品？')) return;
    await fetch(`/api/v1/products/${id}`, {
      method: 'DELETE', headers: authHeaders(),
    });
    fetchProducts(page, search);
  };

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">产品管理</h1>
          <button onClick={() => router.push('/products/new')}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center gap-2">
            <Plus size={18} /> 新建产品
          </button>
        </div>

        <div className="flex gap-3 mb-4">
          <div className="relative flex-1">
            <Search size={18} className="absolute left-3 top-2.5 text-gray-400" />
            <input value={search} onChange={e => setSearch(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
              className="w-full pl-10 pr-4 py-2 border rounded-lg" placeholder="搜索产品名称、SKU..." />
          </div>
          <button onClick={handleSearch} className="bg-gray-100 px-4 py-2 rounded-lg hover:bg-gray-200">搜索</button>
        </div>

        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 text-left text-sm text-gray-500">
              <tr>
                <th className="px-4 py-3">SKU</th>
                <th className="px-4 py-3">中文名称</th>
                <th className="px-4 py-3">英文名称</th>
                <th className="px-4 py-3">品类</th>
                <th className="px-4 py-3">一致性</th>
                <th className="px-4 py-3">更新时间</th>
                <th className="px-4 py-3">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {items.map(p => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-mono">{p.sku}</td>
                  <td className="px-4 py-3 text-sm">{p.product_name_zh}</td>
                  <td className="px-4 py-3 text-sm">{p.product_name_en}</td>
                  <td className="px-4 py-3 text-sm">{p.category}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-1 rounded-full ${statusColors[p.consistency_status]}`}>
                      {statusLabels[p.consistency_status]}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {new Date(p.updated_at).toLocaleDateString('zh-CN')}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button onClick={() => router.push(`/products/${p.id}`)}
                        className="text-blue-600 hover:text-blue-800"><Eye size={16} /></button>
                      <button onClick={() => handleDelete(p.id)}
                        className="text-red-500 hover:text-red-700"><Trash2 size={16} /></button>
                    </div>
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr><td colSpan={7} className="px-4 py-12 text-center text-gray-400">暂无产品数据</td></tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between mt-4 text-sm text-gray-500">
          <span>共 {total} 条</span>
          <div className="flex gap-2">
            <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
              className="px-3 py-1 border rounded disabled:opacity-30">上一页</button>
            <span className="px-3 py-1">第 {page} 页</span>
            <button onClick={() => setPage(p => p + 1)}
              className="px-3 py-1 border rounded">下一页</button>
          </div>
        </div>
      </main>
    </div>
  );
}
