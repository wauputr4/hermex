<script lang="ts">
  import { page } from '$app/stores';

  $: notFound = $page.status === 404;
</script>

<svelte:head>
  <title>{notFound ? 'Halaman tidak ditemukan' : 'Ada kendala'} · Hermex</title>
  <meta name="robots" content="noindex" />
</svelte:head>

<main>
  <a class="brand" href="/" aria-label="Kembali ke beranda Hermex"><span aria-hidden="true">☆</span> hermex.fun</a>
  <section>
    <p class="code">{$page.status}</p>
    <h1>{notFound ? 'Halaman ini belum terbaca.' : 'Hermex sedang terkendala.'}</h1>
    <p>{notFound ? 'Cek kembali alamatnya atau mulai dari halaman utama.' : 'Muat ulang halaman. Kalau masih terjadi, kembali beberapa saat lagi.'}</p>
    <div class="actions">
      <a href="/"><span aria-hidden="true">←</span> Ke halaman utama</a>
      {#if !notFound}<button type="button" on:click={() => location.reload()}><span aria-hidden="true">↻</span> Muat ulang</button>{/if}
    </div>
  </section>
</main>

<style>
  :global(body) { margin: 0; background: #fbfaf6; color: #302a36; font-family: 'Avenir Next', 'Nunito', system-ui, sans-serif; }
  main { width: min(760px, calc(100% - 32px)); min-height: 100vh; margin: auto; }
  .brand { display: flex; align-items: center; gap: 10px; min-height: 78px; border-bottom: 1px solid #e7e1d9; color: inherit; font-weight: 820; text-decoration: none; }
  .brand span { display: grid; width: 34px; height: 34px; place-items: center; border-radius: 11px; background: #fff0ce; color: #5b55d6; font-size: 1.25rem; }
  section { display: grid; min-height: calc(100vh - 120px); align-content: center; padding: 28px 0 70px; }
  .code { margin: 0 0 14px; color: #5b55d6; font-size: .82rem; font-weight: 900; letter-spacing: .16em; }
  h1 { max-width: 700px; margin: 0; font-size: clamp(3rem, 10vw, 6rem); line-height: .95; letter-spacing: -.06em; }
  section > p:not(.code) { max-width: 580px; margin: 24px 0; color: #615968; font-size: 1.08rem; line-height: 1.65; }
  .actions { display: flex; flex-wrap: wrap; gap: 10px; }
  .actions a, .actions button { display: inline-flex; align-items: center; gap: 8px; border: 1px solid #5b55d6; border-radius: 12px; padding: 12px 16px; background: #5b55d6; color: #fff; font: inherit; font-weight: 780; text-decoration: none; cursor: pointer; }
  .actions button { background: transparent; color: #5b55d6; }
  .actions :is(a, button):focus-visible { outline: 3px solid #5b55d6; outline-offset: 3px; }
</style>
