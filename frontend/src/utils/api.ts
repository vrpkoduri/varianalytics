import type { ApiError, ApiResponse } from '@/types/api';

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
 * Generic fetch wrapper with error handling.
 */
async function request<T>(
  service: ServiceName,
  path: string,
  options: RequestInit = {},
): Promise<ApiResponse<T>> {
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
  return { data, status: response.status };
}

/**
 * API client for each microservice.
 */
export const api = {
  gateway: {
    get: <T>(path: string) => request<T>('gateway', path),
    post: <T>(path: string, body: unknown) =>
      request<T>('gateway', path, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    put: <T>(path: string, body: unknown) =>
      request<T>('gateway', path, {
        method: 'PUT',
        body: JSON.stringify(body),
      }),
    delete: <T>(path: string) =>
      request<T>('gateway', path, { method: 'DELETE' }),
  },
  computation: {
    get: <T>(path: string) => request<T>('computation', path),
    post: <T>(path: string, body: unknown) =>
      request<T>('computation', path, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
  },
  reports: {
    get: <T>(path: string) => request<T>('reports', path),
    post: <T>(path: string, body: unknown) =>
      request<T>('reports', path, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
  },
};
