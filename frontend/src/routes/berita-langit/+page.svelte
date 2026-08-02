<script lang="ts">
  export let data: { posts: any[] };
</script>

<svelte:head><title>Berita Langit — Hermex Fun</title><meta name="description" content="Arsip bulanan kejadian yang benar-benar terjadi dan kaitannya dengan peristiwa langit." /></svelte:head>

<main>
  <nav><a href="/">☆ hermex.fun | analisis kepribadian</a></nav>
  <header><p>BERITA LANGIT</p><h1>Yang terjadi, dibaca dari langit</h1><span>Arsip bulanan kejadian yang benar-benar terjadi dan kaitannya dengan peristiwa langit setelah kejadian.</span></header>
  <section aria-label="Daftar artikel">
    {#each data.posts as post}
      <a href={`/berita-langit/${post.slug}`}>
        <small>{post.tag}</small><h2>{post.title}</h2><p>{post.summary}</p><span>Baca artikel →</span>
      </a>
    {/each}
  </section>
</main>

<style>
  main { width: min(1120px, calc(100% - 32px)); min-height: 100vh; margin: auto; color: #302a36; }
  nav { display: flex; align-items: center; min-height: 76px; border-bottom: 1px solid #e7e1d9; }
  nav a { color: inherit; font-weight: 820; text-decoration: none; }
  header { max-width: 820px; padding: 80px 0 52px; }
  header p, small { color: #5b55d6; font-size: .75rem; font-weight: 820; letter-spacing: .08em; text-transform: uppercase; }
  h1 { margin: 0 0 18px; font-size: clamp(3rem, 8vw, 6.6rem); line-height: .9; letter-spacing: -.07em; }
  header span, section p { color: #6f6873; line-height: 1.55; }
  section { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; padding-bottom: 80px; }
  section a { display: grid; align-content: start; min-height: 260px; border: 1px solid #e7e1d9; border-radius: 20px; padding: 22px; background: #fff; color: inherit; text-decoration: none; }
  section h2 { margin: 14px 0 4px; font-size: 1.35rem; letter-spacing: -.03em; }
  section a > span { margin-top: auto; color: #5b55d6; font-weight: 800; }
  @media (max-width: 760px) { header { padding-top: 54px; } section { grid-template-columns: 1fr; } }
</style>
