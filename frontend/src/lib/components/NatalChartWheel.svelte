<script lang="ts">
  export let planets: any[] = [];
  export let aspects: any[] = [];
  export let label = 'Natal chart';

  const signs = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'];
  const short: Record<string, string> = { sun: 'su', moon: 'mo', mercury: 'me', venus: 've', mars: 'ma', jupiter: 'ju', saturn: 'sa', uranus: 'ur', neptune: 'ne', pluto: 'pl', true_node: 'no', lilith: 'li' };

  function point(planet: any, radius = 98) {
    const sign = signs.findIndex((item) => item.toLowerCase() === String(planet?.zodiac_sign ?? '').toLowerCase());
    if (sign < 0) return null;
    const longitude = sign * 30 + Number(planet?.degree_in_sign ?? 0);
    const angle = (longitude - 90) * Math.PI / 180;
    return { x: 140 + Math.cos(angle) * radius, y: 140 + Math.sin(angle) * radius };
  }

  function aspectPlanet(aspect: any, side: 'left' | 'right') {
    const name = String(aspect?.[side] ?? aspect?.[`${side}_planet`] ?? '').toLowerCase();
    return planets.find((planet) => String(planet?.name ?? '').toLowerCase() === name);
  }
</script>

<svg viewBox="0 0 280 280" role="img" aria-label={label}>
  <circle cx="140" cy="140" r="118" fill="#fff" stroke="#302a36" stroke-width="2" />
  <circle cx="140" cy="140" r="88" fill="#fbf8f1" stroke="#302a36" stroke-width="1.5" />
  <circle cx="140" cy="140" r="48" fill="#fff" stroke="#302a36" stroke-width="1.5" />
  {#each Array(12) as _, index}
    {@const angle = (index * 30 - 90) * Math.PI / 180}
    <line x1={140 + Math.cos(angle) * 88} y1={140 + Math.sin(angle) * 88} x2={140 + Math.cos(angle) * 118} y2={140 + Math.sin(angle) * 118} stroke="#d8d2ca" stroke-width="1" />
  {/each}
  {#each aspects as aspect}
    {@const left = aspectPlanet(aspect, 'left')}
    {@const right = aspectPlanet(aspect, 'right')}
    {#if left && right && point(left, 88) && point(right, 88)}
      {@const a = point(left, 88)}
      {@const b = point(right, 88)}
      <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#65cdb8" stroke-width="1.2" opacity=".72" />
    {/if}
  {/each}
  {#each planets as planet}
    {@const position = point(planet)}
    {#if position}
      <circle cx={position.x} cy={position.y} r="9" fill="#f1b86a" stroke="#302a36" stroke-width="1.5" />
      <text x={position.x} y={position.y - 13} fill="#302a36" font-size="9" font-weight="800" text-anchor="middle">{short[String(planet?.name ?? '').toLowerCase()] ?? String(planet?.name ?? '').slice(0, 2)}</text>
    {/if}
  {/each}
</svg>

<style>
  svg { display: block; width: 100%; height: auto; }
</style>
