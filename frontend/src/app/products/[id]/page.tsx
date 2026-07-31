'use client';
import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { getToken } from '@/lib/api';
import Sidebar from '@/components/Sidebar';
import { ArrowLeft, Edit, Save } from 'lucide-react';

const statusColors: Record<string, string> = {
  unchecked: 'bg-gray-100 text-gray-500',
  passed: 'bg-green-100 text-green-700',
  warning: 'bg-yellow-100 text-yellow-700',
  error: 'bg-red-100 text-red-700',
};
const statusLabels: Record<string, string> = {
  unchecked: '未检测', passed: '通过', warning: '警告', error: '错误',
};

export default function ProductDetailPage() {
  const router = useRouter();
  const params = useParams();
  const productId = params.id as string;
  const [product, setProduct] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<any>({});

  const fetchProduct = async () => {
    setLoading(true);
    try {
      const token = getToken();
      const res = await fetch(`/api/v1/products/${productId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Product not found');
      const data = await res.json();
      setProduct(data);
      setForm(data);
    } catch {
      router.push('/products');
    }
    setLoading(false);
  };

  useEffect(() => {
    if (!getToken()) { router.push('/login'); return; }
    fetchProduct();
  }, [productId]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const token = getToken();
      const res = await fetch(`/api/v1/products/${productId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error('更新失败');
      const data = await res.json();
      setProduct(data);
      setEditing(false);
    } catch (err: any) {
      alert(err.message);
    }
    setSaving(false);
  };

  if (loading) return <div className="flex min-h-screen"><Sidebar /><main className="flex-1 p-8">加载中...</main></div>;
  if (!product) return null;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <button onClick={() => router.back()} className="flex items-center gap-2 text-sm text-gray-500 mb-4 hover:text-gray-700">
          <ArrowLeft size={16} /> 返回
        </button>
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">{product.product_name_zh}</h1>
          <button onClick={() => setEditing(!editing)}
            className="flex items-center gap-2 text-sm px-4 py-2 border rounded-lg hover:bg-gray-50">
            {editing ? '取消' : <><Edit size={16} /> 编辑</>}
          </button>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-6 space-y-4 max-w-2xl">
          <div className="grid grid-cols-2 gap-4">
            <div><span className="text-sm text-gray-500">SKU</span><p className="font-mono">{product.sku}</p></div>
            <div><span className="text-sm text-gray-500">品类</span>
              {editing ? <input value={form.category || ''} onChange={e => setForm({...form, category: e.target.value})}
                className="w-full px-3 py-1 border rounded" /> : <p>{product.category || '-'}</p>}
            </div>
          </div>
          <div><span className="text-sm text-gray-500">中文名称</span>
            {editing ? <input value={form.product_name_zh} onChange={e => setForm({...form, product_name_zh: e.target.value})}
              className="w-full px-3 py-1 border rounded" /> : <p>{product.product_name_zh}</p>}
          </div>
          <div><span className="text-sm text-gray-500">英文名称</span>
            {editing ? <input value={form.product_name_en} onChange={e => setForm({...form, product_name_en: e.target.value})}
              className="w-full px-3 py-1 border rounded" /> : <p>{product.product_name_en}</p>}
          </div>
          <div><span className="text-sm text-gray-500">中文描述</span>
            {editing ? <textarea value={form.description_zh || ''} onChange={e => setForm({...form, description_zh: e.target.value})}
              className="w-full px-3 py-1 border rounded" rows={3} /> : <p>{product.description_zh || '-'}</p>}
          </div>
          <div><span className="text-sm text-gray-500">英文描述</span>
            {editing ? <textarea value={form.description_en || ''} onChange={e => setForm({...form, description_en: e.target.value})}
              className="w-full px-3 py-1 border rounded" rows={3} /> : <p>{product.description_en || '-'}</p>}
          </div>
          <div><span className="text-sm text-gray-500">一致性状态</span>
            <span className={`ml-2 text-xs px-2 py-1 rounded-full ${statusColors[product.consistency_status] || ''}`}>
              {statusLabels[product.consistency_status] || product.consistency_status}
            </span>
          </div>
          <div><span className="text-sm text-gray-500">更新时间</span><p>{new Date(product.updated_at).toLocaleString('zh-CN')}</p></div>
          {editing && (
            <button onClick={handleSave} disabled={saving}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2">
              <Save size={18} /> {saving ? '保存中...' : '保存修改'}
            </button>
          )}
        </div>
      </main>
    </div>
  );
}
