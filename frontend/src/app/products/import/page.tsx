'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getToken } from '@/lib/api';
import Sidebar from '@/components/Sidebar';
import { Upload, FileText, ArrowLeft } from 'lucide-react';

export default function ImportPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!getToken()) { router.push('/login'); return; }
  }, []);

  const handleUpload = async () => {
    if (!file) return;
    setError('');
    setUploading(true);
    try {
      const token = getToken();
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch('/api/v1/import/upload', {
        method: 'POST',
        headers: { Authorization: `Bearer ` },
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || '上传失败');
      }
      const data = await res.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message);
    }
    setUploading(false);
  };

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <button onClick={() => router.back()} className="flex items-center gap-2 text-sm text-gray-500 mb-4 hover:text-gray-700">
          <ArrowLeft size={16} /> 返回
        </button>
        <h1 className="text-2xl font-bold mb-6">批量导入</h1>
        {error && <p className="text-red-500 text-sm mb-4">{error}</p>}
        <div className="bg-white rounded-xl shadow-sm p-6 max-w-2xl">
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center mb-4">
            <Upload size={40} className="mx-auto text-gray-400 mb-2" />
            <p className="text-sm text-gray-500 mb-2">上传 CSV 文件进行批量导入</p>
            <input type="file" accept=".csv" onChange={e => setFile(e.target.files?.[0] || null)}
              className="text-sm" />
          </div>
          <button onClick={handleUpload} disabled={!file || uploading}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2">
            <FileText size={18} /> {uploading ? '上传中...' : '开始导入'}
          </button>
          {result && (
            <div className="mt-6 p-4 bg-green-50 rounded-lg">
              <p className="text-green-700 font-medium">导入完成</p>
              <pre className="text-sm mt-2 text-gray-600">{JSON.stringify(result, null, 2)}</pre>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
