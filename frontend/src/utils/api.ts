import type { ApiError } from '@/types/api';

const SERVICE_URLS = {
  gateway: '/api/gateway',
  computation: '/api/computation',
  reports: '/api/reports',
} as const;

type ServiceName = keyof typeof SERVICE_URLS;

let authToken: string | null = null;

/**
 * Set the auth token for API requests.
 */
export function setAuthToken(token: string | null): void {
  authToken = token;
}

/**
 * Convert snake_case keys to camelCase recursively.
 */
function snakeToCamel(obj: any): any {
  if (Array.isArray(obj)) return obj.map(snakeToCamel)
  if (obj !== null && typeof obj === 'object' && !(obj instanceof Date)) {
    return Object.fromEntries(
      Object.entries(obj).map(([k, v]) => [
        k.replace(/_([a-z])/g, (_, c) => c.toUpperCase()),
        snakeToCamel(v),
      ])
    )
  }
  return obj
}

/**
 * Build URL query params from an object, filtering out undefined/empty values.
 */
export function buildParams(
  params: Record<string, string | number | boolean | undefined>,
): string {
  const entries = Object.entries(params).filter(
    ([_, v]) => v !== undefined && v !== '',
  )
  if (entries.length === 0) return ''
  return (
    '?' +
    entries
      .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
      .join('&')
  )
}

/**
 * Build headers for API requests.
 */
function buildHeaders(custom?: Record<string, string>): HeadersInit {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...custom,
  };
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }
  return headers;
}

/**
 * Generic fetch wrapper with error handling and snake_case to camelCase conversion.
 */
async function request<T>(
  service: ServiceName,
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${SERVICE_URLS[service]}${path}`;

  const response = await fetch(url, {
    ...options,
    headers: buildHeaders(options.headers as Record<string, string>),
  });

  if (!response.ok) {
    const error: ApiError = {
      status: response.status,
      message: response.statusText,
    };
    try {
      const body = await response.json();
      error.detail = body.detail || body.message;
    } catch {
      // Response body not JSON
    }
    throw error;
  }

  const data = await response.json();
  return snakeToCamel(data) as T;
}

/**
 * API client for each microservice.
 */
export const api = {
  gateway: {
    get: <T = any>(path: string) => request<T>('gateway', path),
    post: <T = any>(path: string, body: unknown) =>
      request<T>('gateway', path, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    put: <T = any>(path: string, body: unknown) =>
      request<T>('gateway', path, {
        method: 'PUT',
        body: JSON.stringify(body),
      }),
    delete: <T = any>(path: string) =>
      request<T>('gateway', path, { method: 'DELETE' }),
  },
  computation: {
    get: <T = any>(path: string) => request<T>('computation', path),
    post: <T = any>(path: string, body: unknown) =>
      request<T>('computation', path, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
  },
  reports: {
    get: <T = any>(path: string) => request<T>('reports', path),
    post: <T = any>(path: string, body: unknown) =>
      request<T>('reports', path, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
  },
};
