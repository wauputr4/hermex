import type { PageLoad } from './$types';
import { API_BASE } from '$lib/api/hermex';
import { redirect } from '@sveltejs/kit';

export const load: PageLoad = async ({ fetch, params }) => {
  const username = decodeURIComponent(params.slug);
  if (username.startsWith('@')) redirect(308, `/${encodeURIComponent(username.slice(1))}`);
  const response = await fetch(`${API_BASE}/api/v1/public-profiles/${encodeURIComponent(username)}`, {
    credentials: 'include'
  });
  if (!response.ok) return { username, publicProfile: null, error: response.status === 403 ? 'Profil ini private.' : 'Profil ini belum tersedia.' };

  return { username, publicProfile: await response.json(), error: '' };
};
