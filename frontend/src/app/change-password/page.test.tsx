import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

const pushMock = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: pushMock, back: vi.fn(), replace: vi.fn() }),
  usePathname: () => '/change-password',
  useParams: () => ({}),
}));

import ChangePasswordPage from '@/app/change-password/page';
import { setToken, clearToken } from '@/lib/api';

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    headers: { get: () => 'application/json' },
  };
}

describe('ChangePasswordPage', () => {
  beforeEach(() => {
    pushMock.mockClear();
    clearToken();
    setToken('test-token');
    localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('submits the new password and redirects to login', async () => {
    const fetchMock = vi.fn(async (input: unknown) => {
      const url = String(input);
      if (url.includes('/auth/change-password')) {
        return jsonResponse({ message: 'Password changed successfully' });
      }
      return jsonResponse({}, 404);
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<ChangePasswordPage />);
    fireEvent.change(screen.getByLabelText('当前密码'), { target: { value: 'OldPass123!' } });
    fireEvent.change(screen.getByLabelText('新密码'), { target: { value: 'NewPass123!' } });
    fireEvent.change(screen.getByLabelText('确认新密码'), { target: { value: 'NewPass123!' } });
    fireEvent.click(screen.getByRole('button', { name: '确认修改' }));

    await waitFor(() => expect(pushMock).toHaveBeenCalledWith('/login'));
    expect(screen.getByText('密码已修改，请重新登录')).toBeDefined();
  });

  it('rejects mismatched confirmation without calling the API', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);

    render(<ChangePasswordPage />);
    fireEvent.change(screen.getByLabelText('当前密码'), { target: { value: 'OldPass123!' } });
    fireEvent.change(screen.getByLabelText('新密码'), { target: { value: 'NewPass123!' } });
    fireEvent.change(screen.getByLabelText('确认新密码'), { target: { value: 'Different123!' } });
    fireEvent.click(screen.getByRole('button', { name: '确认修改' }));

    expect(await screen.findByText('两次输入的新密码不一致')).toBeDefined();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
