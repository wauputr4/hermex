export const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:5667';

export type BirthPayload = {
  display_name?: string;
  birth_date: string;
  birth_time?: string;
  birth_place: string;
  latitude?: number;
  longitude?: number;
  timezone?: string;
};

export async function apiPost<T>(path: string, payload: unknown): Promise<T> {
  if (typeof navigator !== 'undefined' && !navigator.onLine) {
    throw new Error('Hermex is offline. Saved guest history and education are still available.');
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.json() as Promise<T>;
}

export async function apiGet<T>(path: string): Promise<T> {
  if (typeof navigator !== 'undefined' && !navigator.onLine) {
    throw new Error('Hermex is offline. Saved guest history and education are still available.');
  }

  const response = await fetch(`${API_BASE}${path}`, { credentials: 'include' });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.json() as Promise<T>;
}

export async function apiDelete<T>(path: string): Promise<T> {
  if (typeof navigator !== 'undefined' && !navigator.onLine) {
    throw new Error('Hermex is offline. Saved guest history and education are still available.');
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method: 'DELETE',
    credentials: 'include'
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.json() as Promise<T>;
}

export async function analyzeBirth(payload: BirthPayload) {
  return apiPost('/api/v1/birth/analyze', payload);
}

export async function getProfile(profile_id: string) {
  return apiGet(`/api/v1/profiles/${profile_id}`);
}

export async function publishPublicProfile(payload: {
  profile_id: string;
  username: string;
  email: string;
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

export async function validateBirth(profile_id: string, answers: Record<string, string>) {
  return apiPost('/api/v1/birth/validate', { profile_id, answers });
}

export async function interpretProfile(profile_id: string, language: 'id' | 'en') {
  return apiPost('/api/v1/interpretation', { profile_id, language });
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
  }> }>('/api/v1/user/history');
}

export async function deleteUserHistory(profile_id: string) {
  return apiDelete(`/api/v1/user/history/${encodeURIComponent(profile_id)}`);
}
