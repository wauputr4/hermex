<script lang="ts">
  export type Question = { id: string; prompt: string };
  export let questions: Question[] = [];
  export let count = 0;
  export let answers: Record<string, number> = {};
  export let scaleLabels: Record<string, string> = { '1': 'Sangat tidak sesuai', '5': 'Sangat sesuai' };
  export let busy = false;
  export let onAnswer: (id: string, value: number) => void;
  export let onNext: (index: number) => Promise<void>;
  export let onSubmit: () => void;

  let current = 0;
  let loadingNext = false;
  let loadError = '';
  $: question = questions[current];
  $: answered = Object.keys(answers).length;

  async function goNext() {
    loadError = '';
    loadingNext = true;
    try {
      await onNext(current + 1);
      current += 1;
    } catch (cause) {
      loadError = cause instanceof Error ? cause.message : 'Pertanyaan berikutnya belum dapat dimuat.';
    } finally {
      loadingNext = false;
    }
  }
</script>

{#if question}
  <section class="questionnaire" aria-labelledby="questionnaire-title">
    <header>
      <div>
        <p>Langkah 2 dari 3</p>
        <h1 id="questionnaire-title">Seberapa sesuai dengan dirimu?</h1>
      </div>
      <strong>{current + 1}/{count}</strong>
    </header>
    <div class="progress" aria-hidden="true"><span style={`width:${((current + 1) / count) * 100}%`}></span></div>
    <fieldset>
      <legend>{question.prompt}</legend>
      <div class="ratings">
        {#each [1, 2, 3, 4, 5] as value}
          <label class:filled={(answers[question.id] ?? 0) >= value}>
            <input type="radio" name={question.id} value={value} aria-label={scaleLabels[String(value)] ?? `${value} dari 5`} checked={answers[question.id] === value} on:change={() => onAnswer(question.id, value)} />
            <span aria-hidden="true">★</span>
          </label>
        {/each}
      </div>
      <div class="scale"><span>{scaleLabels['1']}</span><span>{scaleLabels['5']}</span></div>
      {#if loadError}<p class="load-error" role="alert">{loadError}</p>{/if}
    </fieldset>
    <footer>
      <button class="back" type="button" disabled={current === 0 || busy || loadingNext} on:click={() => (current -= 1)}><span aria-hidden="true">←</span> Kembali</button>
      {#if current < count - 1}
        <button type="button" disabled={!answers[question.id] || busy || loadingNext} on:click={goNext}>{#if loadingNext}Menyiapkan…{:else}Lanjut <span aria-hidden="true">→</span>{/if}</button>
      {:else}
        <button type="button" disabled={answered !== count || busy} on:click={onSubmit}>{#if busy}Menyiapkan analisis…{:else}Lihat hasil awal <span aria-hidden="true">→</span>{/if}</button>
      {/if}
    </footer>
  </section>
{/if}

<style>
  .questionnaire { width: min(680px, 100%); margin: 52px auto; }
  header { display: flex; justify-content: space-between; gap: 24px; align-items: start; }
  header p { margin: 0 0 8px; color: #5b55d6; font-weight: 750; }
  h1 { max-width: 570px; margin: 0; color: #302a36; font-size: clamp(1.25rem, 2.6vw, 1.65rem); line-height: 1.2; letter-spacing: -.025em; }
  header strong { flex: 0 0 auto; border: 1px solid #e7e1d9; border-radius: 999px; padding: 9px 12px; color: #615968; }
  .progress { height: 5px; margin: 28px 0 44px; overflow: hidden; border-radius: 99px; background: #e7e1d9; }
  .progress span { display: block; height: 100%; border-radius: inherit; background: #5b55d6; transition: width .2s ease; }
  fieldset { min-width: 0; margin: 0; padding: 0; border: 0; }
  legend { min-height: 3.8em; color: #302a36; font-size: clamp(1.75rem, 4.5vw, 2.65rem); font-weight: 760; line-height: 1.16; letter-spacing: -.035em; }
  .ratings { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-top: 28px; }
  .ratings label { cursor: pointer; }
  .ratings input { position: absolute; opacity: 0; pointer-events: none; }
  .ratings span { display: grid; aspect-ratio: 1; place-items: center; border: 1px solid #d7d0ca; border-radius: 18px; background: #fff; color: #d7d0ca; font-size: clamp(1.55rem, 4vw, 2.25rem); transition: .15s ease; }
  .ratings label:hover span, .ratings label:has(input:focus-visible) span { border-color: #5b55d6; color: #5b55d6; transform: translateY(-2px); }
  .ratings label.filled span { border-color: #5b55d6; background: #f2f0ff; color: #5b55d6; }
  .ratings input:focus-visible + span { outline: 3px solid rgba(91,85,214,.28); outline-offset: 3px; }
  .scale { display: flex; justify-content: space-between; gap: 12px; margin-top: 10px; color: #7c747d; font-size: .8rem; }
  .load-error { margin: 16px 0 0; color: #a33c52; font-size: .82rem; font-weight: 700; }
  footer { display: flex; justify-content: space-between; gap: 12px; margin-top: 44px; }
  button { display: inline-flex; min-height: 50px; align-items: center; justify-content: center; gap: 8px; border: 0; border-radius: 14px; padding: 0 22px; background: #5b55d6; color: #fff; font: inherit; font-weight: 740; cursor: pointer; }
  button.back { border: 1px solid #d7d0ca; background: #fff; color: #302a36; }
  button:disabled { opacity: .45; cursor: not-allowed; transform: none; }
  button:focus-visible { outline: 3px solid rgba(91,85,214,.28); outline-offset: 3px; }
  @media (max-width: 560px) {
    .questionnaire { margin: 32px auto; }
    legend { min-height: 4.6em; }
    .ratings { gap: 7px; }
    .ratings span { border-radius: 14px; }
    footer button { flex: 1; padding: 0 12px; }
  }
  @media (prefers-reduced-motion: reduce) { .progress span, .ratings span { transition: none; } }
</style>
