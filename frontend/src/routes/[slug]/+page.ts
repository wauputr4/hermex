import type { PageLoad } from './$types';
import { API_BASE } from '$lib/api/hermex';
import { redirect } from '@sveltejs/kit';

export const load: PageLoad = async ({ fetch, params }) => {
  if (params.slug.startsWith('@')) redirect(308, `/${params.slug.slice(1)}`);

  const username = decodeURIComponent(params.slug);
  const response = await fetch(`${API_BASE}/api/v1/public-profiles/${encodeURIComponent(username)}`, {
    credentials: 'include'
  });
  if (!response.ok) return { username, publicProfile: null, error: response.status === 403 ? 'Profil ini private.' : 'Profil ini belum tersedia.' };

  return { username, publicProfile: await response.json(), error: '' };
};
