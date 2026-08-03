export const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:5667';
export const SKY_NEWS_FETCH_TIMEOUT_MS = 8000;

export async function fetchWithTimeout(fetcher: typeof fetch, input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const callerSignal = init?.signal;
  const forwardAbort = () => controller.abort(callerSignal?.reason);
  if (callerSignal?.aborted) controller.abort(callerSignal.reason);
  else callerSignal?.addEventListener('abort', forwardAbort, { once: true });
  const timeout = setTimeout(() => controller.abort(), SKY_NEWS_FETCH_TIMEOUT_MS);
  try {
    return await fetcher(input, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timeout);
    callerSignal?.removeEventListener('abort', forwardAbort);
  }
}

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(message: string, status: number, detail?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

async function readError(response: Response): Promise<ApiError> {
  let text = '';
  try {
    text = await response.text();
  } catch (err) {
    return new ApiError(err instanceof Error ? err.message : response.statusText, response.status);
  }
  try {
    const data = JSON.parse(text);
    const detail = data?.detail ?? data?.message ?? text;
    return new ApiError(typeof detail === 'string' ? detail : JSON.stringify(detail), response.status, detail);
  } catch {
    return new ApiError(text || response.statusText, response.status, text);
  }
}

export type BirthPayload = {
  display_name?: string;
  birth_date: string;
  birth_time?: string;
  birth_place: string;
  latitude?: number;
  longitude?: number;
  timezone?: string;
};

export type QuestionnaireAnswer = Record<string, number>;

export async function apiPost<T>(path: string, payload: unknown): Promise<T> {
  if (typeof navigator !== 'undefined' && !navigator.onLine) {
    throw new Error('Hermex sedang offline. Coba lagi saat koneksi kembali.');
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw await readError(response);
  }

  return response.json() as Promise<T>;
}

export async function apiGet<T>(path: string): Promise<T> {
  if (typeof navigator !== 'undefined' && !navigator.onLine) {
    throw new Error('Hermex sedang offline. Coba lagi saat koneksi kembali.');
  }

  const response = await fetch(`${API_BASE}${path}`, { credentials: 'include' });

  if (!response.ok) {
    throw await readError(response);
  }

  return response.json() as Promise<T>;
}

export async function apiDelete<T>(path: string): Promise<T> {
  if (typeof navigator !== 'undefined' && !navigator.onLine) {
    throw new Error('Hermex sedang offline. Coba lagi saat koneksi kembali.');
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method: 'DELETE',
    credentials: 'include'
  });

  if (!response.ok) {
    throw await readError(response);
  }

  return response.json() as Promise<T>;
}

export async function apiPatch<T>(path: string, payload: unknown): Promise<T> {
  if (typeof navigator !== 'undefined' && !navigator.onLine) {
    throw new Error('Hermex sedang offline. Coba lagi saat koneksi kembali.');
  }
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(payload)
  });
  if (!response.ok) throw await readError(response);
  return response.json() as Promise<T>;
}

export async function analyzeBirth(payload: BirthPayload) {
  return apiPost('/api/v1/birth/analyze', payload);
}

export async function getBirthQuestion(profile_id: string, claim_token: string, index: number) {
  return apiPost('/api/v1/birth/question', { profile_id, claim_token, index });
}

export async function getProfile(profile_id: string) {
  return apiGet(`/api/v1/profiles/${profile_id}`);
}

export async function publishPublicProfile(payload: {
  profile_id: string;
  username: string;
  email: string;
  claim_token?: string;
  display_name?: string;
  bio?: string;
}) {
  return apiPost('/api/v1/public-profiles', payload);
}

export async function listPublicProfiles() {
  return apiGet('/api/v1/public-profiles');
}

export async function getPublicProfile(username: string) {
  return apiGet(`/api/v1/public-profiles/${encodeURIComponent(username)}`);
}

export async function getSkyNews() {
  return apiGet('/api/v1/sky-news');
}

export async function getSkyCalendar() {
  return apiGet('/api/v1/sky-calendar');
}

export async function validateBirth(profile_id: string, claim_token: string, answers: QuestionnaireAnswer) {
  return apiPost('/api/v1/birth/validate', { profile_id, claim_token, answers });
}

export async function interpretProfile(profile_id: string, language: 'id' | 'en') {
  return apiPost('/api/v1/interpretation', { profile_id, language });
}

export async function getFullInterpretation(interpretation_id: string) {
  return apiGet(`/api/v1/interpretations/${encodeURIComponent(interpretation_id)}/full`);
}

export async function askHermexDetail(profile_id: string, language: 'id' | 'en', question: string) {
  return apiPost('/api/v1/interpretation/ask', { profile_id, language, question });
}

export async function submitFeedback(payload: {
  profile_id?: string;
  interpretation_id?: string;
  rating: number;
  message?: string;
  source?: string;
}) {
  return apiPost('/api/v1/feedback', payload);
}

export async function getAuthMe() {
  return apiGet<{ authenticated: boolean; user: null | { name?: string; email?: string; picture?: string } }>('/api/v1/auth/me');
}

export async function getEntitlement() {
  return apiGet<{
    plan: string;
    status: string;
    authenticated: boolean;
    source: string;
    current_period_end?: string | null;
    limits: {
      requests_per_minute: number;
      requests_per_day: number;
      max_tokens: number;
    };
  }>('/api/v1/entitlement');
}

export async function syncUserHistory(profile_claims: Array<{ profile_id: string; claim_token: string }>) {
  return apiPost('/api/v1/user/history/sync', { profile_claims });
}

export async function getUserHistory() {
  return apiGet<{ history: Array<{
    profile_id: string;
    display_name?: string;
    birth_place: string;
    created_at: string;
    dominant: string;
    profile: unknown;
    interpretation?: unknown;
    linked_at?: string;
    public_username?: string | null;
    is_public?: boolean;
  }> }>('/api/v1/user/history');
}

export async function getProfileSettings(profile_id: string) {
  return apiGet<{ profile_id: string; username: string | null; is_public: boolean; public_url: string | null }>(`/api/v1/user/profile-settings/${encodeURIComponent(profile_id)}`);
}

export async function updateProfileSettings(profile_id: string, payload: { username: string; is_public: boolean }) {
  return apiPatch(`/api/v1/user/profile-settings/${encodeURIComponent(profile_id)}`, payload);
}

export async function deleteUserHistory(profile_id: string) {
  return apiDelete(`/api/v1/user/history/${encodeURIComponent(profile_id)}`);
}
