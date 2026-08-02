'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { authHeaders } from '@/lib/api';
import { useRequireAuth } from '@/lib/auth';
import Sidebar from '@/components/Sidebar';
import { Upload, FileText, ArrowLeft, Play, RefreshCw, AlertTriangle, CheckCircle } from 'lucide-react';

interface UploadResult {
  file_id: string;
  filename: string;
  total_rows: number;
  headers: string[];
  preview_rows: unknown[];
  auto_mapping: Record<string, string>;
  available_fields: Record<string, string>;
}

interface PreviewResult {
  total_rows: number;
  mapped_fields: number;
  missing_required: string[];
  sku_duplicates: string[];
  rows_with_issues: { row: number; issues: string[] }[];
  can_proceed: boolean;
}

interface ExecuteResult {
  success_count: number;
  skip_count: number;
  error_count: number;
  errors: { row: number; error: string }[];
  mode: string;
}

export default function ImportPage() {
  const router = useRouter();
  useRequireAuth(router);

  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [preview, setPreview] = useState<PreviewResult | null>(null);
  const [executeResult, setExecuteResult] = useState<ExecuteResult | null>(null);
  const [mode, setMode] = useState<'create' | 'update'>('create');
  const [error, setError] = useState('');

  const handleUpload = async () => {
    if (!file) return;
    setError('');
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch('/api/v1/import/upload', {
        method: 'POST',
        headers: authHeaders(),
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: '上传失败' }));
        const detail = typeof err.detail === 'string' ? err.detail : err.detail?.message || '上传失败';
        throw new Error(detail);
      }
      const data: UploadResult = await res.json();
      setUploadResult(data);
      setExecuteResult(null);

      // 上传成功后自动拉取预览校验
      const previewRes = await fetch(`/api/v1/import/preview?file_id=${data.file_id}`, {
        method: 'POST',
        headers: authHeaders(),
      });
      if (previewRes.ok) {
        setPreview(await previewRes.json());
      }
    } catch (err: any) {
      setError(err.message || '上传失败');
    } finally {
      setUploading(false);
    }
  };

  const handleExecute = async () => {
    if (!uploadResult) return;
    setError('');
    setExecuting(true);
    try {
      const res = await fetch(
        `/api/v1/import/execute?file_id=${uploadResult.file_id}&mode=${mode}`,
        {
          method: 'POST',
          headers: authHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify(uploadResult.auto_mapping),
        },
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: '执行失败' }));
        const detail = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail) || '执行失败';
        throw new Error(detail);
      }
      setExecuteResult(await res.json());
    } catch (err: any) {
      setError(err.message || '执行失败');
    } finally {
      setExecuting(false);
    }
  };

  const reset = () => {
    setFile(null);
    setUploadResult(null);
    setPreview(null);
    setExecuteResult(null);
    setError('');
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

        {!uploadResult && (
          <div className="bg-white rounded-xl shadow-sm p-6 max-w-2xl">
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center mb-4">
              <Upload size={40} className="mx-auto text-gray-400 mb-2" />
              <p className="text-sm text-gray-500 mb-2">上传 CSV / Excel 文件进行批量导入（支持 .csv、.xlsx）</p>
              <input
                type="file"
                accept=".csv,.xlsx"
                aria-label="导入文件"
                onChange={e => setFile(e.target.files?.[0] || null)}
                className="text-sm"
              />
              {file && <p className="mt-2 text-sm text-gray-600">{file.name}</p>}
            </div>
            <button
              onClick={handleUpload}
              disabled={!file || uploading}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
            >
              <FileText size={18} /> {uploading ? '上传中...' : '开始导入'}
            </button>
          </div>
        )}

        {uploadResult && (
          <div className="bg-white rounded-xl shadow-sm p-6 max-w-2xl space-y-5">
            <div className="flex items-center justify-between">
              <h2 className="font-bold text-lg">文件已解析</h2>
              <button onClick={reset} className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1">
                <RefreshCw size={14} /> 重新选择
              </button>
            </div>

            <div className="text-sm text-gray-600 space-y-1">
              <p>文件名：{uploadResult.filename}</p>
              <p>共 {uploadResult.total_rows} 行，识别到 {uploadResult.headers.length} 列</p>
            </div>

            <div>
              <p className="text-sm font-medium mb-2">字段映射（自动识别）</p>
              <div className="bg-gray-50 rounded-lg p-3 text-sm space-y-1">
                {Object.entries(uploadResult.auto_mapping).map(([header, field]) => (
                  <p key={header} className="flex justify-between">
                    <span className="text-gray-500">{header}</span>
                    <span className="text-gray-800">→ {field}</span>
                  </p>
                ))}
                {Object.keys(uploadResult.auto_mapping).length === 0 && (
                  <p className="text-yellow-600">未能自动识别字段，请检查表头。</p>
                )}
              </div>
            </div>

            {preview && (preview.missing_required.length > 0 || preview.sku_duplicates.length > 0) && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-800 space-y-1">
                {preview.missing_required.length > 0 && (
                  <p className="flex items-center gap-2">
                    <AlertTriangle size={14} /> 必填字段未映射：{preview.missing_required.join('、')}
                  </p>
                )}
                {preview.sku_duplicates.length > 0 && (
                  <p className="flex items-center gap-2">
                    <AlertTriangle size={14} /> 文件内 SKU 重复：{preview.sku_duplicates.join('、')}
                  </p>
                )}
              </div>
            )}

            <div className="flex items-center gap-4">
              <label className="text-sm text-gray-600">导入模式</label>
              <select
                value={mode}
                onChange={e => setMode(e.target.value as 'create' | 'update')}
                className="px-3 py-2 border rounded-lg text-sm"
              >
                <option value="create">创建（SKU 已存在则跳过）</option>
                <option value="update">更新（SKU 已存在则覆盖，不存在则创建）</option>
              </select>
            </div>

            <button
              onClick={handleExecute}
              disabled={executing}
              className="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
            >
              <Play size={18} /> {executing ? '导入中...' : '执行导入'}
            </button>
          </div>
        )}

        {executeResult && (
          <div className="mt-6 bg-white rounded-xl shadow-sm p-6 max-w-2xl">
            <h3 className="font-bold text-lg mb-3 flex items-center gap-2">
              <CheckCircle size={18} className="text-green-600" /> 导入完成
            </h3>
            <div className="text-sm text-gray-600 space-y-1">
              <p>成功 {executeResult.success_count} 条</p>
              <p>跳过 {executeResult.skip_count} 条</p>
              <p>失败 {executeResult.error_count} 条</p>
            </div>
            {executeResult.errors.length > 0 && (
              <div className="mt-3 bg-red-50 border border-red-200 rounded-lg p-3 text-xs text-red-700 max-h-48 overflow-auto">
                {executeResult.errors.map((e, i) => (
                  <p key={i}>第 {e.row} 行：{e.error}</p>
                ))}
              </div>
            )}
            <button
              onClick={reset}
              className="mt-4 px-4 py-2 border rounded-lg text-sm hover:bg-gray-50 flex items-center gap-2"
            >
              <RefreshCw size={14} /> 继续导入
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
