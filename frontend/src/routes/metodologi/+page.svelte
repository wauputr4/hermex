<script lang="ts">
  const steps = [
    {
      icon: 'orbit',
      title: 'Pola lahirmu dihitung',
      body: 'Tanggal, jam, dan lokasi lahir dipakai untuk menghitung posisi benda langit serta hubungan antarbagiannya. Jika jam lahir kosong, Hermex memakai pukul 00.00 dan menandai hasilnya sebagai perkiraan.'
    },
    {
      icon: 'spark',
      title: 'Dua sumber dibaca bersama',
      body: 'AI membandingkan pola lahir dengan jawabanmu. Hasilnya merangkum bagian yang selaras, bagian yang terasa bertentangan, dan arah refleksi yang bisa kamu lanjutkan.'
    },
    {
      icon: 'boundary',
      title: 'Hasil tetap milikmu untuk ditimbang',
      body: 'Hermex tidak memberi diagnosis atau kepastian tentang masa depan. Gunakan hasil sebagai bahan mengenali diri, bukan pengganti saran medis, psikologis, hukum, keuangan, atau keputusan penting.'
    }
  ];
</script>

<svelte:head>
  <title>Metodologi Analisis — Hermex</title>
  <meta name="description" content="Cara Hermex menggabungkan pola kelahiran dan jawabanmu menjadi analisis reflektif." />
  <link rel="canonical" href="https://hermex.fun/metodologi" />
</svelte:head>

