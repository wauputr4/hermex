<script lang="ts">
  export let profile: unknown = {};

  let copied: 'data' | 'prompt' | '' = '';
  let copyError = '';

  $: chart = (profile as any)?.chart_highlights ?? (profile as any)?.chart ?? {};
  $: planets = normalizePlanets(chart.planets);
  $: rawResult = formatChart(chart, planets);
  $: aiPrompt = `Bantu saya membaca natal chart berikut dengan bahasa sederhana. Hubungkan pola yang berulang antara planet, rumah, aspek, sudut, dan pola dominan yang tersedia. Jelaskan kekuatan, tarik-menarik dalam diri, serta pertanyaan refleksi yang bisa saya renungkan. Jangan menjadikannya diagnosis atau kepastian tentang masa depan.\n\nData natal chart:\n${rawResult}`;
  $: chatGptUrl = `https://chatgpt.com/?q=${encodeURIComponent(aiPrompt)}`;

  function normalizePlanets(value: unknown): any[] {
    if (Array.isArray(value)) return value;
    if (!value || typeof value !== 'object') return [];
    return Object.entries(value).map(([name, planet]) => ({ name, ...(planet as object) }));
  }

  function formatPlanet(planet: any): string {
    const name = String(planet?.name ?? 'planet').replaceAll('_', ' ');
    const sign = String(planet?.zodiac_sign ?? '-');
    const degree = Number(planet?.degree_in_sign);
    const house = planet?.house ?? '-';
    const degreeText = Number.isFinite(degree) ? `${degree.toFixed(2)}°` : '-';
    const longitude = Number(planet?.longitude);
    const extras = [
      Number.isFinite(longitude) ? `longitude ${longitude.toFixed(2)}°` : '',
      planet?.element ? `element ${title(planet.element)}` : '',
      planet?.modality ? `modality ${title(planet.modality)}` : ''
    ].filter(Boolean);
    return `${name[0]?.toUpperCase() ?? ''}${name.slice(1)}: ${sign} ${degreeText}, House ${house}${extras.length ? `, ${extras.join(', ')}` : ''}`;
  }

  function formatAspect(aspect: any): string {
    const left = aspect?.left ?? aspect?.left_planet ?? '?';
    const right = aspect?.right ?? aspect?.right_planet ?? '?';
    const type = aspect?.type ?? aspect?.aspect ?? '-';
    const orb = Number(aspect?.orb);
    return `${title(left)} — ${title(type)} — ${title(right)}${Number.isFinite(orb) ? ` (orb ${orb.toFixed(2)}°)` : ''}`;
  }

  function title(value: unknown): string {
    const text = String(value ?? '-').replaceAll('_', ' ');
    return `${text.charAt(0).toUpperCase()}${text.slice(1)}`;
  }

  function formatObject(value: unknown, prefix = ''): string[] {
    if (value === null || value === undefined || value === '') return [];
    if (Array.isArray(value)) return value.flatMap((item, index) => formatObject(item, `${prefix}${prefix ? ' ' : ''}${index + 1}`));
    if (typeof value !== 'object') return [`${title(prefix)}: ${title(value)}`];
    return Object.entries(value).flatMap(([key, item]) => formatObject(item, prefix ? `${prefix} · ${key}` : key));
  }

  function formatChart(value: any, planetList: any[]): string {
    const sections: string[] = [];
    if (planetList.length) sections.push(`PLANET & RUMAH\n${planetList.map(formatPlanet).join('\n')}`);
    const angles = value?.angles ?? value?.house_angles;
    const angleLines = formatObject(angles);
    if (angleLines.length) sections.push(`SUDUT UTAMA\n${angleLines.join('\n')}`);
    const cusps = value?.houses?.cusps ?? value?.house_cusps;
    if (Array.isArray(cusps) && cusps.length) sections.push(`HOUSE CUSPS\n${cusps.map((item, index) => `House ${index + 1}: ${title(item)}`).join('\n')}`);
    const aspects = Array.isArray(value?.aspects) ? value.aspects : Array.isArray(value?.major_aspects) ? value.major_aspects : [];
    if (aspects.length) sections.push(`ASPEK UTAMA\n${aspects.map(formatAspect).join('\n')}`);
    else if (Number.isFinite(Number(value?.aspects_count))) sections.push(`ASPEK UTAMA\nJumlah aspek terhitung: ${value.aspects_count}`);
    const ruler = value?.chart_ruler;
    if (ruler) sections.push(`CHART RULER\n${formatObject(ruler).join('\n') || title(ruler)}`);
    const patterns = value?.overall_pattern ?? value?.dominant_patterns ?? value?.patterns;
    const patternLines = formatObject(patterns);
    if (patternLines.length) sections.push(`POLA DOMINAN\n${patternLines.join('\n')}`);
    const angular = formatObject(value?.angular_and_dominant_houses);
    if (angular.length) sections.push(`PLANET ANGULAR & RUMAH DOMINAN\n${angular.join('\n')}`);
    if (value?.house_system) sections.push(`SISTEM RUMAH\n${title(value.house_system)}`);
    return sections.join('\n\n');
  }

  async function copyText(value: string, type: 'data' | 'prompt') {
    copyError = '';
    try {
      if (!navigator.clipboard) throw new Error('Clipboard unavailable');
      await navigator.clipboard.writeText(value);
      copied = type;
      window.setTimeout(() => (copied = ''), 1800);
    } catch {
      copyError = 'Belum bisa menyalin. Pilih teksnya lalu salin manual.';
    }
  }
