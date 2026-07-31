export interface User {
  id: string;
  email: string;
  display_name: string;
  role: 'admin' | 'editor' | 'reviewer' | 'viewer';
  is_active: boolean;
}

export interface Product {
  id: string;
  sku: string;
  product_name_zh: string;
  product_name_en: string;
  category: string;
  brand?: string;
  description_zh?: string;
  description_en?: string;
  price?: number;
  currency: string;
  stock?: number;
  color_zh?: string;
  color_en?: string;
  material_zh?: string;
  material_en?: string;
  size?: string;
  weight?: number;
  weight_unit?: string;
  length?: number;
  width?: number;
  height?: number;
  dimension_unit?: string;
  origin?: string;
  model_number?: string;
  extra_fields?: Record<string, any>;
  consistency_status: 'unchecked' | 'passed' | 'warning' | 'error';
  consistency_issues?: any[];
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface Term {
  id: string;
  zh: string;
  en: string;
  category: string;
  note?: string;
  synonyms: string[];
  platform_amazon?: string;
  platform_alibaba?: string;
  is_builtin: boolean;
  created_at: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
