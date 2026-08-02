import { useEffect, useState } from 'react';
import { auth, clearToken, getToken } from '@/lib/api';

export type SessionStatus = 'loading' | 'authenticated' | 'unauthenticated';

export interface SessionUser {
  id: string;
  email: string;
  display_name: string;
  role: string;
  is_active: boolean;
  [key: string]: unknown;
}

/**
 * Session state hook.
 *
 * Fast path: an in-memory token means a fresh login in this page session.
 * Refresh path: no token in memory, so restore the session from the httpOnly
 * cookie via /auth/me — fixes being kicked to /login on every page reload.
 */
export function useSession() {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [status, setStatus] = useState<SessionStatus>('loading');

  useEffect(() => {
    let cancelled = false;

    async function restore() {
      if (getToken()) {
        let storedUser: SessionUser | null = null;
        try {
          const raw = localStorage.getItem('user');
          storedUser = raw ? JSON.parse(raw) : null;
        } catch {
          storedUser = null;
        }
        if (!cancelled) {
          setUser(storedUser);
          setStatus('authenticated');
        }
        return;
      }

      try {
        const me = await auth.me();
        if (!cancelled) {
          setUser(me);
          localStorage.setItem('user', JSON.stringify(me));
          setStatus('authenticated');
        }
      } catch {
        clearToken();
        try {
          localStorage.removeItem('user');
        } catch {
          // ignore storage errors
        }
        if (!cancelled) {
          setUser(null);
          setStatus('unauthenticated');
        }
      }
    }

    restore();
    return () => {
      cancelled = true;
    };
  }, []);

  return { user, status };
}

/** Redirect to /login once the session is confirmed dead. */
export function useRequireAuth(router: { push: (url: string) => void }) {
  const { user, status } = useSession();

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/login');
    }
  }, [status, router]);

  return { user, status };
}
