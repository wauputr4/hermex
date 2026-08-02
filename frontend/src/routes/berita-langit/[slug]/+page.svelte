<script lang="ts">
  type Block = { type: 'heading' | 'event' | 'paragraph'; text: string };
  export let data: any;
  let post: any;
  let posts: any[];
  let meta: any;
  let ogUrl = '';

  $: ({ post, posts, meta, ogUrl } = data);
  $: month = String(post?.tag || '').split(' · ')[0];
  $: cleanedBody = String(post?.body || '').split(/\n\n## (?:Sumber|Cara membaca)/)[0];
  $: blocks = cleanedBody.split(/\n+/).map((text): Block => {
    const clean = text.trim();
    if (clean.startsWith('## ')) return { type: 'heading', text: clean.slice(3).replace('Pembacaan setelah kejadian', 'Kaitannya dengan langit') };
    if (/^\d{1,2}(?:–\d{1,2})?\s/.test(clean)) return { type: 'event', text: clean };
    return { type: 'paragraph', text: clean };
  }).filter((block) => block.text);
</script>

<svelte:head>
  <title>{post?.title || 'Berita Langit'} · Hermex</title>
  {#if post}
    <meta name="description" content={post.summary || post.title} />
    <meta property="og:title" content={`${post.title} · Hermex`} />
    <meta property="og:description" content={post.summary || post.title} />
    <meta property="og:type" content="article" />
    <meta property="og:image" content={ogUrl} />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:image" content={ogUrl} />
  {/if}
</svelte:head>

<main>
  <nav aria-label="Navigasi artikel">
    <a class="brand" href="/"><span aria-hidden="true">☆</span> Hermex</a>
    <a class="back" href="/">← Kembali</a>
  </nav>

  {#if !post}
    <section class="status"><p class="kicker">404</p><h1>Artikelnya belum ada.</h1><a class="button" href="/"><span aria-hidden="true">←</span> Kembali ke Hermex</a></section>
  {:else}
    <article>
      <header class="hero">
        <p class="kicker">Berita dari Langit · Sudah terjadi</p>
        <h1>{post.title}</h1>
        <p class="dek">{post.summary}</p>
        <div class="meta"><span>{month}</span><span>{meta?.entity}</span><span>{meta?.aspect}</span><span>2 menit baca</span></div>
      </header>

      <div class="article-layout">
        <aside aria-label="Tentang artikel">
          <span class="orb" aria-hidden="true"></span>
          <strong>Bukan ramalan</strong>
          <p>Kejadiannya sudah lewat. Sekarang kita lihat pola langit yang ikut muncul.</p>
        </aside>

        <div class="body">
          {#if meta?.timeline?.length > 1}
            <section class="timeline" aria-labelledby="timeline-title">
              <p class="timeline-label">Urutan kejadian</p>
              <h2 id="timeline-title">Dari satu tanggal ke tanggal berikutnya</h2>
              <ol>
                {#each meta.timeline as item}
                  <li><time>{item.date}</time><span>{item.text}</span></li>
                {/each}
              </ol>
            </section>
          {/if}
          {#each blocks as block}
            {#if block.type === 'heading'}
              <h2>{block.text}</h2>
            {:else if block.type === 'event'}
              <p class="event">{block.text}</p>
            {:else}
              <p>{block.text}</p>
            {/if}
          {/each}
        </div>
      </div>

      <footer class="methodology">
        <strong>Metodologi kurasi</strong>
        <p>Hermex memilih kejadian yang sudah berlangsung, mengecek faktanya, lalu membacanya bersama pola langit yang dibahas setelah kejadian. Ini bacaan reflektif, bukan sebab-akibat.</p>
      </footer>

      {#if posts.length > 1}
        <section class="archive" aria-labelledby="archive-title">
          <p class="kicker">Arsip bulanan</p>
          <h2 id="archive-title">Baca bulan lainnya</h2>
          <div class="archive-grid">
            {#each posts.filter((item) => item.slug !== post.slug && /^(Agustus|September|Oktober|November|Desember|Januari|Februari|Maret|April|Mei|Juni|Juli) 20\d\d/.test(item.tag)).slice(0, 12) as item}
              <a href={`/berita-langit/${item.slug}`}><small>{item.tag.split(' · ')[0]}</small><strong>{item.title.split(': ')[1] || item.title}</strong></a>
            {/each}
          </div>
        </section>
      {/if}
    </article>
  {/if}
</main>

<style>
  :global(body) { margin: 0; background: #fbfaf7; color: #302a36; font-family: 'Avenir Next', 'Nunito', system-ui, sans-serif; }
  main { width: min(1120px, calc(100% - 40px)); margin: auto; }
  nav { display: flex; justify-content: space-between; align-items: center; min-height: 78px; border-bottom: 1px solid #e7e2dc; }
  nav a { color: inherit; text-decoration: none; font-weight: 800; }
  .brand { display: flex; align-items: center; gap: 10px; font-size: 1.12rem; }
  .brand span { display: grid; width: 36px; height: 36px; place-items: center; border-radius: 12px; background: #fff0c9; color: #5b55d6; font-size: 1.35rem; }
  .back { color: #615968; }
  article { padding: clamp(64px, 10vw, 120px) 0 90px; }
  .hero { max-width: 920px; padding-bottom: clamp(52px, 8vw, 86px); }
  .kicker { margin: 0 0 18px; color: #5b55d6; font-size: .78rem; font-weight: 900; letter-spacing: .14em; text-transform: uppercase; }
  h1 { max-width: 900px; margin: 0; font-size: clamp(3.4rem, 9vw, 7.8rem); line-height: .95; letter-spacing: -.065em; }
  .dek { max-width: 760px; margin: 30px 0; color: #615968; font-size: clamp(1.15rem, 2.2vw, 1.5rem); line-height: 1.55; }
  .meta { display: flex; flex-wrap: wrap; gap: 10px 22px; color: #746c79; font-size: .88rem; font-weight: 750; }
  .meta span + span::before { content: '•'; margin-right: 22px; color: #f1b86a; }
  .article-layout { display: grid; grid-template-columns: 230px minmax(0, 690px); gap: clamp(48px, 8vw, 110px); border-top: 1px solid #e7e2dc; padding-top: 54px; }
  aside { position: sticky; top: 28px; align-self: start; color: #615968; line-height: 1.55; }
  aside strong { display: block; margin: 18px 0 7px; color: #302a36; }
  aside p { margin: 0; font-size: .9rem; }
  .orb { display: block; width: 48px; height: 48px; border: 2px solid #5b55d6; border-radius: 50%; box-shadow: inset 14px -7px 0 #fff0c9; }
  .body { position: relative; }
  .body::before { content: ''; position: absolute; left: -34px; top: 8px; bottom: 0; width: 1px; background: #ded8e7; }
  .body h2 { position: relative; margin: 72px 0 16px; font-size: clamp(1.8rem, 4vw, 2.55rem); letter-spacing: -.04em; }
  .body h2:first-child { margin-top: 0; }
  .body h2::before { content: ''; position: absolute; left: -40px; top: .42em; width: 11px; height: 11px; border: 3px solid #fbfaf7; border-radius: 50%; background: #5b55d6; }
  .body p { margin: 0 0 22px; color: #514a57; font-family: Georgia, 'Times New Roman', serif; font-size: 1.12rem; line-height: 1.85; }
  .body .event { color: #302a36; font-family: inherit; font-size: .95rem; font-weight: 800; line-height: 1.55; }
  .timeline { margin: 0 0 62px; padding: 24px; border-radius: 20px; background: #f2efff; }
  .timeline h2 { margin: 5px 0 22px; font-size: clamp(1.55rem, 3vw, 2.1rem); }
  .timeline h2::before { display: none; }
  .timeline-label { margin: 0 !important; color: #5b55d6 !important; font-family: inherit !important; font-size: .76rem !important; font-weight: 900; letter-spacing: .12em; text-transform: uppercase; }
  .timeline ol { display: grid; gap: 0; margin: 0; padding: 0; list-style: none; }
  .timeline li { display: grid; grid-template-columns: 120px 1fr; gap: 18px; padding: 16px 0; border-top: 1px solid #dcd6f4; }
  .timeline time { color: #5b55d6; font-weight: 900; }
  .timeline li span { line-height: 1.5; }
  .methodology { display: grid; grid-template-columns: 220px minmax(0, 690px); gap: clamp(48px, 8vw, 120px); margin-top: 72px; padding: 28px 0; border-block: 1px solid #e7e2dc; }
  .methodology strong { font-size: 1.05rem; }
  .methodology p { margin: 0; color: #615968; line-height: 1.65; }
  .status { display: grid; min-height: 70vh; place-content: center; justify-items: center; text-align: center; }
  .archive { margin-top: 90px; padding-top: 52px; border-top: 1px solid #e7e2dc; }
  .archive h2 { margin: 0 0 24px; font-size: clamp(2rem, 5vw, 3.5rem); letter-spacing: -.05em; }
  .archive-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
  .archive-grid a { display: grid; gap: 8px; min-height: 110px; padding: 18px; border: 1px solid #e7e2dc; border-radius: 16px; color: inherit; text-decoration: none; }
  .archive-grid a:hover { border-color: #5b55d6; }
  .archive-grid small { color: #5b55d6; font-weight: 850; }
  .archive-grid strong { line-height: 1.35; }
  .status h1 { max-width: 700px; font-size: clamp(2.5rem, 8vw, 5rem); }
  .button { display: inline-flex; align-items: center; gap: 8px; margin-top: 26px; padding: 13px 20px; border-radius: 14px; background: #5b55d6; color: white; text-decoration: none; font-weight: 800; }
  a:focus-visible { border-radius: 6px; outline: 3px solid rgba(91,85,214,.28); outline-offset: 4px; }
  @media (max-width: 720px) {
    main { width: min(100% - 32px, 1120px); }
    nav { min-height: 68px; }
    article { padding-top: 58px; }
    h1 { font-size: clamp(3rem, 15vw, 5.2rem); line-height: 1; letter-spacing: -.055em; }
    .meta span + span::before { margin-right: 10px; }
    .article-layout { grid-template-columns: 1fr; gap: 44px; padding-top: 38px; }
    aside { position: static; padding: 18px; border-radius: 16px; background: #f3f0eb; }
    .orb { float: left; margin-right: 15px; }
    aside strong { margin-top: 0; }
    .body { padding-left: 24px; }
    .body::before { left: 0; }
    .body h2::before { left: -30px; }
    .timeline li { grid-template-columns: 1fr; gap: 4px; }
    .methodology { grid-template-columns: 1fr; gap: 10px; }
    .archive-grid { grid-template-columns: 1fr; }
  }
</style>
