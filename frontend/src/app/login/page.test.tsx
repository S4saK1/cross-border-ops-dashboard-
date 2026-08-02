import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

const pushMock = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: pushMock, back: vi.fn(), replace: vi.fn() }),
  usePathname: () => '/login',
  useParams: () => ({}),
}));

import LoginPage from '@/app/login/page';

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    headers: { get: () => 'application/json' },
  };
}

describe('LoginPage', () => {
  beforeEach(() => {
    pushMock.mockClear();
    localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('redirects to /change-password when the account requires a forced change', async () => {
    const fetchMock = vi.fn(async (input: unknown, init?: RequestInit) => {
      const url = String(input);
      if (url.includes('/auth/me')) return jsonResponse({ detail: 'Not authenticated' }, 401);
      if (url.includes('/auth/login')) {
        return jsonResponse({
          access_token: 'forced-token',
          refresh_token: null,
          token_type: 'Bearer',
          expires_in: 1800,
          user: { id: 'u1', email: 'a@b.com', display_name: 'A', role: 'viewer' },
          force_password_change: true,
        });
      }
      return jsonResponse({}, 404);
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText('邮箱'), { target: { value: 'a@b.com' } });
    fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'OldPass123!' } });
    fireEvent.click(screen.getByRole('button', { name: '登录' }));

    await waitFor(() => expect(pushMock).toHaveBeenCalledWith('/change-password'));
  });
});
