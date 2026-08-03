<script lang="ts">
  import { onMount } from 'svelte';
  import cityTimezones from 'city-timezones';
  import CharacterCard from '$lib/components/CharacterCard.svelte';
  import PersonalityContour from '$lib/components/PersonalityContour.svelte';
  import Questionnaire, { type Question } from '$lib/components/Questionnaire.svelte';
  import RawResultExport from '$lib/components/RawResultExport.svelte';
  import {
    API_BASE,
    analyzeBirth,
    getBirthQuestion,
    getAuthMe,
    getFullInterpretation,
    getSkyNews,
    getUserHistory,
    interpretProfile,
    listPublicProfiles,
    publishPublicProfile,
    syncUserHistory,
    validateBirth
  } from '$lib/api/hermex';

  type Screen = 'home' | 'natal-loading' | 'questions' | 'ai-loading' | 'preview' | 'character' | 'chart' | 'error';
  type City = { label: string; latitude: number; longitude: number; timezone: string };
  type CityMatch = { city: string; province?: string; country: string; lat: number; lng: number; timezone: string };
  type AuthUser = { name?: string; email?: string; picture?: string };
  type PendingAnalysis = {
    profile: any;
    interpretationId?: string;
    preview?: { summary: string; highlights: string[]; usernames: string[] };
    answers?: Record<string, number>;
    username?: string;
    questions?: Question[];
    questionnaireCount?: number;
  };

  const popularCities = [
    'Jakarta Indonesia', 'Bandung Indonesia', 'Surabaya Indonesia', 'Yogyakarta Indonesia',
    'Semarang Indonesia', 'Malang Indonesia', 'Denpasar Indonesia', 'Makassar Indonesia',
    'Medan Indonesia', 'Balikpapan Indonesia', 'Jayapura Indonesia', 'Singapore',
    'Kuala Lumpur Malaysia', 'Tokyo Japan', 'London United Kingdom', 'New York United States'
  ];

  let screen: Screen = 'home';
  let birthDate = '';
  let birthTime = '';
  let cityQuery = '';
  let citySearchQuery = '';
  let selectedCity: City | null = null;
  let cityOpen = false;
  let citySearchTimer: number | undefined;
  let profile: any = null;
  let questions: Question[] = [];
  let questionnaireCount = 0;
  let scaleLabels: Record<string, string> = { '1': 'Sangat tidak sesuai', '5': 'Sangat sesuai' };
  let answers: Record<string, number> = {};
  let guestPreview = { summary: '', highlights: [] as string[], usernames: [] as string[] };
  let username = '';
  let interpretationId = '';
  let fullResult: any = null;
  let authUser: AuthUser | null = null;
  let error = '';
  let retryScreen: Screen = 'home';
  let skyPosts: any[] = [];
  let communityProfiles: any[] = [];
  let ownedProfiles: any[] = [];
  let loadingMessageIndex = 0;
  let loadingTimer: number | undefined;
  let analysisOpen = true;
  let analysisEntry: HTMLDetailsElement;

  const cities: City[] = uniqueCities(popularCities.flatMap((query) => {
    const matches = (cityTimezones.findFromCityStateProvince(query) || []) as CityMatch[];
    return matches.slice(0, 1).map(toCity);
  }));

  const natalLoadingMessages = ['Memeriksa waktu dan lokasi', 'Menyusun pola awal', 'Menyiapkan pertanyaan'];
  const aiLoadingMessages = ['Membaca jawabanmu', 'Membandingkan pola yang muncul', 'Menyiapkan hasil awal'];

  $: filteredCities = searchCities(citySearchQuery);
  $: selectedCityValid = Boolean(selectedCity && selectedCity.label.toLowerCase() === cityQuery.trim().toLowerCase());
  $: contourValues = questions.map((question) => answers[question.id] ?? 3);
  $: chart = fullResult?.chart ?? fullResult?.interpretation?.chart ?? profile?.chart ?? {};
  $: planets = Object.entries(chart?.planets ?? {}) as [string, any][];
  $: aspects = chart?.aspects ?? [];
  $: fullData = fullResult?.interpretation?.full_analysis ?? fullResult?.full_analysis ?? fullResult?.interpretation ?? fullResult ?? {};
  $: fullSections = normalizeFullSections(fullData);
  $: usernameValid = username.length >= 3;
  $: latestOwnedProfile = ownedProfiles.find((item) => item.public_username);

  onMount(() => {
    navigator.serviceWorker?.getRegistrations().then((registrations) => registrations.forEach((registration) => registration.unregister())).catch(() => undefined);
    restorePending();
    void restoreAuth();
    void getSkyNews().then((result: any) => (skyPosts = (result.posts ?? []).slice(0, 3))).catch(() => undefined);
    void listPublicProfiles().then((result: any) => (communityProfiles = (result.profiles ?? []).slice(0, 8))).catch(() => undefined);
    return () => {
      stopLoadingMessages();
      if (citySearchTimer) window.clearTimeout(citySearchTimer);
    };
  });

  function toCity(city: CityMatch): City {
    return {
      label: [city.city, city.province, city.country].filter(Boolean).join(', '),
      latitude: Number(city.lat), longitude: Number(city.lng), timezone: city.timezone || 'UTC'
    };
  }

  function uniqueCities(items: City[]) {
    const seen = new Set<string>();
    return items.filter((city) => {
      const key = `${city.label}|${city.latitude}|${city.longitude}`.toLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  function searchCities(query: string): City[] {
    if (query.trim().length < 2) return cities.slice(0, 8);
    const matches = (cityTimezones.findFromCityStateProvince(query.trim()) || []) as CityMatch[];
    return uniqueCities(matches.map(toCity)).slice(0, 10);
  }

  function chooseCity(city: City) {
    selectedCity = city;
    cityQuery = city.label;
    citySearchQuery = city.label;
    cityOpen = false;
    error = '';
  }

  function updateCity(value: string) {
    cityQuery = value;
    selectedCity = null;
    cityOpen = true;
    if (citySearchTimer) window.clearTimeout(citySearchTimer);
    citySearchTimer = window.setTimeout(() => (citySearchQuery = value), 150);
  }

  function startLoadingMessages(messages: string[]) {
    stopLoadingMessages();
    loadingMessageIndex = 0;
    loadingTimer = window.setInterval(() => (loadingMessageIndex = (loadingMessageIndex + 1) % messages.length), 1100);
  }

  function stopLoadingMessages() {
    if (loadingTimer) window.clearInterval(loadingTimer);
    loadingTimer = undefined;
  }

  function showScreen(next: Screen) {
    screen = next;
    window.requestAnimationFrame(() => window.scrollTo({ top: 0, behavior: 'auto' }));
  }

  async function beginAnalysis() {
    if (!birthDate) return setError('Isi tanggal lahir terlebih dahulu.');
    if (!selectedCityValid || !selectedCity) return setError('Pilih lokasi lahir dari daftar yang tersedia.');
    error = '';
    showScreen('natal-loading');
    startLoadingMessages(natalLoadingMessages);
    try {
      profile = await analyzeBirth({
        birth_date: birthDate,
        ...(birthTime ? { birth_time: birthTime } : {}),
        birth_place: selectedCity.label,
        latitude: selectedCity.latitude,
        longitude: selectedCity.longitude,
        timezone: selectedCity.timezone
      });
      questionnaireCount = Number(profile?.questionnaire?.count ?? 0);
      const firstQuestion = normalizeQuestion(profile?.questionnaire?.current_question);
      if (!questionnaireCount || !firstQuestion) throw new Error('Pertanyaan belum dapat disiapkan. Coba mulai analisis lagi.');
      questions = [firstQuestion];
      scaleLabels = profile?.questionnaire?.scale?.labels ?? scaleLabels;
      answers = {};
      persistPending();
      showScreen('questions');
    } catch (cause) {
      setError(messageFrom(cause), 'home');
    } finally {
      stopLoadingMessages();
    }
  }

  function answerQuestion(id: string, value: number) {
    answers = { ...answers, [id]: value };
    persistPending();
  }

  function normalizeQuestion(item: any): Question | null {
    const prompt = String(item?.prompt ?? '');
    if (!item?.id || !prompt || /birth time|work style|zodiac|planet|astrolog|chart|house|aspect/i.test(prompt)) return null;
    return { id: String(item.id), prompt };
  }

  async function loadQuestion(index: number) {
    if (questions[index] || !profile?.profile_id || !profile?.claim_token) return;
    const result: any = await getBirthQuestion(profile.profile_id, profile.claim_token, index);
    const next = normalizeQuestion(result?.questionnaire?.current_question);
    if (!next) throw new Error('Pertanyaan berikutnya belum siap. Coba lagi.');
    questions = [...questions, next];
    persistPending();
  }

  async function submitQuestionnaire() {
    if (!profile || questions.some((question) => !answers[question.id])) return;
    showScreen('ai-loading');
    startLoadingMessages(aiLoadingMessages);
    try {
      await validateBirth(profile.profile_id, profile.claim_token, answers);
      const result: any = await interpretProfile(profile.profile_id, profile.claim_token, 'id');
      interpretationId = result.interpretation_id ?? '';
      guestPreview = normalizePreview(result);
      username = guestPreview.usernames[0] ?? 'steadyobserver';
      persistPending();
      if (authUser) await unlockFullResult();
      else showScreen('preview');
    } catch (cause) {
      setError(messageFrom(cause), 'questions');
    } finally {
      stopLoadingMessages();
    }
  }

  function normalizePreview(result: any) {
    let data = result?.interpretation ?? result ?? {};
    const wrapped = data?.preview_summary ?? data?.summary;
    if (typeof wrapped === 'string' && wrapped.trim().startsWith('{')) {
      try {
        const parsed = JSON.parse(wrapped.replace(/^```(?:json)?\s*|\s*```$/g, ''));
        if (parsed && typeof parsed === 'object') data = { ...data, ...parsed };
      } catch {
        // Keep the provider text when it is not complete JSON.
      }
    }
    const list = (value: unknown): string[] => Array.isArray(value) ? value.map(String).filter(Boolean) : value ? [String(value)] : [];
    let summary = String(data.preview_summary ?? data.summary ?? 'Hasil awalmu menunjukkan cara berpikir, kebutuhan emosional, dan dorongan bertindak yang saling melengkapi. Ada pola yang membuatmu cepat membaca situasi, sekaligus kebutuhan untuk memberi diri sendiri waktu sebelum menentukan langkah. Analisis lengkap akan menjelaskan hubungan antarpola ini, termasuk kekuatan yang bisa kamu andalkan dan bagian yang perlu dijaga agar tetap seimbang.');
    if (summary.trim().startsWith('{') && summary.includes('"preview_summary"')) {
      summary = summary.split('"preview_summary"', 2)[1].split(':', 2)[1]?.trim().replace(/^"|"?[},]\s*$/g, '').replaceAll('\\"', '"') || summary;
    }
    const highlights = list(data.highlights ?? data.strengths).slice(0, 3);
    const usernames = list(data.username_suggestions ?? result?.username_suggestions).map(safeUsername).filter(Boolean).slice(0, 3);
    return { summary, highlights, usernames: usernames.length ? usernames : ['steadyobserver', 'quietbuilder', 'curiousnavigator'] };
  }

  function safeUsername(value: string) {
    return value.toLowerCase().replace(/[^a-z0-9_]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 32);
  }

  function updateUsername(value: string) {
    username = safeUsername(value);
    persistPending();
  }

  function startGoogleLogin() {
    if (!usernameValid) {
      error = 'Isi username minimal 3 karakter sebelum melanjutkan.';
      return;
    }
    error = '';
    persistPending();
    window.location.href = `${API_BASE}/api/v1/auth/google/start`;
  }

  function loginWithGoogle() {
    window.location.href = `${API_BASE}/api/v1/auth/google/start`;
  }

  function signOut() {
    window.location.href = `${API_BASE}/api/v1/auth/logout`;
  }

  async function restoreAuth() {
    try {
      const result = await getAuthMe();
      authUser = result.authenticated ? result.user : null;
      ownedProfiles = authUser ? ((await getUserHistory()).history ?? []) : [];
      analysisOpen = !ownedProfiles.some((item) => item.public_username);
      if (authUser && profile?.claim_token && interpretationId) await unlockFullResult();
    } catch {
      authUser = null;
    } finally {
      const url = new URL(window.location.href);
      if (url.searchParams.has('auth')) {
        url.searchParams.delete('auth');
        window.history.replaceState({}, '', url.pathname + url.search);
      }
    }
  }

  async function unlockFullResult() {
    if (!profile?.profile_id || !profile?.claim_token || !interpretationId) return;
    try {
      await syncUserHistory([{ profile_id: profile.profile_id, claim_token: profile.claim_token }]);
      fullResult = await getFullInterpretation(interpretationId);
      if (authUser?.email && usernameValid) {
        const published: any = await publishPublicProfile({
          profile_id: profile.profile_id,
          username,
          email: authUser.email,
          claim_token: profile.claim_token,
          display_name: authUser.name
        });
        localStorage.removeItem('hermex_pending_analysis');
        window.location.href = `/${published?.public_profile?.username ?? username}`;
        return;
      }
      showScreen('character');
    } catch (cause) {
      setError(messageFrom(cause), 'preview');
    }
  }

  function persistPending() {
    if (typeof localStorage === 'undefined' || !profile) return;
    const pending: PendingAnalysis = { profile, interpretationId, preview: guestPreview, answers, username, questions, questionnaireCount };
    localStorage.setItem('hermex_pending_analysis', JSON.stringify(pending));
  }

  function restorePending() {
    try {
      const pending = JSON.parse(localStorage.getItem('hermex_pending_analysis') || 'null') as PendingAnalysis | null;
      if (!pending?.profile) return;
      profile = pending.profile;
      interpretationId = pending.interpretationId ?? '';
      guestPreview = pending.preview
        ? normalizePreview({ interpretation: {
            preview_summary: pending.preview.summary,
            highlights: pending.preview.highlights,
            username_suggestions: pending.preview.usernames
          } })
        : guestPreview;
      answers = pending.answers ?? {};
      username = pending.username ?? guestPreview.usernames[0] ?? '';
      const restoredFirst = normalizeQuestion(profile?.questionnaire?.current_question);
      questions = (pending.questions ?? (restoredFirst ? [restoredFirst] : [])).filter((item) => Boolean(item?.id && item?.prompt));
      questionnaireCount = pending.questionnaireCount ?? Number(profile?.questionnaire?.count ?? questions.length);
      if (interpretationId) screen = 'preview';
    } catch {
      localStorage.removeItem('hermex_pending_analysis');
    }
  }

  function resetAnalysis() {
    screen = 'home';
    analysisOpen = !latestOwnedProfile;
    profile = null;
    fullResult = null;
    interpretationId = '';
    questions = [];
    questionnaireCount = 0;
    answers = {};
    guestPreview = { summary: '', highlights: [], usernames: [] };
    username = '';
    error = '';
    localStorage.removeItem('hermex_pending_analysis');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function confirmRetest() {
    if (!window.confirm('Mulai tes lagi? Hasil yang tersimpan tetap aman, tetapi isian yang belum selesai akan dihapus.')) return;
    resetAnalysis();
    analysisOpen = true;
    requestAnimationFrame(() => {
      analysisEntry?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
  }

  function setError(message: string, retry: Screen = profile ? 'questions' : 'home') {
    error = message;
    retryScreen = retry;
    showScreen(retry === 'home' ? 'home' : 'error');
  }

  function messageFrom(cause: unknown) {
    const message = cause instanceof Error ? cause.message : 'Terjadi kendala saat memproses data.';
    return /failed to fetch/i.test(message) ? 'Belum tersambung ke layanan analisis. Coba lagi sebentar.' : message;
  }

  function normalizeFullSections(value: any): Array<{ title: string; icon: string; body: string[] }> {
    const labels: Array<[string, string, string]> = [
      ['core_identity', 'Identitas dan motivasi inti', '✦'], ['identity_and_motivation', 'Identitas dan motivasi inti', '✦'],
      ['emotional_needs', 'Kebutuhan emosional', '♡'], ['approach_to_life', 'Cara menghadapi situasi baru', '↗'],
      ['social_approach', 'Cara menghadapi situasi baru', '↗'], ['thinking_and_communication', 'Cara berpikir dan berkomunikasi', '◇'],
      ['relationships', 'Nilai dan pola relasi', '∞'], ['relationships_and_values', 'Nilai dan pola relasi', '∞'],
      ['drive_and_boundaries', 'Dorongan dan batas pribadi', '→'], ['inner_dynamics', 'Dinamika internal', '◐'], ['inner_tensions', 'Dinamika internal', '◐'],
      ['dominant_patterns', 'Pola dominan', '◎'], ['growth_focus', 'Fokus pengembangan diri', '↑'],
      ['strengths', 'Kekuatan', '◆'], ['weaknesses', 'Hal yang perlu dijaga', '△'], ['careers', 'Arah eksplorasi', '⌁']
    ];
    const seen = new Set<string>();
    return labels.flatMap(([key, title, icon]) => {
      if (seen.has(title) || value?.[key] == null) return [];
      seen.add(title);
      const raw = value[key];
      const body = Array.isArray(raw) ? raw.map(displayValue) : [displayValue(raw)];
      return [{ title, icon, body: body.filter(Boolean) }];
    }).filter((section) => section.body.length);
  }

  function displayValue(value: unknown): string {
    if (typeof value === 'string') return value;
    if (typeof value === 'number' || typeof value === 'boolean') return String(value);
    if (value && typeof value === 'object') {
      const item = value as Record<string, unknown>;
      const preferred = ['summary', 'description', 'insight', 'text', 'focus'].find((key) => typeof item[key] === 'string');
      if (preferred) return String(item[preferred]);
      return Object.values(item).filter((entry) => typeof entry === 'string').join(' — ');
    }
    return '';
  }

  function planetPoint(planet: any, radius = 108) {
    const angle = ((Number(planet?.longitude ?? 0) - 90) * Math.PI) / 180;
    return { x: 150 + Math.cos(angle) * radius, y: 150 + Math.sin(angle) * radius };
  }
</script>

<svelte:head>
  <title>Analisis Kepribadian — Hermex</title>
  <meta name="description" content="Analisa kepribadian dari tempat tanggal lahir." />
  <meta name="theme-color" content="#fbfaf6" />
  <link rel="canonical" href="https://hermex.fun/" />
  <meta property="og:type" content="website" />
  <meta property="og:url" content="https://hermex.fun/" />
  <meta property="og:title" content="Analisis Kepribadian — Hermex" />
  <meta property="og:description" content="Analisa kepribadian dari tempat tanggal lahir." />
  <meta property="og:image" content="https://hermex.fun/hermex-social-preview.png" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:image" content="https://hermex.fun/hermex-social-preview.png" />
  <link rel="icon" href="/icons/hermex-star.svg" />
</svelte:head>

<main>
  <header class="site-header">
    <button class="brand" type="button" on:click={resetAnalysis} aria-label="Kembali ke halaman awal">
      <svg viewBox="0 0 48 48" aria-hidden="true"><path d="M24 5l5 12 13 2-10 8 3 13-11-7-11 7 3-13-10-8 13-2 5-12z" /></svg>
      <span>hermex.fun</span>
    </button>
    {#if screen !== 'home'}
      <button class="start-over" type="button" aria-label="Mulai ulang analisis" title="Mulai ulang analisis" on:click={resetAnalysis}>
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4.6 9A8 8 0 1 1 4 12M4.6 9V4.5M4.6 9H9" /></svg>
      </button>
    {:else if authUser}
      <details class="account-menu">
        <summary aria-label="Buka menu akun">{#if authUser.picture}<img src={authUser.picture} alt="" referrerpolicy="no-referrer" />{:else}<span>{(authUser.name || authUser.email || 'U').slice(0, 1)}</span>{/if}</summary>
        <div class="account-popover"><strong>{authUser.name || 'Akun Hermex'}</strong><span>{authUser.email}</span><a href="/profil">Atur profil <span aria-hidden="true">→</span></a><button type="button" on:click={signOut}>Keluar</button></div>
      </details>
    {:else}
      <button class="google-icon" type="button" aria-label="Masuk dengan Google" title="Masuk dengan Google" on:click={loginWithGoogle}>
        <svg viewBox="0 0 18 18" aria-hidden="true"><path fill="#4285F4" d="M17.64 9.205c0-.638-.057-1.252-.164-1.841H9v3.481h4.844a4.14 4.14 0 0 1-1.797 2.716v2.259h2.909c1.702-1.567 2.684-3.875 2.684-6.615Z"/><path fill="#34A853" d="M9 18c2.43 0 4.468-.806 5.956-2.18l-2.909-2.259c-.806.54-1.835.859-3.047.859-2.344 0-4.328-1.585-5.037-3.714H.956v2.332A8.998 8.998 0 0 0 9 18Z"/><path fill="#FBBC05" d="M3.963 10.706A5.41 5.41 0 0 1 3.682 9c0-.592.102-1.167.281-1.706V4.962H.956A9.002 9.002 0 0 0 0 9c0 1.452.347 2.827.956 4.038l3.007-2.332Z"/><path fill="#EA4335" d="M9 3.58c1.321 0 2.507.454 3.441 1.345l2.581-2.58C13.464.892 11.426 0 9 0A8.998 8.998 0 0 0 .956 4.962l3.007 2.332C4.672 5.165 6.656 3.58 9 3.58Z"/></svg>
      </button>
    {/if}
  </header>

  {#if screen === 'home'}
    <section class="hero">
      <div class="hero-copy">
        <p class="eyebrow">Kenali pola dirimu</p>
        <h1>Analisa kepribadian dari tempat tanggal lahir</h1>
        <p class="lead">Jawab beberapa pernyataan untuk membandingkan pola kelahiran dengan cara kamu melihat dirimu.</p>
      </div>
      <div class="home-action">
        {#if latestOwnedProfile}
          <article class="returning-card">
            <span aria-hidden="true">↗</span><div><p class="eyebrow">Kartu karaktermu sudah siap</p><h2>Ajak teman ikut menilai</h2><p>Bagikan hasilmu, minta mereka memvalidasi karaktermu, lalu ajak mereka mencoba analisisnya sendiri.</p></div>
            <div class="returning-actions"><a href={`/${latestOwnedProfile.public_username}`}>Buka dan bagikan <span aria-hidden="true">↗</span></a><button type="button" on:click={confirmRetest}><span aria-hidden="true">↻</span> Coba tes lagi</button></div>
          </article>
        {/if}
        <details class="analysis-entry" bind:this={analysisEntry} bind:open={analysisOpen}>
          <summary>{latestOwnedProfile ? 'Buat analisis baru' : 'Mulai analisis'}</summary>
          <form class="birth-form" on:submit|preventDefault={beginAnalysis}>
        <fieldset class="birth-moment">
          <legend>Tanggal dan jam lahir</legend>
          <div class="date-time">
            <label><span>Tanggal lahir</span><input type="date" bind:value={birthDate} max={new Date().toISOString().slice(0, 10)} required /></label>
            <label><span>Jam lahir <small>opsional</small></span><input type="time" bind:value={birthTime} /></label>
          </div>
          <p>Jam kosong dianggap 00.00. Jam yang tepat membantu hasilnya lebih akurat.</p>
        </fieldset>
        <label class="location">Lokasi lahir
          <input
            type="text" value={cityQuery} autocomplete="off" role="combobox" aria-expanded={cityOpen}
            aria-controls="city-options" aria-autocomplete="list" placeholder="Cari kota kelahiran"
            on:focus={() => (cityOpen = true)} on:input={(event) => updateCity(event.currentTarget.value)}
          />
          {#if cityOpen && filteredCities.length}
            <div class="city-options" id="city-options" role="listbox">
              {#each filteredCities as city}
                <button type="button" role="option" aria-selected={selectedCity?.label === city.label} on:click={() => chooseCity(city)}>
                  <strong>{city.label}</strong><small>{city.timezone}</small>
                </button>
              {/each}
            </div>
          {/if}
        </label>
        {#if error}<p class="form-error" role="alert">{error}</p>{/if}
        <button class="primary" type="submit">Mulai analisis <span aria-hidden="true">→</span></button>
        <p class="privacy-note">Data digunakan untuk membuat analisis ini. Hasil bersifat reflektif, bukan penentu keputusan hidup.</p>
          </form>
        </details>
      </div>
    </section>

    {#if communityProfiles.length}
      <section class="community" aria-labelledby="community-title">
        <div><p class="eyebrow">Sudah mencoba</p><h2 id="community-title">Kenalan dengan kartu mereka</h2></div>
        <div class="community-list">{#each communityProfiles as item}<a href={`/${item.username}`}>{#if item.avatar_url}<img src={item.avatar_url} alt="" referrerpolicy="no-referrer" />{:else}<span>{item.username.slice(0,1).toUpperCase()}</span>{/if}<strong>{item.username}</strong></a>{/each}</div>
      </section>
    {/if}

    {#if skyPosts.length}
      <section class="sky-section" aria-labelledby="sky-title">
        <div class="section-title"><p class="eyebrow">Berita Langit</p><h2 id="sky-title">Yang baru terjadi</h2></div>
        <div class="sky-grid">{#each skyPosts as item}<article class="sky-card"><small>{item.tag}</small><h3>{item.title}</h3><p>{item.summary}</p><a href={`/berita-langit/${item.slug}`}>Baca artikel <span aria-hidden="true">↗</span></a></article>{/each}</div>
        <a class="all-news" href="/berita-langit">Lihat semua Berita Langit <span aria-hidden="true">→</span></a>
      </section>
    {/if}
  {:else if screen === 'natal-loading' || screen === 'ai-loading'}
    <section class="loading-state" aria-live="polite">
      <div class="loading-contour"><PersonalityContour values={screen === 'natal-loading' ? [2,3,2,4,3,2,4,2,3,4] : contourValues} label="Analisis sedang diproses" /></div>
      <p class="eyebrow">{screen === 'natal-loading' ? 'Langkah 1 dari 3' : 'Langkah 3 dari 3'}</p>
      <h1>{screen === 'natal-loading' ? natalLoadingMessages[loadingMessageIndex] : aiLoadingMessages[loadingMessageIndex]}</h1>
      <p class="ai-status"><span aria-hidden="true"></span> AI sedang menyusun analisis khusus untukmu</p>
      <p>Proses ini biasanya membutuhkan beberapa detik.</p>
    </section>
  {:else if screen === 'questions'}
    <Questionnaire {questions} count={questionnaireCount} {answers} {scaleLabels} onAnswer={answerQuestion} onNext={loadQuestion} onSubmit={submitQuestionnaire} />
  {:else if screen === 'preview'}
    <section class="preview">
      <div class="preview-grid">
        <div class="preview-contour"><PersonalityContour values={contourValues} /></div>
        <div>
          <p class="eyebrow">Hasil awal</p>
          <h1>Pola utamamu mulai terlihat</h1>
          <p class="preview-summary">{guestPreview.summary}</p>
          {#if guestPreview.highlights.length}<ul class="highlights">{#each guestPreview.highlights as item}<li>{item}</li>{/each}</ul>{/if}
        </div>
      </div>
      <div class="login-gate">
        <div class="gate-copy"><h2>Lihat analisis lengkapmu</h2><p>Gratis. Pilih username, lalu masuk untuk membuka hubungan antarpola dan menyimpan kartu karaktermu.</p></div>
        <div class="suggestions" aria-label="Rekomendasi username">
          {#each guestPreview.usernames as suggestion}<button class:active={username === suggestion} type="button" on:click={() => updateUsername(suggestion)}>@{suggestion}</button>{/each}
        </div>
        <label class="username-field">Username
          <span class="username-input"><span aria-hidden="true">@</span><input value={username} minlength="3" maxlength="32" required aria-describedby="username-help" on:input={(event) => updateUsername(event.currentTarget.value)} /></span>
          <small id="username-help">Wajib diisi, minimal 3 karakter. Rekomendasi ini tetap bisa kamu ubah.</small>
        </label>
        {#if error}<p class="gate-error" role="alert">{error}</p>{/if}
        <button class="google-button" type="button" disabled={!usernameValid} on:click={startGoogleLogin}>
          <svg viewBox="0 0 18 18" aria-hidden="true"><path fill="#4285F4" d="M17.64 9.205c0-.638-.057-1.252-.164-1.841H9v3.481h4.844a4.14 4.14 0 0 1-1.797 2.716v2.259h2.909c1.702-1.567 2.684-3.875 2.684-6.615Z"/><path fill="#34A853" d="M9 18c2.43 0 4.468-.806 5.956-2.18l-2.909-2.259c-.806.54-1.835.859-3.047.859-2.344 0-4.328-1.585-5.037-3.714H.956v2.332A8.998 8.998 0 0 0 9 18Z"/><path fill="#FBBC05" d="M3.963 10.706A5.41 5.41 0 0 1 3.682 9c0-.592.102-1.167.281-1.706V4.962H.956A9.002 9.002 0 0 0 0 9c0 1.452.347 2.827.956 4.038l3.007-2.332Z"/><path fill="#EA4335" d="M9 3.58c1.321 0 2.507.454 3.441 1.345l2.581-2.58C13.464.892 11.426 0 9 0A8.998 8.998 0 0 0 .956 4.962l3.007 2.332C4.672 5.165 6.656 3.58 9 3.58Z"/></svg>
          <span>Lanjutkan dengan Google</span>
        </button>
      </div>
    </section>
  {:else if screen === 'character'}
    <CharacterCard summary={guestPreview.summary} highlights={guestPreview.highlights} {username} values={contourValues} onUsername={updateUsername} onFull={() => showScreen('chart')} />
  {:else if screen === 'chart'}
    <section class="chart-page">
      <button class="back-link" type="button" on:click={() => showScreen('character')}>← Kembali ke kartu karakter</button>
      <p class="eyebrow">Analisis lengkap</p>
      <h1>Bagaimana setiap bagian dirimu saling terhubung</h1>
      {#if fullSections.length}
        <div class="analysis-sections">
          {#each fullSections as section}<article><span aria-hidden="true">{section.icon}</span><div><h2>{section.title}</h2>{#each section.body as paragraph}<p>{paragraph}</p>{/each}</div></article>{/each}
        </div>
      {:else}<p class="empty-detail">Penjelasan lengkap belum tersedia, tetapi detail natal chart tetap bisa dibaca di bawah.</p>{/if}

      <details class="natal-details">
        <summary>Lihat detail natal chart</summary>
        <div class="wheel-layout">
          <svg class="natal-wheel" viewBox="0 0 300 300" role="img" aria-label="Natal chart">
            <circle cx="150" cy="150" r="128" /><circle cx="150" cy="150" r="92" /><circle cx="150" cy="150" r="46" />
            {#each Array(12) as _, index}
              {@const angle = (Math.PI * 2 * index) / 12}
              <line x1={150 + Math.cos(angle) * 92} y1={150 + Math.sin(angle) * 92} x2={150 + Math.cos(angle) * 128} y2={150 + Math.sin(angle) * 128} />
            {/each}
            {#each aspects.slice(0, 14) as aspect}
              {@const left = chart?.planets?.[aspect.left]}
              {@const right = chart?.planets?.[aspect.right]}
              {#if left && right}<line class="aspect" x1={planetPoint(left).x} y1={planetPoint(left).y} x2={planetPoint(right).x} y2={planetPoint(right).y} />{/if}
            {/each}
            {#each planets as [name, planet]}
              {@const point = planetPoint(planet)}
              <circle class="planet" cx={point.x} cy={point.y} r="9" /><text x={point.x} y={point.y - 13} text-anchor="middle">{name.slice(0, 2)}</text>
            {/each}
          </svg>
          <div class="planet-list">
            {#each planets as [name, planet]}
              {@const house = chart?.houses?.planet_houses?.[name]}
              <article><strong>{name}</strong><span>{planet.zodiac_sign} {Number(planet.degree_in_sign ?? 0).toFixed(1)}°</span>{#if house}<small>House {house}</small>{/if}</article>
            {/each}
          </div>
        </div>
      </details>
      <RawResultExport {profile} analysis={fullData} {username} />
      <a class="methodology-link" href="/metodologi"><span aria-hidden="true">◎</span><span><strong>Lihat cara Hermex menyusun hasil</strong><small>Dari data lahir, pertanyaan, sampai batas interpretasinya.</small></span><span aria-hidden="true">→</span></a>
    </section>
  {:else if screen === 'error'}
    <section class="error-state"><span>!</span><h1>Analisis belum selesai</h1><p role="alert">{error}</p><button class="primary" type="button" on:click={() => showScreen(retryScreen)}><span aria-hidden="true">↻</span> Coba lagi</button></section>
  {/if}

  {#if screen !== 'questions' && screen !== 'natal-loading' && screen !== 'ai-loading'}
    <footer>
      <div><span>© {new Date().getFullYear()} Hermex</span><small class="credit">Created by <a href="https://wau.my.id" target="_blank" rel="noreferrer">wau.my.id</a></small></div>
      <nav aria-label="Tautan footer"><a href="/metodologi">Metodologi</a><a href="/terms">Terms</a><a href="/privacy">Privacy</a><a class="social" href="https://github.com/wauputr4/hermex" aria-label="GitHub Hermex" target="_blank" rel="noreferrer"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2a10 10 0 0 0-3.16 19.49c.5.09.68-.22.68-.48v-1.87c-2.78.6-3.37-1.18-3.37-1.18-.45-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.61.07-.61 1 .07 1.53 1.03 1.53 1.03.9 1.53 2.35 1.09 2.92.83.09-.65.35-1.09.64-1.34-2.22-.25-4.55-1.11-4.55-4.94 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.64 0 0 .84-.27 2.75 1.02A9.58 9.58 0 0 1 12 6.82c.85 0 1.7.11 2.5.34 1.91-1.29 2.75-1.02 2.75-1.02.55 1.37.2 2.39.1 2.64.64.7 1.03 1.59 1.03 2.68 0 3.84-2.34 4.69-4.57 4.93.36.31.68.92.68 1.85v2.77c0 .27.18.58.69.48A10 10 0 0 0 12 2Z" /></svg></a><a class="social" href="https://www.threads.com/@wauputra" aria-label="Threads @wauputra" target="_blank" rel="noreferrer"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12.01 2C6.49 2 3 5.66 3 11.22 3 16.73 6.27 20 11.77 20c4.68 0 7.23-2.42 7.23-6.27 0-2.64-1.49-4.62-4.26-5.3-.2-2.21-1.44-3.44-3.64-3.44-1.73 0-2.91.9-3.29 2.41l1.72.46c.2-.77.72-1.15 1.55-1.15 1.02 0 1.55.64 1.57 1.96-.3-.02-.6-.03-.91-.03-3.6 0-5.59 1.47-5.59 4.13 0 2.18 1.59 3.58 4.05 3.58 2.47 0 4.16-1.44 4.16-3.9 0-.17-.01-.33-.02-.49 1.44.49 2.13 1.57 2.13 3.18 0 2.84-1.96 4.62-5.11 4.62-4.39 0-7.04-2.78-7.04-7.4 0-4.67 2.81-7.5 7.48-7.5 4.57 0 7.15 2.85 7.15 7.45H21C21 5.76 17.57 2 12.01 2Zm-.82 11.67c-1.37 0-2.29-.65-2.29-1.65 0-1.22 1.04-1.9 3.4-1.9.42 0 .83.02 1.21.06.03.2.04.4.04.61 0 1.81-.82 2.88-2.36 2.88Z" /></svg></a></nav>
    </footer>
  {/if}
</main>

<style>
  main { width: min(1180px, calc(100% - 40px)); min-height: 100vh; margin: auto; }
  .site-header { display: flex; justify-content: space-between; align-items: center; min-height: 84px; border-bottom: 1px solid #e7e1d9; }
  .brand, .start-over { border: 0; background: transparent; color: #302a36; cursor: pointer; }
  .brand { display: flex; align-items: center; gap: 10px; padding: 0; font-size: 1.1rem; font-weight: 820; }
  .brand svg { width: 34px; height: 34px; padding: 6px; border-radius: 11px; background: #fff0ce; fill: #f1b86a; stroke: #302a36; stroke-width: 1.5; }
  .start-over { display: grid; width: 44px; height: 44px; place-items: center; border-radius: 50%; color: #615968; }
  .start-over:hover { background: #f2f0ff; color: #5b55d6; }
  .start-over:focus-visible { outline: 3px solid rgba(91,85,214,.28); outline-offset: 2px; }
  .start-over svg { width: 22px; height: 22px; fill: none; stroke: currentColor; stroke-width: 1.9; stroke-linecap: round; stroke-linejoin: round; }
  .google-icon { display: grid; width: 40px; height: 40px; place-items: center; border: 1px solid #e7e1d9; border-radius: 50%; background: #fff; cursor: pointer; }
  .google-icon svg { width: 18px; height: 18px; }
  .account-menu { position: relative; }
  .account-menu summary { display: grid; width: 42px; height: 42px; overflow: hidden; place-items: center; border: 1px solid #e7e1d9; border-radius: 50%; background: #fff0ce; color: #302a36; font-weight: 800; cursor: pointer; list-style: none; }
  .account-menu summary::-webkit-details-marker { display: none; }
  .account-menu img { width: 100%; height: 100%; object-fit: cover; }
  .account-popover { position: absolute; z-index: 20; top: 50px; right: 0; display: grid; width: min(280px, calc(100vw - 32px)); gap: 8px; border: 1px solid #e7e1d9; border-radius: 16px; padding: 14px; background: #fff; box-shadow: 0 18px 44px rgba(48,42,54,.14); }
  .account-popover span { overflow: hidden; color: #827b82; font-size: .76rem; text-overflow: ellipsis; }
  .account-popover a, .account-popover button { border: 0; border-radius: 9px; padding: 9px; background: #f7f5f1; color: #302a36; font: inherit; font-weight: 700; text-align: left; text-decoration: none; cursor: pointer; }
  .hero { display: grid; grid-template-columns: 1fr minmax(360px, 470px); gap: clamp(44px, 8vw, 110px); align-items: center; min-height: min(730px, calc(100vh - 84px)); padding: 72px 0; }
  .eyebrow { margin: 0 0 12px; color: #5b55d6; font-size: .76rem; font-weight: 800; letter-spacing: .09em; text-transform: uppercase; }
  .hero h1, .preview h1, .chart-page > h1, .loading-state h1, .error-state h1 { margin: 0; max-width: 720px; font-size: clamp(2.8rem, 6.6vw, 5.8rem); line-height: .94; letter-spacing: -.065em; }
  .lead { max-width: 620px; margin: 24px 0 0; color: #615968; font-size: clamp(1rem, 1.6vw, 1.2rem); line-height: 1.65; }
  .birth-form { position: relative; border: 1px solid #e7e1d9; border-radius: 24px; padding: 28px; background: rgba(255,255,255,.88); box-shadow: 0 24px 70px rgba(48,42,54,.08); }
  .birth-moment { margin: 0; border: 1px solid #d7d0ca; border-radius: 16px; padding: 16px; }
  .birth-moment legend { padding: 0 7px; color: #302a36; font-size: .86rem; font-weight: 740; }
  .birth-moment p { margin: 10px 0 0; color: #827b82; font-size: .72rem; line-height: 1.45; }
  .date-time { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  label { display: grid; gap: 8px; color: #302a36; font-size: .86rem; font-weight: 740; }
  label > span { color: #827b82; font-size: .72rem; font-weight: 600; }
  .date-time label > span { display: flex; justify-content: space-between; color: #615968; }
  .date-time label small { font-size: inherit; font-weight: 560; }
  label small { color: #827b82; font-weight: 500; line-height: 1.45; }
  input { width: 100%; min-width: 0; min-height: 50px; border: 1px solid #d7d0ca; border-radius: 13px; padding: 0 14px; background: #fff; color: #302a36; }
  input:focus { border-color: #5b55d6; outline-color: rgba(91,85,214,.2); }
  .location { position: relative; margin-top: 18px; }
  .city-options { position: absolute; z-index: 10; top: calc(100% + 6px); left: 0; right: 0; max-height: 270px; overflow: auto; border: 1px solid #d7d0ca; border-radius: 14px; padding: 6px; background: #fff; box-shadow: 0 18px 44px rgba(48,42,54,.14); }
  .city-options button { display: grid; width: 100%; border: 0; border-radius: 9px; padding: 10px; background: transparent; color: #302a36; text-align: left; cursor: pointer; }
  .city-options button:hover, .city-options button[aria-selected="true"] { background: #f2f0ff; }
  .city-options small { color: #827b82; }
  .primary { display: flex; justify-content: space-between; align-items: center; width: 100%; min-height: 54px; margin-top: 22px; border: 0; border-radius: 14px; padding: 0 18px; background: #5b55d6; color: #fff; font-weight: 760; cursor: pointer; }
  .privacy-note, .form-error { margin: 14px 2px 0; color: #827b82; font-size: .76rem; line-height: 1.45; }
  .form-error { color: #a33c52; font-weight: 700; }
  .home-action, .analysis-entry { min-width: 0; }
  .analysis-entry { border: 0; }
  .analysis-entry > summary { margin-bottom: 12px; color: #5b55d6; font-weight: 760; cursor: pointer; }
  .analysis-entry[open] > summary { display: none; }
  .returning-card { margin-bottom: 14px; border: 1px solid #e7e1d9; border-radius: 22px; padding: 24px; background: #302a36; color: #fff; }
  .returning-card h2 { margin: 0 0 8px; }
  .returning-card p { color: #e8e3eb; line-height: 1.5; }
  .returning-card a { display: inline-block; border-radius: 12px; padding: 11px 14px; background: #f1b86a; color: #302a36; font-weight: 800; text-decoration: none; }
  .returning-actions { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
  .returning-actions button { border: 1px solid rgba(255,255,255,.35); border-radius: 10px; padding: 8px 11px; background: transparent; color: #fff; font: inherit; font-size: .76rem; font-weight: 760; cursor: pointer; }
  .returning-actions button:hover { border-color: #fff; }
  .returning-actions button:focus-visible { outline: 3px solid rgba(241,184,106,.45); outline-offset: 2px; }
  .community, .sky-section { margin: 54px 0; border-top: 1px solid #e7e1d9; padding-top: 34px; }
  .community h2, .sky-section h2 { margin: 0; font-size: clamp(1.5rem, 3vw, 2.25rem); letter-spacing: -.03em; }
  .community-list { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 20px; }
  .community-list a { display: flex; align-items: center; gap: 8px; border: 1px solid #e7e1d9; border-radius: 999px; padding: 7px 12px 7px 7px; color: #302a36; font-weight: 720; text-decoration: none; }
  .community-list img, .community-list span:first-child { display: grid; width: 28px; height: 28px; place-items: center; border-radius: 50%; object-fit: cover; background: #fff0ce; }
  .sky-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-top: 20px; }
  .sky-card { display: grid; align-content: start; min-height: 220px; border: 1px solid #e7e1d9; border-radius: 18px; padding: 20px; color: #302a36; text-decoration: none; }
  .sky-card h3 { margin: 0; font-size: 1.2rem; letter-spacing: -.02em; }
  .sky-card p:not(.eyebrow) { color: #615968; line-height: 1.5; }
  .all-news { display: inline-block; margin-top: 20px; color: #5b55d6; font-weight: 760; text-decoration: none; }
  .loading-state, .error-state { display: grid; justify-items: center; align-content: center; min-height: 72vh; text-align: center; }
  .loading-contour { width: min(260px, 68vw); margin-bottom: 28px; animation: breathe 2.2s ease-in-out infinite; }
  .loading-state h1, .error-state h1 { max-width: 760px; font-size: clamp(2.2rem, 5vw, 4.8rem); }
  .loading-state > p:last-child, .error-state p { color: #827b82; }
  .loading-state .ai-status { display: flex; align-items: center; gap: 8px; margin: 24px 0 4px; color: #615968; font-size: .86rem; font-weight: 700; }
  .ai-status span { width: 8px; height: 8px; border-radius: 50%; background: #5b55d6; box-shadow: 0 0 0 6px rgba(91,85,214,.12); animation: signal 1.4s ease-in-out infinite; }
  .preview { width: min(920px, 100%); margin: 58px auto; }
  .preview-grid { display: grid; grid-template-columns: minmax(220px, .7fr) 1.3fr; gap: clamp(30px, 6vw, 72px); align-items: center; }
  .preview-contour { padding: 10px; border-radius: 50%; background: #fff; }
  .preview h1 { font-size: clamp(2.5rem, 6vw, 5rem); }
  .preview-summary { color: #615968; font-size: 1.06rem; line-height: 1.65; }
  .highlights { display: flex; flex-wrap: wrap; gap: 8px; margin: 20px 0 0; padding: 0; list-style: none; }
  .highlights li { border-radius: 999px; padding: 8px 12px; background: #fff3dc; color: #594638; font-size: .84rem; font-weight: 700; }
  .login-gate { display: grid; grid-template-columns: 1fr minmax(260px, 380px); gap: 20px 34px; align-items: end; margin-top: 48px; border-top: 1px solid #e7e1d9; padding-top: 30px; }
  .login-gate h2 { margin: 0; font-size: 1.3rem; }
  .login-gate p { margin: 6px 0 0; color: #827b82; line-height: 1.55; }
  .suggestions { display: flex; flex-wrap: wrap; gap: 8px; margin: 18px 0; }
  .suggestions button { width: auto; min-height: 0; margin: 0; border: 1px solid #d7d0ca; border-radius: 999px; padding: 7px 10px; background: #fff; color: #615968; font-size: .78rem; cursor: pointer; }
  .suggestions button.active { border-color: #5b55d6; background: #f2f0ff; color: #5b55d6; }
  .login-gate .suggestions { grid-column: 1 / -1; margin: 0; }
  .username-field { min-width: 0; }
  .username-input { display: flex; align-items: center; min-height: 50px; border: 1px solid #d7d0ca; border-radius: 13px; background: #fff; color: #827b82; font-size: 1rem; }
  .username-input > span { padding-left: 14px; }
  .username-input input { min-height: 48px; border: 0; padding-left: 3px; }
  .username-input:focus-within { border-color: #5b55d6; outline: 2px solid rgba(91,85,214,.2); }
  .username-input input:focus { outline: 0; }
  .username-field small { color: #827b82; font-weight: 500; line-height: 1.4; }
  .gate-error { grid-column: 1 / -1; margin: -8px 0 0 !important; color: #a33c52 !important; font-size: .78rem; font-weight: 700; }
  .login-gate .google-button { display: flex; justify-content: center; align-items: center; gap: 12px; width: 100%; min-height: 44px; margin: 0; border: 1px solid #747775; border-radius: 4px; padding: 0 12px; background: #fff; color: #1f1f1f; font-family: Arial, sans-serif; font-size: 14px; font-weight: 500; line-height: 20px; cursor: pointer; }
  .google-button svg { flex: 0 0 18px; width: 18px; height: 18px; }
  .google-button:hover:not(:disabled) { background: #f8faff; box-shadow: 0 1px 2px rgba(60,64,67,.3); }
  .google-button:disabled { opacity: .48; cursor: not-allowed; }
  .chart-page { width: min(940px, 100%); margin: 52px auto 90px; }
  .chart-page > h1 { font-size: clamp(2.6rem, 6vw, 5.4rem); }
  .back-link { margin-bottom: 50px; border: 0; padding: 0; background: transparent; color: #5b55d6; font-weight: 760; cursor: pointer; }
  .analysis-sections { margin-top: 58px; border-top: 1px solid #e7e1d9; }
  .analysis-sections article { display: grid; grid-template-columns: 70px 1fr; gap: 24px; border-bottom: 1px solid #e7e1d9; padding: 30px 0; }
  .analysis-sections article > span { display: grid; width: 38px; height: 38px; place-items: center; border-radius: 50%; background: #fff0d1; color: #5b55d6; font-size: 1.1rem; font-weight: 820; }
  .analysis-sections h2 { margin: 0 0 10px; font-size: 1.35rem; }
  .analysis-sections p { margin: 7px 0; color: #615968; line-height: 1.65; }
  .empty-detail { color: #827b82; }
  .natal-details { margin-top: 48px; border: 1px solid #e7e1d9; border-radius: 24px; padding: 22px; background: #fff; }
  .natal-details summary { cursor: pointer; color: #302a36; font-weight: 780; }
  .wheel-layout { display: grid; grid-template-columns: minmax(280px, .9fr) 1.1fr; gap: 34px; align-items: start; margin-top: 28px; }
  .natal-wheel { width: 100%; max-width: 430px; margin: auto; }
  .natal-wheel circle, .natal-wheel line { fill: none; stroke: #d7d0ca; stroke-width: 1; }
  .natal-wheel .aspect { stroke: rgba(91,85,214,.48); }
  .natal-wheel .planet { fill: #f1b86a; stroke: #302a36; stroke-width: 1.5; }
  .natal-wheel text { fill: #302a36; font-size: 8px; font-weight: 800; }
  .planet-list { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .planet-list article { display: grid; border-radius: 12px; padding: 12px; background: #fbfaf6; }
  .planet-list span, .planet-list small { color: #827b82; font-size: .8rem; }
  .methodology-link { display: grid; grid-template-columns: 42px 1fr auto; gap: 14px; align-items: center; margin-top: 18px; border: 1px solid #e7e1d9; border-radius: 18px; padding: 18px; background: #fff; color: #302a36; text-decoration: none; }
  .methodology-link > span:first-child { display: grid; width: 42px; height: 42px; place-items: center; border-radius: 13px; background: #f2efff; color: #5b55d6; font-size: 1.25rem; }
  .methodology-link strong, .methodology-link small { display: block; }
  .methodology-link small { margin-top: 3px; color: #827b82; }
  .methodology-link:focus-visible { outline: 3px solid rgba(91,85,214,.25); outline-offset: 3px; }
  .error-state > span { display: grid; width: 54px; height: 54px; margin-bottom: 22px; place-items: center; border-radius: 50%; background: #fbe6e9; color: #a33c52; font-size: 1.5rem; font-weight: 800; }
  .error-state .primary { width: auto; min-width: 180px; }
  footer { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; min-height: 100px; border-top: 1px solid #e7e1d9; color: #827b82; font-size: .82rem; }
  footer .credit { display: block; margin-top: 5px; }
  footer nav { display: flex; flex-wrap: wrap; align-items: center; justify-content: flex-end; gap: 18px; }
  footer a { color: #615968; text-decoration: none; }
  footer .social { display: grid; flex: 0 0 32px; width: 32px; height: 32px; place-items: center; border: 1px solid #e7e1d9; border-radius: 50%; }
  footer svg { width: 17px; fill: currentColor; }
  @keyframes breathe { 50% { transform: scale(1.035) rotate(1.5deg); opacity: .82; } }
  @keyframes signal { 50% { box-shadow: 0 0 0 10px rgba(91,85,214,0); opacity: .72; } }
  @media (max-width: 760px) {
    main { width: min(100% - 28px, 680px); }
    .site-header { min-height: 68px; }
    .hero { grid-template-columns: 1fr; gap: 36px; min-height: auto; padding: 54px 0; }
    .hero h1 { font-size: clamp(2.9rem, 14vw, 4.7rem); }
    .birth-form { padding: 20px; }
    .preview-grid, .wheel-layout { grid-template-columns: 1fr; }
    .preview-grid h1 { font-size: clamp(2.5rem, 12vw, 4.1rem); }
    .preview-summary { overflow-wrap: anywhere; font-size: 1rem; }
    .preview-contour { width: min(270px, 80%); margin: auto; }
    .login-gate { grid-template-columns: 1fr; }
    .login-gate .suggestions, .gate-error { grid-column: 1; }
    .community, .sky-section { margin: 36px 0; }
    .sky-grid { grid-template-columns: 1fr; }
    .analysis-sections article { grid-template-columns: 38px minmax(0, 1fr); gap: 12px; }
    .suggestions { gap: 6px; }
    .suggestions button { max-width: 100%; overflow-wrap: anywhere; }
  }
  @media (max-width: 480px) {
    .date-time { grid-template-columns: 1fr; }
    .planet-list { grid-template-columns: 1fr; }
    footer { flex-direction: column; align-items: flex-start; gap: 20px; padding: 24px 0; }
    footer nav { justify-content: flex-start; }
  }
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { scroll-behavior: auto !important; animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; }
  }
</style>
