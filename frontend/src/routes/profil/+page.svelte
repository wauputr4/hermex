<script lang="ts">
  import { onMount } from 'svelte';
  import { API_BASE, deleteUserHistory, getAuthMe, getProfileSettings, getUserHistory, updateProfileSettings } from '$lib/api/hermex';

  let user: any = null;
  let profiles: any[] = [];
  let selected = '';
  let username = '';
  let savedUsername = '';
  let isPublic = true;
  let status = '';
  let saving = false;
  let deleting = false;

  onMount(async () => {
    try {
      const auth = await getAuthMe();
      if (!auth.authenticated) return;
      user = auth.user;
      profiles = (await getUserHistory()).history.filter((item) => item.public_username);
      if (profiles[0]) await choose(profiles[0].profile_id);
    } catch (error) {
      status = error instanceof Error ? error.message : 'Profil belum bisa dimuat.';
    }
  });

  async function choose(profileId: string) {
    selected = profileId;
    username = '';
    savedUsername = '';
    isPublic = true;
    status = '';
    try {
      const settings = await getProfileSettings(profileId);
      username = settings.username ?? '';
      savedUsername = settings.username ?? '';
      isPublic = settings.is_public;
    } catch (error) {
      status = error instanceof Error ? error.message : 'Pengaturan profil belum bisa dimuat.';
    }
  }

  async function save() {
    if (!selected || username.trim().length < 3) return;
    saving = true;
    status = '';
    try {
      const result: any = await updateProfileSettings(selected, { username: username.trim().toLowerCase(), is_public: isPublic });
      username = result.username;
      savedUsername = result.username;
      status = 'Perubahan tersimpan.';
    } catch (error) {
      status = error instanceof Error ? error.message : 'Perubahan belum tersimpan.';
    } finally {
      saving = false;
    }
  }

  async function removeProfile() {
    if (!selected || deleting || !window.confirm('Hapus data analisis ini? Profil, hasil, dan umpan baliknya tidak dapat dipulihkan.')) return;
    deleting = true;
    status = '';
    try {
      await deleteUserHistory(selected);
      profiles = profiles.filter((profile) => profile.profile_id !== selected);
      selected = '';
      username = '';
      savedUsername = '';
      if (profiles[0]) await choose(profiles[0].profile_id);
      else status = 'Data analisis telah dihapus.';
    } catch (error) {
      status = error instanceof Error ? error.message : 'Data belum bisa dihapus.';
    } finally {
      deleting = false;
    }
  }
</script>

<svelte:head><title>Profil — Hermex</title><meta name="description" content="Atur username dan visibilitas kartu karakter Hermex." /></svelte:head>

<main>
  <nav><a href="/">☆ hermex.fun | analisis kepribadian</a>{#if user?.picture}<img src={user.picture} alt="" referrerpolicy="no-referrer" />{/if}</nav>
  <header><p>PROFILMU</p><h1>Atur kartu karaktermu</h1><span>Ganti tautan profil atau tentukan siapa yang boleh melihat hasilmu.</span></header>
  {#if !user && !status}
    <section class="empty"><h2>Masuk dulu, ya</h2><p>Pengaturan ini hanya bisa dibuka oleh pemilik profil.</p><a href={`${API_BASE}/api/v1/auth/google/start`}>Masuk dengan Google</a></section>
  {:else if profiles.length}
    <form on:submit|preventDefault={save}>
      {#if profiles.length > 1}<label>Kartu yang diatur<select bind:value={selected} on:change={(event) => choose(event.currentTarget.value)}>{#each profiles as profile}<option value={profile.profile_id}>{profile.public_username}</option>{/each}</select></label>{/if}
      <label>Username<span class="username"><b>/</b><input bind:value={username} minlength="3" maxlength="32" pattern="[a-z0-9_]+" required /></span><small>Huruf kecil, angka, dan garis bawah.</small></label>
      <label class="visibility"><input type="checkbox" bind:checked={isPublic} /><span><strong>Tampilkan ke publik</strong><small>Matikan untuk menyembunyikan profil dari orang lain. Kamu tetap bisa membukanya saat login.</small></span></label>
      <button disabled={saving}>{#if saving}Menyimpan…{:else}<span aria-hidden="true">✓</span> Simpan perubahan{/if}</button>
      {#if status}<p role="status">{status}</p>{/if}
      <a class="view" href={`/${savedUsername}`}>Lihat kartu karakter →</a>
      <button class="delete" type="button" disabled={deleting} on:click={removeProfile}><span aria-hidden="true">⌫</span> {deleting ? 'Menghapus…' : 'Hapus data analisis'}</button>
    </form>
  {:else if user}
    <section class="empty"><h2>Belum ada kartu</h2><p>Selesaikan satu analisis agar pengaturan profil muncul di sini.</p>{#if status}<p role="status">{status}</p>{/if}<a href="/">Mulai analisis <span aria-hidden="true">→</span></a></section>
  {:else if status}<p role="alert">{status}</p>{/if}
</main>

<style>
  main { width: min(760px, calc(100% - 32px)); min-height: 100vh; margin: auto; color: #302a36; }
  nav { display: flex; justify-content: space-between; align-items: center; min-height: 76px; border-bottom: 1px solid #e7e1d9; }
  nav a { color: inherit; font-weight: 820; text-decoration: none; }
  nav img { width: 40px; height: 40px; border-radius: 50%; object-fit: cover; }
  header { padding: 76px 0 38px; }
  header p { margin: 0 0 10px; color: #5b55d6; font-size: .78rem; font-weight: 820; letter-spacing: .1em; }
  h1 { margin: 0 0 16px; font-size: clamp(2.7rem, 8vw, 5.4rem); line-height: .95; letter-spacing: -.06em; }
  header span, .empty p { color: #6f6873; line-height: 1.6; }
  form, .empty { display: grid; gap: 22px; border: 1px solid #e7e1d9; border-radius: 24px; padding: clamp(22px, 5vw, 38px); background: #fff; }
  label { display: grid; gap: 8px; font-weight: 760; }
  input, select { min-height: 50px; border: 1px solid #d7d0ca; border-radius: 12px; padding: 0 14px; background: #fff; color: #302a36; font: inherit; }
  .username { display: flex; align-items: center; border: 1px solid #d7d0ca; border-radius: 12px; }
  .username b { padding-left: 14px; color: #827b82; }
  .username input { flex: 1; min-width: 0; border: 0; }
  small { color: #827b82; font-weight: 500; line-height: 1.45; }
  .visibility { grid-template-columns: auto 1fr; align-items: start; border-radius: 16px; padding: 18px; background: #f7f5f1; }
  .visibility input { width: 20px; min-height: 20px; margin: 2px 0 0; }
  .visibility span, .visibility small { display: block; }
  button, .empty a { min-height: 52px; border: 0; border-radius: 13px; padding: 0 18px; background: #5b55d6; color: #fff; font-weight: 800; text-decoration: none; cursor: pointer; }
  button { display: inline-flex; align-items: center; justify-content: center; gap: 8px; }
  .empty a { display: grid; width: fit-content; place-items: center; }
  .view { color: #5b55d6; font-weight: 760; text-decoration: none; }
  .delete { justify-self: start; min-height: auto; padding: 0; background: transparent; color: #a33c52; font-size: .82rem; font-weight: 760; }
  .delete:hover { color: #84283d; text-decoration: underline; }
  :is(a, button):focus-visible { outline: 3px solid rgba(91,85,214,.28); outline-offset: 3px; }
  [role='status'], [role='alert'] { margin: 0; color: #5b55d6; }
</style>
