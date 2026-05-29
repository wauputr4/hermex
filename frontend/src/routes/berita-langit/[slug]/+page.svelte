<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { getSkyNews } from '$lib/api/hermex';

  let post: any = null;
  let relatedPosts: any[] = [];
  let loading = true;
  let error = '';

  $: slug = $page.params.slug;
  $: paragraphs = String(post?.body || '')
    .split(/\n+/)
    .map((item) => item.trim())
    .filter(Boolean);

  onMount(async () => {
    try {
      const response = await getSkyNews();
      const posts = response.posts || [];
      post = posts.find((item: any) => item.slug === slug);
      relatedPosts = posts.filter((item: any) => item.slug !== slug).slice(0, 3);
      if (!post) {
        error = 'Artikel Berita Langit tidak ditemukan.';
      }
    } catch (err) {
      error = err instanceof Error ? err.message : 'Gagal memuat Berita Langit.';
    } finally {
      loading = false;
    }
  });
</script>

<main class="article-shell">
  <section class="article-frame">
    <header class="topbar">
      <a class="brand" href="/">
        <span class="brand-mark">✧</span>
        <span>
          <small>Hermex Quest</small>
          <strong>Berita Langit</strong>
        </span>
      </a>
      <a class="home-link" href="/">Kembali ke app</a>
    </header>

    {#if loading}
      <article class="article-card loading-card">
        <div class="orbit" aria-hidden="true">
          <span></span>
          <span></span>
          <span></span>
        </div>
        <h1>Membaca langit...</h1>
        <p>Hermex sedang mengambil artikel terbaru.</p>
      </article>
    {:else if error}
      <article class="article-card">
        <p class="eyebrow">404</p>
        <h1>{error}</h1>
        <p>Artikel mungkin sudah dipindah atau slug-nya berubah dari dashboard admin.</p>
        <a class="primary-link" href="/">Buka Hermex</a>
      </article>
    {:else}
      <article class="article-card">
        <p class="eyebrow">{post.tag}</p>
        <h1>{post.title}</h1>
        <p class="summary">{post.summary}</p>

        <div class="sky-visual" aria-hidden="true">
          <svg viewBox="0 0 260 160" role="img">
            <defs>
              <linearGradient id="skyGlow" x1="0" x2="1" y1="0" y2="1">
                <stop offset="0%" stop-color="#fff0a6" />
                <stop offset="55%" stop-color="#f5bfd1" />
                <stop offset="100%" stop-color="#baf4df" />
              </linearGradient>
            </defs>
            <rect width="260" height="160" rx="34" fill="url(#skyGlow)" />
            <circle cx="128" cy="78" r="46" fill="none" stroke="#3f2a4d" stroke-width="4" stroke-dasharray="7 9" opacity=".32" />
            <path d="M128 38c-17 9-25 32-16 51 8 18 28 28 47 23-8 12-22 20-39 18-25-3-43-25-40-50 3-26 25-44 48-42Z" fill="#fff7bd" stroke="#3f2a4d" stroke-width="5" />
            <path d="m81 85 13 7 7 14 7-14 13-7-13-7-7-14-7 14-13 7Z" fill="#f59a72" stroke="#3f2a4d" stroke-width="5" />
            <circle cx="190" cy="65" r="15" fill="#79d5c3" stroke="#3f2a4d" stroke-width="5" />
            <circle cx="73" cy="57" r="12" fill="#79d5c3" stroke="#3f2a4d" stroke-width="5" />
          </svg>
        </div>

        <div class="article-body">
          {#each paragraphs as paragraph}
            <p>{paragraph}</p>
          {/each}
        </div>
      </article>

      {#if relatedPosts.length}
        <section class="related-card">
          <h2>Baca juga</h2>
          <div class="related-grid">
            {#each relatedPosts as item}
              <a href={`/berita-langit/${item.slug}`}>
                <small>{item.tag}</small>
                <strong>{item.title}</strong>
                <span>{item.summary}</span>
              </a>
            {/each}
          </div>
        </section>
      {/if}
    {/if}
  </section>
</main>

<style>
  :global(body) {
    margin: 0;
    background:
      radial-gradient(circle at top left, rgba(255, 230, 159, .75), transparent 34%),
      radial-gradient(circle at bottom right, rgba(178, 246, 222, .75), transparent 38%),
      #fffaf0;
    color: #3f2a4d;
    font-family: 'Avenir Next', 'Nunito', ui-rounded, system-ui, sans-serif;
  }

  .article-shell {
    min-height: 100vh;
    padding: 22px;
  }

  .article-frame {
    width: min(980px, 100%);
    margin: 0 auto;
    border: 8px solid rgba(63, 42, 77, .07);
    border-radius: 38px;
    background:
      radial-gradient(circle at 1px 1px, rgba(63, 42, 77, .09) 1px, transparent 0) 0 0 / 22px 22px,
      rgba(255, 253, 247, .84);
    padding: clamp(18px, 4vw, 34px);
    box-shadow: 0 30px 80px rgba(63, 42, 77, .12);
  }

  .topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 22px;
  }

  .brand,
  .home-link,
  .primary-link,
  .related-grid a {
    color: inherit;
    text-decoration: none;
  }

  .brand {
    display: inline-flex;
    align-items: center;
    gap: 12px;
    font-weight: 900;
  }

  .brand-mark {
    display: grid;
    width: 56px;
    height: 56px;
    place-items: center;
    border-radius: 18px;
    background: #fff0a6;
    font-size: 1.7rem;
  }

  .brand small,
  .eyebrow {
    display: block;
    color: #8e6b45;
    font-size: .78rem;
    font-weight: 950;
    letter-spacing: .13em;
    text-transform: uppercase;
  }

  .home-link,
  .primary-link {
    border-radius: 999px;
    background: #3f2a4d;
    color: #fff8df;
    padding: 12px 18px;
    font-weight: 900;
  }

  .article-card,
  .related-card {
    border: 1px solid rgba(63, 42, 77, .12);
    border-radius: 30px;
    background: rgba(255, 253, 247, .92);
    padding: clamp(20px, 4vw, 38px);
    box-shadow: 0 18px 50px rgba(63, 42, 77, .08);
  }

  h1 {
    max-width: 760px;
    margin: 8px 0 14px;
    font-size: clamp(2.3rem, 8vw, 5rem);
    letter-spacing: -.075em;
    line-height: .88;
  }

  .summary {
    max-width: 760px;
    margin: 0;
    color: rgba(63, 42, 77, .75);
    font-size: clamp(1.05rem, 2vw, 1.35rem);
    font-weight: 800;
    line-height: 1.45;
  }

  .sky-visual {
    margin: 28px 0;
  }

  .sky-visual svg {
    width: min(100%, 520px);
    height: auto;
    display: block;
  }

  .article-body {
    display: grid;
    gap: 18px;
    max-width: 760px;
  }

  .article-body p {
    margin: 0;
    color: rgba(63, 42, 77, .86);
    font-size: 1.05rem;
    font-weight: 700;
    line-height: 1.75;
  }

  .related-card {
    margin-top: 18px;
  }

  .related-card h2 {
    margin: 0 0 14px;
    font-size: 1.5rem;
  }

  .related-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
  }

  .related-grid a {
    display: grid;
    gap: 8px;
    border: 1px solid rgba(63, 42, 77, .1);
    border-radius: 22px;
    background: rgba(186, 244, 223, .28);
    padding: 16px;
  }

  .related-grid small {
    color: #8e6b45;
    font-weight: 950;
    text-transform: uppercase;
  }

  .related-grid strong {
    font-size: 1.05rem;
  }

  .related-grid span {
    color: rgba(63, 42, 77, .68);
    font-weight: 750;
    line-height: 1.45;
  }

  .loading-card {
    display: grid;
    min-height: 420px;
    place-items: center;
    text-align: center;
  }

  .orbit {
    position: relative;
    width: 92px;
    height: 92px;
    border: 3px dashed rgba(63, 42, 77, .25);
    border-radius: 999px;
    animation: spin 4s linear infinite;
  }

  .orbit span {
    position: absolute;
    width: 18px;
    height: 18px;
    border-radius: 999px;
    background: #79d5c3;
  }

  .orbit span:nth-child(1) { left: 8px; top: 18px; }
  .orbit span:nth-child(2) { right: 0; top: 32px; background: #f4c252; }
  .orbit span:nth-child(3) { left: 44px; bottom: 0; background: #f59a72; }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  @media (max-width: 720px) {
    .article-shell {
      padding: 10px;
    }

    .article-frame {
      border-width: 5px;
      border-radius: 28px;
    }

    .topbar,
    .related-grid {
      grid-template-columns: 1fr;
      display: grid;
    }

    .home-link {
      text-align: center;
    }
  }
</style>
