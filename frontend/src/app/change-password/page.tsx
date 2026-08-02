'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { auth, clearToken } from '@/lib/api';
import { useRequireAuth } from '@/lib/auth';
import Sidebar from '@/components/Sidebar';
import { KeyRound, ArrowLeft } from 'lucide-react';

export default function ChangePasswordPage() {
  const router = useRouter();
  useRequireAuth(router);

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setMessage('');

    if (newPassword !== confirmPassword) {
      setError('两次输入的新密码不一致');
      return;
    }
    if (newPassword.length < 8) {
      setError('新密码长度不能少于 8 位');
      return;
    }

    setLoading(true);
    try {
      await auth.changePassword(currentPassword, newPassword);
      clearToken();
      try {
        localStorage.removeItem('user');
      } catch {
        // ignore storage errors
      }
      setMessage('密码已修改，请重新登录');
      router.push('/login');
    } catch (err: any) {
      setError(err.message || '修改失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <button onClick={() => router.push('/')} className="flex items-center gap-2 text-sm text-gray-500 mb-4 hover:text-gray-700">
          <ArrowLeft size={16} /> 返回
        </button>
        <h1 className="text-2xl font-bold mb-6 flex items-center gap-2">
          <KeyRound size={24} /> 修改密码
        </h1>

        <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm p-6 space-y-4 max-w-md">
          {message && <p className="text-green-600 text-sm">{message}</p>}
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <div>
            <label className="block text-sm font-medium mb-1">当前密码</label>
            <input
              type="password"
              aria-label="当前密码"
              value={currentPassword}
              onChange={e => setCurrentPassword(e.target.value)}
              required
              className="w-full px-3 py-2 border rounded-lg"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">新密码</label>
            <input
              type="password"
              aria-label="新密码"
              value={newPassword}
              onChange={e => setNewPassword(e.target.value)}
              required
              className="w-full px-3 py-2 border rounded-lg"
              placeholder="至少 8 位，含大小写字母和数字"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">确认新密码</label>
            <input
              type="password"
              aria-label="确认新密码"
              value={confirmPassword}
              onChange={e => setConfirmPassword(e.target.value)}
              required
              className="w-full px-3 py-2 border rounded-lg"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? '提交中...' : '确认修改'}
          </button>
        </form>
      </main>
    </div>
  );
}
