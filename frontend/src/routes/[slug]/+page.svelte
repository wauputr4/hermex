<script lang="ts">
  import { onMount } from 'svelte';
  import PersonalityContour from '$lib/components/PersonalityContour.svelte';
  import RawResultExport from '$lib/components/RawResultExport.svelte';
  import { getProfileSettings, getPublicProfile, submitFeedback, updateProfileSettings } from '$lib/api/hermex';

  export let data: any;

  const sectionMeta: Record<string, { label: string; icon: string }> = {
    core_identity: { label: 'Identitas dan motivasi inti', icon: '☉' },
    emotional_needs: { label: 'Kebutuhan emosional', icon: '☾' },
    social_approach: { label: 'Cara menghadapi situasi baru', icon: '↗' },
    thinking_and_communication: { label: 'Cara berpikir dan berkomunikasi', icon: '✎' },
    relationships_and_values: { label: 'Relasi dan nilai pribadi', icon: '♡' },
    drive_and_boundaries: { label: 'Dorongan dan batas pribadi', icon: '→' },
    inner_tensions: { label: 'Tarik-menarik dalam diri', icon: '↔' },
    dominant_patterns: { label: 'Pola yang paling kuat', icon: '✶' },
    growth_focus: { label: 'Arah bertumbuh', icon: '✦' }
  };

  let shareStatus = '';
  let exportStatus = '';
  let feedbackStatus = '';
  let feedbackRating = 0;
  let feedbackText = '';
  let feedbackPending = false;
  let isPublic = true;
  let visibilityPending = false;
  let visibilityStatus = '';
  let exportSurface: HTMLElement;
  $: publicProfile = data.publicProfile;
  $: error = data.error;
  $: interpretation = publicProfile?.latest_interpretation?.interpretation ?? {};
  $: summary = textValue(interpretation.preview_summary ?? interpretation.summary);
  $: highlights = stringList(interpretation.highlights ?? interpretation.strengths);
  $: identityKeywords = keywordList(interpretation.identity_keywords, highlights);
  $: fullAnalysis = objectValue(interpretation.full_analysis ?? publicProfile?.full_analysis);
  $: analysisSections = Object.entries(fullAnalysis)
    .filter(([, value]) => textValue(value))
    .map(([key, value]) => ({ key, text: textValue(value), ...(sectionMeta[key] ?? { label: titleCase(key), icon: '✦' }) }));
  $: planets = publicProfile?.profile?.chart_highlights?.planets ?? [];
  $: contourValues = Array.from({ length: 10 }, (_, index) => {
    const planet = planets[index % Math.max(planets.length, 1)];
    return planet ? 1 + (Math.round(Number(planet.degree_in_sign ?? index * 3)) % 5) : 3;
  });
  $: avatar = publicProfile?.avatar_url ?? publicProfile?.picture ?? publicProfile?.profile?.avatar_url ?? '';
  $: displayName = publicProfile?.display_name || `@${publicProfile?.username ?? ''}`;
  $: pageTitle = publicProfile?.username ? `@${publicProfile.username} · Hermex` : 'Profil Hermex';

  onMount(async () => {
    if (!data.username) return;
    try {
      publicProfile = await getPublicProfile(data.username);
      error = '';
    } catch {
      // The server-rendered public payload remains usable when auth refresh fails.
    }
    if (publicProfile?.viewer_is_owner && publicProfile.profile_id) {
      try {
        isPublic = (await getProfileSettings(publicProfile.profile_id)).is_public;
      } catch {
        visibilityStatus = 'Pengaturan visibilitas belum bisa dimuat.';
      }
    }
  });

  function objectValue(value: unknown): Record<string, unknown> {
    const parsed = parseJson(value);
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed as Record<string, unknown> : {};
  }

  function textValue(value: unknown): string {
    const parsed = parseJson(value);
    if (typeof parsed === 'string') return parsed;
    if (parsed && typeof parsed === 'object') {
      const item = parsed as Record<string, unknown>;
      return textValue(item.preview_summary ?? item.summary ?? item.description ?? '');
    }
    return '';
  }

  function parseJson(value: unknown): unknown {
    if (typeof value !== 'string') return value;
    const trimmed = value.trim();
    if (!trimmed.startsWith('{') && !trimmed.startsWith('[')) return value;
    try { return JSON.parse(trimmed); } catch { return value; }
  }

  function stringList(value: unknown): string[] {
    const parsed = parseJson(value);
    return Array.isArray(parsed) ? parsed.map(textValue).filter(Boolean).slice(0, 5) : [];
  }

  function keywordList(value: unknown, fallback: string[]): Array<{ word: string; icon: string }> {
    const parsed = parseJson(value);
    const candidates = Array.isArray(parsed) && parsed.length ? parsed : fallback;
    return candidates.slice(0, 3).map((item: any, index) => {
      const rawWord = typeof item === 'object' ? textValue(item.word ?? item.label) : textValue(item);
      const word = (rawWord.trim().split(/\s+/)[0] || ['Jernih', 'Hangat', 'Teguh'][index]).replace(/[^\p{L}\p{N}-]/gu, '');
      return { word, icon: typeof item === 'object' && item.icon ? String(item.icon) : iconFor(word, index) };
    });
  }

  function iconFor(word: string, index: number): string {
    const normalized = word.toLowerCase();
    if (/tenang|damai|stabil|sabar/.test(normalized)) return '☾';
    if (/cerdas|logis|analitis|jernih|pikir/.test(normalized)) return '✎';
    if (/hangat|peduli|empati|lembut/.test(normalized)) return '♡';
    if (/berani|tegas|kuat|tangguh/.test(normalized)) return '⚡';
    if (/kreatif|imajinatif|inovatif/.test(normalized)) return '✦';
    return ['◎', '↗', '✶'][index] ?? '✦';
  }

  function titleCase(value: string): string {
    return value.replaceAll('_', ' ').replace(/^./, (letter) => letter.toUpperCase());
  }

  async function shareProfile() {
    const shareData = { title: pageTitle, text: `Menurutmu, kartu karakter ${publicProfile.username} ini akurat? Coba validasi, lalu bikin analisismu juga di Hermex.`, url: window.location.href };
    try {
      if (navigator.share) {
        await navigator.share(shareData);
        shareStatus = 'Siap dibagikan.';
      } else {
        await navigator.clipboard.writeText(window.location.href);
        shareStatus = 'Link tersalin.';
      }
    } catch (error) {
      if ((error as Error).name !== 'AbortError') shareStatus = 'Link belum bisa disalin.';
    }
  }

  async function exportProfile() {
    if (!exportSurface) return;
    exportStatus = 'Menyiapkan gambar…';
    try {
      const { toPng } = await import('html-to-image');
      const image = await toPng(exportSurface, { backgroundColor: '#fbf8f1', cacheBust: true, pixelRatio: 2 });
      const link = document.createElement('a');
      link.download = `hermex-${publicProfile.username}.png`;
      link.href = image;
      link.click();
      exportStatus = 'Gambar berhasil diunduh.';
    } catch {
      exportStatus = 'Gambar belum bisa dibuat. Coba lagi.';
    }
  }

  async function saveFeedback() {
    if (!feedbackRating || feedbackPending) return;
    feedbackPending = true;
    feedbackStatus = '';
    try {
      await submitFeedback({
        profile_id: publicProfile.owner_profile_id ?? publicProfile.profile_id,
        interpretation_id: publicProfile.latest_interpretation?.interpretation_id,
        rating: feedbackRating,
        message: feedbackText.trim() || undefined,
        source: 'accuracy'
      });
      feedbackStatus = 'Makasih, penilaianmu sudah tersimpan.';
      feedbackText = '';
    } catch {
      feedbackStatus = 'Penilaian belum tersimpan. Coba lagi.';
    } finally {
      feedbackPending = false;
    }
  }

  async function saveVisibility() {
    if (!publicProfile?.viewer_is_owner || !publicProfile.profile_id || visibilityPending) return;
    visibilityPending = true;
    visibilityStatus = '';
    try {
      await updateProfileSettings(publicProfile.profile_id, { username: publicProfile.username, is_public: isPublic });
      publicProfile = { ...publicProfile, is_public: isPublic };
      visibilityStatus = isPublic ? 'Profilmu sekarang tampil ke publik.' : 'Profilmu sekarang hanya bisa kamu lihat.';
    } catch {
      visibilityStatus = 'Visibilitas belum tersimpan. Coba lagi.';
    } finally {
      visibilityPending = false;
    }
  }
