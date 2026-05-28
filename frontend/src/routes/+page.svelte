<script lang="ts">
  import { onMount } from 'svelte';
  import { analyzeBirth, interpretProfile, validateBirth } from '$lib/api/hermex';

  type Lang = 'id' | 'en';
  type Screen = 'home' | 'profile' | 'hermes-loading' | 'hermes' | 'learn' | 'register' | 'ai-error';

  const t = {
    id: {
      badge: 'Alpha game', title: 'Mulai quest astrologi kecilmu.',
      subtitle: 'Masukkan data lahir, lihat chart kosmik, lalu minta Hermes membaca pola umum untuk refleksi diri.',
      name: 'Nama', optional: 'opsional', date: 'Tanggal lahir', time: 'Jam lahir', place: 'Tempat lahir', citySearch: 'Cari kota lahir',
      analyze: 'Buka Astrologyku', analyzing: 'Membuka chart...', edit: 'Edit data', language: 'Bahasa', selectedCity: 'Kota terpilih',
      locationHint: 'Lat/lon dan zona waktu ikut memengaruhi chart.', features: 'Yang bisa dicoba', profile: 'Kartu Karakter', chart: 'Chart Explorer',
      askHermes: 'Analisis Kosmik Saya', validating: 'Kunci kepastian', validate: 'Jawab validasi cepat', processingTitle: 'Hermes sedang membaca chart',
      processingBody: 'Menggabungkan posisi planet, zodiac, house, aspect, dan bahasa yang kamu pilih.', hermes: 'Analisis Kosmik Saya', summary: 'Ringkasan',
      strengths: 'Kekuatan', weaknesses: 'Kelemahan', love: 'Percintaan', interests: 'Minat', talents: 'Bakat', career: 'Arah Karier', fiveYear: 'Roadmap 5 tahun terakhir',
      back: 'Kembali ke chart', askAgain: 'Tanya ulang Hermes', learn: 'Belajar Astrology', register: 'Daftar untuk penjelasan lengkap', feedback: 'Seberapa cocok hasilnya?', suggestion: 'Saran dan masukan (opsional)', sendFeedback: 'Kirim feedback', registerTitle: 'Daftar untuk membaca detail lengkap', registerBody: 'MVP ini belum menyimpan akun. Ini placeholder untuk halaman registrasi berikutnya.', email: 'Email', aiErrorTitle: 'Gagal menghubungkan AI Hermex', aiErrorBody: 'Hermes belum bisa terhubung ke provider AI. Chart kamu tetap aman; coba lagi sebentar lagi atau kembali ke chart.', retry: 'Coba lagi', ethics: 'Untuk refleksi dan pengembangan diri, bukan ramalan mutlak.'
    },
    en: {
      badge: 'Alpha game', title: 'Start your tiny astrology quest.',
      subtitle: 'Enter birth context, inspect the cosmic chart, then ask Hermes for a general reflective reading.',
      name: 'Name', optional: 'optional', date: 'Birth date', time: 'Birth time', place: 'Birth place', citySearch: 'Search birth city',
      analyze: 'Open My Astrology', analyzing: 'Opening chart...', edit: 'Edit data', language: 'Language', selectedCity: 'Selected city',
      locationHint: 'Latitude, longitude, and timezone influence the chart.', features: 'Things to try', profile: 'Character Card', chart: 'Chart Explorer',
      askHermes: 'My Cosmic Analysis', validating: 'Confidence key', validate: 'Answer quick validation', processingTitle: 'Hermes is reading your chart',
      processingBody: 'Combining planets, zodiac, houses, aspects, and your selected language.', hermes: 'My Cosmic Analysis', summary: 'Summary',
      strengths: 'Strengths', weaknesses: 'Weaknesses', love: 'Love', interests: 'Interests', talents: 'Talents', career: 'Career Paths', fiveYear: 'Last 5-Year Roadmap',
      back: 'Back to chart', askAgain: 'Ask Hermes again', learn: 'Learn Astrology', register: 'Register for full explanation', feedback: 'How accurate did this feel?', suggestion: 'Suggestions and feedback (optional)', sendFeedback: 'Send feedback', registerTitle: 'Register to read the full detail', registerBody: 'This MVP does not create accounts yet. This is a placeholder for the next registration flow.', email: 'Email', aiErrorTitle: 'Could not connect Hermex AI', aiErrorBody: 'Hermes could not reach the AI provider. Your chart is safe; try again in a moment or return to the chart.', retry: 'Retry', ethics: 'For reflection and self-development, not deterministic prediction.'
    }
  } satisfies Record<Lang, Record<string, string>>;

  const cityOptions = [
    { label: 'Jakarta, Indonesia', latitude: -6.2088, longitude: 106.8456, timezone: 'Asia/Jakarta' },
    { label: 'Bandung, Indonesia', latitude: -6.9175, longitude: 107.6191, timezone: 'Asia/Jakarta' },
    { label: 'Surabaya, Indonesia', latitude: -7.2575, longitude: 112.7521, timezone: 'Asia/Jakarta' },
    { label: 'Yogyakarta, Indonesia', latitude: -7.7956, longitude: 110.3695, timezone: 'Asia/Jakarta' },
    { label: 'Semarang, Indonesia', latitude: -6.9667, longitude: 110.4167, timezone: 'Asia/Jakarta' },
    { label: 'Malang, Indonesia', latitude: -7.9666, longitude: 112.6326, timezone: 'Asia/Jakarta' },
    { label: 'Denpasar, Indonesia', latitude: -8.65, longitude: 115.2167, timezone: 'Asia/Makassar' },
    { label: 'Makassar, Indonesia', latitude: -5.1477, longitude: 119.4327, timezone: 'Asia/Makassar' },
    { label: 'Medan, Indonesia', latitude: 3.5952, longitude: 98.6722, timezone: 'Asia/Jakarta' },
    { label: 'Balikpapan, Indonesia', latitude: -1.2379, longitude: 116.8529, timezone: 'Asia/Makassar' },
    { label: 'Jayapura, Indonesia', latitude: -2.5916, longitude: 140.669, timezone: 'Asia/Jayapura' },
    { label: 'Singapore', latitude: 1.3521, longitude: 103.8198, timezone: 'Asia/Singapore' },
    { label: 'Kuala Lumpur, Malaysia', latitude: 3.139, longitude: 101.6869, timezone: 'Asia/Kuala_Lumpur' },
    { label: 'Tokyo, Japan', latitude: 35.6762, longitude: 139.6503, timezone: 'Asia/Tokyo' },
    { label: 'London, United Kingdom', latitude: 51.5072, longitude: -0.1276, timezone: 'Europe/London' },
    { label: 'New York, United States', latitude: 40.7128, longitude: -74.006, timezone: 'America/New_York' }
  ];

  let lang: Lang = 'id';
  let screen: Screen = 'home';
  let activeFeature = 0;
  let quoteIndex = 0;
  let rating = 0;
  let feedbackText = '';
  let display_name = 'Wauputra';
  let birth_date = '1997-06-19';
  let birth_time = '17:45';
  let birth_place = 'Jakarta, Indonesia';
  let email = '';
  let cityQuery = 'Jakarta, Indonesia';
  let selectedCity: (typeof cityOptions)[number] | null = cityOptions[0];
  let cityPickerOpen = false;
  let loading = false;
  let error = '';
  let profile: any = null;
  let validation: any = null;
  let interpretation: any = null;

  $: copy = t[lang];

  $: quotes = lang === 'id'
    ? [
        'Kenali dirimu; langit hanya membantu memberi cermin. - Socrates',
        'Hidup yang diperiksa membuat pilihan lebih sadar. - Socrates',
        'Karakter membentuk arah hidup. - Heraclitus',
        'Waktu adalah bayangan bergerak dari keabadian. - Plato',
        'Kebiasaan kecil membentuk diri. - Aristotle',
        'Kuasa pertama adalah menata pikiran sendiri. - Marcus Aurelius',
        'Imajinasi bisa lebih ramai daripada kenyataan. - Seneca',
        'Simbol membantu jiwa mengenal lapis terdalamnya. - Plotinus',
        'Manusia membawa langit kecil di dalam dirinya. - Paracelsus',
        'Bintang memberi kecenderungan, bukan memaksa takdir. - Ptolemaic tradition',
        'Yang di atas mencerminkan yang di bawah. - Hermetic tradition',
        'Kesadaran membuat pola lama bisa dibaca ulang. - Carl Jung',
        'Chart adalah peta refleksi, bukan penjara takdir. - Hermex'
      ]
    : [
        'Know yourself; the sky only helps mirror you. - Socrates',
        'An examined life makes choice more conscious. - Socrates',
        'Character shapes the direction of life. - Heraclitus',
        'Time is the moving image of eternity. - Plato',
        'Small habits quietly shape the self. - Aristotle',
        'The first power is governing your own mind. - Marcus Aurelius',
        'Imagination can be louder than reality. - Seneca',
        'Symbols help the soul know its deeper layers. - Plotinus',
        'A person carries a small sky within. - Paracelsus',
        'The stars incline; they do not compel. - Ptolemaic tradition',
        'As above, so below. - Hermetic tradition',
        'Awareness lets old patterns be read again. - Carl Jung',
        'A chart is a mirror, not a prison. - Hermex'
      ];
  let activeEducation = 0;

  $: educationCards = lang === 'id'
    ? [
        ['Planet', 'Planet menggambarkan fungsi batin. Matahari identitas, Bulan emosi, Merkurius cara berpikir, Venus rasa suka, Mars dorongan aksi.'],
        ['Zodiac sign', 'Zodiac adalah gaya ekspresi. Planet yang sama terasa berbeda saat berada di Gemini, Cancer, Libra, atau Capricorn.'],
        ['House', 'House menunjukkan area hidup. Planet di house 7 sering terbaca lewat relasi, house 10 lewat karier, house 1 lewat diri.'],
        ['Aspect', 'Aspect adalah hubungan antar planet. Trine terasa mengalir, square menantang, opposition mengajak integrasi.']
      ]
    : [
        ['Planets', 'Planets describe inner functions. Sun identity, Moon emotion, Mercury thought, Venus preference, Mars action.'],
        ['Zodiac signs', 'Zodiac signs are expression styles. The same planet feels different in Gemini, Cancer, Libra, or Capricorn.'],
        ['Houses', 'Houses show life areas. House 7 points to relationships, house 10 to career, house 1 to selfhood.'],
        ['Aspects', 'Aspects are planet relationships. Trines flow, squares challenge, oppositions ask integration.']
      ];

  $: features = lang === 'id'
    ? [
        ['Natal Chart', 'Lihat zodiac sign, planet, house, dan aspect.'],
        ['Hermes AI', 'Analisis ringkas berbasis chart, bukan teks random.'],
        ['Minat & Bakat', 'Pisahkan kekuatan, kelemahan, dan arah eksplorasi.'],
        ['Roadmap 5 Tahun', 'Peta umum untuk dicoba bertahap.'],
        ['Jodoh Similarity', 'Coming soon: cari kecocokan relasi dari dua chart astrology.']
      ]
    : [
        ['Natal Chart', 'Inspect zodiac signs, planets, houses, and aspects.'],
        ['Hermes AI', 'Concise chart-based interpretation, not random text.'],
        ['Interests & Talents', 'Separate strengths, weaknesses, and explorations.'],
        ['5-Year Roadmap', 'A general path to test gradually.'],
        ['Partner Similarity', 'Coming soon: compare relationship compatibility from two astrology charts.']
      ];
  $: filteredCities = cityOptions.filter((city) => city.label.toLowerCase().includes(cityQuery.toLowerCase())).slice(0, 8);
  $: planets = profile ? Object.entries(profile.chart?.planets ?? {}) as [string, any][] : [];
  $: aspects = profile?.chart?.aspects ?? [];
  $: chartLines = aspects.slice(0, 8).map((aspect: any) => ({
    left: planetPoint(aspect.left),
    right: planetPoint(aspect.right),
    type: aspect.type
  })).filter((line: any) => line.left && line.right);
  $: houses = profile?.chart?.houses ?? {};
  $: oracle = interpretation ? normalizeInterpretation(interpretation) : null;
  $: summaryHighlight = oracle ? highlightSummary(oracle.summary) : { lead: '', rest: '' };

  onMount(() => {
    if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => undefined);
    const timer = window.setInterval(() => (quoteIndex = (quoteIndex + 1) % quotes.length), 2600);
    return () => window.clearInterval(timer);
  });

  function toggleLang() { lang = lang === 'id' ? 'en' : 'id'; }
  function chooseCity(city: (typeof cityOptions)[number]) { selectedCity = city; birth_place = city.label; cityQuery = city.label; cityPickerOpen = false; }
  function onCityInput(value: string) { cityQuery = value; birth_place = value; cityPickerOpen = true; selectedCity = cityOptions.find((city) => city.label.toLowerCase() === value.toLowerCase()) ?? null; }
  function planetPoint(name: string) {
    const planet = profile?.chart?.planets?.[name];
    if (!planet) return null;
    const angle = ((planet.longitude - 90) * Math.PI) / 180;
    return { x: 150 + Math.cos(angle) * 105, y: 150 + Math.sin(angle) * 105, name, sign: planet.zodiac_sign };
  }

  function highlightSummary(summary: string) {
    const parts = summary.split(/(?<=[.!?])\s+/).filter(Boolean);
    return { lead: parts.slice(0, 2).join(' '), rest: parts.slice(2).join(' ') };
  }

  function displayValue(value: unknown): string {
    if (typeof value === 'string') return value;
    if (typeof value === 'number' || typeof value === 'boolean') return String(value);
    if (value && typeof value === 'object') {
      const item = value as Record<string, unknown>;
      for (const key of ['title', 'name', 'role', 'career', 'path', 'label', 'focus', 'description', 'summary', 'theme']) {
        if (typeof item[key] === 'string' && String(item[key]).trim()) return String(item[key]);
      }
      const values = Object.values(item).filter((entry) => ['string', 'number', 'boolean'].includes(typeof entry)).map(String);
      if (values.length) return values.slice(0, 3).join(' - ');
    }
    return JSON.stringify(value);
  }
  function asList(value: unknown): string[] { if (Array.isArray(value)) return value.map(displayValue).filter(Boolean); if (value) return [displayValue(value)]; return []; }
  function normalizeInterpretation(result: any) {
    const data = result?.interpretation ?? {};
    const fallback = lang === 'id' ? 'Hermes belum mengirim ringkasan rapi. Coba tanya ulang.' : 'Hermes did not return a clean summary yet. Try again.';
    return {
      summary: displayValue(data.summary || fallback),
      strengths: asList(data.strengths), weaknesses: asList(data.weaknesses), love: asList(data.love),
      interests: asList(data.interests), talents: asList(data.talents), careers: asList(data.careers),
      fiveYear: Array.isArray(data.five_year_roadmap) ? data.five_year_roadmap : asList(data.five_year_roadmap),
      confidence: data.confidence ?? result?.confidence
    };
  }
  function roadmapTitle(item: any, index: number) { return item?.year || item?.horizon || `Year ${index + 1}`; }
  function roadmapText(item: any) { return item?.description || item?.focus || item?.theme || displayValue(item); }
  function explainMore() { screen = 'register'; }
  function submitFeedback() { feedbackText = ''; rating = 0; }

  async function runAnalysis() {
    loading = true; error = ''; interpretation = null; validation = null;
    try {
      profile = await analyzeBirth({ display_name, birth_date, birth_place, ...(birth_time ? { birth_time } : {}), ...(selectedCity ? { latitude: selectedCity.latitude, longitude: selectedCity.longitude, timezone: selectedCity.timezone } : {}) });
      screen = 'profile';
    } catch (err) { error = err instanceof Error ? err.message : 'Unknown error'; }
    finally { loading = false; }
  }
  async function runValidation() {
    if (!profile) return;
    validation = await validateBirth(profile.profile_id, { birth_time_certainty: birth_time ? 'known' : 'unknown', current_pull: 'building' });
    profile.traits = validation.traits; profile.needs_validation = false;
  }
  async function runInterpretation() {
    if (!profile) return;
    loading = true; screen = 'hermes-loading'; error = '';
    try {
      interpretation = await interpretProfile(profile.profile_id, lang);
      if (String(interpretation?.provider ?? '').includes('error')) {
        error = copy.aiErrorBody;
        screen = 'ai-error';
      } else {
        screen = 'hermes';
      }
    }
    catch (err) { error = err instanceof Error ? err.message : 'Unknown error'; screen = 'ai-error'; }
    finally { loading = false; }
  }
