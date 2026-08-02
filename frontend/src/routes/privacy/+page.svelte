<svelte:head>
  <title>Kebijakan Privasi | Hermex</title>
  <meta name="description" content="Cara Hermex menyimpan, memakai, dan menghapus data kelahiran, akun, serta hasil analisa." />
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
      <p class="eyebrow">Kebijakan privasi</p>
      <h1>Datamu dipakai untuk membuat hasilmu.</h1>
      <p class="lead">Halaman ini menjelaskan data apa yang diproses Hermex, ke mana data dikirim, dan pilihan yang kamu punya atas data tersebut.</p>
      <p class="updated">Diperbarui 1 Agustus 2026</p>
    </div>

    <div class="policy">
      <section><span>01</span><div><h2>Data yang kamu berikan</h2><p>Hermex memproses tanggal, jam, dan lokasi lahir, jawaban kuesioner, username, serta feedback yang kamu kirim. Jika kamu login, nama, email, dan foto profil dasar dari Google juga dapat disimpan untuk menghubungkan hasil ke akunmu.</p></div></section>
      <section><span>02</span><div><h2>Penyimpanan tamu</h2><p>Browser dapat menyimpan draf data kelahiran, lokasi yang dipilih, jawaban kuesioner, dan progres analisa agar kamu dapat melanjutkan alur yang belum selesai. Kamu dapat menghapusnya melalui data situs pada browser.</p></div></section>
      <section><span>03</span><div><h2>Perhitungan dan AI</h2><p>Backend menyimpan profil perhitungan, jawaban, permintaan ke model, dan hasil analisa. Konteks yang diperlukan dapat dikirim ke penyedia AI yang dikonfigurasi pengelola. Kata sandi Google tidak pernah diterima Hermex.</p></div></section>
      <section><span>04</span><div><h2>Profil publik</h2><p>Username dan kartu karakter dapat dibagikan melalui halaman publik jika opsi publik dinyalakan. Pemilik akun dapat mematikannya dari pengaturan profil; data khusus pemilik seperti ekspor mentah dan feedback tidak ditampilkan kepada pengunjung lain.</p></div></section>
      <section><span>05</span><div><h2>Analitik</h2><p>Versi yang dipasang di server bisa memakai Google Analytics jika measurement ID diisi. Data ini membantu melihat cara orang memakai halaman. Instalasi lokal dan self-hosted bisa menonaktifkannya.</p></div></section>
      <section><span>06</span><div><h2>Penelitian bersifat opt-in</h2><p>Hermex belum memakai data akunmu sebagai data penelitian. Jika penelitian untuk mengevaluasi atau menguji klaim astrologi dibuka, data hanya dapat dipakai setelah kamu memberikan persetujuan terpisah. Menggunakan Hermex bukan persetujuan penelitian, dan persetujuan dapat ditarik.</p></div></section>
      <section><span>07</span><div><h2>Akses dan penghapusan</h2><p>Kamu dapat meminta akses atau penghapusan data akun dan hasil dengan menghubungi <a href="mailto:me@wau.my.id">me@wau.my.id</a> dari email yang terhubung ke akun. Verifikasi dapat diminta untuk melindungi data dari permintaan pihak lain.</p></div></section>
      <section><span>08</span><div><h2>Self-hosting</h2><p>Operator instalasi self-hosted mengendalikan penyimpanan, penyedia AI, kunci, dan kebijakan operasionalnya sendiri. Kebijakan ini berlaku untuk layanan Hermex yang dikelola di hermex.fun.</p></div></section>
    </div>

    <aside><h2>Perlu bantuan soal data?</h2><p>Kirim email ke <a href="mailto:me@wau.my.id">me@wau.my.id</a>. Jelaskan akun atau profil yang dimaksud tanpa mengirim kata sandi.</p></aside>
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
  h1 { max-width: 760px; margin: 0; font-size: clamp(2.7rem, 7vw, 5.4rem); line-height: .96; letter-spacing: -.06em; }
  .lead { max-width: 680px; margin: 28px 0 14px; color: #615968; font-size: clamp(1rem, 1.8vw, 1.2rem); line-height: 1.65; }
  .updated { margin: 0; color: #8a828b; font-size: .82rem; }
  .policy { margin-top: clamp(58px, 9vw, 96px); border-top: 1px solid #d7d0ca; }
  section { display: grid; grid-template-columns: 52px 1fr; gap: 24px; padding: 30px 0; border-bottom: 1px solid #e7e1d9; }
  section > span { color: #5b55d6; font-size: .78rem; font-weight: 800; letter-spacing: .06em; }
  h2 { margin: 0 0 8px; font-size: clamp(1.15rem, 2vw, 1.4rem); letter-spacing: -.02em; }
  section p, aside p { max-width: 720px; margin: 0; color: #615968; line-height: 1.7; }
  section a, aside a { color: #4e48c8; font-weight: 750; }
  aside { margin-top: 48px; border-radius: 18px; padding: 28px; background: #f2f0ff; }
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
