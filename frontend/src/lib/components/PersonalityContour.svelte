<script lang="ts">
  export let values: number[] = [];
  export let label = 'Kontur kepribadian';

  const count = 10;
  $: normalized = Array.from({ length: count }, (_, index) => Math.max(1, Math.min(5, Number(values[index] ?? 3))));
  $: points = normalized.map((value, index) => {
    const angle = (Math.PI * 2 * index) / count - Math.PI / 2;
    const radius = 36 + value * 10;
    return `${100 + Math.cos(angle) * radius},${100 + Math.sin(angle) * radius}`;
  }).join(' ');
</script>

<svg class="contour" viewBox="0 0 200 200" role="img" aria-label={label}>
  <circle cx="100" cy="100" r="86" fill="none" stroke="#5b55d6" stroke-width="1.5" />
  {#each [36, 56, 76] as radius}
    <circle cx="100" cy="100" r={radius} fill="none" stroke="#e7e1d9" stroke-width="1" />
  {/each}
  {#each normalized as _, index}
    {@const angle = (Math.PI * 2 * index) / count - Math.PI / 2}
    <line x1="100" y1="100" x2={100 + Math.cos(angle) * 86} y2={100 + Math.sin(angle) * 86} stroke="#e7e1d9" stroke-width="1" />
  {/each}
  <polygon {points} fill="#5b55d624" stroke="#5b55d6" stroke-width="2.5" stroke-linejoin="round" />
  {#each normalized as value, index}
    {@const angle = (Math.PI * 2 * index) / count - Math.PI / 2}
    {@const radius = 36 + value * 10}
    <circle cx={100 + Math.cos(angle) * radius} cy={100 + Math.sin(angle) * radius} r="4" fill="#f1b86a" stroke="#302a36" stroke-width="1.5" />
  {/each}
</svg>

<style>
  .contour { width: 100%; height: auto; overflow: visible; }
</style>
