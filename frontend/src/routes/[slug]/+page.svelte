<script lang="ts">
  import { onMount } from 'svelte';
  import { getPublicProfile } from '$lib/api/hermex';

  let username = '';
  let loading = true;
  let error = '';
  let publicProfile: any = null;

  function displayValue(value: unknown): string {
    if (typeof value === 'string') return value;
    if (value && typeof value === 'object') {
      const item = value as Record<string, unknown>;
      for (const key of ['summary', 'title', 'focus', 'description']) {
        if (typeof item[key] === 'string') return String(item[key]);
      }
    }
    return value ? String(value) : '';
  }

  function publicSummary(value: unknown): string {
    return displayValue(value)
      .replace(/^Anda adalah individu dengan/i, 'Individu ini menunjukkan')
      .replace(/^Anda adalah/i, 'Profil ini menunjukkan')
      .replace(/^Anda memiliki/i, 'Individu ini memiliki')
      .replace(/^Anda\b/i, 'Individu ini')
      .replace(/^Kamu\b/i, 'Individu ini');
  }

  onMount(async () => {
    const path = window.location.pathname;
    if (!path.startsWith('/@')) {
      window.location.href = '/';
      return;
    }
    username = decodeURIComponent(path.slice(2));
    try {
      publicProfile = await getPublicProfile(username);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Profile not found';
    } finally {
      loading = false;
    }
  });
</script>

<svelte:head>
  <title>{username ? `@${username} - Hermex` : 'Hermex Public Profile'}</title>
  <meta name="theme-color" content="#f4c15d" />
</svelte:head>

<main class="public-shell">
  <section class="public-card">
    <a class="brand" href="/">Hermex Fun</a>
    {#if loading}
      <p>Loading public astrology profile...</p>
    {:else if error}
      <h1>Profile belum ditemukan</h1>
      <p>{error}</p>
      <a class="action" href="/">Buat Astrologyku</a>
    {:else}
      <p class="eyebrow">Public astrology profile</p>
      <h1>@{publicProfile.username}</h1>
      <h2>{publicProfile.display_name || 'Hermex Guest'}</h2>
      <p>{publicProfile.bio || 'Profile astrology reflektif dari Hermex Fun.'}</p>
      <div class="chips">
        <span>{publicProfile.profile?.traits?.dominant_element}</span>
        {#each (publicProfile.profile?.traits?.interests ?? []).slice(0, 4) as item}
          <span>{item}</span>
        {/each}
      </div>
      {#if publicProfile.latest_interpretation}
        <article class="summary">
          <strong>Ringkasan Hermes</strong>
          <p>{publicSummary(publicProfile.latest_interpretation.interpretation?.summary)}</p>
        </article>
      {/if}
      <a class="action" href={`/?u=${publicProfile.username}`}>Buka di Hermex</a>
    {/if}
  </section>
</main>

<style>
  :global(body) {
    margin: 0;
    color: #45304f;
    background: radial-gradient(circle at 12% 8%, rgba(244, 193, 93, .48), transparent 22rem),
      radial-gradient(circle at 88% 16%, rgba(128, 213, 187, .42), transparent 24rem),
      linear-gradient(145deg, #fff8df, #f5e4ee 52%, #dff5ed);
    font-family: Avenir Next, Nunito, Trebuchet MS, sans-serif;
  }
  .public-shell {
    min-height: 100vh;
    display: grid;
    place-items: center;
    padding: 22px;
  }
  .public-card {
    width: min(760px, 100%);
    border: 5px solid rgba(69, 48, 79, .12);
    border-radius: 36px;
    background: rgba(255, 253, 243, .9);
    box-shadow: 0 30px 90px rgba(82, 47, 79, .16);
    padding: 28px;
  }
  .brand, .action {
    display: inline-flex;
    border-radius: 999px;
    padding: 12px 16px;
    background: #45304f;
    color: #fff8df;
    font-weight: 950;
    text-decoration: none;
  }
  .eyebrow {
    margin-top: 30px;
    color: #8f6884;
    text-transform: uppercase;
    letter-spacing: .1em;
    font-weight: 950;
  }
  h1 {
    margin: 8px 0 0;
    font-size: clamp(2.4rem, 8vw, 5rem);
    line-height: .9;
    letter-spacing: -.07em;
  }
  h2 {
    margin: 12px 0 0;
  }
  p {
    color: rgba(69, 48, 79, .74);
    font-weight: 760;
    line-height: 1.55;
  }
  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 18px 0;
  }
  .chips span {
    border-radius: 999px;
    padding: 9px 12px;
    background: #fff0a8;
    color: #45304f;
    font-weight: 950;
  }
  .summary {
    border-radius: 26px;
    background: linear-gradient(135deg, #fff0a8, #dcfff1);
    padding: 18px;
    margin: 18px 0;
  }
</style>
