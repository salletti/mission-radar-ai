import { getAuthToken } from "./auth_token";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function authHeaders(): Promise<Record<string, string>> {
  const token = await getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function get<T>(
  path: string,
  params?: Record<string, string | number | boolean | undefined>
): Promise<T> {
  let url = path;
  if (params) {
    const searchParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) {
        searchParams.append(key, String(value));
      }
    }
    const qs = searchParams.toString();
    if (qs) url += `?${qs}`;
  }

  const response = await fetch(url, { headers: await authHeaders() });

  if (!response.ok) {
    let message: string;
    try {
      const data = await response.json();
      message =
        typeof data.detail === "string"
          ? data.detail
          : `Erreur ${response.status}`;
    } catch {
      message = `Erreur ${response.status} — backend indisponible ou réponse non-JSON`;
    }
    throw new ApiError(response.status, message);
  }

  return response.json() as Promise<T>;
}

export async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    let message: string;
    try {
      const data = await response.json();
      message =
        typeof data.detail === "string"
          ? data.detail
          : `Erreur ${response.status}`;
    } catch {
      message = `Erreur ${response.status} — backend indisponible ou réponse non-JSON`;
    }
    throw new ApiError(response.status, message);
  }

  return response.json() as Promise<T>;
}
