import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ImportPage from '@/app/products/import/page';
import { setToken, clearToken } from '@/lib/api';

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    headers: { get: () => 'application/json' },
  };
}

describe('ImportPage', () => {
  beforeEach(() => {
    clearToken();
    setToken('test-token');
    localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('runs upload → preview → execute flow', async () => {
    const fetchMock = vi.fn(async (input: unknown, init?: RequestInit) => {
      const url = String(input);
      if (url.includes('/api/v1/import/upload')) {
        return jsonResponse({
          file_id: 'f1',
          filename: 'products.csv',
          total_rows: 2,
          headers: ['SKU', 'product_name_zh'],
          preview_rows: [],
          auto_mapping: { SKU: 'sku', product_name_zh: 'product_name_zh' },
          available_fields: { sku: 'SKU' },
        });
      }
      if (url.includes('/api/v1/import/preview')) {
        return jsonResponse({
          total_rows: 2,
          mapped_fields: 2,
          missing_required: [],
          sku_duplicates: [],
          rows_with_issues: [],
          can_proceed: true,
        });
      }
      if (url.includes('/api/v1/import/execute')) {
        return jsonResponse({
          success_count: 2,
          skip_count: 0,
          error_count: 0,
          errors: [],
          mode: 'create',
        });
      }
      return jsonResponse({}, 404);
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<ImportPage />);

    const fileInput = screen.getByLabelText('导入文件');
    fireEvent.change(fileInput, {
      target: { files: [new File(['sku,name'], 'products.csv', { type: 'text/csv' })] },
    });
    fireEvent.click(screen.getByText('开始导入'));

    // 上传成功 → 进入预览步骤
    expect(await screen.findByText('文件已解析')).toBeDefined();
    expect(screen.getByText(/共 2 行/)).toBeDefined();

    // 执行导入 → 展示结果
    fireEvent.click(screen.getByText('执行导入'));
    expect(await screen.findByText('导入完成')).toBeDefined();
    expect(screen.getByText(/成功 2 条/)).toBeDefined();
    expect(screen.getByText(/失败 0 条/)).toBeDefined();
  });
});
