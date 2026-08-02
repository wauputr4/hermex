import type { PageLoad } from './$types';
import { API_BASE } from '$lib/api/hermex';

export const load: PageLoad = async ({ fetch }) => {
  try {
    const response = await fetch(`${API_BASE}/api/v1/sky-news`);
    return { posts: response.ok ? (await response.json()).posts || [] : [] };
  } catch {
    return { posts: [] };
  }
};