</script>

<section class="raw-export" aria-labelledby="raw-result-title">
  <div class="heading">
    <span class="icon" aria-hidden="true">
      <svg viewBox="0 0 24 24"><path d="M8 7h9M8 12h9M8 17h6M5 4v16M19 4v16" /></svg>
    </span>
    <div>
      <p>Data hasilmu</p>
      <h2 id="raw-result-title">Bawa hasil ini ke mana saja</h2>
    </div>
  </div>
  <p class="intro">Salin highlight chart untuk disimpan sendiri, atau buka di ChatGPT untuk membantu membaca polanya.</p>

  <pre>{rawResult || 'Data chart belum tersedia.'}</pre>

  <div class="actions">
    <button type="button" on:click={() => copyText(rawResult, 'data')}>
      <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="8" y="8" width="11" height="11" rx="2" /><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2" /></svg>
      {copied === 'data' ? 'Sudah disalin' : 'Salin hasil'}
    </button>
    <a href={chatGptUrl} target="_blank" rel="noreferrer">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3a4.5 4.5 0 0 1 4.3 3.2 4.5 4.5 0 0 1 2.7 7.9 4.5 4.5 0 0 1-7 5.3 4.5 4.5 0 0 1-7.3-4.6A4.5 4.5 0 0 1 7 6.1 4.5 4.5 0 0 1 12 3Z" /><path d="m9 8 6 3.5v7M15 8.5 9 12v7M6.5 11.5 12 15l5.5-3.3" /></svg>
      Open in ChatGPT
    </a>
  </div>
  <div class="prompt-block">
    <h3>Prompt untuk bertanya ke AI</h3>
    <pre>{aiPrompt}</pre>
    <button class="copy-prompt" type="button" on:click={() => copyText(aiPrompt, 'prompt')}>{copied === 'prompt' ? 'Prompt tersalin' : 'Salin prompt'}</button>
  </div>
  <small>Hanya bagikan data yang nyaman kamu bagikan. ChatGPT adalah layanan terpisah dari Hermex.</small>
  <p class="copy-error" aria-live="polite">{copyError}</p>
</section>

<style>
  .raw-export { margin-top: 32px; border: 1px solid #e7e1d9; border-radius: 24px; padding: clamp(20px, 4vw, 34px); background: #fff; color: #302a36; }
  .heading { display: flex; gap: 14px; align-items: center; }
  .icon { display: grid; flex: 0 0 44px; height: 44px; place-items: center; border-radius: 14px; background: #fff0ce; color: #5b55d6; }
  .icon svg, .actions svg { width: 21px; fill: none; stroke: currentColor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 1.8; }
  p, h2 { margin: 0; }
  .heading p { color: #5b55d6; font-size: .72rem; font-weight: 820; letter-spacing: .1em; text-transform: uppercase; }
  h2 { margin-top: 2px; font-size: clamp(1.35rem, 3vw, 1.8rem); letter-spacing: -.025em; }
  .intro { max-width: 670px; margin: 18px 0; color: #615968; line-height: 1.65; }
  pre { max-height: 280px; overflow: auto; margin: 0; border-radius: 16px; padding: 18px; background: #f5f3ef; color: #413a48; font: 500 .78rem/1.65 ui-monospace, SFMono-Regular, Menlo, monospace; white-space: pre-wrap; overflow-wrap: anywhere; }
  .actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }
  .actions button, .actions a { display: inline-flex; min-height: 44px; align-items: center; justify-content: center; gap: 9px; border: 1px solid #5b55d6; border-radius: 12px; padding: 0 16px; color: #5b55d6; background: #fff; font: inherit; font-size: .88rem; font-weight: 760; text-decoration: none; cursor: pointer; }
  .actions button { background: #5b55d6; color: #fff; }
  .actions button:focus-visible, .actions a:focus-visible { outline: 3px solid rgba(91,85,214,.25); outline-offset: 3px; }
  small { display: block; margin-top: 14px; color: #7d7581; font-size: .76rem; line-height: 1.5; }
  .prompt-block { margin-top: 24px; padding-top: 22px; border-top: 1px solid #e7e1d9; }
  .prompt-block h3 { margin: 0 0 10px; font-size: 1rem; }
  .copy-error { min-height: 1.25em; margin: 8px 0 0; color: #a33c52; font-size: .78rem; font-weight: 700; }
  .copy-prompt { min-height: 42px; margin-top: 10px; border: 1px solid #5b55d6; border-radius: 12px; padding: 0 15px; background: #fff; color: #5b55d6; font: inherit; font-size: .86rem; font-weight: 760; cursor: pointer; }
  @media (max-width: 520px) { .actions > * { flex: 1 1 100%; } }
</style>
