import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useSession } from '@/lib/auth';
import * as api from '@/lib/api';

describe('useSession', () => {
  beforeEach(() => {
    localStorage.clear();
    api.clearToken();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('treats an in-memory token as authenticated without a network call', () => {
    api.setToken('abc');
    localStorage.setItem('user', JSON.stringify({ id: 'u1', role: 'admin' }));
    const { result } = renderHook(() => useSession());
    expect(result.current.status).toBe('authenticated');
    expect(result.current.user?.role).toBe('admin');
  });

  it('restores the session via /auth/me when no token is in memory', async () => {
    const meSpy = vi.spyOn(api.auth, 'me').mockResolvedValue({
      id: 'u1',
      email: 'a@b.com',
      display_name: 'A',
      role: 'viewer',
      is_active: true,
    });
    const { result } = renderHook(() => useSession());
    await waitFor(() => expect(result.current.status).toBe('authenticated'));
    expect(meSpy).toHaveBeenCalledOnce();
    expect(result.current.user?.email).toBe('a@b.com');
    expect(JSON.parse(localStorage.getItem('user') || '{}').id).toBe('u1');
  });

  it('marks the session as unauthenticated when /auth/me returns 401', async () => {
    vi.spyOn(api.auth, 'me').mockRejectedValue(new Error('Unauthorized'));
    const { result } = renderHook(() => useSession());
    await waitFor(() => expect(result.current.status).toBe('unauthenticated'));
    expect(result.current.user).toBeNull();
  });
});
