<script lang="ts">
  import { onMount } from 'svelte';
  import NatalChartWheel from '$lib/components/NatalChartWheel.svelte';
  import { getPublicProfile } from '$lib/api/hermex';
  export let data: any;

  let refreshedProfile: any = null;
  let refreshError = '';
  $: profile = refreshedProfile ?? data.publicProfile;
  $: error = refreshError || data.error;
  $: chart = profile?.profile?.chart_highlights ?? {};
  $: traits = profile?.profile?.traits ?? {};
  $: planets = normalizePlanets(chart.planets);
  $: aspects = Array.isArray(chart.aspects) ? chart.aspects : Array.isArray(chart.major_aspects) ? chart.major_aspects : [];
  $: angles = Object.entries(chart.angles ?? {}) as [string, unknown][];
  $: houseCusps = Array.isArray(chart.house_cusps) ? chart.house_cusps : [];
  $: interests = [...(traits.interests ?? []), ...(traits.talents ?? [])].filter(Boolean).slice(0, 3);

  onMount(async () => {
    if (!data.username) return;
    try { refreshedProfile = await getPublicProfile(data.username); refreshError = ''; } catch { /* Keep the public/private server state. */ }
  });

  function normalizePlanets(value: unknown): any[] {
    if (Array.isArray(value)) return value;
    if (!value || typeof value !== 'object') return [];
    return Object.entries(value).map(([name, planet]) => ({ name, ...(planet as object) }));
  }

  function title(value: unknown): string {
    const text = String(value ?? '-').replaceAll('_', ' ');
    return `${text.charAt(0).toUpperCase()}${text.slice(1)}`;
  }

  function degree(value: unknown): string {
    const number = Number(value);
    return Number.isFinite(number) ? `${number.toFixed(2)}°` : '-';
  }

  function angleText(value: unknown): string {
    if (!value || typeof value !== 'object') return degree(value);
    const angle = value as Record<string, unknown>;
    const sign = title(angle.zodiac_sign ?? angle.sign ?? '');
    const position = degree(angle.degree_in_sign ?? angle.longitude ?? angle.degree);
    return sign && sign !== '-' ? `${sign} ${position}` : position;
  }

  function aspectText(aspect: any): string {
    return `${title(aspect?.left ?? aspect?.left_planet)} ${title(aspect?.type ?? aspect?.aspect)} ${title(aspect?.right ?? aspect?.right_planet)}`;
  }
</script>

<svelte:head>
  <title>{profile?.username ? `Natal chart @${profile.username} · Hermex` : 'Natal chart · Hermex'}</title>
  <meta name="description" content="Kartu Karakter dan Chart Explorer Hermex." />
</svelte:head>