</script>

<svelte:head>
  <title>{pageTitle}</title>
  <meta name="description" content={summary || 'Kartu karakter publik dari Hermex.'} />
  <meta name="theme-color" content="#fbf8f1" />
</svelte:head>

<main class="profile-shell">
  <nav aria-label="Navigasi utama">
    <a class="brand" href="/" aria-label="Hermex, kembali ke beranda"><span aria-hidden="true">☆</span> hermex.fun <small>AI Analisis Kepribadian berdasarkan data astrologi</small></a>
  </nav>

  {#if error || !publicProfile}
    <section class="empty">
      <span class="empty-icon" aria-hidden="true">☆</span>
      <h1>{error === 'Profil ini private.' ? 'Profil ini private' : 'Profil belum ketemu'}</h1>
      <p>{error === 'Profil ini private.' ? 'Pemilik kartu memilih untuk tidak menampilkan hasilnya ke publik.' : error || 'Cek lagi username yang kamu buka.'}</p>
      <a class="primary" href="/"><span aria-hidden="true">✦</span> Buat kartu karaktermu</a>
    </section>
  {:else}
    <section class="export-surface" bind:this={exportSurface} aria-label={`Kartu karakter ${publicProfile.username}`}>
      <p class="export-title"><span aria-hidden="true">☆</span> Analisis Kepribadian AI <span>| Hermex Fun</span></p>

      <header class="identity">
        {#if avatar}
          <img class="avatar" src={avatar} alt={`Foto profil ${displayName}`} referrerpolicy="no-referrer" crossorigin="anonymous" />
        {:else}
          <span class="avatar avatar-fallback" aria-hidden="true">{displayName.slice(0, 1).toUpperCase()}</span>
        {/if}
        <p class="display-name">{displayName}</p>
        <h1>@{publicProfile.username}</h1>
        {#if publicProfile.bio}<p class="bio">{publicProfile.bio}</p>{/if}
        {#if identityKeywords.length}
          <ul class="identity-keywords" aria-label="Tiga karakter utama">
            {#each identityKeywords as keyword}
              <li><span aria-hidden="true">{keyword.icon}</span><strong>{keyword.word}</strong></li>
            {/each}
          </ul>
        {/if}
      </header>

      <article class="character-card" aria-labelledby="character-title">
        <div class="contour-wrap"><PersonalityContour values={contourValues} label={`Kontur karakter ${displayName}`} /></div>
        <div class="character-copy">
          <p class="eyebrow"><span aria-hidden="true">✦</span> Kartu karakter</p>
          <h2 id="character-title">Pola yang paling terasa</h2>
          {#if summary}<p class="summary">{summary}</p>{/if}
          {#if highlights.length}
            <ul class="traits" aria-label="Pola utama">
              {#each highlights as item}<li>{item}</li>{/each}
            </ul>
          {/if}
        </div>
      </article>

      {#if analysisSections.length}
        <section class="analysis" aria-labelledby="analysis-title">
          <div class="section-heading">
            <p class="eyebrow"><span aria-hidden="true">✶</span> Analisis lengkap</p>
            <h2 id="analysis-title">Kenali bagian dirimu satu per satu</h2>
          </div>
          <div class="analysis-list">
            {#each analysisSections as section}
              <article>
                <span class="section-icon" aria-hidden="true">{section.icon}</span>
                <div><h3>{section.label}</h3><p>{section.text}</p></div>
              </article>
            {/each}
          </div>
        </section>
      {/if}
    </section>

    <a class="natal-link" href={`/${publicProfile.username}/natal-chart`}>
      <span class="natal-mark" aria-hidden="true">◎</span>
      <span><small>Detail natal chart</small><strong>Lihat Kartu Karakter & Chart Explorer</strong><em>Posisi lengkap yang dipakai sebagai bahan analisis.</em></span>
      <span aria-hidden="true">→</span>
    </a>

    {#if publicProfile.viewer_is_owner}
      <section class="feedback-card" aria-labelledby="feedback-title">
        <div class="feedback-copy">
          <p class="eyebrow"><span aria-hidden="true">♡</span> Khusus untukmu</p>
          <h2 id="feedback-title">Seberapa akurat hasil Hermex?</h2>
          <p>Bantu kami membuat pembacaannya makin pas. Cerita tambahan boleh dikosongkan.</p>
        </div>
        <fieldset>
          <legend>Pilih 1 sampai 5 bintang</legend>
          <div class="rating">
            {#each [1, 2, 3, 4, 5] as star}
              <button class:active={star <= feedbackRating} type="button" aria-label={`${star} bintang`} aria-pressed={feedbackRating === star} on:click={() => (feedbackRating = star)}>★</button>
            {/each}
          </div>
        </fieldset>
        <label for="feedback-text">Feedback <span>opsional</span></label>
        <textarea id="feedback-text" bind:value={feedbackText} maxlength="1200" rows="4" placeholder="Bagian mana yang terasa paling pas atau kurang pas?"></textarea>
        <button class="feedback-submit" type="button" disabled={!feedbackRating || feedbackPending} on:click={saveFeedback}><span aria-hidden="true">✓</span> {feedbackPending ? 'Menyimpan…' : 'Kirim penilaian'}</button>
        <p class="feedback-status" aria-live="polite">{feedbackStatus}</p>
      </section>
    {/if}

    {#if publicProfile.viewer_is_owner}
      <details class="owner-export">
        <summary><span aria-hidden="true">▤</span><span><strong>Data hasilmu</strong><small>Buka untuk menyalin highlight chart atau membawanya ke ChatGPT.</small></span><span class="chevron" aria-hidden="true">⌄</span></summary>
        <RawResultExport profile={publicProfile.profile} />
      </details>
    {/if}
    <a class="methodology-link" href="/metodologi"><span aria-hidden="true">◎</span><span><strong>Cara hasil ini disusun</strong><small>Lihat metodologi dan batas interpretasi Hermex.</small></span><span aria-hidden="true">→</span></a>

    <section class="share-panel" aria-labelledby="share-title">
      <span class="share-mark" aria-hidden="true">↗</span>
      <div><h2 id="share-title">Minta temanmu ikut menilai</h2><p>Bagikan profil ini agar temanmu bisa memvalidasi karaktermu, lalu ajak mereka mencoba analisisnya sendiri.</p></div>
      <div class="share-actions">
        <button class="primary" type="button" on:click={shareProfile}><span aria-hidden="true">↗</span> Bagikan profil</button>
        <button class="secondary" type="button" on:click={exportProfile}><span aria-hidden="true">↓</span> Unduh gambar</button>
      </div>
      <p class="share-status" aria-live="polite">{shareStatus || exportStatus}</p>
    </section>

    {#if publicProfile.viewer_is_owner}
      <section class="visibility-card" aria-labelledby="visibility-title">
        <div>
          <p class="eyebrow"><span aria-hidden="true">◉</span> Khusus untukmu</p>
          <h2 id="visibility-title">Siapa yang bisa melihat profil ini?</h2>
        </div>
        <label class="visibility-control">
          <input type="checkbox" bind:checked={isPublic} />
          <span><strong>Tampilkan ke publik</strong><small>Matikan agar profil hanya bisa dibuka olehmu saat login.</small></span>
        </label>
        <button class="visibility-save" type="button" disabled={visibilityPending} on:click={saveVisibility}><span aria-hidden="true">✓</span> {visibilityPending ? 'Menyimpan…' : 'Simpan visibilitas'}</button>
        <p class="visibility-status" role="status">{visibilityStatus}</p>
      </section>
    {/if}
  {/if}
</main>

<style>
  :global(*) { box-sizing: border-box; }
  :global(body) { margin: 0; color: #302a36; background: #fbf8f1; font-family: Inter, Avenir Next, system-ui, sans-serif; }
  :global(button), :global(a) { font: inherit; }
  .profile-shell { width: min(860px, 100%); min-height: 100vh; margin: 0 auto; padding: 24px 22px 64px; }
  nav { display: flex; justify-content: center; padding-bottom: 32px; }
  .brand { display: inline-flex; align-items: center; gap: 8px; color: #302a36; font-size: 1.05rem; font-weight: 900; text-decoration: none; }
  .brand span { display: grid; place-items: center; width: 34px; height: 34px; border-radius: 11px; background: #fff0ca; color: #8c5c18; font-size: 1.4rem; }
  .brand small { color: #716a78; font-size: .8rem; font-weight: 650; }
  .export-surface { margin: 0; padding: 28px; border-radius: 34px; background: #fbf8f1; }
  .export-title { display: flex; align-items: center; justify-content: center; gap: 8px; margin: 0 0 28px; color: #5b55d6; font-size: .82rem; font-weight: 900; letter-spacing: .045em; text-align: center; text-transform: uppercase; }
  .export-title > span:last-child { color: #302a36; }
  .identity { display: grid; justify-items: center; text-align: center; }
  .avatar { width: 96px; height: 96px; border: 4px solid #fff; border-radius: 50%; object-fit: cover; box-shadow: 0 12px 34px rgba(48,42,54,.14); }
  .avatar-fallback { display: grid; place-items: center; background: #5b55d6; color: #fff; font-size: 2.2rem; font-weight: 900; }
  .display-name { margin: 16px 0 2px; color: #716a78; font-weight: 700; }
  h1 { max-width: 100%; margin: 0; overflow-wrap: anywhere; font-size: clamp(2.35rem, 8vw, 4.8rem); line-height: .95; letter-spacing: -.065em; }
  .bio { max-width: 560px; margin: 14px 0 0; color: #716a78; line-height: 1.6; }
  .identity-keywords { display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; margin: 24px 0 0; padding: 0; list-style: none; }
  .identity-keywords li { display: inline-flex; min-width: 112px; align-items: center; justify-content: center; gap: 8px; border: 1px solid #ded9d1; border-radius: 18px; padding: 11px 15px; background: #fff; }
  .identity-keywords li span { color: #5b55d6; font-size: 1.2rem; }
  .identity-keywords strong { font-size: .9rem; text-transform: capitalize; }
  .character-card { display: grid; grid-template-columns: minmax(210px, .72fr) minmax(0, 1.28fr); gap: clamp(24px, 6vw, 64px); align-items: center; margin-top: 42px; padding: clamp(26px, 5vw, 54px); border: 1px solid #ded9d1; border-radius: 32px; background: #fff; box-shadow: 0 20px 50px rgba(48,42,54,.07); }
  .contour-wrap { border-radius: 50%; background: #f8f7ff; padding: 10px; }
  .eyebrow { display: flex; align-items: center; gap: 8px; margin: 0 0 10px; color: #5b55d6; font-size: .78rem; font-weight: 900; letter-spacing: .09em; text-transform: uppercase; }
  h2 { margin: 0; font-size: clamp(1.65rem, 4vw, 2.65rem); line-height: 1.04; letter-spacing: -.045em; }
  .summary { margin: 18px 0 0; color: #5e5865; font-size: 1.06rem; line-height: 1.72; }
  .traits { display: flex; flex-wrap: wrap; gap: 8px; margin: 22px 0 0; padding: 0; list-style: none; }
  .traits li { padding: 9px 13px; border-radius: 999px; background: #fff0ca; color: #5a4730; font-size: .86rem; font-weight: 800; }
  .analysis { margin-top: 64px; }
  .section-heading { max-width: 620px; margin-bottom: 22px; }
  .analysis-list { border-top: 1px solid #ded9d1; }
  .analysis-list article { display: grid; grid-template-columns: 48px minmax(0,1fr); gap: 18px; padding: 30px 0; border-bottom: 1px solid #ded9d1; }
  .section-icon { display: grid; place-items: center; width: 44px; height: 44px; border-radius: 15px; background: #f2efff; color: #5b55d6; font-size: 1.35rem; }
  h3 { margin: 3px 0 8px; font-size: 1.25rem; letter-spacing: -.025em; }
  .analysis-list p { max-width: 680px; margin: 0; color: #67616e; line-height: 1.72; }
  .natal-link { display: grid; grid-template-columns: 50px minmax(0,1fr) auto; gap: 16px; align-items: center; margin-top: 26px; border: 1px solid #ded9d1; border-radius: 22px; padding: 20px; background: #fff; color: #302a36; text-decoration: none; }
  .natal-mark { display: grid; width: 50px; height: 50px; place-items: center; border-radius: 16px; background: #f2efff; color: #5b55d6; font-size: 1.45rem; }
  .natal-link small, .natal-link strong, .natal-link em { display: block; }
  .natal-link small { margin: 0 0 3px; color: #5b55d6; font-size: .72rem; font-style: normal; font-weight: 850; letter-spacing: .08em; text-transform: uppercase; }
  .natal-link strong { font-size: 1.08rem; }
  .natal-link em { margin-top: 4px; color: #716a78; font-size: .82rem; font-style: normal; }
  .feedback-card { margin-top: 34px; border: 1px solid #ded9d1; border-radius: 26px; padding: clamp(22px, 4vw, 34px); background: #fff; }
  .feedback-copy > p:last-child { max-width: 640px; margin: 12px 0 22px; color: #67616e; line-height: 1.6; }
  fieldset { margin: 0 0 20px; border: 0; padding: 0; }
  legend, .feedback-card label { display: block; margin-bottom: 8px; color: #4c4553; font-size: .82rem; font-weight: 800; }
  .feedback-card label span { color: #8a838f; font-weight: 600; }
  .rating { display: flex; gap: 7px; }
  .rating button { display: grid; width: 48px; height: 48px; place-items: center; border: 1px solid #ded9d1; border-radius: 14px; background: #fbf8f1; color: #c6bec9; font-size: 1.5rem; cursor: pointer; }
  .rating button.active { border-color: #e5a443; background: #fff0ca; color: #e5a443; }
  .rating button:focus-visible, textarea:focus-visible { outline: 3px solid rgba(91,85,214,.25); outline-offset: 2px; }
  textarea { width: 100%; resize: vertical; border: 1px solid #ded9d1; border-radius: 15px; padding: 13px 15px; background: #fbfaf7; color: #302a36; font: inherit; line-height: 1.5; }
  .feedback-submit { min-height: 46px; margin-top: 13px; border: 0; border-radius: 14px; padding: 0 18px; background: #5b55d6; color: #fff; font: inherit; font-weight: 850; cursor: pointer; }
  .feedback-submit { display: inline-flex; align-items: center; gap: 8px; }
  .feedback-submit:disabled { cursor: not-allowed; opacity: .45; }
  .feedback-status { min-height: 1.25em; margin: 10px 0 0; color: #67616e; font-size: .82rem; }
  .owner-export { margin-top: 34px; }
  .owner-export > summary { display: grid; grid-template-columns: 42px minmax(0,1fr) auto; gap: 14px; align-items: center; border: 1px solid #ded9d1; border-radius: 18px; padding: 18px; background: #fff; cursor: pointer; list-style: none; }
  .owner-export > summary::-webkit-details-marker { display: none; }
  .owner-export > summary > span:first-child { display: grid; width: 42px; height: 42px; place-items: center; border-radius: 13px; background: #fff0ca; color: #8c5c18; font-size: 1.2rem; }
  .owner-export summary strong, .owner-export summary small { display: block; }
  .owner-export summary small { margin-top: 3px; color: #716a78; }
  .owner-export .chevron { transition: transform .18s ease; }
  .owner-export[open] .chevron { transform: rotate(180deg); }
  .methodology-link { display: grid; grid-template-columns: 42px 1fr auto; gap: 14px; align-items: center; margin-top: 16px; border: 1px solid #ded9d1; border-radius: 18px; padding: 18px; background: #fff; color: #302a36; text-decoration: none; }
  .methodology-link > span:first-child { display: grid; width: 42px; height: 42px; place-items: center; border-radius: 13px; background: #f2efff; color: #5b55d6; font-size: 1.2rem; }
  .methodology-link strong, .methodology-link small { display: block; }
  .methodology-link small { margin-top: 3px; color: #716a78; }
  .share-panel { position: relative; display: grid; grid-template-columns: auto 1fr auto; gap: 18px; align-items: center; margin-top: 58px; padding: 26px; border-radius: 26px; background: #302a36; color: #fff; }
  .share-mark { display: grid; place-items: center; width: 48px; height: 48px; border-radius: 16px; background: #f1b86a; color: #302a36; font-size: 1.4rem; font-weight: 900; }
  .share-panel h2 { font-size: 1.35rem; letter-spacing: -.025em; }
  .share-panel p { margin: 5px 0 0; color: #d9d4dd; line-height: 1.45; }
  .share-actions { display: flex; gap: 9px; }
  .primary { display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: 48px; padding: 0 18px; border: 0; border-radius: 15px; background: #f1b86a; color: #302a36; font-weight: 900; text-decoration: none; cursor: pointer; }
  .primary:hover { background: #ffd38b; }
  .secondary { display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: 48px; border: 1px solid #665e6e; border-radius: 15px; padding: 0 18px; background: transparent; color: #fff; font: inherit; font-weight: 850; cursor: pointer; }
  .secondary:hover { background: #463e4e; }
  .primary:focus-visible, a:focus-visible { outline: 3px solid #5b55d6; outline-offset: 3px; }
  .share-status { position: absolute; right: 26px; bottom: 5px; font-size: .75rem; }
  .visibility-card { display: grid; gap: 18px; margin-top: 34px; border: 1px solid #ded9d1; border-radius: 24px; padding: clamp(22px, 4vw, 30px); background: #fff; }
  .visibility-card h2 { font-size: 1.5rem; }
  .visibility-control { display: grid; grid-template-columns: auto 1fr; gap: 12px; align-items: start; border-radius: 16px; padding: 17px; background: #f7f5f1; cursor: pointer; }
  .visibility-control input { width: 21px; height: 21px; margin: 2px 0 0; accent-color: #5b55d6; }
  .visibility-control span, .visibility-control small { display: block; }
  .visibility-control small { margin-top: 3px; color: #716a78; font-weight: 500; line-height: 1.45; }
  .visibility-save { display: inline-flex; width: fit-content; min-height: 46px; align-items: center; gap: 8px; border: 0; border-radius: 14px; padding: 0 18px; background: #5b55d6; color: #fff; font-weight: 850; cursor: pointer; }
  .visibility-save:disabled { cursor: wait; opacity: .55; }
  .visibility-status { min-height: 1.25em; margin: -8px 0 0; color: #67616e; font-size: .82rem; }
  .empty { display: grid; justify-items: center; gap: 12px; padding: 20vh 20px 0; text-align: center; }
  .empty-icon { font-size: 3rem; color: #5b55d6; }
  .empty p { margin: 0 0 12px; color: #716a78; }
  @media (max-width: 680px) {
    .profile-shell { padding: 18px 16px 40px; }
    nav { padding-bottom: 24px; }
    .brand small { display: none; }
    .export-surface { padding: 20px 8px; border-radius: 26px; }
    .character-card { grid-template-columns: 1fr; text-align: left; margin-top: 32px; border-radius: 26px; }
    .contour-wrap { width: min(260px, 78vw); margin: 0 auto; }
    .share-panel { grid-template-columns: auto 1fr; }
    .share-actions { grid-column: 1 / -1; flex-direction: column; }
    .share-actions button { width: 100%; }
  }
  @media (max-width: 420px) {
    .profile-shell { padding-inline: 12px; }
    .character-card { padding: 22px 18px; }
    .identity-keywords { display: grid; width: min(260px, 100%); gap: 7px; }
    .identity-keywords li { min-width: 0; padding-inline: 12px; }
    .analysis-list article { grid-template-columns: 40px minmax(0,1fr); gap: 13px; }
    .section-icon { width: 38px; height: 38px; border-radius: 12px; }
    .share-panel { padding: 22px 18px 28px; }
    .share-status { right: 18px; }
    .rating { justify-content: space-between; }
    .rating button { width: min(48px, 17vw); }
  }
  @media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto !important; } }
</style>
