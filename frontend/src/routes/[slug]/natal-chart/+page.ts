import type { PageLoad } from './$types';
import { API_BASE } from '$lib/api/hermex';
import { redirect } from '@sveltejs/kit';

export const load: PageLoad = async ({ fetch, params }) => {
  const username = decodeURIComponent(params.slug);
  if (username.startsWith('@')) redirect(308, `/${encodeURIComponent(username.slice(1))}/natal-chart`);
  const response = await fetch(`${API_BASE}/api/v1/public-profiles/${encodeURIComponent(username)}`, { credentials: 'include' });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    return { username, publicProfile: null, error: response.status === 403 || /private/i.test(body?.detail ?? '') ? 'Profil ini private.' : 'Profil belum ketemu.' };
  }
  return { username, publicProfile: await response.json(), error: '' };
};
