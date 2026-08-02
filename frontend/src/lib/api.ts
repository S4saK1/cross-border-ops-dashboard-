const API_BASE = '/api/v1';

// Token helpers retained for gradual migration (ADR-007)
// httpOnly cookies are now the primary auth mechanism;
// Authorization header is sent as fallback during migration.
let accessToken: string | null = null;

export function setToken(token: string) {
  accessToken = token;
}

export function getToken(): string | null {
  return accessToken;
}

export function clearToken() {
  accessToken = null;
}

/** Build request headers, only attaching the Bearer token when one exists. */
export function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const token = getToken();
  if (token) {
    return { ...extra, Authorization: `Bearer ${token}` };
  }
  return extra;
}

async function request(path: string, options: RequestInit = {}) {
  const token = getToken();
  const headers: Record<string, string> = {
    ...((options.headers as Record<string, string>) || {}),
  };
  // Send Bearer token as fallback during httpOnly cookie migration
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    credentials: 'include',  // Send httpOnly cookies
  });

  if (res.status === 401) {
    clearToken();
    localStorage.removeItem('user');
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  if (res.headers.get('content-type')?.includes('text/csv')) {
    return res;
  }
  return res.json();
}

// Auth
export const auth = {
  login: (email: string, password: string) =>
    request('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  me: () => request('/auth/me'),
  logout: () => request('/auth/logout', { method: 'POST', body: JSON.stringify({}) }),
  changePassword: (currentPassword: string, newPassword: string) =>
    request('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    }),
};

// Products
export const products = {
  list: (params?: Record<string, string>) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : '';
    return request(`/products${qs}`);
  },
  get: (id: string) => request(`/products/${id}`),
  create: (data: any) => request('/products', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: any) => request(`/products/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id: string) => request(`/products/${id}`, { method: 'DELETE' }),
};

// Terms
export const terms = {
  list: (params?: Record<string, string>) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : '';
    return request(`/terms${qs}`);
  },
  create: (data: any) => request('/terms', { method: 'POST', body: JSON.stringify(data) }),
};

// Export
export const exportApi = {
  csv: (platform: string, productIds: string[]) =>
    request('/export/csv', { method: 'POST', body: JSON.stringify({ platform, product_ids: productIds }) }),
};

// Import
export const importApi = {
  upload: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return request('/import/upload', { method: 'POST', body: formData });
  },
  preview: (fileId: string) => request(`/import/preview?file_id=${fileId}`, { method: 'POST' }),
  execute: (fileId: string, fieldMapping: Record<string, string>, mode: string) =>
    request(`/import/execute?file_id=${fileId}&mode=${mode}`, { method: 'POST', body: JSON.stringify(fieldMapping) }),
};