<main>
  <nav><a href="/">☆ hermex.fun</a><a href={profile?.username ? `/${profile.username}` : '/'}>← Kembali ke profil</a></nav>

  {#if error || !profile}
    <section class="empty"><span aria-hidden="true">◎</span><h1>{error || 'Natal chart belum tersedia'}</h1><p>Hasil lengkap hanya dapat dibuka jika pemilik mengizinkannya.</p><a href="/">Buat analisismu</a></section>
  {:else}
    <header class="hero">
      <p>Detail natal chart</p>
      <h1>Kartu langit saat @{profile.username} lahir</h1>
      <span>Posisi ini dipakai sebagai salah satu bahan untuk membaca kepribadian di Hermex.</span>
    </header>

    <section class="character-card" aria-labelledby="character-title">
      <div class="wheel"><NatalChartWheel {planets} {aspects} label={`Natal chart @${profile.username}`} /></div>
      <div class="character-copy">
        <p class="eyebrow">✦ Kartu Karakter</p>
        <h2 id="character-title">Pola dasar chart</h2>
        {#if traits.dominant_element}<div class="element">{title(traits.dominant_element)}</div>{/if}
        {#if traits.confidence?.label || traits.confidence}<p class="confidence">Tingkat keyakinan data: {title(traits.confidence?.label ?? traits.confidence)}</p>{/if}
        {#if interests.length}<ul>{#each interests as item}<li>{item}</li>{/each}</ul>{/if}
      </div>
    </section>

    <section class="explorer" aria-labelledby="explorer-title">
      <div class="heading"><p class="eyebrow">◎ Chart Explorer</p><h2 id="explorer-title">Lihat setiap posisi</h2></div>
      {#if planets.length}
        <div class="planet-grid">
          {#each planets as planet}
            <article><span>{String(planet.name ?? '').slice(0, 2)}</span><div><h3>{title(planet.name)}</h3><p>{title(planet.zodiac_sign)} {degree(planet.degree_in_sign)}</p><small>House {planet.house ?? '-'}</small></div></article>
          {/each}
        </div>
      {:else}<p>Data posisi belum tersedia.</p>{/if}

      {#if aspects.length}
        <div class="metric"><h3>Aspek utama</h3><ul>{#each aspects as aspect}<li>{aspectText(aspect)}{#if Number.isFinite(Number(aspect.orb))}<small>orb {Number(aspect.orb).toFixed(2)}°</small>{/if}</li>{/each}</ul></div>
      {:else if chart.aspects_count}
        <div class="metric"><h3>Aspek utama</h3><p>{chart.aspects_count} hubungan antarposisi terhitung.</p></div>
      {/if}

      {#if angles.length || houseCusps.length}
        <div class="metric chart-grid">
          {#if angles.length}<div><h3>Sudut utama</h3><ul>{#each angles as [name, value]}<li><span>{title(name)}</span><strong>{angleText(value)}</strong></li>{/each}</ul></div>{/if}
          {#if houseCusps.length}<div><h3>House cusps</h3><ul>{#each houseCusps as cusp, index}<li><span>House {index + 1}</span><strong>{degree(cusp)}</strong></li>{/each}</ul></div>{/if}
        </div>
      {/if}

      <div class="metrics">
        {#if chart.house_system}<article><small>Sistem rumah</small><strong>{title(chart.house_system)}</strong></article>{/if}
        {#if chart.chart_ruler}<article><small>Chart ruler</small><strong>{title(chart.chart_ruler?.planet ?? chart.chart_ruler)}</strong></article>{/if}
        {#if chart.overall_pattern?.dominant_modality}<article><small>Modalitas dominan</small><strong>{title(chart.overall_pattern.dominant_modality)}</strong></article>{/if}
        {#if chart.overall_pattern?.dominant_planet}<article><small>Planet dominan</small><strong>{title(chart.overall_pattern.dominant_planet)}</strong></article>{/if}
        {#if chart.overall_pattern?.dominant_element}<article><small>Elemen dominan</small><strong>{title(chart.overall_pattern.dominant_element)}</strong></article>{/if}
        {#if chart.angular_and_dominant_houses?.dominant_houses?.length}<article><small>Rumah dominan</small><strong>{chart.angular_and_dominant_houses.dominant_houses.map((item: any) => `House ${item.house}`).join(', ')}</strong></article>{/if}
      </div>
    </section>
  {/if}
</main>

<style>
  :global(*) { box-sizing: border-box; }
  :global(body) { margin: 0; background: #fbf8f1; color: #302a36; font-family: Inter, Avenir Next, system-ui, sans-serif; }
  main { width: min(980px, calc(100% - 36px)); margin: 0 auto; padding: 24px 0 72px; }
  nav { display: flex; justify-content: space-between; align-items: center; padding-bottom: 30px; border-bottom: 1px solid #e7e1d9; }
  nav a { color: #302a36; font-weight: 850; text-decoration: none; }
  .hero { max-width: 760px; padding: clamp(54px, 9vw, 96px) 0 42px; }
  .hero p, .eyebrow { margin: 0 0 10px; color: #5b55d6; font-size: .78rem; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; }
  h1 { margin: 0; font-size: clamp(2.4rem, 7vw, 5.3rem); line-height: .94; letter-spacing: -.065em; }
  .hero span { display: block; margin-top: 24px; color: #6d6673; font-size: 1.08rem; line-height: 1.65; }
  .character-card { display: grid; grid-template-columns: minmax(280px, .9fr) minmax(0,1.1fr); gap: clamp(28px, 7vw, 72px); align-items: center; border: 1px solid #ded9d1; border-radius: 32px; padding: clamp(26px, 5vw, 56px); background: #fff; box-shadow: 0 22px 55px rgba(48,42,54,.07); }
  .wheel { border-radius: 50%; padding: 8px; background: #f7f5ff; }
  h2 { margin: 0; font-size: clamp(1.8rem, 4vw, 3.2rem); line-height: 1; letter-spacing: -.05em; }
  .element { display: inline-flex; margin-top: 22px; border-radius: 999px; padding: 9px 14px; background: #f2efff; color: #5b55d6; font-weight: 900; text-transform: uppercase; }
  .confidence { margin: 17px 0 0; color: #716a78; line-height: 1.5; }
  .character-copy ul { display: flex; flex-wrap: wrap; gap: 8px; margin: 22px 0 0; padding: 0; list-style: none; }
  .character-copy li { border-radius: 999px; padding: 9px 13px; background: #fff0ca; color: #57452e; font-size: .84rem; font-weight: 800; }
  .explorer { margin-top: 42px; border: 1px solid #ded9d1; border-radius: 32px; padding: clamp(24px, 5vw, 48px); background: #fff; }
  .heading { margin-bottom: 28px; }
  .planet-grid { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 12px; }
  .planet-grid article { display: grid; grid-template-columns: 42px minmax(0,1fr); gap: 14px; align-items: center; border-radius: 18px; padding: 18px; background: #f5f3ef; }
  .planet-grid article > span { display: grid; width: 42px; height: 42px; place-items: center; border-radius: 13px; background: #fff0ca; color: #5b55d6; font-size: .75rem; font-weight: 900; text-transform: uppercase; }
  h3, .planet-grid p { margin: 0; }
  .planet-grid h3 { font-size: 1.04rem; }
  .planet-grid p { margin-top: 3px; color: #615a67; }
  .planet-grid small { color: #817985; }
  .metric { margin-top: 30px; border-top: 1px solid #e7e1d9; padding-top: 28px; }
  .metric ul { display: grid; gap: 8px; margin: 16px 0 0; padding: 0; list-style: none; }
  .metric li { display: flex; justify-content: space-between; gap: 16px; border-radius: 12px; padding: 12px 14px; background: #f5f3ef; }
  .chart-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 24px; }
  .metrics { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 10px; margin-top: 24px; }
  .metrics article { border: 1px solid #e7e1d9; border-radius: 15px; padding: 15px; }
  .metrics small, .metrics strong { display: block; }
  .metrics small { margin-bottom: 4px; color: #7d7581; }
  .empty { display: grid; justify-items: center; padding: 20vh 20px 0; text-align: center; }
  .empty > span { color: #5b55d6; font-size: 3rem; }
  .empty p { color: #716a78; }
  .empty a { border-radius: 14px; padding: 13px 18px; background: #5b55d6; color: #fff; font-weight: 850; text-decoration: none; }
  a:focus-visible { outline: 3px solid #5b55d6; outline-offset: 3px; }
  @media (max-width: 680px) { main { width: min(100% - 28px, 980px); } .character-card, .planet-grid, .chart-grid { grid-template-columns: 1fr; } .wheel { width: min(340px, 88vw); margin: auto; } .metrics { grid-template-columns: 1fr; } }
  @media (max-width: 420px) { nav a:first-child { font-size: .9rem; } nav a:last-child { font-size: .8rem; } .explorer { padding-inline: 18px; } }
</style>
