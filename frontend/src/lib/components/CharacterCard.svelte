<script lang="ts">
  import PersonalityContour from './PersonalityContour.svelte';

  export let summary = '';
  export let highlights: string[] = [];
  export let username = '';
  export let values: number[] = [];
  export let onUsername: (value: string) => void;
  export let onFull: () => void;
</script>

<article class="character-card">
  <div class="visual"><PersonalityContour {values} /></div>
  <div class="content">
    <p class="eyebrow">Kartu karakter</p>
    <h1>{username ? `@${username}` : 'Profil kepribadianmu'}</h1>
    <p class="summary">{summary}</p>
    {#if highlights.length}
      <ul>{#each highlights.slice(0, 3) as item}<li>{item}</li>{/each}</ul>
    {/if}
    <label>Username pilihanmu
      <div class="username"><span>@</span><input value={username} maxlength="32" on:input={(event) => onUsername(event.currentTarget.value)} /></div>
    </label>
    <button type="button" on:click={onFull}>Lihat lengkap <span aria-hidden="true">→</span></button>
  </div>
</article>

<style>
  .character-card { display: grid; grid-template-columns: minmax(220px, .82fr) 1.18fr; gap: clamp(28px, 6vw, 72px); align-items: center; width: min(920px, 100%); margin: 42px auto; border: 1px solid #e7e1d9; border-radius: 28px; padding: clamp(24px, 5vw, 54px); background: #fff; box-shadow: 0 24px 70px rgba(48,42,54,.08); }
  .visual { border-radius: 50%; background: #fbfaf6; padding: 12px; }
  .eyebrow { margin: 0 0 10px; color: #5b55d6; font-weight: 780; letter-spacing: .08em; text-transform: uppercase; font-size: .75rem; }
  h1 { margin: 0; color: #302a36; font-size: clamp(2rem, 5vw, 3.5rem); line-height: 1; letter-spacing: -.045em; }
  .summary { color: #615968; font-size: 1.05rem; line-height: 1.65; }
  ul { margin: 22px 0; padding: 0; display: flex; flex-wrap: wrap; gap: 8px; list-style: none; }
  li { border-radius: 999px; padding: 8px 12px; background: #fff3dc; color: #594638; font-size: .86rem; font-weight: 700; }
  label { display: grid; gap: 7px; color: #615968; font-size: .82rem; font-weight: 720; }
  .username { display: flex; align-items: center; border: 1px solid #d7d0ca; border-radius: 14px; padding: 0 14px; background: #fbfaf6; }
  .username span { color: #5b55d6; font-weight: 800; }
  input { width: 100%; min-width: 0; border: 0; padding: 13px 4px; background: transparent; color: #302a36; font: inherit; font-weight: 720; outline: 0; }
  .username:focus-within { outline: 3px solid rgba(91,85,214,.2); border-color: #5b55d6; }
  button { display: inline-flex; gap: 12px; align-items: center; margin-top: 18px; border: 0; padding: 10px 0; background: transparent; color: #5b55d6; font: inherit; font-weight: 780; cursor: pointer; }
  button:focus-visible { outline: 3px solid rgba(91,85,214,.28); outline-offset: 4px; border-radius: 4px; }
  @media (max-width: 700px) { .character-card { grid-template-columns: 1fr; } .visual { width: min(270px, 82%); margin: auto; } }
</style>
