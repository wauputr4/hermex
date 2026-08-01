import type { PageLoad } from './$types';
import { API_BASE } from '$lib/api/hermex';
import { articleMeta } from '$lib/articleMeta';

export const load: PageLoad = async ({ fetch, params, url }) => {
  const response = await fetch(`${API_BASE}/api/v1/sky-news`);
  if (!response.ok) return { post: null, posts: [], meta: null, ogUrl: '' };

  const posts = (await response.json()).posts || [];
  const post = posts.find((item: any) => item.slug === params.slug) || null;
  const meta = articleMeta[params.slug] || null;
  const query = new URLSearchParams({
    title: post?.title || 'Berita dari Langit',
    month: post?.tag?.split(' · ')[0] || '',
    entity: meta?.entity || '',
    aspect: meta?.aspect || ''
  });

  return { post, posts, meta, ogUrl: `${url.origin}/berita-langit/${params.slug}/og.svg?${query}` };
};