<main>
  <header>
    <a class="brand" href="/" aria-label="Kembali ke Hermex">
      <svg viewBox="0 0 48 48" aria-hidden="true"><path d="M24 5l5 12 13 2-10 8 3 13-11-7-11 7 3-13-10-8 13-2 5-12z" /></svg>
      <span>hermex.fun</span>
    </a>
    <a class="back" href="/"><span aria-hidden="true">←</span> Kembali</a>
  </header>

  <section class="hero">
    <div>
      <p class="eyebrow">Metodologi</p>
      <h1>Dari data lahir sampai jadi bahan mengenali diri</h1>
    </div>
    <p class="lead">Hermex membuat <strong>natal chart</strong>—peta posisi benda langit saat kamu lahir—lalu membandingkan pola simboliknya dengan jawabanmu. Bukan untuk menebak hidupmu, tapi membantu melihat pola yang mungkin luput.</p>
  </section>

  <section class="plain-guide" aria-labelledby="plain-guide-title">
    <div class="guide-title"><p class="eyebrow">Versi singkatnya</p><h2 id="plain-guide-title">Natal chart itu apa?</h2></div>
    <div class="guide-copy">
      <p>Bayangkan langit seperti foto 360° yang diambil tepat ketika kamu lahir. Tanggal dan jam menentukan posisi planet; lokasi menentukan bagian langit yang sedang naik di ufuk dan pembagian dua belas rumah.</p>
      <p>Hermex memakai Swiss Ephemeris untuk menghitung posisi tersebut. Sesudah itu, jarak sudut antarplanet dikelompokkan sebagai aspek, misalnya konjungsi, trine, square, dan opposition. Tradisi astrologi memberi makna simbolik pada susunan ini; AI membantu merangkumnya dengan jawaban kuesionermu.</p>
    </div>
  </section>

  <section class="path" aria-label="Proses analisis Hermex">
    {#each steps as step}
      <article>
        <span class="step-icon" aria-hidden="true">
          {#if step.icon === 'orbit'}
            <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3" /><ellipse cx="12" cy="12" rx="9" ry="4.5" transform="rotate(-28 12 12)" /><circle class="fill" cx="19" cy="8" r="1.7" /></svg>
          {:else if step.icon === 'spark'}
            <svg viewBox="0 0 24 24"><path d="m12 3 1.7 5.3L19 10l-5.3 1.7L12 17l-1.7-5.3L5 10l5.3-1.7L12 3Z" /><path d="m18.5 16 .7 2.3 2.3.7-2.3.7-.7 2.3-.7-2.3-2.3-.7 2.3-.7.7-2.3Z" /></svg>
          {:else}
            <svg viewBox="0 0 24 24"><path d="M12 3 5 6v5c0 4.7 2.8 8 7 10 4.2-2 7-5.3 7-10V6l-7-3Z" /><path d="m9 12 2 2 4-4" /></svg>
          {/if}
        </span>
        <div><h2>{step.title}</h2><p>{step.body}</p></div>
      </article>
    {/each}
  </section>

  <aside>
    <span aria-hidden="true">✦</span>
    <div><h2>Yang kamu lihat adalah interpretasi, bukan vonis</h2><p>Kalau satu bagian tidak terasa cocok, anggap itu undangan untuk bertanya—bukan sesuatu yang harus kamu percaya.</p></div>
  </aside>

  <section class="references" aria-labelledby="references-title">
    <p class="eyebrow">Baca sumbernya</p>
    <h2 id="references-title">Perhitungan nyata, interpretasi tetap perlu ditimbang</h2>
    <p>Posisi benda langit dapat dihitung secara astronomis. Namun, klaim bahwa natal chart dapat menjelaskan kepribadian secara akurat belum didukung bukti ilmiah yang kuat. Karena itu Hermex menempatkan hasilnya sebagai alat refleksi.</p>
    <ul>
      <li><a href="https://www.astro.com/swisseph-download/doc/swisseph.htm" target="_blank" rel="noreferrer">Dokumentasi Swiss Ephemeris</a><span>Cara posisi planet, Ascendant, dan rumah dihitung oleh mesin yang dipakai Hermex.</span></li>
      <li><a href="https://ssd.jpl.nasa.gov/planets/orbits.html" target="_blank" rel="noreferrer">JPL NASA: Planetary Orbits &amp; Ephemerides</a><span>Latar astronomi tentang ephemeris atau tabel posisi benda langit.</span></li>
      <li><a href="https://www.nature.com/articles/318419a0.pdf" target="_blank" rel="noreferrer">Nature: A double-blind test of astrology</a><span>Penelitian terkontrol mengenai klaim natal chart dan kepribadian.</span></li>
    </ul>
  </section>

  <footer><span>© {new Date().getFullYear()} Hermex</span><nav aria-label="Tautan legal"><a href="/terms">Terms</a><a href="/privacy">Privacy</a></nav></footer>
</main>

<style>
  :global(body) { margin: 0; background: #fbfaf6; color: #302a36; font-family: 'Avenir Next', 'Nunito', 'Trebuchet MS', sans-serif; }
  :global(*) { box-sizing: border-box; }
  main { width: min(1000px, calc(100% - 40px)); min-height: 100vh; margin: auto; }
  header { display: flex; min-height: 84px; align-items: center; justify-content: space-between; border-bottom: 1px solid #e7e1d9; }
  .brand { display: flex; align-items: center; gap: 10px; color: #302a36; font-size: 1.1rem; font-weight: 820; text-decoration: none; }
  .brand svg { width: 34px; height: 34px; padding: 6px; border-radius: 11px; background: #fff0ce; fill: #f1b86a; stroke: #302a36; stroke-width: 1.5; }
  .back { display: inline-flex; align-items: center; gap: 7px; color: #5b55d6; font-size: .88rem; font-weight: 760; text-decoration: none; }
  .hero { display: grid; grid-template-columns: 1.15fr .85fr; gap: clamp(30px, 7vw, 90px); align-items: end; padding: clamp(70px, 11vw, 128px) 0 64px; }
  .eyebrow { margin: 0 0 12px; color: #5b55d6; font-size: .78rem; font-weight: 850; letter-spacing: .12em; text-transform: uppercase; }
  h1 { max-width: 700px; margin: 0; font-size: clamp(2.8rem, 7vw, 5.6rem); line-height: .94; letter-spacing: -.06em; }
  .lead { margin: 0 0 6px; color: #615968; font-size: clamp(1rem, 2vw, 1.15rem); line-height: 1.7; }
  .path { border-top: 1px solid #e7e1d9; }
  .plain-guide { display: grid; grid-template-columns: .7fr 1.3fr; gap: clamp(30px, 7vw, 90px); margin-bottom: 64px; border: 1px solid #e7e1d9; border-radius: 24px; padding: clamp(24px, 5vw, 42px); background: #fff; }
  .plain-guide h2, .references h2 { margin: 0; font-size: clamp(1.8rem, 4vw, 3rem); line-height: 1.05; letter-spacing: -.04em; }
  .guide-copy p, .references > p:not(.eyebrow) { margin: 0 0 14px; color: #615968; line-height: 1.72; }
  article { display: grid; grid-template-columns: 64px 1fr; gap: 22px; padding: 34px 0; border-bottom: 1px solid #e7e1d9; }
  .step-icon { display: grid; width: 54px; height: 54px; place-items: center; border-radius: 17px; background: #fff0ce; color: #5b55d6; }
  .step-icon svg { width: 29px; fill: none; stroke: currentColor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 1.6; }
  .step-icon .fill { fill: #f1b86a; stroke: #302a36; }
  article h2, aside h2 { margin: 0 0 9px; font-size: clamp(1.35rem, 3vw, 1.8rem); letter-spacing: -.025em; }
  article p, aside p { max-width: 730px; margin: 0; color: #615968; font-size: 1rem; line-height: 1.72; }
  aside { display: flex; gap: 18px; margin: 64px 0; border-radius: 24px; padding: clamp(24px, 5vw, 42px); background: #302a36; color: #fff; }
  aside > span { color: #f1b86a; font-size: 2rem; }
  aside p { color: #dcd5df; }
  .references { margin: 64px 0; }
  .references > p:not(.eyebrow) { max-width: 760px; margin-top: 18px; }
  .references ul { display: grid; gap: 10px; margin: 28px 0 0; padding: 0; list-style: none; }
  .references li { display: grid; grid-template-columns: minmax(220px, .7fr) 1.3fr; gap: 18px; border-top: 1px solid #e7e1d9; padding: 18px 0; }
  .references li:last-child { border-bottom: 1px solid #e7e1d9; }
  .references a { color: #5b55d6; font-weight: 780; }
  .references li span { color: #615968; line-height: 1.55; }
  footer { display: flex; min-height: 100px; align-items: center; justify-content: space-between; border-top: 1px solid #e7e1d9; color: #7d7581; font-size: .85rem; }
  footer nav { display: flex; gap: 20px; }
  footer a { color: inherit; text-decoration: none; }
  a:focus-visible { outline: 3px solid rgba(91,85,214,.25); outline-offset: 4px; border-radius: 4px; }
  @media (max-width: 680px) { main { width: min(100% - 28px, 1000px); } header { min-height: 68px; } .hero, .plain-guide { grid-template-columns: 1fr; } .hero { padding: 58px 0 44px; } h1 { font-size: clamp(2.65rem, 14vw, 4.2rem); } article { grid-template-columns: 48px 1fr; gap: 14px; padding: 28px 0; } .step-icon { width: 44px; height: 44px; border-radius: 14px; } .step-icon svg { width: 24px; } aside { margin: 42px 0; } .references li { grid-template-columns: 1fr; gap: 6px; } }
</style>
