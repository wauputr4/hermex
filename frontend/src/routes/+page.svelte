<script lang="ts">
  import cityTimezones from 'city-timezones';
  import { ApiError } from '$lib/api/hermex';
  import { onMount } from 'svelte';
  import { API_BASE, analyzeBirth, askHermexDetail, deleteUserHistory, getAuthMe, getProfile, getPublicProfile, getSkyCalendar, getSkyNews, getUserHistory, interpretProfile, listPublicProfiles, publishPublicProfile, submitFeedback as submitFeedbackApi, syncUserHistory, validateBirth } from '$lib/api/hermex';

  const GA_MEASUREMENT_ID = import.meta.env.VITE_GA_MEASUREMENT_ID?.trim() ?? '';

  function installGoogleAnalytics() {
    if (!GA_MEASUREMENT_ID || typeof window === 'undefined' || typeof document === 'undefined') return;
    if (document.querySelector(`script[data-hermex-ga="${GA_MEASUREMENT_ID}"]`)) return;

    const script = document.createElement('script');
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(GA_MEASUREMENT_ID)}`;
    script.dataset.hermexGa = GA_MEASUREMENT_ID;
    document.head.appendChild(script);

    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || function gtag(...args: unknown[]){ window.dataLayer.push(args); };
    window.gtag('js', new Date());
    window.gtag('config', GA_MEASUREMENT_ID, { anonymize_ip: true });
  }

  type Lang = 'id' | 'en';
  type Screen = 'home' | 'account' | 'profile' | 'hermes-loading' | 'hermes' | 'learn' | 'learn-detail' | 'register' | 'terms' | 'history' | 'connect' | 'public-profile' | 'sky-news' | 'sky-article' | 'hermes-chat' | 'ai-error';
  type GuestHistoryItem = { profile_id: string; display_name?: string; birth_place: string; created_at: string; dominant: string; profile: any; interpretation?: any; interpretation_id?: string; updated_at?: string; public_username?: string };
  type GuestGameState = { xp: number; streak: number; badges: string[]; dailyQuestDate?: string };
  type AuthUser = { name?: string; email?: string; picture?: string };

  const t = {
    id: {
      badge: 'Alpha game', title: 'Mulai quest astrologi kecilmu.',
      subtitle: 'Masukkan data lahir, lihat chart kosmik, lalu minta Hermes membaca pola umum untuk refleksi diri.',
      name: 'Nama atau username', optional: 'opsional', date: 'Tanggal lahir', time: 'Jam lahir', place: 'Tempat lahir', citySearch: 'Cari kota lahir',
      analyze: 'Buka Astrologyku', analyzing: 'Membuka chart...', edit: 'Edit data', language: 'Bahasa', selectedCity: 'Kota terpilih',
      locationHint: 'Lat/lon dan zona waktu ikut memengaruhi chart.', features: 'Yang bisa dicoba', home: 'Home', profile: 'Kartu Karakter', profileTab: 'Profile', chart: 'Chart Explorer', install: 'Install Hermex', installHint: 'Biar chart dan history guest tetap mudah dibuka lagi.', installUnavailable: 'Jika opsi install tidak muncul, coba buka Hermex dengan browser lain lalu pilih Add to Home Screen / Install app.', dismiss: 'Tutup', history: 'History', connect: 'Connect', hermexNav: 'Hermex AI', skyNews: 'Berita Langit', offlineTitle: 'Mode offline aktif', offlineBody: 'Kamu tetap bisa membuka draft, history, dan edukasi yang tersimpan. AI aktif lagi saat internet kembali.', onlineTitle: 'Terhubung',
      askHermes: 'Analisis Kosmik Saya', validating: 'Kunci kepastian', validate: 'Jawab validasi cepat', processingTitle: 'Hermes sedang membaca chart',
      processingBody: 'Menggabungkan posisi planet, zodiac, house, aspect, dan bahasa yang kamu pilih.', hermes: 'Analisis Kosmik Saya', summary: 'Ringkasan',
      strengths: 'Kekuatan', weaknesses: 'Kelemahan', love: 'Percintaan', interests: 'Minat', talents: 'Bakat', career: 'Arah Karier', fiveYear: 'Roadmap 5 tahun terakhir',
      back: 'Kembali ke chart', askAgain: 'Tanya ulang Hermes', learn: 'Belajar Astrology', register: 'Daftar untuk penjelasan lengkap', feedback: 'Seberapa cocok hasilnya?', suggestion: 'Saran dan masukan (opsional)', sendFeedback: 'Kirim feedback', share: 'Publikasikan profil astrology', copied: 'Link tersalin', publishProfile: 'Buat halaman publik', publicProfile: 'Profile publik', username: 'Username', usernameHint: 'Username unik untuk shortlink Hermex.', registerTitle: 'Daftar untuk membaca detail lengkap', registerBody: 'Masuk untuk menyimpan progres lintas perangkat. Untuk MVP, Google login masih berupa opsi tampilan.', googleLogin: 'Lanjut dengan Google', email: 'Email', aiErrorTitle: 'Gagal menghubungkan AI Hermex', aiErrorBody: 'Hermes belum bisa terhubung ke provider AI. Chart kamu tetap aman; coba lagi sebentar lagi atau kembali ke chart.', aiLimitMinute: 'Limit AI per menit tercapai. Coba lagi sebentar lagi.', aiLimitDay: 'Limit AI hari ini sudah habis. Coba lagi besok atau gunakan akun dengan limit lebih besar.', retry: 'Coba lagi', historyTitle: 'History Guest', emptyHistory: 'Belum ada history di perangkat ini.', askDetail: 'Tanya detail ke Hermex', askPlaceholder: 'Contoh: kenapa karier saya condong ke edukasi?', dailyQuest: 'Daily Cosmic Quest', dailyQuestBody: 'Claim refleksi harian untuk menyimpan streak guest dan badge lokal.', claimBadge: 'Claim badge hari ini', claimedBadge: 'Quest hari ini selesai', xp: 'XP', badges: 'Badge', accountTitle: 'Profile Saya', accountGuest: 'Belum login. Kamu tetap bisa memakai Hermex sebagai guest.', currentCard: 'Kartu karakter aktif', viewCard: 'Lihat kartu karakter', logout: 'Keluar', termsTitle: 'Syarat Google OAuth', termsIntro: 'Sebelum lanjut Google login, pahami dulu cara Hermex memakai data dan batas MVP open-source ini.', termsAccept: 'Saya setuju dan lanjut', termsBack: 'Baca nanti', ethics: 'Untuk refleksi dan pengembangan diri, bukan ramalan mutlak.'
    },
    en: {
      badge: 'Alpha game', title: 'Start your tiny astrology quest.',
      subtitle: 'Enter birth context, inspect the cosmic chart, then ask Hermes for a general reflective reading.',
      name: 'Name or username', optional: 'optional', date: 'Birth date', time: 'Birth time', place: 'Birth place', citySearch: 'Search birth city',
      analyze: 'Open My Astrology', analyzing: 'Opening chart...', edit: 'Edit data', language: 'Language', selectedCity: 'Selected city',
      locationHint: 'Latitude, longitude, and timezone influence the chart.', features: 'Things to try', home: 'Home', profile: 'Character Card', profileTab: 'Profile', chart: 'Chart Explorer', install: 'Install Hermex', installHint: 'Keep your guest chart and history easy to reopen.', installUnavailable: 'If the install option does not appear, open Hermex in another browser and choose Add to Home Screen / Install app.', dismiss: 'Close', history: 'History', connect: 'Connect', hermexNav: 'Hermex AI', skyNews: 'Sky News', offlineTitle: 'Offline mode is on', offlineBody: 'You can still open saved drafts, local history, and education. AI returns when internet is back.', onlineTitle: 'Connected',
      askHermes: 'My Cosmic Analysis', validating: 'Confidence key', validate: 'Answer quick validation', processingTitle: 'Hermes is reading your chart',
      processingBody: 'Combining planets, zodiac, houses, aspects, and your selected language.', hermes: 'My Cosmic Analysis', summary: 'Summary',
      strengths: 'Strengths', weaknesses: 'Weaknesses', love: 'Love', interests: 'Interests', talents: 'Talents', career: 'Career Paths', fiveYear: 'Last 5-Year Roadmap',
      back: 'Back to chart', askAgain: 'Ask Hermes again', learn: 'Learn Astrology', register: 'Register for full explanation', feedback: 'How accurate did this feel?', suggestion: 'Suggestions and feedback (optional)', sendFeedback: 'Send feedback', share: 'Publish astrology profile', copied: 'Link copied', publishProfile: 'Create public page', publicProfile: 'Public profile', username: 'Username', usernameHint: 'Unique username for your Hermex shortlink.', registerTitle: 'Register to read the full detail', registerBody: 'Sign in to keep progress across devices. For this MVP, Google login is a visual option.', googleLogin: 'Continue with Google', email: 'Email', aiErrorTitle: 'Could not connect Hermex AI', aiErrorBody: 'Hermes could not reach the AI provider. Your chart is safe; try again in a moment or return to the chart.', aiLimitMinute: 'The AI minute limit has been reached. Try again in a moment.', aiLimitDay: "Today's AI limit has been reached. Try again tomorrow or use an account with a higher limit.", retry: 'Retry', historyTitle: 'Guest History', emptyHistory: 'No local history on this device yet.', askDetail: 'Ask Hermex for detail', askPlaceholder: 'Example: why does my career lean toward education?', dailyQuest: 'Daily Cosmic Quest', dailyQuestBody: 'Claim a daily reflection to keep local guest streaks and badges.', claimBadge: 'Claim today badge', claimedBadge: 'Today quest complete', xp: 'XP', badges: 'Badges', accountTitle: 'My Profile', accountGuest: 'Not signed in yet. You can still use Hermex as a guest.', currentCard: 'Active character card', viewCard: 'View character card', logout: 'Logout', termsTitle: 'Google OAuth Terms', termsIntro: 'Before continuing with Google login, review how Hermex uses data and the current open-source MVP boundary.', termsAccept: 'I agree and continue', termsBack: 'Read later', ethics: 'For reflection and self-development, not deterministic prediction.'
    }
  } satisfies Record<Lang, Record<string, string>>;

  type CityOption = { label: string; latitude: number; longitude: number; timezone: string };
  type CityTimezoneMatch = {
    city: string;
    city_ascii?: string;
    country: string;
    iso2?: string;
    province?: string;
    lat: number;
    lng: number;
    timezone: string;
  };
  const popularCityQueries = [
    'Jakarta Indonesia', 'Bandung Indonesia', 'Surabaya Indonesia', 'Yogyakarta Indonesia',
    'Semarang Indonesia', 'Malang Indonesia', 'Denpasar Indonesia', 'Makassar Indonesia',
    'Medan Indonesia', 'Balikpapan Indonesia', 'Jayapura Indonesia', 'Singapore',
    'Kuala Lumpur Malaysia', 'Tokyo Japan', 'London United Kingdom', 'New York United States'
  ];
  const toCityOption = (city: CityTimezoneMatch): CityOption => ({
    label: [city.city, city.province, city.country].filter(Boolean).join(', '),
    latitude: Number.isFinite(Number(city.lat)) ? Number(city.lat) : 0,
    longitude: Number.isFinite(Number(city.lng)) ? Number(city.lng) : 0,
    timezone: city.timezone || 'UTC'
  });
  const uniqueCities = (cities: CityOption[]) => {
    const seen = new Set<string>();
    return cities.filter((city) => {
      const key = `${city.label.toLowerCase()}|${city.latitude}|${city.longitude}|${city.timezone}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  };
  const cityOptions: CityOption[] = uniqueCities(
    popularCityQueries.flatMap((query) => {
      const matches = (cityTimezones.findFromCityStateProvince(query) || []) as CityTimezoneMatch[];
      return matches.slice(0, 1).map(toCityOption);
    })
  );

  let lang: Lang = 'id';
  let screen: Screen = 'home';
  let activeFeature = 0;
  let quoteIndex = 0;
  let rating = 0;
  let feedbackText = '';
  let feedbackSent = false;
  let display_name = 'Wauputra';
  let birth_date = '1997-06-19';
  let birth_time = '17:45';
  let birth_place = 'Jakarta, Indonesia';
  let email = '';
  let cityQuery = 'Jakarta, Indonesia';
  let selectedCity: CityOption | null = cityOptions[0];
  let cityPickerOpen = false;
  let loading = false;
  let error = '';
  let profile: any = null;
  let validation: any = null;
  let interpretation: any = null;
  let installPromptEvent: any = null;
  let canInstall = false;
  let installDismissed = false;
  let installMessage = '';
  let guestHistory: GuestHistoryItem[] = [];
  let shareStatus = '';
  let shareLink = '';
  let detailQuestion = '';
  let detailAnswer = '';
  let detailLoading = false;
  let storageReady = false;
  let isOnline = true;
  let gameState: GuestGameState = { xp: 0, streak: 0, badges: [] };
  let gameMessage = '';
  let termsAccepted = false;
  let authUser: AuthUser | null = null;
  let authChecked = false;
  let accountSyncDone = false;
  let accountStatus = '';
  let formStep = 0;
  let usernameInput = '';
  let publicProfile: any = null;
  let publicProfiles: any[] = [];
  let publicProfileStatus = '';
  let publishLoading = false;
  let skyPosts: any[] = [];
  let skyCalendar: any[] = [];
  let selectedSkyPost: any = null;

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

  $: educationDetailRows = lang === 'id'
    ? [
        [['Matahari', 'Identitas, vitalitas, arah sadar.'], ['Bulan', 'Emosi, kebutuhan aman, kebiasaan batin.'], ['Merkurius', 'Cara berpikir, bahasa, belajar.'], ['Venus', 'Rasa suka, relasi, estetika.'], ['Mars', 'Aksi, keberanian, dorongan.'], ['Jupiter', 'Ekspansi, makna, peluang.'], ['Saturnus', 'Struktur, batas, kedewasaan.']],
        [['Aries', 'Langsung, berani, memulai.'], ['Taurus', 'Stabil, sensorial, konsisten.'], ['Gemini', 'Komunikatif, ingin tahu, adaptif.'], ['Cancer', 'Emosional, merawat, protektif.'], ['Leo', 'Ekspresif, kreatif, terlihat.'], ['Virgo', 'Analitis, rapi, memperbaiki.'], ['Libra', 'Relasional, adil, harmonis.'], ['Scorpio', 'Intens, mendalam, transformatif.'], ['Sagittarius', 'Eksploratif, filosofis, luas.'], ['Capricorn', 'Struktural, ambisius, bertahap.'], ['Aquarius', 'Inovatif, komunitas, visioner.'], ['Pisces', 'Imajinatif, empatik, spiritual.']],
        [['House 1', 'Diri, tubuh, kesan pertama.'], ['House 2', 'Nilai, uang, rasa aman.'], ['House 3', 'Komunikasi, belajar, saudara.'], ['House 4', 'Rumah, akar, keluarga.'], ['House 5', 'Kreativitas, romansa, ekspresi.'], ['House 6', 'Rutinitas, kerja harian, kesehatan.'], ['House 7', 'Relasi, pasangan, kerja sama.'], ['House 8', 'Kedalaman, krisis, transformasi.'], ['House 9', 'Makna, perjalanan, pendidikan tinggi.'], ['House 10', 'Karier, reputasi, arah publik.'], ['House 11', 'Komunitas, harapan, jejaring.'], ['House 12', 'Bawah sadar, retreat, pelepasan.']],
        [['Conjunction', 'Energi planet menyatu dan terasa kuat.'], ['Sextile', 'Peluang yang mengalir saat diaktifkan.'], ['Square', 'Tegangan yang mendorong latihan.'], ['Trine', 'Bakat natural dan aliran mudah.'], ['Opposition', 'Dua kutub yang perlu diintegrasikan.']]
      ][activeEducation]
    : [
        [['Sun', 'Identity, vitality, conscious direction.'], ['Moon', 'Emotion, safety needs, inner habits.'], ['Mercury', 'Thinking, language, learning.'], ['Venus', 'Taste, relationships, aesthetics.'], ['Mars', 'Action, courage, drive.'], ['Jupiter', 'Expansion, meaning, opportunity.'], ['Saturn', 'Structure, boundaries, maturity.']],
        [['Aries', 'Direct, brave, initiating.'], ['Taurus', 'Stable, sensory, consistent.'], ['Gemini', 'Communicative, curious, adaptive.'], ['Cancer', 'Emotional, caring, protective.'], ['Leo', 'Expressive, creative, visible.'], ['Virgo', 'Analytical, tidy, improving.'], ['Libra', 'Relational, fair, harmonious.'], ['Scorpio', 'Intense, deep, transformative.'], ['Sagittarius', 'Exploratory, philosophical, broad.'], ['Capricorn', 'Structural, ambitious, gradual.'], ['Aquarius', 'Innovative, communal, visionary.'], ['Pisces', 'Imaginative, empathic, spiritual.']],
        [['House 1', 'Self, body, first impression.'], ['House 2', 'Values, money, security.'], ['House 3', 'Communication, learning, siblings.'], ['House 4', 'Home, roots, family.'], ['House 5', 'Creativity, romance, expression.'], ['House 6', 'Routine, daily work, health.'], ['House 7', 'Relationships, partners, cooperation.'], ['House 8', 'Depth, crisis, transformation.'], ['House 9', 'Meaning, travel, higher learning.'], ['House 10', 'Career, reputation, public direction.'], ['House 11', 'Community, hopes, networks.'], ['House 12', 'Unconscious, retreat, release.']],
        [['Conjunction', 'Planet energies merge and feel strong.'], ['Sextile', 'Opportunities that flow when activated.'], ['Square', 'Tension that pushes practice.'], ['Trine', 'Natural talent and easy flow.'], ['Opposition', 'Two poles that ask integration.']]
      ][activeEducation];

  $: features = lang === 'id'
    ? [
        ['Natal Chart', 'Lihat zodiac sign, planet, house, dan aspect.'],
        ['Hermes AI', 'Coming soon: tanya detail setelah flow donasi/subscription siap.'],
        ['Minat & Bakat', 'Pisahkan kekuatan, kelemahan, dan arah eksplorasi.'],
        ['Roadmap 5 Tahun', 'Peta umum untuk dicoba bertahap.'],
        ['Jodoh Similarity', 'Coming soon: cari kecocokan relasi dari dua chart astrology.']
      ]
    : [
        ['Natal Chart', 'Inspect zodiac signs, planets, houses, and aspects.'],
        ['Hermes AI', 'Coming soon: deeper chat after donation/subscription is ready.'],
        ['Interests & Talents', 'Separate strengths, weaknesses, and explorations.'],
        ['5-Year Roadmap', 'A general path to test gradually.'],
        ['Partner Similarity', 'Coming soon: compare relationship compatibility from two astrology charts.']
      ];
  $: formSteps = lang === 'id'
    ? ['Data lahir', 'Lokasi lahir', 'Identitas guest']
    : ['Birth data', 'Birth place', 'Guest identity'];
  $: filteredCities = searchCities(cityQuery);
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
  $: keyTakeaways = oracle ? [oracle.strengths[0], oracle.weaknesses[0], oracle.careers[0]].filter(Boolean) : [];
  $: latestSkyPost = skyPosts[0];
  $: dailyQuestDone = gameState.dailyQuestDate === localDateKey();

  function localDateKey(date = new Date()) {
    const year = date.getFullYear();
    const month = `${date.getMonth() + 1}`.padStart(2, '0');
    const day = `${date.getDate()}`.padStart(2, '0');
    return `${year}-${month}-${day}`;
  }
  function dateKeyToUtcDay(value: string) {
    const [year, month, day] = value.split('-').map(Number);
    if (!year || !month || !day) return 0;
    return Date.UTC(year, month - 1, day) / 86400000;
  }

  onMount(() => {
    installGoogleAnalytics();
    if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => undefined);
    const draft = localStorage.getItem('hermex_guest_draft');
    if (draft) {
      try {
        const saved = JSON.parse(draft);
        display_name = saved.display_name ?? display_name;
        birth_date = saved.birth_date ?? birth_date;
        birth_time = saved.birth_time ?? birth_time;
        birth_place = saved.birth_place ?? birth_place;
        email = saved.email ?? email;
        usernameInput = saved.usernameInput ?? usernameInput;
        cityQuery = saved.cityQuery ?? cityQuery;
        selectedCity = saved.selectedCity ?? selectedCity;
      } catch { /* ignore broken local draft */ }
    }
    guestHistory = loadGuestHistory();
    gameState = loadGameState();
    termsAccepted = localStorage.getItem('hermex_google_terms') === 'accepted';
    installDismissed = localStorage.getItem('hermex_install_dismissed') === 'yes';
    isOnline = navigator.onLine;
    storageReady = true;
    const params = new URLSearchParams(window.location.search);
    const sharedProfile = params.get('profile');
    const publicUsername = params.get('u');
    const authStatus = params.get('auth');
    if (authStatus?.startsWith('google')) screen = 'account';
    loadAuthUser();
    loadSkyNews();
    if (publicUsername) {
      openPublicProfile(publicUsername);
    }
    if (sharedProfile) {
      getProfile(sharedProfile).then((loaded) => {
        profile = loaded;
        rememberGuest(loaded);
        screen = 'profile';
      }).catch(() => undefined);
    }
    const installHandler = (event: Event) => {
      event.preventDefault();
      installPromptEvent = event;
      canInstall = true;
    };
    window.addEventListener('beforeinstallprompt', installHandler);
    const onlineHandler = () => (isOnline = navigator.onLine);
    window.addEventListener('online', onlineHandler);
    window.addEventListener('offline', onlineHandler);
    const timer = window.setInterval(() => (quoteIndex = (quoteIndex + 1) % quotes.length), 2600);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener('beforeinstallprompt', installHandler);
      window.removeEventListener('online', onlineHandler);
      window.removeEventListener('offline', onlineHandler);
    };
  });

  function toggleLang() { lang = lang === 'id' ? 'en' : 'id'; }
  function searchCities(query: string): CityOption[] {
    const normalized = query.trim();
    if (normalized.length < 2) return cityOptions.slice(0, 8);
    const matches = (cityTimezones.findFromCityStateProvince(normalized) || []) as CityTimezoneMatch[];
    return uniqueCities(matches.map(toCityOption)).slice(0, 12);
  }
  function chooseCity(city: CityOption) { selectedCity = city; birth_place = city.label; cityQuery = city.label; cityPickerOpen = false; }
  function onCityInput(value: string) {
    cityQuery = value;
    birth_place = value;
    cityPickerOpen = true;
    selectedCity = searchCities(value).find((city) => city.label.toLowerCase() === value.toLowerCase()) ?? null;
  }
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
  function publicSummary(value: unknown): string {
    return displayValue(value)
      .replace(/^Anda adalah individu dengan/i, 'Individu ini menunjukkan')
      .replace(/^Anda adalah/i, 'Profil ini menunjukkan')
      .replace(/^Anda memiliki/i, 'Individu ini memiliki')
      .replace(/^Anda\b/i, 'Individu ini')
      .replace(/^Kamu\b/i, 'Individu ini');
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
  function roadmapTitle(_item: any, index: number) { return String(new Date().getFullYear() - 5 + index); }
  function roadmapText(item: any) { return item?.description || item?.focus || item?.theme || displayValue(item); }
  function explainMore() { screen = 'register'; }
  function loadGuestHistory(): GuestHistoryItem[] {
    try { return JSON.parse(localStorage.getItem('hermex_guest_history') || '[]'); }
    catch { return []; }
  }
  function loadGameState(): GuestGameState {
    try {
      return { xp: 0, streak: 0, badges: [], ...JSON.parse(localStorage.getItem('hermex_guest_game') || '{}') };
    } catch {
      return { xp: 0, streak: 0, badges: [] };
    }
  }
  function saveGameState(nextState: GuestGameState) {
    gameState = nextState;
    localStorage.setItem('hermex_guest_game', JSON.stringify(nextState));
  }
  function completeDailyQuest() {
    const today = localDateKey();
    if (dailyQuestDone) return;
    const dayGap = gameState.dailyQuestDate ? dateKeyToUtcDay(today) - dateKeyToUtcDay(gameState.dailyQuestDate) : 1;
    const nextStreak = dayGap === 1 ? gameState.streak + 1 : 1;
    const badges = Array.from(new Set([...gameState.badges, 'Mercury Spark']));
    saveGameState({ xp: gameState.xp + 15, streak: nextStreak, badges, dailyQuestDate: today });
    gameMessage = lang === 'id' ? 'Badge Mercury Spark tersimpan lokal.' : 'Mercury Spark badge saved locally.';
    window.setTimeout(() => (gameMessage = ''), 1800);
  }
  function acceptTerms() {
    termsAccepted = true;
    localStorage.setItem('hermex_google_terms', 'accepted');
    screen = 'connect';
  }
  function startGoogleLogin() {
    window.location.href = `${API_BASE}/api/v1/auth/google/start`;
  }
  async function loadAuthUser() {
    try {
      const result = await getAuthMe();
      authUser = result.authenticated ? result.user : null;
      if (authUser) await syncLocalHistoryToAccount();
    } catch {
      authUser = null;
    } finally {
      authChecked = true;
    }
  }
  function logoutGoogle() {
    authUser = null;
    accountSyncDone = false;
    accountStatus = '';
    storageReady = false;
    profile = null;
    interpretation = null;
    validation = null;
    publicProfile = null;
    email = '';
    usernameInput = '';
    shareLink = '';
    guestHistory = [];
    localStorage.removeItem('hermex_guest_history');
    localStorage.removeItem('hermex_guest_draft');
    window.location.href = `${API_BASE}/api/v1/auth/logout`;
  }
  async function syncLocalHistoryToAccount() {
    if (accountSyncDone) return;
    accountSyncDone = true;
    const profileClaims = Array.from(new Map([
      ...guestHistory.map((item) => item.profile),
      profile
    ].filter((item) => item?.profile_id && item?.claim_token).map((item) => [item.profile_id, {
      profile_id: item.profile_id,
      claim_token: item.claim_token
    }])).values());
    try {
      if (profileClaims.length) await syncUserHistory(profileClaims as Array<{ profile_id: string; claim_token: string }>);
      const result = await getUserHistory();
      guestHistory = result.history.map((item: any) => ({
        profile_id: item.profile_id,
        display_name: item.display_name,
        birth_place: item.birth_place,
        created_at: item.created_at,
        dominant: item.dominant,
        profile: item.profile,
        interpretation: item.interpretation,
        interpretation_id: item.interpretation?.interpretation_id,
        updated_at: item.linked_at
      }));
      localStorage.setItem('hermex_guest_history', JSON.stringify(guestHistory));
      if (guestHistory[0] && !profile) {
        profile = guestHistory[0].profile;
        interpretation = guestHistory[0].interpretation ?? null;
      }
      accountStatus = lang === 'id' ? 'History guest sudah terhubung ke akun Google.' : 'Guest history is linked to your Google account.';
    } catch {
      accountStatus = lang === 'id' ? 'Login aktif, tapi sync history belum berhasil.' : 'Login is active, but history sync has not completed.';
    }
  }
  async function removeHistoryItem(item: GuestHistoryItem) {
    if (authUser) await deleteUserHistory(item.profile_id).catch(() => undefined);
    guestHistory = guestHistory.filter((entry) => entry.profile_id !== item.profile_id);
    localStorage.setItem('hermex_guest_history', JSON.stringify(guestHistory));
    if (profile?.profile_id === item.profile_id) {
      profile = null;
      interpretation = null;
      screen = 'account';
    }
  }
  function safeUsername(value: string) {
    return value.toLowerCase().trim().replace(/[^a-z0-9_]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 32);
  }
  async function loadSkyNews() {
    try {
      const result: any = await getSkyNews();
      skyPosts = result.posts ?? [];
    } catch {
      skyPosts = [];
    }
    try {
      const result: any = await getSkyCalendar();
      skyCalendar = result.events ?? [];
    } catch {
      skyCalendar = [];
    }
  }
  async function openConnect() {
    screen = 'connect';
    try {
      const result: any = await listPublicProfiles();
      publicProfiles = result.profiles ?? [];
    } catch {
      publicProfiles = [];
    }
  }
  async function openPublicProfile(username: string) {
    try {
      publicProfile = await getPublicProfile(username);
      profile = publicProfile.profile;
      interpretation = publicProfile.latest_interpretation;
      screen = 'public-profile';
    } catch (err) {
      publicProfileStatus = err instanceof Error ? err.message : 'Unknown error';
      screen = 'connect';
    }
  }
  function rememberGuest(nextProfile: any, nextInterpretation: any = interpretation) {
    if (!nextProfile?.profile_id) return;
    const item = {
      profile_id: nextProfile.profile_id,
      display_name: nextProfile.display_name,
      birth_place: nextProfile.birth_place,
      created_at: nextProfile.created_at,
      dominant: nextProfile.traits?.dominant_element ?? '-',
      profile: nextProfile,
      interpretation: nextInterpretation,
      interpretation_id: nextInterpretation?.interpretation_id,
      updated_at: new Date().toISOString()
    };
    guestHistory = [item, ...guestHistory.filter((entry) => entry.profile_id !== item.profile_id)].slice(0, 12);
    localStorage.setItem('hermex_guest_history', JSON.stringify(guestHistory));
  }
  async function installApp() {
    if (!installPromptEvent) {
      canInstall = false;
      installMessage = copy.installUnavailable;
      return;
    }
    await installPromptEvent.prompt();
    installPromptEvent = null;
    canInstall = false;
  }
  function dismissInstallBadge() {
    installDismissed = true;
    localStorage.setItem('hermex_install_dismissed', 'yes');
  }
  async function shareProfile() {
    if (!profile?.profile_id) return;
    const username = safeUsername(usernameInput || display_name || profile.display_name || '');
    if (!email.trim() || username.length < 3) {
      publicProfileStatus = lang === 'id' ? 'Isi email dan username unik dulu untuk membuat halaman publik.' : 'Add email and a unique username first to create a public page.';
      screen = 'connect';
      return;
    }
    publishLoading = true;
    publicProfileStatus = '';
    try {
      const result: any = await publishPublicProfile({
        profile_id: profile.profile_id,
        username,
        email,
        claim_token: profile.claim_token,
        display_name: display_name || profile.display_name,
        bio: lang === 'id' ? 'Profil astrology reflektif dari Hermex Fun.' : 'Reflective astrology profile from Hermex Fun.'
      });
      publicProfile = result.public_profile;
      usernameInput = publicProfile.username;
      const list: any = await listPublicProfiles().catch(() => ({ profiles: [] }));
      publicProfiles = list.profiles ?? [];
    } catch (err) {
      publicProfileStatus = err instanceof Error ? err.message : 'Unknown error';
      return;
    } finally {
      publishLoading = false;
    }
    const link = `${window.location.origin}/@${usernameInput}`;
    shareLink = link;
    let copied = false;
    if (navigator.share) {
      await navigator.share({ title: 'Hermex Fun', text: 'Coba lihat profile astrology Hermex ini.', url: link }).then(() => (copied = true)).catch(() => undefined);
    }
    if (!copied && navigator.clipboard) {
      await navigator.clipboard.writeText(link).then(() => (copied = true)).catch(() => undefined);
    }
    shareStatus = copied ? copy.copied : (lang === 'id' ? 'Salin link di bawah ini' : 'Copy the link below');
    screen = 'public-profile';
    window.setTimeout(() => (shareStatus = ''), 1600);
  }
  async function submitFeedback() {
    if (!rating) return;
    try {
      await submitFeedbackApi({ profile_id: profile?.profile_id, interpretation_id: interpretation?.interpretation_id, rating, message: feedbackText, source: 'pwa' });
      feedbackSent = true;
    } catch {
      return;
    }
    feedbackText = '';
    rating = 0;
  }
  async function askDetail() {
    if (!profile || !detailQuestion.trim()) return;
    if (!isOnline) {
      detailAnswer = lang === 'id' ? 'Hermex AI butuh internet. Mode offline tetap bisa membuka history dan edukasi.' : 'Hermex AI needs internet. Offline mode can still open history and education.';
      return;
    }
    detailLoading = true;
    detailAnswer = '';
    try {
      const result: any = await askHermexDetail(profile.profile_id, lang, detailQuestion.trim());
      detailAnswer = displayValue(result?.interpretation?.summary || result?.interpretation);
    } catch (err) {
      detailAnswer = err instanceof Error ? err.message : 'Unknown error';
    } finally {
      detailLoading = false;
    }
  }
  function openHistoryItem(item: GuestHistoryItem) {
    profile = item.profile;
    interpretation = item.interpretation ?? null;
    screen = interpretation ? 'hermes' : 'profile';
  }

  function escapeHtml(value: string) {
    const map: Record<string, string> = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return value.replace(/[&<>"']/g, (char) => map[char] || char);
  }
  function formatInsight(item: string) {
    const text = escapeHtml(item);
    const split = text.split(/[:;,-]\s+/);
    if (split.length > 1 && split[0].length < 46) return `<strong>${split[0]}</strong>: ${split.slice(1).join(' ')}`;
    const words = text.split(' ');
    return `<strong>${words.slice(0, 3).join(' ')}</strong>${words.length > 3 ? ` ${words.slice(3).join(' ')}` : ''}`;
  }

  $: if (storageReady) {
    localStorage.setItem('hermex_guest_draft', JSON.stringify({ display_name, birth_date, birth_time, birth_place, email, usernameInput, cityQuery, selectedCity }));
  }

  function friendlyErrorMessage(err: unknown) {
    const message = err instanceof Error ? err.message : 'Unknown error';
    const lower = message.toLowerCase();
    const status = err && typeof err === 'object' && 'status' in err ? Number((err as { status?: unknown }).status) : undefined;
    if (status === 429) {
      if (lower.includes('per day') || lower.includes('day')) return copy.aiLimitDay;
      if (lower.includes('per minute') || lower.includes('minute')) return copy.aiLimitMinute;
      return lang === 'id'
        ? 'Limit request sudah tercapai. Coba lagi nanti.'
        : 'The request limit has been reached. Try again later.';
    }
    if (lower.includes('request limit reached') || lower.includes('too many requests')) {
      if (lower.includes('day')) return copy.aiLimitDay;
      if (lower.includes('minute')) return copy.aiLimitMinute;
      return lang === 'id'
        ? 'Limit request sudah tercapai. Coba lagi nanti.'
        : 'The request limit has been reached. Try again later.';
    }
    return message;
  }

  async function runAnalysis() {
    loading = true; error = ''; interpretation = null; validation = null;
    try {
      profile = await analyzeBirth({ display_name, birth_date, birth_place, ...(birth_time ? { birth_time } : {}), ...(selectedCity ? { latitude: selectedCity.latitude, longitude: selectedCity.longitude, timezone: selectedCity.timezone } : {}) });
      rememberGuest(profile);
      screen = 'profile';
    } catch (err) { error = friendlyErrorMessage(err); }
    finally { loading = false; }
  }
  async function runValidation() {
    if (!profile) return;
    validation = await validateBirth(profile.profile_id, { birth_time_certainty: birth_time ? 'known' : 'unknown', current_pull: 'building' });
    profile.traits = validation.traits; profile.needs_validation = false;
  }
  async function runInterpretation() {
    if (!profile) return;
    loading = true; screen = 'hermes-loading'; error = ''; feedbackSent = false;
    try {
      interpretation = await interpretProfile(profile.profile_id, lang);
      if (String(interpretation?.provider ?? '').includes('error')) {
        error = copy.aiErrorBody;
        screen = 'ai-error';
      } else {
        rememberGuest(profile, interpretation);
        screen = 'hermes';
      }
    }
    catch (err) { error = friendlyErrorMessage(err); screen = 'ai-error'; }
    finally { loading = false; }
  }
</script>

<svelte:head><title>Hermex Fun</title><meta name="theme-color" content="#f4c15d" /><link rel="manifest" href="/manifest.webmanifest" /><link rel="icon" href="/icons/hermex-star.svg" /></svelte:head>

<main class="app-shell">
  <section class="phone-frame">
    <header class="topbar">
      <button class="brand" type="button" on:click={() => (screen = 'home')}><svg viewBox="0 0 64 64"><path d="M32 5l7 17 18 2-14 12 4 18-15-10-15 10 4-18L7 24l18-2 7-17z"/><circle cx="25" cy="30" r="2.5"/><circle cx="39" cy="30" r="2.5"/><path d="M25 39c4 3 10 3 14 0"/></svg><div><p>{copy.badge}</p><strong>Hermex Fun</strong></div></button>
      {#if screen !== 'home'}<button class="ghost" on:click={() => (screen = 'home')}>{copy.edit}</button>{/if}<button class="lang" on:click={toggleLang}>{lang.toUpperCase()}</button>
    </header>

    <nav class="bottom-nav"><button class:active={screen === 'home'} on:click={() => (screen = 'home')}>⌂<span>{copy.home}</span></button><button class:active={screen === 'account'} on:click={() => (screen = 'account')}>✦<span>{copy.profileTab}</span></button><button class:active={screen === 'connect'} on:click={openConnect}>↗<span>{copy.connect}</span></button><button class:active={screen === 'hermes-chat'} on:click={() => (screen = 'hermes-chat')}>☿<span>{copy.hermexNav}</span></button></nav>

    {#if screen === 'home'}
      <section class="hero-card"><div><span>{copy.features}</span><h1>{copy.title}</h1><p>{copy.subtitle}</p></div><svg viewBox="0 0 220 220"><circle cx="110" cy="110" r="82"/><circle cx="110" cy="110" r="50"/><path d="M138 47a31 31 0 1 0 0 62 38 38 0 1 1 0-62z"/><circle cx="49" cy="83" r="13"/><circle cx="171" cy="148" r="16"/><path d="M101 128l8 18 18 8-18 8-8 18-8-18-18-8 18-8 8-18z"/></svg></section>
      {#if !installDismissed}<div class="install-badge show"><button type="button" on:click={installApp}>⬇ {copy.install}<small>{installMessage || copy.installHint}</small></button><button class="install-close" type="button" aria-label={copy.dismiss} on:click={dismissInstallBadge}>×</button></div>{/if}
      {#if !isOnline}<section class="offline-banner"><strong>☁ {copy.offlineTitle}</strong><span>{copy.offlineBody}</span></section>{/if}
      <section class="feature-row">{#each features as feature, index}<button class:active={activeFeature === index} on:click={() => (activeFeature = index)}>{@render Icon(index)}<strong>{feature[0]}</strong><small>{feature[1]}</small></button>{/each}</section>
      <nav class="knowledge-nav"><button on:click={() => (screen = 'learn')}>☿ {copy.learn}</button><button on:click={() => (screen = 'sky-news')}>☾ {copy.skyNews}</button></nav>
      {#if latestSkyPost}<section class="latest-sky"><small>{lang === 'id' ? 'Latest Berita Langit' : 'Latest Sky News'}</small><h2>{latestSkyPost.title}</h2><p>{latestSkyPost.summary}</p><a href={`/berita-langit/${latestSkyPost.slug}`}>{lang === 'id' ? 'Baca article' : 'Read article'}</a></section>{/if}
      <section class="home-grid single"><article class="card form-card quest-form"><div class="section-title"><span>01</span><h2>Profil Pemain</h2></div>
        <div class="quest-steps">{#each formSteps as step, index}<button class:active={formStep === index} on:click={() => (formStep = index)}><span>{index + 1}</span>{step}</button>{/each}</div>
        {#if formStep === 0}<div class="split"><label>{copy.date}<input type="date" bind:value={birth_date} /></label><label>{copy.time} <small>{copy.optional}</small><input type="time" bind:value={birth_time} /><small class="field-hint">{lang === 'id' ? 'Semakin detail, house dan aspek chart makin akurat.' : 'More detail improves houses and chart precision.'}</small></label></div>{/if}
        {#if formStep === 1}<label class="city-picker">{copy.place}<input value={cityQuery} placeholder={copy.citySearch} autocomplete="off" role="combobox" aria-controls="city-options" aria-expanded={cityPickerOpen ? 'true' : 'false'} on:focus={() => (cityPickerOpen = true)} on:input={(event) => onCityInput(event.currentTarget.value)} />{#if cityPickerOpen && filteredCities.length}<div class="city-menu" id="city-options">{#each filteredCities as city}<button type="button" on:mousedown|preventDefault={() => chooseCity(city)}><strong>{city.label}</strong><small>{city.latitude.toFixed(4)}, {city.longitude.toFixed(4)} · {city.timezone}</small></button>{/each}</div>{/if}</label>{#if selectedCity}<p class="location-note">{copy.selectedCity}: {selectedCity.label}<br />{copy.locationHint}</p>{/if}{/if}
        {#if formStep === 2}<label>{copy.email} <small>{copy.optional}</small><input type="email" bind:value={email} placeholder="you@example.com" /></label><label>{copy.name} <small>{copy.optional}</small><input bind:value={display_name} on:input={() => { if (!usernameInput) usernameInput = safeUsername(display_name); }} /></label><label>{copy.username} <small>{copy.optional}</small><input bind:value={usernameInput} placeholder="wauputra" on:input={() => (usernameInput = safeUsername(usernameInput))} /><small class="field-hint">{copy.usernameHint}</small></label>{/if}
        <div class="route-actions">{#if formStep > 0}<button class="soft-action" on:click={() => (formStep = Math.max(0, formStep - 1))}>{copy.back}</button>{/if}{#if formStep < 2}<button class="primary-action" on:click={() => (formStep = Math.min(2, formStep + 1))}>{lang === 'id' ? 'Lanjut quest' : 'Next quest'}</button>{:else}<button class="primary-action" on:click={runAnalysis} disabled={loading}>✦ {loading ? copy.analyzing : copy.analyze}</button>{/if}</div>{#if error}<p class="error">{error}</p>{/if}
      </article></section>
    {/if}

    {#if screen === 'account'}<section class="card account-page"><div class="section-title"><span>✦</span><h2>{copy.accountTitle}</h2></div><div class="account-hero">{#if authUser}<div class="account-id">{#if authUser.picture}<img src={authUser.picture} alt="" />{:else}<span>{(authUser.name || authUser.email || 'G').slice(0, 1)}</span>{/if}<div><strong>{authUser.name || 'Google User'}</strong><small>{authUser.email}</small></div></div>{#if accountStatus}<small>{accountStatus}</small>{/if}<button class="share-action" on:click={logoutGoogle}>{copy.logout}</button>{:else}<p>{authChecked ? copy.accountGuest : copy.analyzing}</p><button class="google-action" on:click={startGoogleLogin}>G {copy.googleLogin}</button>{/if}</div><div class="account-grid"><article><h3>{copy.currentCard}</h3>{#if profile}<p><strong>{profile.display_name || 'Guest'}</strong> · {profile.traits.dominant_element}</p><div class="chips compact">{#each profile.traits.interests as item}<span>{item}</span>{/each}</div><button class="soft-action oracle-button" on:click={() => (screen = 'profile')}>{copy.viewCard}</button>{:else}<p>{lang === 'id' ? 'Belum ada chart aktif. Buka Astrologyku dulu untuk membuat kartu karakter.' : 'No active chart yet. Open your astrology first to create a character card.'}</p><button class="soft-action oracle-button" on:click={() => (screen = 'home')}>{copy.analyze}</button>{/if}</article><article><h3>{copy.historyTitle}</h3>{#if guestHistory.length}<div class="history-list mini">{#each guestHistory.slice(0, 4) as item}<article class="history-entry"><button on:click={() => openHistoryItem(item)}><strong>{item.display_name || 'Guest'}</strong><span>{item.birth_place}</span><small>{item.dominant} · {item.interpretation ? 'AI saved' : 'chart only'} · {new Date(item.created_at).toLocaleDateString()}</small></button><button class="delete-history" on:click={() => removeHistoryItem(item)}>{lang === 'id' ? 'Hapus' : 'Delete'}</button></article>{/each}</div><button class="share-action" on:click={() => (screen = 'history')}>{copy.history}</button>{:else}<p>{copy.emptyHistory}</p>{/if}</article><article><h3>{copy.publicProfile}</h3><p>{lang === 'id' ? 'Buat halaman publik seperti shortlink bio astrology agar muncul di Connect.' : 'Create a public astrology bio shortlink so it appears in Connect.'}</p><button class="share-action" on:click={openConnect}>↗ {copy.connect}</button></article></div></section>{/if}
    {#if screen === 'account'}<section class="game-card account-quest"><div>{@render Icon(3)}<div><h2>{copy.dailyQuest}</h2><p>{copy.dailyQuestBody}</p></div></div><div class="game-stats"><span>{copy.xp}: {gameState.xp}</span><span>Streak: {gameState.streak}</span><span>{copy.badges}: {gameState.badges.length}</span></div>{#if gameState.badges.length}<div class="badge-row">{#each gameState.badges as badge}<span>✦ {badge}</span>{/each}</div>{/if}<button class="soft-action oracle-button" disabled={dailyQuestDone} on:click={completeDailyQuest}>{dailyQuestDone ? copy.claimedBadge : copy.claimBadge}</button>{#if gameMessage}<small>{gameMessage}</small>{/if}</section>{/if}

    {#if screen === 'profile' && profile}
      <section class="profile-grid"><article class="card character-card"><div class="section-title"><span>02</span><h2>{copy.profile}</h2></div><div class="natal-wheel"><svg viewBox="0 0 300 300"><circle cx="150" cy="150" r="132"/><circle cx="150" cy="150" r="96"/><circle cx="150" cy="150" r="44"/>{#each Array(12) as _, index}<line x1="150" y1="18" x2="150" y2="54" transform={`rotate(${index * 30} 150 150)`}/>{/each}{#each chartLines as line}<line class="aspect-line" x1={line.left.x} y1={line.left.y} x2={line.right.x} y2={line.right.y}/>{/each}{#each planets as [name, planet]}{@const point = planetPoint(name)}{#if point}<g><circle cx={point.x} cy={point.y} r="10"/><text x={point.x} y={point.y - 15}>{name.slice(0, 2)}</text></g>{/if}{/each}</svg></div><h3>{profile.display_name || 'Seeker'}</h3><p class="dominant">{profile.traits.dominant_element}</p><div class="meter"><span style={`width:${Math.round(profile.traits.confidence.score * 100)}%`}></span></div><p>{profile.traits.confidence.label} ({profile.traits.confidence.score})</p><div class="chips">{#each profile.traits.interests as item}<span>{item}</span>{/each}</div>{#if profile.needs_validation}<button class="soft-action" on:click={runValidation}>{copy.validate}</button>{/if}</article>
      <article class="card chart-card"><div class="section-title"><span>03</span><h2>{copy.chart}</h2></div><div class="planet-grid">{#each planets as [name, planet]}<div><strong>{name.replace('_', ' ')}</strong><span>{planet.zodiac_sign} {planet.degree_in_sign}°</span><small>House {houses.planet_houses?.[name] ?? '-'}</small></div>{/each}</div><div class="aspect-list"><h3>Aspects</h3>{#each aspects.slice(0, 10) as aspect}<p><strong>{aspect.left}</strong> {aspect.type} <strong>{aspect.right}</strong> <small>orb {aspect.orb}</small></p>{/each}</div><button class="soft-action oracle-button" on:click={runInterpretation} disabled={!isOnline}>{copy.askHermes}</button>{#if !isOnline}<p class="field-hint">{copy.offlineBody}</p>{/if}</article></section>
    {/if}

    {#if screen === 'hermes-loading'}<section class="loading-screen"><div class="loader"><span></span><span></span><span></span><strong>☿</strong></div><h2>{copy.processingTitle}</h2><p class="quote">{quotes[quoteIndex]}</p><small>{copy.processingBody}</small></section>{/if}

    {#if screen === 'hermes' && oracle}<section class="card hermes-card"><div class="section-title"><span>04</span><h2>{copy.hermes}</h2></div><div class="summary-card">{@render Icon(1)}<p><mark>{summaryHighlight.lead}</mark>{#if summaryHighlight.rest}<br /><span>{summaryHighlight.rest}</span>{/if}</p></div>{#if keyTakeaways.length}<div class="takeaway-row">{#each keyTakeaways as item}<span>✦ {item}</span>{/each}</div>{/if}<div class="insight-grid">{@render Insight(copy.love, oracle.love, '♡')}{@render Insight(copy.strengths, oracle.strengths, '✦')}{@render Insight(copy.weaknesses, oracle.weaknesses, '△')}{@render Insight(copy.interests, oracle.interests, '☉')}{@render Insight(copy.talents, oracle.talents, '☾')}{@render Insight(copy.career, oracle.careers, '☿')}</div><div class="timeline"><h3>{copy.fiveYear}</h3>{#each oracle.fiveYear.slice(0, 5) as item, index}<div><span>{roadmapTitle(item, index)}</span><p>{roadmapText(item)}</p></div>{/each}<button class="text-link" on:click={explainMore}>{copy.register}</button></div>{#if !feedbackSent}<div class="feedback"><h3>{copy.feedback}</h3><div class="stars">{#each [1,2,3,4,5] as star}<button class:active={rating >= star} on:click={() => (rating = star)}>★</button>{/each}</div><textarea bind:value={feedbackText} placeholder={copy.suggestion}></textarea><button class="soft-action" on:click={submitFeedback}>{copy.sendFeedback}</button><button class="share-action" on:click={shareProfile}>↗ {publishLoading ? copy.analyzing : copy.share}</button>{#if publicProfileStatus}<small>{publicProfileStatus}</small>{/if}{#if shareStatus}<small>{shareStatus}</small>{/if}{#if shareLink}<input class="share-link" readonly value={shareLink} on:focus={(event) => event.currentTarget.select()} />{/if}</div>{:else}<div class="feedback-done">✦ {lang === 'id' ? 'Feedback tersimpan. Terima kasih.' : 'Feedback saved. Thank you.'}</div><div class="feedback share-only"><button class="share-action" on:click={shareProfile}>↗ {publishLoading ? copy.analyzing : copy.share}</button>{#if publicProfileStatus}<small>{publicProfileStatus}</small>{/if}{#if shareStatus}<small>{shareStatus}</small>{/if}{#if shareLink}<input class="share-link" readonly value={shareLink} on:focus={(event) => event.currentTarget.select()} />{/if}</div>{/if}<div class="route-actions"><button class="soft-action" on:click={() => (screen = 'profile')}>{copy.back}</button><button class="soft-action oracle-button" on:click={runInterpretation}>{copy.askAgain}</button></div></section>{/if}



    {#if screen === 'ai-error'}<section class="card ai-error-page"><div class="section-title"><span>!</span><h2>{copy.aiErrorTitle}</h2></div><div class="error-visual">{@render Icon(1, true)}<p>{error || copy.aiErrorBody}</p></div><div class="route-actions"><button class="soft-action" on:click={() => (screen = 'profile')}>{copy.back}</button><button class="soft-action oracle-button" on:click={runInterpretation}>{copy.retry}</button></div></section>{/if}

    {#if screen === 'learn'}<section class="card learn-page"><div class="section-title"><span>☿</span><h2>{copy.learn}</h2></div><div class="education-grid">{#each educationCards as card, index}<button class:active={activeEducation === index} on:click={() => { activeEducation = index; screen = 'learn-detail'; }}>{@render Icon(index)}<h3>{card[0]}</h3><p>{card[1]}</p><small>{lang === 'id' ? 'Buka detail' : 'Open detail'}</small></button>{/each}</div><button class="soft-action" on:click={() => (screen = 'home')}>{copy.back}</button></section>{/if}
    {#if screen === 'learn-detail'}<section class="card learn-page detail-page"><div class="section-title"><span>☿</span><h2>{educationCards[activeEducation][0]}</h2></div><article class="education-detail">{@render Icon(activeEducation, true)}<div><p>{educationCards[activeEducation][1]}</p><p>{lang === 'id' ? 'Bayangkan ini seperti lapisan peta: planet adalah aktor, zodiac adalah gaya bicara, house adalah panggung, dan aspect adalah hubungan antar aktor.' : 'Think of this as map layers: planets are actors, zodiac signs are speaking styles, houses are stages, and aspects are relationships between actors.'}</p></div></article><div class="detail-list">{#each educationDetailRows as row}<article><strong>{row[0]}</strong><p>{row[1]}</p></article>{/each}</div><button class="soft-action" on:click={() => (screen = 'learn')}>{copy.learn}</button></section>{/if}
    {#if screen === 'history'}<section class="card history-page"><div class="section-title"><span>⌁</span><h2>{copy.historyTitle}</h2></div>{#if guestHistory.length}<div class="history-list">{#each guestHistory as item}<article class="history-entry"><button on:click={() => openHistoryItem(item)}><strong>{item.display_name || 'Guest'}</strong><span>{item.birth_place}</span><small>{item.dominant} · {item.interpretation ? 'AI saved' : 'chart only'} · {new Date(item.created_at).toLocaleDateString()}</small></button><button class="delete-history" on:click={() => removeHistoryItem(item)}>{lang === 'id' ? 'Hapus riwayat' : 'Delete history'}</button></article>{/each}</div>{:else}<p>{copy.emptyHistory}</p>{/if}</section>{/if}
    {#if screen === 'connect'}<section class="card connect-page"><div class="section-title"><span>↗</span><h2>{copy.connect}</h2></div><p>{lang === 'id' ? 'Publikasikan profil astrology seperti shortlink bio. Email dan username wajib agar link publik tidak duplikat.' : 'Publish an astrology profile like a bio shortlink. Email and username are required so public links stay unique.'}</p><div class="split"><label>{copy.email}<input type="email" bind:value={email} placeholder="you@example.com" /></label><label>{copy.username}<input bind:value={usernameInput} placeholder="wauputra" on:input={() => (usernameInput = safeUsername(usernameInput))} /><small>{copy.usernameHint}</small></label></div><button class="share-action" on:click={shareProfile}>↗ {publishLoading ? copy.analyzing : copy.publishProfile}</button>{#if publicProfileStatus}<small>{publicProfileStatus}</small>{/if}{#if shareStatus}<small>{shareStatus}</small>{/if}{#if shareLink}<input class="share-link" readonly value={shareLink} on:focus={(event) => event.currentTarget.select()} />{/if}<h3>{lang === 'id' ? 'Connect publik' : 'Public Connect'}</h3>{#if publicProfiles.length}<div class="connect-grid">{#each publicProfiles as item}<button on:click={() => openPublicProfile(item.username)}><strong>@{item.username}</strong><span>{item.display_name || 'Guest'} · {item.profile?.traits?.dominant_element}</span><small>{item.latest_interpretation ? publicSummary(item.latest_interpretation.interpretation?.summary).slice(0, 90) : 'Natal chart ready'}</small></button>{/each}</div>{:else}<p>{lang === 'id' ? 'Belum ada profile publik. Jadilah yang pertama.' : 'No public profiles yet. Be the first.'}</p>{/if}</section>{/if}
    {#if screen === 'public-profile' && publicProfile}<section class="card public-page"><div class="section-title"><span>↗</span><h2>@{publicProfile.username}</h2></div><div class="public-hero">{@render Icon(0)}<div><h3>{publicProfile.display_name || 'Hermex Guest'}</h3><p>{publicProfile.bio || (lang === 'id' ? 'Profile astrology publik dari Hermex.' : 'Public astrology profile from Hermex.')}</p><div class="chips compact"><span>{publicProfile.profile?.traits?.dominant_element}</span>{#each (publicProfile.profile?.traits?.interests ?? []).slice(0, 3) as item}<span>{item}</span>{/each}</div></div></div>{#if publicProfile.latest_interpretation}<div class="summary-card mini">{@render Icon(1)}<p>{publicSummary(publicProfile.latest_interpretation.interpretation?.summary)}</p></div>{/if}<button class="soft-action oracle-button" on:click={() => { profile = publicProfile.profile; interpretation = publicProfile.latest_interpretation; screen = interpretation ? 'hermes' : 'profile'; }}>{lang === 'id' ? 'Buka detail astrology' : 'Open astrology detail'}</button></section>{/if}
    {#if screen === 'sky-news'}<section class="card sky-page"><div class="section-title"><span>☾</span><h2>{copy.skyNews}</h2></div><p>{lang === 'id' ? 'Blog ringan tentang simbol langit dan cara membacanya sebagai refleksi peristiwa di bumi, bukan klaim sebab-akibat mutlak.' : 'A light blog about sky symbols and how to read them as earthly reflection, not deterministic causality.'}</p>{#if latestSkyPost}<article class="latest-sky in-page"><small>{latestSkyPost.tag}</small><h2>{latestSkyPost.title}</h2><p>{latestSkyPost.summary}</p><a href={`/berita-langit/${latestSkyPost.slug}`}>{lang === 'id' ? 'Baca latest article' : 'Read latest article'}</a></article>{/if}<div class="calendar-card"><h3>{lang === 'id' ? 'Calendar Astrology' : 'Astrology Calendar'}</h3>{#if skyCalendar.length}<div class="calendar-list">{#each skyCalendar as event}<article><time>{event.event_date}</time><strong>{event.title}</strong><span>{event.tag}</span><p>{event.summary}</p></article>{/each}</div>{:else}<p>{lang === 'id' ? 'Belum ada calendar event.' : 'No calendar events yet.'}</p>{/if}</div><div class="sky-list">{#each skyPosts as post}<article>{@render Icon(3)}<div><small>{post.tag}</small><h3>{post.title}</h3><p>{post.summary}</p><a href={`/berita-langit/${post.slug}`}>{lang === 'id' ? 'Buka article' : 'Open article'}</a></div></article>{/each}</div></section>{/if}
    {#if screen === 'hermes-chat'}<section class="card chat-page coming-soon"><div class="section-title"><span>☿</span><h2>{copy.hermexNav}</h2></div>{@render Icon(1, true)}<h3>{lang === 'id' ? 'Coming soon: tanya Hermes lebih detail' : 'Coming soon: ask Hermes for deeper detail'}</h3><p>{lang === 'id' ? 'Fitur chat detail akan dibuka setelah flow donasi/subscription siap. Untuk sekarang, gunakan Analisis Kosmik dan simpan profile publikmu dulu.' : 'Detailed chat opens after the donation/subscription flow is ready. For now, use Cosmic Analysis and save your public profile first.'}</p><button class="soft-action oracle-button" on:click={() => (profile ? screen = 'hermes' : screen = 'home')}>{profile ? copy.askHermes : copy.analyze}</button></section>{/if}
    {#if screen === 'terms'}<section class="card terms-page"><div class="section-title"><span>§</span><h2>{copy.termsTitle}</h2></div><p>{copy.termsIntro}</p><ol><li>{lang === 'id' ? 'Google login hanya dipakai untuk identitas akun dan sinkronisasi progres ketika fitur akun aktif.' : 'Google login is used only for account identity and progress sync when accounts are enabled.'}</li><li>{lang === 'id' ? 'Data lahir dan chart dipakai untuk membuat pengalaman Hermex, bukan untuk keputusan medis, finansial, hukum, atau hidup-kritis.' : 'Birth data and charts are used to power Hermex, not for medical, financial, legal, or life-critical decisions.'}</li><li>{lang === 'id' ? 'Versi self-hosted tetap bisa berjalan penuh dengan provider AI dan storage milik sendiri.' : 'Self-hosted versions can still run fully with your own AI provider and storage.'}</li><li>{lang === 'id' ? 'Versi hosted Hermex dapat menambahkan donasi atau langganan untuk fitur premium di masa depan.' : 'Hosted Hermex may add donation or subscription access for premium features later.'}</li></ol><div class="route-actions"><button class="soft-action" on:click={() => (screen = 'register')}>{copy.termsBack}</button><button class="soft-action oracle-button" on:click={acceptTerms}>G {copy.termsAccept}</button></div></section>{/if}
    {#if screen === 'register'}<section class="card register-page"><div class="section-title"><span>✦</span><h2>{copy.registerTitle}</h2></div><p>{copy.registerBody}</p><button class="google-action" on:click={startGoogleLogin}>G {copy.googleLogin}</button><div class="split"><input placeholder="Email" /><input placeholder="Nama" /></div><button class="primary-action" on:click={() => (screen = 'hermes')}>{copy.back}</button></section>{/if}
    <footer><p>{copy.ethics}</p><div class="legal-links"><a href="/terms">Terms</a><a href="/privacy">Privacy</a></div></footer>
  </section>
</main>

{#snippet Icon(kind: number, big = false)}<svg class:big viewBox="0 0 64 64"><circle cx="32" cy="32" r="25"/><path d={kind === 0 ? 'M32 10l5 16 17 1-14 10 5 17-13-10-13 10 5-17-14-10 17-1 5-16z' : kind === 1 ? 'M43 14a20 20 0 1 0 0 40 26 26 0 1 1 0-40z' : kind === 2 ? 'M17 44c8-22 22-30 38-22-5 20-18 29-38 22z' : 'M32 10l7 15 15 7-15 7-7 15-7-15-15-7 15-7 7-15z'} /></svg>{/snippet}
{#snippet Insight(title: string, items: string[], icon: string)}<article class="insight"><div><span>{icon}</span><h3>{title}</h3></div>{#if items.length}<ul>{#each items.slice(0, 4) as item}<li>{@html formatInsight(item)}</li>{/each}</ul>{:else}<p>-</p>{/if}</article>{/snippet}

<style>
  :global(:root){--ink:#45304f;--muted:#7f7184;--accent:#56ad91}:global(*){box-sizing:border-box}:global(body){margin:0;color:#45304f;background:radial-gradient(circle at 12% 8%,rgba(244,193,93,.5),transparent 22rem),radial-gradient(circle at 88% 16%,rgba(128,213,187,.42),transparent 24rem),linear-gradient(145deg,#fff8df,#f5e4ee 52%,#dff5ed);font-family:Avenir Next,Nunito,Trebuchet MS,sans-serif}.app-shell{min-height:100vh;padding:22px}.phone-frame{width:min(1080px,100%);margin:0 auto;border:5px solid rgba(69,48,79,.12);border-radius:38px;background:rgba(255,253,243,.88);box-shadow:0 30px 90px rgba(82,47,79,.16);padding:24px;position:relative;overflow:hidden}.phone-frame:before{content:'';position:absolute;inset:0;background-image:radial-gradient(circle,rgba(69,48,79,.07) 1px,transparent 1.5px);background-size:26px 26px;pointer-events:none}.topbar,.hero-card,.feature-row,.home-grid,.profile-grid,.loading-screen,.hermes-card,footer{position:relative;z-index:1}.topbar{display:flex;align-items:center;gap:12px;margin-bottom:18px}.brand{display:flex;align-items:center;gap:12px}.brand svg{width:54px;height:54px;border-radius:18px;background:#fff2aa;padding:8px;fill:#f4c15d;stroke:#45304f;stroke-width:3}.brand circle{fill:#45304f;stroke:none}.brand path:last-child{fill:none;stroke-linecap:round}.brand p{margin:0;color:#8f6884;font-size:.75rem;font-weight:850;letter-spacing:.1em;text-transform:uppercase}.brand strong{font-size:1.18rem}.lang,.ghost{margin-left:auto;border:0;border-radius:999px;padding:10px 14px;background:#45304f;color:#fff7cf;font-weight:900;cursor:pointer}.ghost{background:rgba(69,48,79,.1);color:#45304f}.ghost+.lang{margin-left:6px}.hero-card{display:grid;grid-template-columns:1fr 210px;gap:18px;align-items:center;padding:28px;border-radius:34px;background:linear-gradient(135deg,#fff0a8,#f4cbd5 56%,#c9f1e3);box-shadow:0 18px 48px rgba(126,79,109,.14)}.hero-card span{display:inline-flex;border-radius:999px;padding:8px 12px;background:rgba(255,255,255,.7);color:#805d78;font-size:.78rem;font-weight:900;text-transform:uppercase;letter-spacing:.08em}h1{margin:14px 0 12px;max-width:680px;font-size:clamp(2.25rem,7vw,5.2rem);line-height:.88;letter-spacing:-.07em;font-weight:950}.hero-card p{margin:0;color:rgba(69,48,79,.74);font-size:1.02rem;line-height:1.55;font-weight:730}.hero-card svg{width:100%}.hero-card circle:nth-child(-n+2){fill:none;stroke:rgba(69,48,79,.2);stroke-width:6;stroke-dasharray:9 11;animation:spin 24s linear infinite;transform-origin:center}.hero-card path:nth-child(3){fill:#fff8c7;stroke:#45304f;stroke-width:5}.hero-card circle:nth-child(n+4){fill:#80d5bb;stroke:#45304f;stroke-width:5}.hero-card path:last-child{fill:#f09d73;stroke:#45304f;stroke-width:5}.feature-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin:18px 0}.feature-row button{display:grid;grid-template-columns:42px 1fr;gap:8px;align-items:center;text-align:left;border:2px solid transparent;border-radius:22px;background:rgba(255,255,255,.72);padding:14px;color:#45304f;cursor:pointer}.feature-row button.active{border-color:#80d5bb;background:#f2fffa}.feature-row small{grid-column:2;color:#7f7184;font-weight:700}.home-grid,.profile-grid{display:grid;grid-template-columns:1.05fr .95fr;gap:18px}.home-grid.single{grid-template-columns:1fr}.learn-strip{position:relative;z-index:1;width:100%;border:0;border-radius:22px;margin:0 0 18px;padding:15px 18px;background:#fffdf7;color:#45304f;font-weight:950;box-shadow:0 12px 32px rgba(82,47,79,.08);cursor:pointer}.card{border:2px solid rgba(69,48,79,.11);border-radius:30px;background:rgba(255,255,255,.8);box-shadow:0 18px 45px rgba(82,47,79,.1);padding:22px}.section-title{display:flex;align-items:center;gap:10px;margin-bottom:18px}.section-title span{display:grid;place-items:center;width:34px;height:34px;border-radius:12px;background:#45304f;color:#fff7cf;font-weight:950}h2,h3{margin:0}.split{display:grid;grid-template-columns:1fr 1fr;gap:12px}label{display:grid;gap:7px;margin-bottom:13px;color:#6d4b79;font-weight:850}label small{color:#ad7aa0;font-size:.78rem}input{width:100%;border:2px solid rgba(69,48,79,.14);border-radius:18px;padding:14px 15px;background:#fffaf1;color:#45304f;font:800 1rem Avenir Next,sans-serif;outline:none}.city-picker{position:relative}.city-menu{position:absolute;z-index:6;left:0;right:0;top:calc(100% - 4px);display:grid;gap:6px;max-height:265px;overflow:auto;padding:8px;border:2px solid rgba(69,48,79,.12);border-radius:18px;background:#fffdf6;box-shadow:0 20px 40px rgba(69,48,79,.18)}.city-menu button{display:grid;gap:2px;text-align:left;border:0;border-radius:13px;padding:10px 12px;background:transparent;color:#45304f}.city-menu button:hover{background:#fff0d6}.city-menu small,.location-note{color:rgba(69,48,79,.62);font-size:.78rem;font-weight:750}.primary-action,.soft-action{display:inline-flex;align-items:center;justify-content:center;gap:10px;width:100%;border:0;border-radius:22px;padding:15px 18px;color:#fff7cf;background:#45304f;box-shadow:0 9px 0 #2d1f35,0 20px 28px rgba(69,48,79,.18);font-weight:900;font-size:1rem;cursor:pointer}.primary-action:disabled,.soft-action:disabled{opacity:.58;cursor:not-allowed}.soft-action{margin-top:16px;background:#f09d73;color:#45304f;box-shadow:0 8px 0 #c96d4c}.oracle-button{background:#80d5bb;box-shadow:0 8px 0 #56ad91}.active-feature{display:grid;place-items:center;text-align:center;align-content:center;background:linear-gradient(160deg,#f2f6ff,#fffdf7)}svg.big{width:150px;height:150px}.feature-row svg{width:42px;height:42px;max-width:42px;max-height:42px;min-width:42px;align-self:center;justify-self:center;fill:#fff2aa;stroke:#45304f;stroke-width:4}.active-feature svg{width:min(150px,44vw);height:auto;max-width:150px;fill:#fff2aa;stroke:#45304f;stroke-width:4}.feature-row svg path,.active-feature svg path{fill:#f09d73}.character-card{text-align:center}.natal-wheel{width:min(360px,100%);margin:0 auto 14px}.natal-wheel svg{width:100%;height:auto}.natal-wheel circle{fill:none;stroke:#45304f;stroke-width:2}.natal-wheel line{stroke:rgba(69,48,79,.28);stroke-width:1.5}.natal-wheel .aspect-line{stroke:#80d5bb;stroke-width:2;opacity:.9}.natal-wheel g circle{fill:#f4c15d;stroke:#45304f;stroke-width:2}.natal-wheel text{font-size:10px;text-anchor:middle;fill:#45304f;font-weight:900}.avatar{display:grid;place-items:center;width:118px;height:118px;margin:0 auto 12px;border-radius:34px;background:#fff0a8;color:#45304f;font-size:4rem}.dominant{display:inline-flex;margin:0 0 10px;padding:7px 12px;border-radius:999px;background:#f2e8f7;color:#6d4b79;font-weight:900;text-transform:uppercase}.meter{height:14px;border-radius:999px;background:rgba(69,48,79,.1);overflow:hidden}.meter span{display:block;height:100%;background:linear-gradient(90deg,#f09d73,#f4c15d,#80d5bb)}.chips{display:flex;flex-wrap:wrap;justify-content:center;gap:8px;margin-top:13px}.chips span{border:2px solid rgba(69,48,79,.1);border-radius:999px;background:#fff0a8;padding:8px 11px;color:#5c3a65;font-size:.83rem;font-weight:850}.planet-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.planet-grid div{border-radius:18px;background:#f7f3ea;padding:12px}.aspect-list{margin-top:14px;border-radius:22px;background:#f6f3ed;padding:14px}.aspect-list p{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin:8px 0;color:#5e5064;font-weight:760}.aspect-list small{color:#8b788f}.planet-grid strong{text-transform:capitalize;display:block}.planet-grid span,.planet-grid small{display:block;color:#75657a;font-weight:750}details{margin-top:12px;border-radius:18px;background:#f6f3ed;padding:12px}summary{cursor:pointer;font-weight:900}pre{max-height:220px;overflow:auto;white-space:pre-wrap;font-size:.8rem}.loading-screen{min-height:560px;display:grid;place-items:center;align-content:center;text-align:center;border-radius:32px;background:linear-gradient(135deg,rgba(255,240,168,.65),rgba(220,255,241,.78))}.loader{position:relative;width:180px;height:180px;display:grid;place-items:center}.loader:before{content:'';position:absolute;inset:18px;border:3px dashed rgba(69,48,79,.28);border-radius:50%;animation:spin 7s linear infinite}.loader span{position:absolute;width:28px;height:28px;border-radius:50%;background:#80d5bb;animation:float 1.7s ease-in-out infinite}.loader span:nth-child(1){left:18px;top:70px}.loader span:nth-child(2){right:22px;top:42px;background:#f4c15d}.loader span:nth-child(3){bottom:24px;right:54px;background:#f09d73}.loader strong{font-size:4rem;color:#45304f}.loading-screen .quote{min-height:34px;font-size:1.05rem;font-weight:900;color:#6d4b79;animation:fadeQuote 2.6s ease-in-out infinite}.loading-screen small{color:#7a6d7e;font-weight:760}.hermes-card{min-height:620px}.summary-card{display:grid;grid-template-columns:76px 1fr;gap:16px;align-items:start;border-radius:26px;background:linear-gradient(135deg,#fff0a8,#dcfff1);padding:18px}.summary-card svg{width:70px;fill:#fff2aa;stroke:#45304f;stroke-width:4}.summary-card svg path{fill:#f09d73}.summary-card p{margin:0;line-height:1.5;font-weight:780;color:rgba(69,48,79,.8)}.summary-card mark{background:linear-gradient(120deg,rgba(244,193,93,.55),rgba(128,213,187,.45));border-radius:10px;padding:2px 5px;color:#45304f}.summary-card span{color:#67566d}.insight-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:14px}.insight{border-radius:22px;background:#fffdf7;border:1px solid rgba(69,48,79,.1);padding:14px}.insight div{display:flex;align-items:center;gap:8px}.insight div span{display:grid;place-items:center;width:34px;height:34px;border-radius:12px;background:#f2e8f7}.insight ul{margin:10px 0 0;padding-left:18px;color:#6a5a70;font-weight:720}.timeline{margin-top:14px;border-radius:24px;background:#f6f3ed;padding:16px}.timeline>div{display:grid;grid-template-columns:90px 1fr;gap:12px;border-top:1px solid rgba(69,48,79,.1);padding:10px 0}.timeline span{font-weight:950;color:#80623e}.timeline p{margin:0;color:#67566d;font-weight:720;line-height:1.45}.text-link{margin-top:12px;border:0;border-radius:999px;background:#45304f;color:#fff8df;padding:10px 14px;font-weight:900;cursor:pointer}.feedback{margin-top:14px;border-radius:24px;background:#fffdf7;border:1px solid rgba(69,48,79,.1);padding:16px}.stars{display:flex;gap:6px;margin:10px 0}.stars button{border:0;background:transparent;color:#c8b8cb;font-size:2rem;cursor:pointer}.stars button.active{color:#f4c15d}.feedback textarea{width:100%;min-height:78px;border:1px solid rgba(69,48,79,.14);border-radius:16px;padding:12px;font:inherit}.route-actions{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:18px}.learn-page,.register-page,.terms-page{position:relative;z-index:1}.education-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}.education-grid button{border:1px solid rgba(69,48,79,.1);border-radius:24px;background:#fffdf7;padding:16px;text-align:left;color:#45304f;cursor:pointer;transition:transform .18s ease,border-color .18s ease}.education-grid button:hover,.education-grid button.active{transform:translateY(-2px);border-color:#80d5bb;background:#f2fffa}.education-grid svg,.education-detail svg{width:54px;height:54px;fill:#fff2aa;stroke:#45304f;stroke-width:4}.education-grid svg path,.education-detail svg path{fill:#f09d73}.education-grid p,.register-page p,.terms-page p,.education-detail p{color:#6d6072;font-weight:720;line-height:1.5}.education-detail{display:grid;grid-template-columns:110px 1fr;gap:18px;align-items:center;margin-top:14px;border-radius:28px;background:linear-gradient(135deg,#fff0a8,#dcfff1);padding:20px}.education-detail svg{width:96px;height:96px}.ai-error-page{position:relative;z-index:1}.error-visual{display:grid;grid-template-columns:120px 1fr;gap:18px;align-items:center;border-radius:28px;background:linear-gradient(135deg,#fff0a8,#f8d8d8);padding:22px}.error-visual svg{width:100px;height:100px;fill:#fff2aa;stroke:#45304f;stroke-width:4}.error-visual svg path{fill:#f09d73}.error-visual p{font-weight:850;color:#6d4b79;line-height:1.5}footer{position:relative;z-index:1;padding:18px 0 0;text-align:center;color:rgba(69,48,79,.58);font-weight:780}.error{color:#b3264c;font-weight:850}@keyframes spin{to{transform:rotate(360deg)}}@keyframes float{50%{transform:translateY(-10px)}}@keyframes fadeQuote{0%,100%{opacity:.35;transform:translateY(4px)}35%,75%{opacity:1;transform:translateY(0)}}@media(max-width:860px){.app-shell{padding:8px}.phone-frame{padding:14px;border-radius:30px}.hero-card,.home-grid,.profile-grid,.insight-grid,.route-actions,.education-grid{grid-template-columns:1fr}.feature-row{grid-template-columns:1fr 1fr}.planet-grid{grid-template-columns:1fr 1fr}.hero-card svg{max-width:180px;order:-1;margin:auto}}@media(max-width:560px){.feature-row,.split,.planet-grid,.timeline>div,.education-detail,.error-visual{grid-template-columns:1fr}.summary-card{grid-template-columns:1fr}.topbar{flex-wrap:wrap}}
button.brand { border: 0; background: transparent; color: inherit; padding: 0; text-align: left; cursor: pointer; }
.install-badge { display: none; width: 100%; margin: 14px 0; border: 0; border-radius: 24px; padding: 16px 18px; background: linear-gradient(135deg, #fff0a8, #cff7e8); color: var(--ink); font-weight: 950; box-shadow: 0 8px 0 rgba(47,36,55,.16); text-align: left; grid-template-columns: 1fr auto; align-items: center; gap: 10px; }
.install-badge.show { display: grid; }
.install-badge > button:first-child { border: 0; background: transparent; color: var(--ink); font: inherit; font-weight: 950; text-align: left; padding: 0; cursor: pointer; }
.install-badge small { display: block; margin-top: 4px; color: var(--muted); font-weight: 800; }
.install-close { width: 34px; height: 34px; border: 0; border-radius: 999px; background: rgba(69,48,79,.12); color: var(--ink); font-size: 22px; font-weight: 950; cursor: pointer; }
.field-hint { display: block; margin-top: 6px; color: var(--muted); font-size: .78rem; line-height: 1.35; }
.history-strip { margin-top: 10px; background: linear-gradient(135deg, #fffdf7, #effbf6); }
.share-action, .google-action { width: 100%; border: 0; border-radius: 999px; padding: 14px 18px; margin-top: 12px; background: #fffdf7; color: var(--ink); font-weight: 950; box-shadow: inset 0 0 0 2px rgba(47,36,55,.12), 0 6px 0 rgba(47,36,55,.12); }
.google-action { background: linear-gradient(135deg, #fff, #eef5ff); }
.bottom-nav { position: relative; z-index: 20; display: grid; grid-template-columns: repeat(4, minmax(92px, 1fr)); gap: 8px; width: min(640px, 100%); margin: -4px 0 18px auto; padding: 8px; border: 1px solid rgba(47,36,55,.1); border-radius: 28px; background: rgba(255,253,247,.86); backdrop-filter: blur(14px); box-shadow: 0 18px 44px rgba(47,36,55,.16); }
.bottom-nav button { border: 0; border-radius: 20px; padding: 10px 6px; background: transparent; color: var(--muted); font-weight: 950; display: grid; gap: 2px; place-items: center; }
.bottom-nav button.active { background: #4b3155; color: #fff8df; }
.bottom-nav span { font-size: .72rem; }
.history-list { display: grid; gap: 12px; }
.history-list button { border: 1px solid rgba(47,36,55,.12); border-radius: 22px; padding: 16px; background: #fffdf7; color: var(--ink); text-align: left; display: grid; gap: 4px; }
.history-list span, .history-list small { color: var(--muted); font-weight: 800; }
.history-entry { display: grid; grid-template-columns: 1fr auto; gap: 8px; align-items: stretch; }
.history-entry .delete-history { min-width: 104px; background: #fff0a8; color: var(--ink); text-align: center; place-items: center; font-weight: 950; }
.detail-list { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; margin: 14px 0; }
.detail-list article { border-radius: 20px; padding: 14px; background: rgba(255,253,247,.72); border: 1px solid rgba(47,36,55,.1); }
.detail-list p { margin: 6px 0 0; color: var(--muted); font-weight: 800; }
.education-grid button small { color: var(--accent); font-weight: 950; }
.chat-page textarea { width: 100%; min-height: 130px; border-radius: 22px; border: 1px solid rgba(47,36,55,.14); padding: 16px; font: inherit; box-sizing: border-box; }
.detail-answer { margin-top: 14px; display: grid; grid-template-columns: 58px 1fr; gap: 12px; align-items: start; border-radius: 24px; padding: 16px; background: linear-gradient(135deg, #fff6aa, #c9f7ed); }
.detail-answer p { margin: 0; line-height: 1.55; }
.share-link { margin-top: 10px; font-size: .78rem; }
.insight li strong { color: var(--ink); background: linear-gradient(180deg, transparent 55%, rgba(244,193,93,.35) 0); }
.offline-banner, .game-card { position: relative; z-index: 1; margin: 14px 0 18px; border: 2px solid rgba(69,48,79,.1); border-radius: 26px; padding: 16px; background: linear-gradient(135deg, #f2f6ff, #dcfff1); box-shadow: 0 14px 38px rgba(69,48,79,.08); }
.offline-banner { display: grid; gap: 4px; color: var(--ink); }
.offline-banner span { color: var(--muted); font-weight: 800; }
.game-card > div:first-child { display: grid; grid-template-columns: 64px 1fr; gap: 14px; align-items: center; }
.game-card svg { width: 58px; height: 58px; fill: #fff2aa; stroke: var(--ink); stroke-width: 4; }
.game-card svg path { fill: #f09d73; }
.game-card p { margin: 6px 0 0; color: var(--muted); font-weight: 800; }
.game-stats, .badge-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
.game-stats span, .badge-row span { border-radius: 999px; padding: 8px 11px; background: #fffdf7; color: var(--ink); font-weight: 950; box-shadow: inset 0 0 0 1px rgba(69,48,79,.1); }
.badge-row span { background: #fff0a8; }
.terms-page ol { margin: 16px 0 0; padding-left: 22px; color: var(--muted); font-weight: 820; line-height: 1.55; }
.account-page { position: relative; z-index: 1; }
.account-hero { border-radius: 26px; padding: 16px; background: linear-gradient(135deg, #fff0a8, #dcfff1); }
.account-id { display: flex; align-items: center; gap: 12px; }
.account-id img, .account-id > span { width: 54px; height: 54px; border-radius: 18px; object-fit: cover; background: #45304f; color: #fff8df; display: grid; place-items: center; font-weight: 950; font-size: 1.4rem; }
.account-id strong, .account-id small { display: block; }
.account-id small { color: var(--muted); font-weight: 850; margin-top: 2px; }
.account-grid { display: grid; grid-template-columns: .9fr 1.1fr; gap: 14px; margin-top: 14px; }
.account-grid article { border: 1px solid rgba(69,48,79,.1); border-radius: 24px; padding: 16px; background: #fffdf7; }
.chips.compact { justify-content: flex-start; }
.history-list.mini { margin-top: 10px; }
.history-list.mini button { padding: 12px; border-radius: 18px; }
.knowledge-nav { position: relative; z-index: 1; display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 18px; }
.knowledge-nav button { border: 1px solid rgba(69,48,79,.1); border-radius: 999px; padding: 15px 18px; background: #fffdf7; color: var(--ink); font-weight: 950; cursor: pointer; box-shadow: 0 12px 32px rgba(82,47,79,.08); }
.latest-sky { position: relative; z-index: 1; margin: 0 0 18px; border-radius: 28px; padding: 18px; background: linear-gradient(135deg, #fff0a8, #dcfff1); border: 1px solid rgba(69,48,79,.1); }
.latest-sky small { color: #8f6884; font-weight: 950; text-transform: uppercase; letter-spacing: .08em; }
.latest-sky p { color: var(--muted); font-weight: 820; }
.latest-sky a, .sky-list a { display: inline-flex; margin-top: 8px; border-radius: 999px; padding: 9px 13px; background: #45304f; color: #fff8df; text-decoration: none; font-weight: 950; }
.latest-sky.in-page { margin-top: 14px; }
.quest-form { overflow: visible; }
.quest-steps { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 16px; }
.quest-steps button { border: 1px solid rgba(69,48,79,.12); border-radius: 18px; padding: 10px; background: #fffdf7; color: var(--muted); font-weight: 950; cursor: pointer; }
.quest-steps button.active { background: #4b3155; color: #fff8df; }
.quest-steps span { display: inline-grid; place-items: center; width: 22px; height: 22px; margin-right: 6px; border-radius: 999px; background: rgba(244,193,93,.6); color: var(--ink); }
.takeaway-row { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; }
.takeaway-row span { border-radius: 999px; padding: 9px 12px; background: #fff0a8; color: var(--ink); font-weight: 950; }
.feedback-done { margin-top: 14px; border-radius: 999px; padding: 12px 16px; background: #dcfff1; color: var(--ink); font-weight: 950; text-align: center; }
.connect-grid, .sky-list, .calendar-list { display: grid; gap: 12px; margin-top: 14px; }
.connect-grid button { border: 1px solid rgba(69,48,79,.12); border-radius: 22px; background: #fffdf7; padding: 14px; text-align: left; color: var(--ink); cursor: pointer; }
.connect-grid strong, .connect-grid span, .connect-grid small { display: block; }
.connect-grid span, .connect-grid small { color: var(--muted); font-weight: 800; margin-top: 4px; }
.public-hero, .sky-list article { display: grid; grid-template-columns: 74px 1fr; gap: 14px; align-items: start; border: 1px solid rgba(69,48,79,.1); border-radius: 26px; padding: 16px; background: #fffdf7; }
.public-hero svg, .sky-list svg { width: 58px; height: 58px; fill: #fff2aa; stroke: var(--ink); stroke-width: 4; }
.public-hero svg path, .sky-list svg path { fill: #f09d73; }
.summary-card.mini { margin-top: 14px; grid-template-columns: 54px 1fr; }
.sky-list small { color: var(--accent); font-weight: 950; text-transform: uppercase; letter-spacing: .08em; }
.sky-list details { background: rgba(69,48,79,.05); }
.calendar-card { margin-top: 14px; border-radius: 26px; padding: 16px; background: #fffdf7; border: 1px solid rgba(69,48,79,.1); }
.calendar-list article { border-radius: 20px; padding: 14px; background: rgba(69,48,79,.05); }
.calendar-list time, .calendar-list span { display: inline-flex; margin-right: 8px; color: var(--muted); font-weight: 900; }
.calendar-list strong { display: block; margin: 6px 0; }
.coming-soon { display: grid; justify-items: center; text-align: center; gap: 12px; }
.coming-soon svg { width: 110px; height: 110px; fill: #fff2aa; stroke: var(--ink); stroke-width: 4; }
.coming-soon svg path { fill: #f09d73; }
footer p { margin: 0 0 8px; }
.legal-links { display: flex; justify-content: center; gap: 12px; }
.legal-links a { color: var(--ink); font-weight: 950; text-decoration: none; }
.legal-links a:hover { text-decoration: underline; }
@media (max-width: 720px) { .bottom-nav { position: fixed; left: 14px; right: 14px; bottom: 10px; width: auto; margin: 0; grid-template-columns: repeat(4, 1fr); } .install-badge.show { position: fixed; left: 14px; right: 14px; bottom: 92px; width: auto; z-index: 24; margin: 0; } .phone-frame { padding-bottom: 184px; } .account-grid, .knowledge-nav, .quest-steps, .public-hero, .sky-list article, .history-entry { grid-template-columns: 1fr; } }
@media (max-width: 720px) {
  :global(body) { background: linear-gradient(165deg, #fff8df 0%, #f8e8ee 46%, #e2f7ef 100%); }
  .app-shell { padding: 0; }
  .phone-frame { min-height: 100vh; border: 0; border-radius: 0; padding: 14px 14px calc(176px + env(safe-area-inset-bottom)); box-shadow: none; background: rgba(255,253,243,.94); overflow: visible; }
  .topbar { position: sticky; top: 0; z-index: 30; margin: -14px -14px 12px; padding: 12px 14px 10px; background: linear-gradient(180deg, rgba(255,253,243,.98), rgba(255,253,243,.86)); backdrop-filter: blur(16px); border-bottom: 1px solid rgba(69,48,79,.08); }
  .brand { min-width: 0; flex: 1; }
  .brand svg { width: 46px; height: 46px; border-radius: 16px; flex: 0 0 auto; }
  .brand p { font-size: .64rem; letter-spacing: .08em; }
  .brand strong { display: block; max-width: 170px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 1.02rem; }
  .ghost, .lang { padding: 9px 12px; min-height: 40px; }
  .hero-card { grid-template-columns: 1fr; gap: 14px; padding: 22px 20px; border-radius: 30px; min-height: auto; }
  .hero-card svg { width: 140px; max-width: 44vw; order: -1; justify-self: center; }
  .hero-card span { font-size: .68rem; padding: 7px 10px; }
  h1 { font-size: clamp(2.35rem, 14vw, 3.7rem); line-height: .9; letter-spacing: -.075em; margin: 12px 0 10px; }
  .hero-card p { font-size: .95rem; line-height: 1.45; }
  .feature-row { grid-template-columns: 1fr; gap: 10px; margin: 14px 0; }
  .feature-row button { min-height: 74px; grid-template-columns: 48px 1fr; border-radius: 24px; padding: 13px 14px; background: rgba(255,255,255,.82); box-shadow: 0 10px 26px rgba(82,47,79,.07); }
  .feature-row svg { width: 42px; height: 42px; }
  .feature-row small { font-size: .76rem; line-height: 1.28; }
  .learn-strip { margin-bottom: 12px; padding: 14px 16px; border-radius: 20px; }
  .card, .offline-banner, .game-card, .latest-sky, .calendar-card { border-radius: 26px; padding: 18px; }
  .section-title { margin-bottom: 14px; align-items: flex-start; }
  .section-title span { width: 32px; height: 32px; border-radius: 11px; flex: 0 0 auto; }
  .section-title h2 { font-size: 1.55rem; line-height: 1.05; }
  .quest-steps { display: flex; gap: 8px; overflow-x: auto; padding: 0 0 4px; scroll-snap-type: x mandatory; }
  .quest-steps button { min-width: 148px; scroll-snap-align: start; text-align: left; }
  .split { grid-template-columns: 1fr; gap: 0; }
  label { margin-bottom: 14px; gap: 6px; }
  input, .chat-page textarea, .feedback textarea { min-height: 54px; border-radius: 18px; font-size: 16px; padding: 14px 15px; }
  .city-menu { position: fixed; left: 14px; right: 14px; top: auto; bottom: calc(102px + env(safe-area-inset-bottom)); max-height: 45vh; border-radius: 24px; padding: 10px; z-index: 40; }
  .primary-action, .soft-action, .share-action, .google-action { min-height: 54px; border-radius: 20px; padding: 14px 16px; }
  .route-actions { grid-template-columns: 1fr; gap: 10px; }
  .route-actions .soft-action { margin-top: 0; }
  .game-card > div:first-child, .summary-card, .detail-answer, .public-hero, .sky-list article { grid-template-columns: 54px 1fr; gap: 12px; }
  .summary-card { padding: 16px; border-radius: 24px; }
  .summary-card svg, .public-hero svg, .sky-list svg, .game-card svg { width: 50px; height: 50px; }
  .insight-grid, .education-grid, .planet-grid, .account-grid, .knowledge-nav { grid-template-columns: 1fr; }
  .timeline { padding: 14px; }
  .timeline > div { grid-template-columns: 64px 1fr; gap: 10px; }
  .timeline p, .insight li, .education-grid p, .connect-grid span, .connect-grid small { line-height: 1.42; }
  .natal-wheel { width: min(310px, 100%); }
  .loading-screen { min-height: 68vh; border-radius: 28px; padding: 24px 18px; }
  .loader { width: 150px; height: 150px; }
  .bottom-nav { left: 12px; right: 12px; bottom: calc(10px + env(safe-area-inset-bottom)); grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 4px; padding: 7px; border-radius: 26px; background: rgba(255,253,247,.94); }
  .bottom-nav button { min-width: 0; min-height: 58px; border-radius: 20px; padding: 8px 3px; font-size: 1rem; }
  .bottom-nav span { max-width: 72px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: .68rem; }
  .install-badge.show { left: 12px; right: 12px; bottom: calc(88px + env(safe-area-inset-bottom)); padding: 13px 14px; border-radius: 22px; box-shadow: 0 10px 28px rgba(69,48,79,.18); }
  .install-badge small { font-size: .76rem; line-height: 1.3; }
  .install-close { width: 32px; height: 32px; }
  footer { padding-bottom: 8px; }
}
@media (max-width: 390px) {
  .phone-frame { padding-left: 10px; padding-right: 10px; }
  .topbar { margin-left: -10px; margin-right: -10px; padding-left: 10px; padding-right: 10px; }
  .brand strong { max-width: 132px; }
  h1 { font-size: clamp(2.1rem, 15vw, 3.1rem); }
  .hero-card, .card, .offline-banner, .game-card, .latest-sky, .calendar-card { padding: 16px; }
  .feature-row button { grid-template-columns: 42px 1fr; }
  .bottom-nav { left: 8px; right: 8px; }
  .bottom-nav span { font-size: .62rem; max-width: 58px; }
  .install-badge.show { left: 8px; right: 8px; }
}
</style>
