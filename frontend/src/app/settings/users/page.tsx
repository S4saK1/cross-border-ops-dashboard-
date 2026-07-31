'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getToken } from '@/lib/api';
import Sidebar from '@/components/Sidebar';
import { Users, Plus, X, Check, AlertCircle } from 'lucide-react';

const ROLE_OPTIONS = ['admin', 'editor', 'reviewer', 'viewer'] as const;
const roleLabels: Record<string, string> = {
  admin: '管理员', editor: '编辑', reviewer: '审核', viewer: '只读',
};

// ── Create User Modal ──
function CreateUserModal({ open, onClose, onCreated }: {
  open: boolean; onClose: () => void; onCreated: () => void;
}) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [role, setRole] = useState('viewer');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const token = getToken();
      const res = await fetch('/api/v1/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ email, password, display_name: displayName, role }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: '创建失败' }));
        throw new Error(typeof err.detail === 'string' ? err.detail : err.detail?.message || '创建失败');
      }
      onCreated();
      onClose();
      setEmail(''); setPassword(''); setDisplayName(''); setRole('viewer');
    } catch (err: any) {
      setError(err.message);
    }
    setLoading(false);
  };

  if (!open) return null;
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md p-6" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold">创建用户</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600"><X size={20} /></button>
        </div>
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex items-center gap-2">
            <AlertCircle size={16} /> {error}
          </div>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">邮箱</label>
            <input type="email" required value={email} onChange={e => setEmail(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg text-sm" placeholder="user@example.com" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">显示名称</label>
            <input type="text" required value={displayName} onChange={e => setDisplayName(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg text-sm" placeholder="张三" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">密码</label>
            <input type="password" required value={password} onChange={e => setPassword(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg text-sm" placeholder="至少8位，含大小写+数字+符号" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">角色</label>
            <select value={role} onChange={e => setRole(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg text-sm">
              {ROLE_OPTIONS.map(r => <option key={r} value={r}>{roleLabels[r]}</option>)}
            </select>
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 px-4 py-2 border rounded-lg text-sm hover:bg-gray-50">取消</button>
            <button type="submit" disabled={loading}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50">
              {loading ? '创建中...' : '创建'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Reset Password Result Modal ──
function ResetPasswordModal({ open, onClose, tempPassword, userId }: {
  open: boolean; onClose: () => void; tempPassword: string; userId: string;
}) {
  const [copied, setCopied] = useState(false);
  if (!open) return null;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(tempPassword);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md p-6" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold">密码已重置</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600"><X size={20} /></button>
        </div>
        <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-800 flex items-center gap-2">
          <AlertCircle size={16} />
          请将临时密码安全地交付给用户。用户下次登录时将被要求修改密码。
        </div>
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">临时密码</label>
          <div className="flex gap-2">
            <input type="text" readOnly value={tempPassword}
              className="flex-1 px-3 py-2 bg-gray-50 border rounded-lg text-sm font-mono select-all" />
            <button onClick={handleCopy}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${copied ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}>
              {copied ? <Check size={16} /> : '复制'}
            </button>
          </div>
        </div>
        <button onClick={onClose} className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">关闭</button>
      </div>
    </div>
  );
}

// ── Main Page ──
export default function UsersPage() {
  const router = useRouter();
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Modals
  const [showCreate, setShowCreate] = useState(false);
  const [resetPwdModal, setResetPwdModal] = useState({ open: false, password: '', userId: '' });

  // Bulk selection
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkLoading, setBulkLoading] = useState(false);

  const fetchUsers = async () => {
    setLoading(true);
    setError('');
    try {
      const token = getToken();
      const res = await fetch('/api/v1/users', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 403) { router.push('/'); return; }
      if (!res.ok) throw new Error('加载失败');
      const data = await res.json();
      setUsers(Array.isArray(data) ? data : data.items || []);
    } catch (err: any) {
      setError(err.message);
    }
    setLoading(false);
  };

  useEffect(() => {
    if (!getToken()) { router.push('/login'); return; }
    fetchUsers();
  }, []);

  // ── Actions ──

  const handleRoleChange = async (userId: string, newRole: string) => {
    try {
      const token = getToken();
      const res = await fetch(`/api/v1/users/${userId}/role?role=${newRole}`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: '操作失败' }));
        throw new Error(typeof err.detail === 'string' ? err.detail : '操作失败');
      }
      setUsers(prev => prev.map(u => u.id === userId ? { ...u, role: newRole } : u));
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleToggleActive = async (userId: string, currentlyActive: boolean) => {
    const action = currentlyActive ? '禁用' : '启用';
    if (!confirm(`确认${action}该用户？`)) return;
    try {
      const token = getToken();
      if (currentlyActive) {
        // Disable via DELETE
        const res = await fetch(`/api/v1/users/${userId}`, {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error('操作失败');
        setUsers(prev => prev.map(u => u.id === userId ? { ...u, is_active: false } : u));
      } else {
        // Enable via PUT
        const res = await fetch(`/api/v1/users/${userId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ is_active: true }),
        });
        if (!res.ok) throw new Error('操作失败');
        setUsers(prev => prev.map(u => u.id === userId ? { ...u, is_active: true } : u));
      }
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleResetPassword = async (userId: string) => {
    if (!confirm('确认重置该用户的密码？其所有活跃会话将被撤销。')) return;
    try {
      const token = getToken();
      const res = await fetch(`/api/v1/users/${userId}/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({}),
      });
      if (!res.ok) throw new Error('操作失败');
      const data = await res.json();
      setResetPwdModal({ open: true, password: data.temporary_password, userId });
    } catch (err: any) {
      alert(err.message);
    }
  };

  // ── Bulk Actions ──

  const toggleSelect = (userId: string) => {
    setSelected(prev => {
      const next = new Set(prev);
      next.has(userId) ? next.delete(userId) : next.add(userId);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selected.size === users.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(users.map(u => u.id)));
    }
  };

  const handleBulkAction = async (action: 'disable' | 'enable') => {
    const label = action === 'disable' ? '禁用' : '启用';
    if (!confirm(`确认批量${label} ${selected.size} 个用户？`)) return;
    setBulkLoading(true);
    try {
      const token = getToken();
      const operations = Array.from(selected).map(userId => ({ user_id: userId, action }));
      const res = await fetch('/api/v1/users/bulk', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ operations }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: '批量操作失败' }));
        throw new Error(typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail));
      }
      setSelected(new Set());
      fetchUsers();
    } catch (err: any) {
      alert(err.message);
    }
    setBulkLoading(false);
  };

  // ── Render ──

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Users size={24} /> 用户管理
          </h1>
          <button onClick={() => setShowCreate(true)}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center gap-2 text-sm">
            <Plus size={18} /> 创建用户
          </button>
        </div>

        {/* Bulk actions bar */}
        {selected.size > 0 && (
          <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-center justify-between">
            <span className="text-sm text-blue-800">已选择 {selected.size} 个用户</span>
            <div className="flex gap-2">
              <button onClick={() => handleBulkAction('enable')} disabled={bulkLoading}
                className="px-3 py-1.5 bg-green-600 text-white rounded text-xs hover:bg-green-700 disabled:opacity-50">
                批量启用
              </button>
              <button onClick={() => handleBulkAction('disable')} disabled={bulkLoading}
                className="px-3 py-1.5 bg-red-600 text-white rounded text-xs hover:bg-red-700 disabled:opacity-50">
                批量禁用
              </button>
              <button onClick={() => setSelected(new Set())}
                className="px-3 py-1.5 border rounded text-xs hover:bg-gray-50">取消选择</button>
            </div>
          </div>
        )}

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex items-center gap-2">
            <AlertCircle size={16} /> {error}
          </div>
        )}

        {loading ? <p className="text-gray-400">加载中...</p> : (
          <div className="bg-white rounded-xl shadow-sm overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50 text-left text-sm text-gray-500">
                <tr>
                  <th className="px-4 py-3 w-10">
                    <input type="checkbox" checked={selected.size === users.length && users.length > 0}
                      onChange={toggleSelectAll} className="rounded" />
                  </th>
                  <th className="px-4 py-3">邮箱</th>
                  <th className="px-4 py-3">姓名</th>
                  <th className="px-4 py-3">角色</th>
                  <th className="px-4 py-3">状态</th>
                  <th className="px-4 py-3 w-48">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {users.map((u: any) => (
                  <tr key={u.id} className="hover:bg-gray-50 text-sm">
                    <td className="px-4 py-3">
                      <input type="checkbox" checked={selected.has(u.id)}
                        onChange={() => toggleSelect(u.id)} className="rounded" />
                    </td>
                    <td className="px-4 py-3">{u.email}</td>
                    <td className="px-4 py-3">{u.display_name || '-'}</td>
                    <td className="px-4 py-3">
                      <select value={u.role} onChange={e => handleRoleChange(u.id, e.target.value)}
                        className="text-xs px-2 py-1 rounded border border-gray-200 bg-white hover:border-blue-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none">
                        {ROLE_OPTIONS.map(r => <option key={r} value={r}>{roleLabels[r]}</option>)}
                      </select>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-1 rounded-full ${u.is_active ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                        {u.is_active ? '活跃' : '禁用'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1">
                        <button onClick={() => handleToggleActive(u.id, u.is_active)}
                          className={`text-xs px-2 py-1 rounded ${u.is_active ? 'bg-red-50 text-red-600 hover:bg-red-100' : 'bg-green-50 text-green-600 hover:bg-green-100'}`}>
                          {u.is_active ? '禁用' : '启用'}
                        </button>
                        <button onClick={() => handleResetPassword(u.id)}
                          className="text-xs px-2 py-1 rounded bg-yellow-50 text-yellow-600 hover:bg-yellow-100">
                          重置密码
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {users.length === 0 && (
                  <tr><td colSpan={6} className="px-4 py-12 text-center text-gray-400">暂无用户数据</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </main>

      <CreateUserModal open={showCreate} onClose={() => setShowCreate(false)} onCreated={fetchUsers} />
      <ResetPasswordModal open={resetPwdModal.open} onClose={() => setResetPwdModal({ open: false, password: '', userId: '' })}
        tempPassword={resetPwdModal.password} userId={resetPwdModal.userId} />
    </div>
  );
}