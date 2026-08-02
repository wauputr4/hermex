import type { PageLoad } from './$types';
import { error } from '@sveltejs/kit';
import { API_BASE } from '$lib/api/hermex';
import { articleMeta } from '$lib/articleMeta';

export const load: PageLoad = async ({ fetch, params, url }) => {
  try {
    const response = await fetch(`${API_BASE}/api/v1/sky-news`);
    if (!response.ok) return { post: null, posts: [], meta: null, ogUrl: '' };
    const posts = (await response.json()).posts || [];
    const post = posts.find((item: any) => item.slug === params.slug);
    if (!post) throw error(404, 'Artikel belum tersedia.');
    return { post, posts, meta: articleMeta[params.slug] || null, ogUrl: `${url.origin}/berita-langit/${params.slug}/og.svg` };
  } catch (cause) {
    if (cause && typeof cause === 'object' && 'status' in cause && (cause as { status: number }).status === 404) throw cause;
    return { post: null, posts: [], meta: null, ogUrl: '' };
  }
};