</script>

<svelte:head><title>Hermex Quest</title><meta name="theme-color" content="#f4c15d" /><link rel="manifest" href="/manifest.webmanifest" /><link rel="icon" href="/icons/hermex-star.svg" /></svelte:head>

<main class="app-shell">
  <section class="phone-frame">
    <header class="topbar">
      <div class="brand"><svg viewBox="0 0 64 64"><path d="M32 5l7 17 18 2-14 12 4 18-15-10-15 10 4-18L7 24l18-2 7-17z"/><circle cx="25" cy="30" r="2.5"/><circle cx="39" cy="30" r="2.5"/><path d="M25 39c4 3 10 3 14 0"/></svg><div><p>{copy.badge}</p><strong>Hermex Quest</strong></div></div>
      {#if screen !== 'home'}<button class="ghost" on:click={() => (screen = 'home')}>{copy.edit}</button>{/if}<button class="lang" on:click={toggleLang}>{lang.toUpperCase()}</button>
    </header>

    {#if screen === 'home'}
      <section class="hero-card"><div><span>{copy.features}</span><h1>{copy.title}</h1><p>{copy.subtitle}</p></div><svg viewBox="0 0 220 220"><circle cx="110" cy="110" r="82"/><circle cx="110" cy="110" r="50"/><path d="M138 47a31 31 0 1 0 0 62 38 38 0 1 1 0-62z"/><circle cx="49" cy="83" r="13"/><circle cx="171" cy="148" r="16"/><path d="M101 128l8 18 18 8-18 8-8 18-8-18-18-8 18-8 8-18z"/></svg></section>
      <section class="feature-row">{#each features as feature, index}<button class:active={activeFeature === index} on:click={() => (activeFeature = index)}>{@render Icon(index)}<strong>{feature[0]}</strong><small>{feature[1]}</small></button>{/each}</section>
      <button class="learn-strip" on:click={() => (screen = 'learn')}>☿ {copy.learn}</button>
      <section class="home-grid single"><article class="card form-card"><div class="section-title"><span>01</span><h2>Profil Pemain</h2></div>
        <div class="split"><label>{copy.date}<input type="date" bind:value={birth_date} /></label><label>{copy.time} <small>{copy.optional}</small><input type="time" bind:value={birth_time} /></label></div>
        <label class="city-picker">{copy.place}<input value={cityQuery} placeholder={copy.citySearch} autocomplete="off" role="combobox" aria-controls="city-options" aria-expanded={cityPickerOpen ? 'true' : 'false'} on:focus={() => (cityPickerOpen = true)} on:input={(event) => onCityInput(event.currentTarget.value)} />{#if cityPickerOpen && filteredCities.length}<div class="city-menu" id="city-options">{#each filteredCities as city}<button type="button" on:mousedown|preventDefault={() => chooseCity(city)}><strong>{city.label}</strong><small>{city.latitude.toFixed(4)}, {city.longitude.toFixed(4)} · {city.timezone}</small></button>{/each}</div>{/if}</label>
        {#if selectedCity}<p class="location-note">{copy.selectedCity}: {selectedCity.label}<br />{copy.locationHint}</p>{/if}
        <label>{copy.email} <small>{copy.optional}</small><input type="email" bind:value={email} placeholder="you@example.com" /></label>
        <label>{copy.name} <small>{copy.optional}</small><input bind:value={display_name} /></label>
        <button class="primary-action" on:click={runAnalysis} disabled={loading}>✦ {loading ? copy.analyzing : copy.analyze}</button>{#if error}<p class="error">{error}</p>{/if}
      </article></section>
    {/if}

    {#if screen === 'profile' && profile}
      <section class="profile-grid"><article class="card character-card"><div class="section-title"><span>02</span><h2>{copy.profile}</h2></div><div class="natal-wheel"><svg viewBox="0 0 300 300"><circle cx="150" cy="150" r="132"/><circle cx="150" cy="150" r="96"/><circle cx="150" cy="150" r="44"/>{#each Array(12) as _, index}<line x1="150" y1="18" x2="150" y2="54" transform={`rotate(${index * 30} 150 150)`}/>{/each}{#each chartLines as line}<line class="aspect-line" x1={line.left.x} y1={line.left.y} x2={line.right.x} y2={line.right.y}/>{/each}{#each planets.slice(0, 7) as [name, planet]}{@const point = planetPoint(name)}{#if point}<g><circle cx={point.x} cy={point.y} r="10"/><text x={point.x} y={point.y - 15}>{name.slice(0, 2)}</text></g>{/if}{/each}</svg></div><h3>{profile.display_name || 'Seeker'}</h3><p class="dominant">{profile.traits.dominant_element}</p><div class="meter"><span style={`width:${Math.round(profile.traits.confidence.score * 100)}%`}></span></div><p>{profile.traits.confidence.label} ({profile.traits.confidence.score})</p><div class="chips">{#each profile.traits.interests as item}<span>{item}</span>{/each}</div>{#if profile.needs_validation}<button class="soft-action" on:click={runValidation}>{copy.validate}</button>{/if}</article>
      <article class="card chart-card"><div class="section-title"><span>03</span><h2>{copy.chart}</h2></div><div class="planet-grid">{#each planets.slice(0, 7) as [name, planet]}<div><strong>{name}</strong><span>{planet.zodiac_sign} {planet.degree_in_sign}°</span><small>House {houses.planet_houses?.[name] ?? '-'}</small></div>{/each}</div><div class="aspect-list"><h3>Aspects</h3>{#each aspects.slice(0, 6) as aspect}<p><strong>{aspect.left}</strong> {aspect.type} <strong>{aspect.right}</strong> <small>orb {aspect.orb}</small></p>{/each}</div><button class="soft-action oracle-button" on:click={runInterpretation}>{copy.askHermes}</button></article></section>
    {/if}

    {#if screen === 'hermes-loading'}<section class="loading-screen"><div class="loader"><span></span><span></span><span></span><strong>☿</strong></div><h2>{copy.processingTitle}</h2><p class="quote">{quotes[quoteIndex]}</p><small>{copy.processingBody}</small></section>{/if}

    {#if screen === 'hermes' && oracle}<section class="card hermes-card"><div class="section-title"><span>04</span><h2>{copy.hermes}</h2></div><div class="summary-card">{@render Icon(1)}<p><mark>{summaryHighlight.lead}</mark>{#if summaryHighlight.rest}<br /><span>{summaryHighlight.rest}</span>{/if}</p></div><div class="insight-grid">{@render Insight(copy.love, oracle.love, '♡')}{@render Insight(copy.strengths, oracle.strengths, '✦')}{@render Insight(copy.weaknesses, oracle.weaknesses, '△')}{@render Insight(copy.interests, oracle.interests, '☉')}{@render Insight(copy.talents, oracle.talents, '☾')}{@render Insight(copy.career, oracle.careers, '☿')}</div><div class="timeline"><h3>{copy.fiveYear}</h3>{#each oracle.fiveYear.slice(0, 5) as item, index}<div><span>{roadmapTitle(item, index)}</span><p>{roadmapText(item)}</p></div>{/each}<button class="text-link" on:click={explainMore}>{copy.register}</button></div><div class="feedback"><h3>{copy.feedback}</h3><div class="stars">{#each [1,2,3,4,5] as star}<button class:active={rating >= star} on:click={() => (rating = star)}>★</button>{/each}</div><textarea bind:value={feedbackText} placeholder={copy.suggestion}></textarea><button class="soft-action" on:click={submitFeedback}>{copy.sendFeedback}</button></div><div class="route-actions"><button class="soft-action" on:click={() => (screen = 'profile')}>{copy.back}</button><button class="soft-action oracle-button" on:click={runInterpretation}>{copy.askAgain}</button></div></section>{/if}



    {#if screen === 'ai-error'}<section class="card ai-error-page"><div class="section-title"><span>!</span><h2>{copy.aiErrorTitle}</h2></div><div class="error-visual">{@render Icon(1, true)}<p>{copy.aiErrorBody}</p></div><div class="route-actions"><button class="soft-action" on:click={() => (screen = 'profile')}>{copy.back}</button><button class="soft-action oracle-button" on:click={runInterpretation}>{copy.retry}</button></div></section>{/if}

    {#if screen === 'learn'}<section class="card learn-page"><div class="section-title"><span>☿</span><h2>{copy.learn}</h2></div><div class="education-grid">{#each educationCards as card, index}<button class:active={activeEducation === index} on:click={() => (activeEducation = index)}>{@render Icon(index)}<h3>{card[0]}</h3><p>{card[1]}</p></button>{/each}</div><article class="education-detail">{@render Icon(activeEducation, true)}<div><h3>{educationCards[activeEducation][0]}</h3><p>{educationCards[activeEducation][1]}</p><p>{lang === 'id' ? 'Bayangkan ini seperti lapisan peta: planet adalah aktor, zodiac adalah gaya bicara, house adalah panggung, dan aspect adalah hubungan antar aktor.' : 'Think of this as map layers: planets are actors, zodiac signs are speaking styles, houses are stages, and aspects are relationships between actors.'}</p></div></article><button class="soft-action" on:click={() => (screen = 'home')}>{copy.back}</button></section>{/if}
    {#if screen === 'register'}<section class="card register-page"><div class="section-title"><span>✦</span><h2>{copy.registerTitle}</h2></div><p>{copy.registerBody}</p><div class="split"><input placeholder="Email" /><input placeholder="Nama" /></div><button class="primary-action" on:click={() => (screen = 'hermes')}>{copy.back}</button></section>{/if}
    <footer>{copy.ethics}</footer>
  </section>
</main>

{#snippet Icon(kind: number, big = false)}<svg class:big viewBox="0 0 64 64"><circle cx="32" cy="32" r="25"/><path d={kind === 0 ? 'M32 10l5 16 17 1-14 10 5 17-13-10-13 10 5-17-14-10 17-1 5-16z' : kind === 1 ? 'M43 14a20 20 0 1 0 0 40 26 26 0 1 1 0-40z' : kind === 2 ? 'M17 44c8-22 22-30 38-22-5 20-18 29-38 22z' : 'M32 10l7 15 15 7-15 7-7 15-7-15-15-7 15-7 7-15z'} /></svg>{/snippet}
{#snippet Insight(title: string, items: string[], icon: string)}<article class="insight"><div><span>{icon}</span><h3>{title}</h3></div>{#if items.length}<ul>{#each items.slice(0, 4) as item}<li>{item}</li>{/each}</ul>{:else}<p>-</p>{/if}</article>{/snippet}

<style>
  :global(*){box-sizing:border-box}:global(body){margin:0;color:#45304f;background:radial-gradient(circle at 12% 8%,rgba(244,193,93,.5),transparent 22rem),radial-gradient(circle at 88% 16%,rgba(128,213,187,.42),transparent 24rem),linear-gradient(145deg,#fff8df,#f5e4ee 52%,#dff5ed);font-family:Avenir Next,Nunito,Trebuchet MS,sans-serif}.app-shell{min-height:100vh;padding:22px}.phone-frame{width:min(1080px,100%);margin:0 auto;border:5px solid rgba(69,48,79,.12);border-radius:38px;background:rgba(255,253,243,.88);box-shadow:0 30px 90px rgba(82,47,79,.16);padding:24px;position:relative;overflow:hidden}.phone-frame:before{content:'';position:absolute;inset:0;background-image:radial-gradient(circle,rgba(69,48,79,.07) 1px,transparent 1.5px);background-size:26px 26px;pointer-events:none}.topbar,.hero-card,.feature-row,.home-grid,.profile-grid,.loading-screen,.hermes-card,footer{position:relative;z-index:1}.topbar{display:flex;align-items:center;gap:12px;margin-bottom:18px}.brand{display:flex;align-items:center;gap:12px}.brand svg{width:54px;height:54px;border-radius:18px;background:#fff2aa;padding:8px;fill:#f4c15d;stroke:#45304f;stroke-width:3}.brand circle{fill:#45304f;stroke:none}.brand path:last-child{fill:none;stroke-linecap:round}.brand p{margin:0;color:#8f6884;font-size:.75rem;font-weight:850;letter-spacing:.1em;text-transform:uppercase}.brand strong{font-size:1.18rem}.lang,.ghost{margin-left:auto;border:0;border-radius:999px;padding:10px 14px;background:#45304f;color:#fff7cf;font-weight:900;cursor:pointer}.ghost{background:rgba(69,48,79,.1);color:#45304f}.ghost+.lang{margin-left:6px}.hero-card{display:grid;grid-template-columns:1fr 210px;gap:18px;align-items:center;padding:28px;border-radius:34px;background:linear-gradient(135deg,#fff0a8,#f4cbd5 56%,#c9f1e3);box-shadow:0 18px 48px rgba(126,79,109,.14)}.hero-card span{display:inline-flex;border-radius:999px;padding:8px 12px;background:rgba(255,255,255,.7);color:#805d78;font-size:.78rem;font-weight:900;text-transform:uppercase;letter-spacing:.08em}h1{margin:14px 0 12px;max-width:680px;font-size:clamp(2.25rem,7vw,5.2rem);line-height:.88;letter-spacing:-.07em;font-weight:950}.hero-card p{margin:0;color:rgba(69,48,79,.74);font-size:1.02rem;line-height:1.55;font-weight:730}.hero-card svg{width:100%}.hero-card circle:nth-child(-n+2){fill:none;stroke:rgba(69,48,79,.2);stroke-width:6;stroke-dasharray:9 11;animation:spin 24s linear infinite;transform-origin:center}.hero-card path:nth-child(3){fill:#fff8c7;stroke:#45304f;stroke-width:5}.hero-card circle:nth-child(n+4){fill:#80d5bb;stroke:#45304f;stroke-width:5}.hero-card path:last-child{fill:#f09d73;stroke:#45304f;stroke-width:5}.feature-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin:18px 0}.feature-row button{display:grid;grid-template-columns:42px 1fr;gap:8px;align-items:center;text-align:left;border:2px solid transparent;border-radius:22px;background:rgba(255,255,255,.72);padding:14px;color:#45304f;cursor:pointer}.feature-row button.active{border-color:#80d5bb;background:#f2fffa}.feature-row small{grid-column:2;color:#7f7184;font-weight:700}.home-grid,.profile-grid{display:grid;grid-template-columns:1.05fr .95fr;gap:18px}.home-grid.single{grid-template-columns:1fr}.learn-strip{position:relative;z-index:1;width:100%;border:0;border-radius:22px;margin:0 0 18px;padding:15px 18px;background:#fffdf7;color:#45304f;font-weight:950;box-shadow:0 12px 32px rgba(82,47,79,.08);cursor:pointer}.card{border:2px solid rgba(69,48,79,.11);border-radius:30px;background:rgba(255,255,255,.8);box-shadow:0 18px 45px rgba(82,47,79,.1);padding:22px}.section-title{display:flex;align-items:center;gap:10px;margin-bottom:18px}.section-title span{display:grid;place-items:center;width:34px;height:34px;border-radius:12px;background:#45304f;color:#fff7cf;font-weight:950}h2,h3{margin:0}.split{display:grid;grid-template-columns:1fr 1fr;gap:12px}label{display:grid;gap:7px;margin-bottom:13px;color:#6d4b79;font-weight:850}label small{color:#ad7aa0;font-size:.78rem}input{width:100%;border:2px solid rgba(69,48,79,.14);border-radius:18px;padding:14px 15px;background:#fffaf1;color:#45304f;font:800 1rem Avenir Next,sans-serif;outline:none}.city-picker{position:relative}.city-menu{position:absolute;z-index:6;left:0;right:0;top:calc(100% - 4px);display:grid;gap:6px;max-height:265px;overflow:auto;padding:8px;border:2px solid rgba(69,48,79,.12);border-radius:18px;background:#fffdf6;box-shadow:0 20px 40px rgba(69,48,79,.18)}.city-menu button{display:grid;gap:2px;text-align:left;border:0;border-radius:13px;padding:10px 12px;background:transparent;color:#45304f}.city-menu button:hover{background:#fff0d6}.city-menu small,.location-note{color:rgba(69,48,79,.62);font-size:.78rem;font-weight:750}.primary-action,.soft-action{display:inline-flex;align-items:center;justify-content:center;gap:10px;width:100%;border:0;border-radius:22px;padding:15px 18px;color:#fff7cf;background:#45304f;box-shadow:0 9px 0 #2d1f35,0 20px 28px rgba(69,48,79,.18);font-weight:900;font-size:1rem;cursor:pointer}.soft-action{margin-top:16px;background:#f09d73;color:#45304f;box-shadow:0 8px 0 #c96d4c}.oracle-button{background:#80d5bb;box-shadow:0 8px 0 #56ad91}.active-feature{display:grid;place-items:center;text-align:center;align-content:center;background:linear-gradient(160deg,#f2f6ff,#fffdf7)}svg.big{width:150px;height:150px}.feature-row svg,.active-feature svg{fill:#fff2aa;stroke:#45304f;stroke-width:4}.feature-row svg path,.active-feature svg path{fill:#f09d73}.character-card{text-align:center}.natal-wheel{width:min(360px,100%);margin:0 auto 14px}.natal-wheel svg{width:100%;height:auto}.natal-wheel circle{fill:none;stroke:#45304f;stroke-width:2}.natal-wheel line{stroke:rgba(69,48,79,.28);stroke-width:1.5}.natal-wheel .aspect-line{stroke:#80d5bb;stroke-width:2;opacity:.9}.natal-wheel g circle{fill:#f4c15d;stroke:#45304f;stroke-width:2}.natal-wheel text{font-size:10px;text-anchor:middle;fill:#45304f;font-weight:900}.avatar{display:grid;place-items:center;width:118px;height:118px;margin:0 auto 12px;border-radius:34px;background:#fff0a8;color:#45304f;font-size:4rem}.dominant{display:inline-flex;margin:0 0 10px;padding:7px 12px;border-radius:999px;background:#f2e8f7;color:#6d4b79;font-weight:900;text-transform:uppercase}.meter{height:14px;border-radius:999px;background:rgba(69,48,79,.1);overflow:hidden}.meter span{display:block;height:100%;background:linear-gradient(90deg,#f09d73,#f4c15d,#80d5bb)}.chips{display:flex;flex-wrap:wrap;justify-content:center;gap:8px;margin-top:13px}.chips span{border:2px solid rgba(69,48,79,.1);border-radius:999px;background:#fff0a8;padding:8px 11px;color:#5c3a65;font-size:.83rem;font-weight:850}.planet-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.planet-grid div{border-radius:18px;background:#f7f3ea;padding:12px}.aspect-list{margin-top:14px;border-radius:22px;background:#f6f3ed;padding:14px}.aspect-list p{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin:8px 0;color:#5e5064;font-weight:760}.aspect-list small{color:#8b788f}.planet-grid strong{text-transform:capitalize;display:block}.planet-grid span,.planet-grid small{display:block;color:#75657a;font-weight:750}details{margin-top:12px;border-radius:18px;background:#f6f3ed;padding:12px}summary{cursor:pointer;font-weight:900}pre{max-height:220px;overflow:auto;white-space:pre-wrap;font-size:.8rem}.loading-screen{min-height:560px;display:grid;place-items:center;align-content:center;text-align:center;border-radius:32px;background:linear-gradient(135deg,rgba(255,240,168,.65),rgba(220,255,241,.78))}.loader{position:relative;width:180px;height:180px;display:grid;place-items:center}.loader:before{content:'';position:absolute;inset:18px;border:3px dashed rgba(69,48,79,.28);border-radius:50%;animation:spin 7s linear infinite}.loader span{position:absolute;width:28px;height:28px;border-radius:50%;background:#80d5bb;animation:float 1.7s ease-in-out infinite}.loader span:nth-child(1){left:18px;top:70px}.loader span:nth-child(2){right:22px;top:42px;background:#f4c15d}.loader span:nth-child(3){bottom:24px;right:54px;background:#f09d73}.loader strong{font-size:4rem;color:#45304f}.loading-screen .quote{min-height:34px;font-size:1.05rem;font-weight:900;color:#6d4b79;animation:fadeQuote 2.6s ease-in-out infinite}.loading-screen small{color:#7a6d7e;font-weight:760}.hermes-card{min-height:620px}.summary-card{display:grid;grid-template-columns:76px 1fr;gap:16px;align-items:start;border-radius:26px;background:linear-gradient(135deg,#fff0a8,#dcfff1);padding:18px}.summary-card svg{width:70px;fill:#fff2aa;stroke:#45304f;stroke-width:4}.summary-card svg path{fill:#f09d73}.summary-card p{margin:0;line-height:1.5;font-weight:780;color:rgba(69,48,79,.8)}.summary-card mark{background:linear-gradient(120deg,rgba(244,193,93,.55),rgba(128,213,187,.45));border-radius:10px;padding:2px 5px;color:#45304f}.summary-card span{color:#67566d}.insight-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:14px}.insight{border-radius:22px;background:#fffdf7;border:1px solid rgba(69,48,79,.1);padding:14px}.insight div{display:flex;align-items:center;gap:8px}.insight div span{display:grid;place-items:center;width:34px;height:34px;border-radius:12px;background:#f2e8f7}.insight ul{margin:10px 0 0;padding-left:18px;color:#6a5a70;font-weight:720}.timeline{margin-top:14px;border-radius:24px;background:#f6f3ed;padding:16px}.timeline>div{display:grid;grid-template-columns:90px 1fr;gap:12px;border-top:1px solid rgba(69,48,79,.1);padding:10px 0}.timeline span{font-weight:950;color:#80623e}.timeline p{margin:0;color:#67566d;font-weight:720;line-height:1.45}.text-link{margin-top:12px;border:0;border-radius:999px;background:#45304f;color:#fff8df;padding:10px 14px;font-weight:900;cursor:pointer}.feedback{margin-top:14px;border-radius:24px;background:#fffdf7;border:1px solid rgba(69,48,79,.1);padding:16px}.stars{display:flex;gap:6px;margin:10px 0}.stars button{border:0;background:transparent;color:#c8b8cb;font-size:2rem;cursor:pointer}.stars button.active{color:#f4c15d}.feedback textarea{width:100%;min-height:78px;border:1px solid rgba(69,48,79,.14);border-radius:16px;padding:12px;font:inherit}.route-actions{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:18px}.learn-page,.register-page{position:relative;z-index:1}.education-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}.education-grid button{border:1px solid rgba(69,48,79,.1);border-radius:24px;background:#fffdf7;padding:16px;text-align:left;color:#45304f;cursor:pointer;transition:transform .18s ease,border-color .18s ease}.education-grid button:hover,.education-grid button.active{transform:translateY(-2px);border-color:#80d5bb;background:#f2fffa}.education-grid svg,.education-detail svg{width:54px;height:54px;fill:#fff2aa;stroke:#45304f;stroke-width:4}.education-grid svg path,.education-detail svg path{fill:#f09d73}.education-grid p,.register-page p,.education-detail p{color:#6d6072;font-weight:720;line-height:1.5}.education-detail{display:grid;grid-template-columns:110px 1fr;gap:18px;align-items:center;margin-top:14px;border-radius:28px;background:linear-gradient(135deg,#fff0a8,#dcfff1);padding:20px}.education-detail svg{width:96px;height:96px}.ai-error-page{position:relative;z-index:1}.error-visual{display:grid;grid-template-columns:120px 1fr;gap:18px;align-items:center;border-radius:28px;background:linear-gradient(135deg,#fff0a8,#f8d8d8);padding:22px}.error-visual svg{width:100px;height:100px;fill:#fff2aa;stroke:#45304f;stroke-width:4}.error-visual svg path{fill:#f09d73}.error-visual p{font-weight:850;color:#6d4b79;line-height:1.5}footer{position:relative;z-index:1;padding:18px 0 0;text-align:center;color:rgba(69,48,79,.58);font-weight:780}.error{color:#b3264c;font-weight:850}@keyframes spin{to{transform:rotate(360deg)}}@keyframes float{50%{transform:translateY(-10px)}}@keyframes fadeQuote{0%,100%{opacity:.35;transform:translateY(4px)}35%,75%{opacity:1;transform:translateY(0)}}@media(max-width:860px){.app-shell{padding:8px}.phone-frame{padding:14px;border-radius:30px}.hero-card,.home-grid,.profile-grid,.insight-grid,.route-actions,.education-grid{grid-template-columns:1fr}.feature-row{grid-template-columns:1fr 1fr}.planet-grid{grid-template-columns:1fr 1fr}.hero-card svg{max-width:180px;order:-1;margin:auto}}@media(max-width:560px){.feature-row,.split,.planet-grid,.timeline>div,.education-detail,.error-visual{grid-template-columns:1fr}.summary-card{grid-template-columns:1fr}.topbar{flex-wrap:wrap}}
</style>
