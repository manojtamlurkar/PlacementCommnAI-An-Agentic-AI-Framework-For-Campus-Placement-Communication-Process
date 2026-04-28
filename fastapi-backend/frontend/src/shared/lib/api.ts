import type { StandardResponse } from "../types/api";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status = 500) {
    super(message);
    this.status = status;
  }
}

async function parseJson<T>(response: Response): Promise<T> {
  const text = await response.text();
  if (!text) {
    return {} as T;
  }
  return JSON.parse(text) as T;
}

export async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  const json = await parseJson<unknown>(response);

  if (!response.ok) {
    const detail =
      typeof json === "object" &&
      json !== null &&
      "detail" in json &&
      typeof (json as { detail?: unknown }).detail === "string"
        ? (json as { detail: string }).detail
        : response.statusText || "Request failed";
    throw new ApiError(detail, response.status);
  }

  return json as T;
}

export async function requestData<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await request<StandardResponse<T>>(path, init);
  return response.data as T;
}

export { API_BASE };
