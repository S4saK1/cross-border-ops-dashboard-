'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getToken } from '@/lib/api';
import Sidebar from '@/components/Sidebar';
import { ArrowLeft, Save } from 'lucide-react';

export default function NewProductPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    sku: '', product_name_zh: '', product_name_en: '',
    category: '', description_zh: '', description_en: '',
    platform: 'amazon',
  });

  useEffect(() => {
    if (!getToken()) { router.push('/login'); return; }
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const token = getToken();
      const res = await fetch('/api/v1/products', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(form),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || '创建失败');
      }
      router.push('/products');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <button onClick={() => router.back()} className="flex items-center gap-2 text-sm text-gray-500 mb-4 hover:text-gray-700">
          <ArrowLeft size={16} /> 返回
        </button>
        <h1 className="text-2xl font-bold mb-6">新建产品</h1>
        {error && <p className="text-red-500 text-sm mb-4">{error}</p>}
        <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm p-6 space-y-4 max-w-2xl">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">SKU *</label>
              <input required value={form.sku} onChange={e => setForm({...form, sku: e.target.value})}
                className="w-full px-3 py-2 border rounded-lg" placeholder="SKU-001" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">品类</label>
              <input value={form.category} onChange={e => setForm({...form, category: e.target.value})}
                className="w-full px-3 py-2 border rounded-lg" placeholder="电子产品" />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">中文名称 *</label>
            <input required value={form.product_name_zh} onChange={e => setForm({...form, product_name_zh: e.target.value})}
              className="w-full px-3 py-2 border rounded-lg" placeholder="中文产品名" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">英文名称 *</label>
            <input required value={form.product_name_en} onChange={e => setForm({...form, product_name_en: e.target.value})}
              className="w-full px-3 py-2 border rounded-lg" placeholder="English product name" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">平台</label>
            <select value={form.platform} onChange={e => setForm({...form, platform: e.target.value})}
              className="w-full px-3 py-2 border rounded-lg">
              <option value="amazon">Amazon</option>
              <option value="shopify">Shopify</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">中文描述</label>
            <textarea value={form.description_zh} onChange={e => setForm({...form, description_zh: e.target.value})}
              className="w-full px-3 py-2 border rounded-lg" rows={3} placeholder="中文描述" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">英文描述</label>
            <textarea value={form.description_en} onChange={e => setForm({...form, description_en: e.target.value})}
              className="w-full px-3 py-2 border rounded-lg" rows={3} placeholder="English description" />
          </div>
          <button type="submit" disabled={loading}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2">
            <Save size={18} /> {loading ? '保存中...' : '保存'}
          </button>
        </form>
      </main>
    </div>
  );
}
