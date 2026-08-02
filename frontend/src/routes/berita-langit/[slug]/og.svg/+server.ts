import type { RequestHandler } from './$types';
import { API_BASE, fetchWithTimeout } from '$lib/api/hermex';
import { articleMeta } from '$lib/articleMeta';

const escapeXml = (value: string) => value.replace(/[<>&'\"]/g, (char) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', "'": '&apos;', '"': '&quot;' })[char] || char);
const wrap = (value: string, limit = 26) => {
  const lines: string[] = [];
  for (const word of value.split(/\s+/)) {
    const last = lines.at(-1);
    if (!last || `${last} ${word}`.length > limit) lines.push(word);
    else lines[lines.length - 1] = `${last} ${word}`;
  }
  return lines.slice(0, 4);
};

export const GET: RequestHandler = async ({ fetch, params }) => {
  let post: any = null;
  try {
    const response = await fetchWithTimeout(fetch, `${API_BASE}/api/v1/sky-news`);
    if (response.ok) post = ((await response.json()).posts || []).find((item: any) => item.slug === params.slug);
  } catch {
    // The fallback still produces a valid image if the API is unavailable.
  }
  const meta = articleMeta[params.slug];
  const title = wrap(post?.title || 'Berita dari Langit').map(escapeXml);
  const month = escapeXml(post?.tag?.split(' · ')[0] || 'Hermex');
  const entity = escapeXml(meta?.entity || 'Peristiwa terpilih');
  const aspect = escapeXml(meta?.aspect || 'Catatan langit');
  const titleSvg = title.map((line, index) => `<text x="86" y="${250 + index * 92}" class="title">${line}</text>`).join('');

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
    <style>.title{font:800 76px system-ui,sans-serif;fill:#302a36;letter-spacing:-3px}.meta{font:800 24px system-ui,sans-serif;fill:#5b55d6}.small{font:700 22px system-ui,sans-serif;fill:#615968}</style>
    <rect width="1200" height="630" fill="#fbfaf7"/><circle cx="1060" cy="120" r="122" fill="#fff0c9"/><circle cx="1095" cy="92" r="92" fill="#fbfaf7"/>
    <rect x="86" y="40" width="50" height="50" rx="14" fill="#fff0c9"/><path d="M111 50l5 12 13 2-10 8 3 13-11-7-11 7 3-13-10-8 13-2 5-12z" fill="#f1b86a" stroke="#302a36" stroke-width="1.5"/>
    <text x="152" y="76" class="meta">HERMEX FUN · HERMEX.FUN</text><text x="86" y="124" class="small">BERITA DARI LANGIT</text><text x="86" y="166" class="small">${month}  ·  ${entity}  ·  ${aspect}</text>
    ${titleSvg}<path d="M86 574H1114" stroke="#5b55d6" stroke-width="4"/><text x="86" y="612" class="small">Peristiwa yang sudah terjadi, dibaca bersama langitnya.</text>
  </svg>`;
  return new Response(svg, { headers: { 'content-type': 'image/svg+xml; charset=utf-8', 'cache-control': 'public, max-age=86400' } });
};
