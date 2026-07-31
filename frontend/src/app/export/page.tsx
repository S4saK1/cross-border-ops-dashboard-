'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getToken } from '@/lib/api';
import Sidebar from '@/components/Sidebar';
import { Download, CheckSquare, Square } from 'lucide-react';

export default function ExportPage() {
  const router = useRouter();
  const [platform, setPlatform] = useState('amazon');
  const [products, setProducts] = useState<any[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [page, setPage] = useState(1);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    if (!getToken()) { router.push('/login'); return; }
    fetch(`/api/v1/products?page=${page}&page_size=20`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    }).then(r => r.json()).then(d => setProducts(d.items || [])).catch(() => {});
  }, [page]);

  const toggle = (id: string) => {
    setSelected(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (selected.size === products.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(products.map(p => p.id)));
    }
  };

  const handleExport = async () => {
    if (selected.size === 0) return;
    setExporting(true);
    try {
      const res = await fetch(`/api/v1/export/csv`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify({ platform, product_ids: Array.from(selected) }),
      });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${platform}_export.csv`;
      a.click();
    } catch (err) { alert('导出失败'); }
    setExporting(false);
  };

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <h1 className="text-2xl font-bold mb-6">CSV 导出</h1>

        <div className="flex gap-4 mb-6">
          {[{ id: 'amazon', label: 'Amazon' }, { id: 'alibaba', label: '阿里国际站' }].map(p => (
            <button key={p.id} onClick={() => setPlatform(p.id)}
              className={`px-6 py-4 rounded-xl border-2 text-left transition ${
                platform === p.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
              }`}>
              <p className="font-bold text-lg">{p.label}</p>
              <p className="text-sm text-gray-500">{p.id === 'amazon' ? '37 字段' : '29 字段'}</p>
            </button>
          ))}
        </div>

        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b flex items-center gap-3">
            <button onClick={toggleAll} className="text-gray-500">
              {selected.size === products.length ? <CheckSquare size={20} /> : <Square size={20} />}
            </button>
            <span className="text-sm text-gray-500">已选 {selected.size} 个产品</span>
          </div>
          <table className="w-full">
            <thead className="bg-gray-50 text-left text-sm text-gray-500">
              <tr>
                <th className="px-4 py-3 w-10"></th>
                <th className="px-4 py-3">SKU</th>
                <th className="px-4 py-3">中文名称</th>
                <th className="px-4 py-3">英文名称</th>
                <th className="px-4 py-3">品类</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {products.map(p => (
                <tr key={p.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => toggle(p.id)}>
                  <td className="px-4 py-3">
                    {selected.has(p.id) ? <CheckSquare size={18} className="text-blue-600" /> : <Square size={18} className="text-gray-300" />}
                  </td>
                  <td className="px-4 py-3 text-sm font-mono">{p.sku}</td>
                  <td className="px-4 py-3 text-sm">{p.product_name_zh}</td>
                  <td className="px-4 py-3 text-sm">{p.product_name_en}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{p.category}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-6 flex justify-end">
          <button onClick={handleExport} disabled={selected.size === 0 || exporting}
            className="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center gap-2">
            <Download size={18} />
            {exporting ? '导出中...' : `导出 CSV (${selected.size} 个产品)`}
          </button>
        </div>
      </main>
    </div>
  );
}
