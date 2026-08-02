'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { authHeaders } from '@/lib/api';
import { useRequireAuth } from '@/lib/auth';
import Sidebar from '@/components/Sidebar';
import { FileText } from 'lucide-react';

export default function AuditPage() {
  const router = useRouter();
  const { status } = useRequireAuth(router);
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const fetchLogs = async (p: number) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/v1/audit-logs?page=${p}&page_size=20`, {
        headers: authHeaders(),
      });
      if (res.status === 403) { router.push('/'); return; }
      const data = await res.json();
      setLogs(data.items || []);
      setTotal(data.total || 0);
    } catch {}
    setLoading(false);
  };

  useEffect(() => {
    if (status !== 'authenticated') return;
    fetchLogs(page);
  }, [page, status]);

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <h1 className="text-2xl font-bold mb-6 flex items-center gap-2">
          <FileText size={24} /> 审计日志
        </h1>
        {loading ? <p>加载中...</p> : (
          <>
            <div className="bg-white rounded-xl shadow-sm overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50 text-left text-sm text-gray-500">
                  <tr>
                    <th className="px-4 py-3">时间</th>
                    <th className="px-4 py-3">用户ID</th>
                    <th className="px-4 py-3">操作</th>
                    <th className="px-4 py-3">资源类型</th>
                    <th className="px-4 py-3">资源ID</th>
                    <th className="px-4 py-3">详情</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {logs.map((log: any) => (
                    <tr key={log.id} className="hover:bg-gray-50 text-sm">
                      <td className="px-4 py-3 text-gray-500">{new Date(log.created_at).toLocaleString('zh-CN')}</td>
                      <td className="px-4 py-3 font-mono text-xs">{log.user_id?.slice(0, 8)}...</td>
                      <td className="px-4 py-3">{log.action}</td>
                      <td className="px-4 py-3">{log.resource_type}</td>
                      <td className="px-4 py-3 font-mono text-xs">{log.resource_id?.slice(0, 8)}...</td>
                      <td className="px-4 py-3 text-xs text-gray-500">{log.details || '-'}</td>
                    </tr>
                  ))}
                  {logs.length === 0 && (
                    <tr><td colSpan={6} className="px-4 py-12 text-center text-gray-400">暂无审计日志</td></tr>
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
          </>
        )}
      </main>
    </div>
  );
}
