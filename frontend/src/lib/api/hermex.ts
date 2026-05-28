export const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

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
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.json() as Promise<T>;
}

export async function analyzeBirth(payload: BirthPayload) {
  return apiPost('/api/v1/birth/analyze', payload);
}

export async function validateBirth(profile_id: string, answers: Record<string, string>) {
  return apiPost('/api/v1/birth/validate', { profile_id, answers });
}

export async function interpretProfile(profile_id: string, language: 'id' | 'en') {
  return apiPost('/api/v1/interpretation', { profile_id, language });
}
