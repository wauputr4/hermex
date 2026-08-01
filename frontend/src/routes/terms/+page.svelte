<svelte:head>
  <title>Ketentuan Penggunaan | Hermex</title>
  <meta
    name="description"
    content="Ketentuan penggunaan Hermex sebagai alat refleksi dan analisa kepribadian berbantuan AI."
  />
</svelte:head>

<main>
  <header>
    <a class="brand" href="/" aria-label="Kembali ke Hermex">
      <svg viewBox="0 0 48 48" aria-hidden="true"><path d="M24 5l5 12 13 2-10 8 3 13-11-7-11 7 3-13-10-8 13-2 5-12z" /></svg>
      <span>Hermex</span>
    </a>
    <a class="back" href="/"><span aria-hidden="true">←</span> Kembali ke beranda</a>
  </header>

  <article>
    <div class="intro">
      <p class="eyebrow">Ketentuan penggunaan</p>
      <h1>Gunakan hasilnya sebagai bahan refleksi.</h1>
      <p class="lead">
        Hermex membantu membaca pola kepribadian dari data kelahiran dan jawabanmu.
        Dengan menggunakan layanan ini, kamu menyetujui ketentuan berikut.
      </p>
      <p class="updated">Diperbarui 1 Agustus 2026</p>
    </div>

    <div class="terms">
      <section>
        <span>01</span>
        <div><h2>Bukan nasihat profesional</h2><p>Hasil Hermex bersifat reflektif dan dapat mengandung kekeliruan. Jangan menjadikannya pengganti nasihat medis, psikologis, hukum, keuangan, atau keputusan penting lainnya.</p></div>
      </section>

      <section>
        <span>02</span>
        <div><h2>Penggunaan sebagai tamu</h2><p>Kamu dapat mencoba analisa awal tanpa login. Browser dapat menyimpan data kelahiran, jawaban, dan progres sementara agar alur dapat dilanjutkan.</p></div>
      </section>

      <section>
        <span>03</span>
        <div><h2>Login dengan Google</h2><p>Login diperlukan untuk membuka hasil lengkap dan menghubungkannya ke akunmu. Hermex hanya meminta identitas dasar seperti nama, email, dan foto profil. Hermex tidak menerima kata sandi Google milikmu.</p></div>
      </section>

      <section>
        <span>04</span>
        <div><h2>Analisa berbantuan AI</h2><p>Hasil bergantung pada model, konfigurasi, dan data yang diberikan. Hermex tidak menjamin setiap keluaran AI selalu lengkap, akurat, atau sesuai untuk semua keadaan.</p></div>
      </section>

      <section>
        <span>05</span>
        <div><h2>Penggunaan yang wajar</h2><p>Jangan menyalahgunakan layanan, mencoba melewati batas akses, mengganggu sistem, atau menggunakan Hermex untuk merugikan orang lain.</p></div>
      </section>

      <section>
        <span>06</span>
        <div><h2>Open source dan self-hosting</h2><p>Versi self-hosted dikelola oleh operator masing-masing. Penyimpanan data, penyedia AI, dan kebijakan operasionalnya menjadi tanggung jawab operator tersebut.</p></div>
      </section>
    </div>

    <aside>
      <h2>Ada pertanyaan?</h2>
      <p>Hubungi pengelola melalui <a href="https://github.com/wauputr4/hermex">repositori Hermex di GitHub</a>.</p>
    </aside>
  </article>
</main>

<style>
  :global(body) { margin: 0; background: #fbfaf7; color: #302a36; font-family: Avenir Next, Nunito, Trebuchet MS, sans-serif; }
  main { width: min(1060px, calc(100% - 40px)); margin: auto; }
  header { display: flex; min-height: 84px; align-items: center; justify-content: space-between; border-bottom: 1px solid #e7e1d9; }
  .brand { display: flex; align-items: center; gap: 10px; color: #302a36; font-size: 1.1rem; font-weight: 820; text-decoration: none; }
  .brand svg { width: 34px; height: 34px; box-sizing: border-box; padding: 6px; border-radius: 11px; background: #fff0ce; fill: #f1b86a; stroke: #302a36; stroke-width: 1.5; }
  .back { display: inline-flex; align-items: center; gap: 7px; color: #615968; font-size: .92rem; font-weight: 700; text-decoration: none; }
  article { padding: clamp(56px, 9vw, 104px) 0 80px; }
  .intro { max-width: 780px; border-left: 5px solid #5b55d6; padding-left: clamp(20px, 4vw, 40px); }
  .eyebrow { margin: 0 0 14px; color: #5b55d6; font-size: .76rem; font-weight: 800; letter-spacing: .09em; text-transform: uppercase; }
  h1 { max-width: 720px; margin: 0; font-size: clamp(2.7rem, 7vw, 5.4rem); line-height: .96; letter-spacing: -.06em; }
  .lead { max-width: 680px; margin: 28px 0 14px; color: #615968; font-size: clamp(1rem, 1.8vw, 1.2rem); line-height: 1.65; }
  .updated { margin: 0; color: #8a828b; font-size: .82rem; }
  .terms { margin-top: clamp(58px, 9vw, 96px); border-top: 1px solid #d7d0ca; }
  section { display: grid; grid-template-columns: 52px 1fr; gap: 24px; padding: 30px 0; border-bottom: 1px solid #e7e1d9; }
  section > span { color: #5b55d6; font-size: .78rem; font-weight: 800; letter-spacing: .06em; }
  h2 { margin: 0 0 8px; font-size: clamp(1.15rem, 2vw, 1.4rem); letter-spacing: -.02em; }
  section p, aside p { max-width: 720px; margin: 0; color: #615968; line-height: 1.7; }
  aside { margin-top: 48px; border-radius: 18px; padding: 28px; background: #f2f0ff; }
  aside a { color: #4e48c8; font-weight: 750; }
  a:focus-visible { border-radius: 6px; outline: 3px solid rgba(91,85,214,.28); outline-offset: 4px; }
  @media (max-width: 560px) {
    main { width: min(100% - 28px, 1060px); }
    header { min-height: 72px; }
    .back { font-size: 0; }
    .back::after { content: 'Kembali'; font-size: .88rem; }
    article { padding-top: 44px; }
    section { grid-template-columns: 36px 1fr; gap: 12px; padding: 24px 0; }
    aside { padding: 22px; }
  }
</style>
