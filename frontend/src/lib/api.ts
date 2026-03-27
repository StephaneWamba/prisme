const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`, { next: { revalidate: 60 } });
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json();
}

// --- Types ---
export interface CatalogHealth {
  catalog_score: number;
  text_score: number;
  visual_score: number;
  product_count: number;
}

export interface ScorePoint {
  date: string;
  catalog_score: number;
  text_score: number;
  visual_score: number;
}

export interface Category {
  category: string;
  avg_catalog_score: number;
  avg_text_score: number;
  avg_visual_score: number;
  product_count: number;
}

export interface Product {
  ean: string;
  product_name: string;
  categories: string;
  catalog_score: number;
  text_score: number;
  visual_score: number;
  thumbnail_url_128?: string;
  has_anomaly_text?: boolean;
  has_anomaly_visual?: boolean;
}

export interface ProductDetail extends Product {
  thumbnail_url_256?: string;
  thumbnail_url_512?: string;
  image_url?: string;
  primary_object_label?: string;
  resolution_score?: number;
  sharpness_score?: number;
  centration_score?: number;
  image_width_px?: number;
  image_height_px?: number;
}

export interface Anomaly {
  anomaly_id: string;
  metric_name: string;
  anomaly_type: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  observed_value: number;
  expected_value?: number;
  z_score?: number;
  description: string;
  run_date: string;
}

export interface Report {
  report_id: string;
  report_date: string;
  executive_summary: string;
  catalog_score: number;
  text_score: number;
  visual_score: number;
  critical_issues: string[];
  worst_categories: string[];
  recommendations: string[];
}

export interface FieldCompleteness {
  metric_name: string;
  metric_value: number;
}

// --- API calls ---

export async function getCatalogHealth() {
  return get<{ health: CatalogHealth; evolution: ScorePoint[] }>("/catalog/health");
}

export async function getCategories() {
  return get<Category[]>("/catalog/categories");
}

export async function getProducts(params: {
  page?: number;
  per_page?: number;
  min_score?: number;
  max_score?: number;
  category?: string;
}) {
  const qs = new URLSearchParams();
  if (params.page) qs.set("page", String(params.page));
  if (params.per_page) qs.set("per_page", String(params.per_page));
  if (params.min_score !== undefined) qs.set("min_score", String(params.min_score));
  if (params.max_score !== undefined) qs.set("max_score", String(params.max_score));
  if (params.category) qs.set("category", params.category);
  return get<{ items: Product[]; total: number; page: number; per_page: number }>(
    `/products?${qs}`
  );
}

export async function getProductDetail(ean: string) {
  return get<ProductDetail>(`/products/${ean}`);
}

export async function getAnomalies(params?: { type?: string; severity?: string }) {
  const qs = new URLSearchParams();
  if (params?.type) qs.set("type", params.type);
  if (params?.severity) qs.set("severity", params.severity);
  return get<Anomaly[]>(`/anomalies?${qs}`);
}

export async function getLatestReport() {
  return get<Report>("/reports/latest");
}

export async function getQualityCoverage() {
  return get<{ total: number; has_image_url: number; has_thumbnail: number; thumbnail_pct: number }>(
    "/quality/coverage"
  );
}

export async function getFieldCompleteness() {
  return get<FieldCompleteness[]>("/quality/fields");
}

export async function searchVisual(image_url: string) {
  return post<Array<{ ean: string; distance: number; product_name?: string; thumbnail_url?: string }>>(
    "/search/visual",
    { image_url }
  );
}
