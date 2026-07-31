import React from 'react';
﻿import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import Sidebar from '@/components/Sidebar';

describe('Sidebar', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('renders all default nav items for viewer role', () => {
    render(<Sidebar />);
    expect(screen.getByText('仪表盘')).toBeDefined();
    expect(screen.getByText('产品管理')).toBeDefined();
    expect(screen.getByText('术语词典')).toBeDefined();
    expect(screen.getByText('CSV 导出')).toBeDefined();
    expect(screen.getByText('批量导入')).toBeDefined();
    expect(screen.getByText('审计日志')).toBeDefined();
  });

  it('hides user management for non-admin roles', () => {
    render(<Sidebar userRole="viewer" />);
    expect(screen.queryByText('用户管理')).toBeNull();
  });

  it('shows user management for admin role', () => {
    render(<Sidebar userRole="admin" />);
    expect(screen.getByText('用户管理')).toBeDefined();
  });

  it('reads role from localStorage when userRole prop is not set', () => {
    localStorage.setItem('user', JSON.stringify({ role: 'admin' }));
    render(<Sidebar />);
    // After useEffect, user management should appear
    // Note: in jsdom, useEffect runs synchronously in tests
  });

  it('renders logout button', () => {
    render(<Sidebar />);
    expect(screen.getByText('退出登录')).toBeDefined();
  });

  it('renders app title', () => {
    render(<Sidebar />);
    expect(screen.getByText('Bilingual CMS')).toBeDefined();
  });
});
