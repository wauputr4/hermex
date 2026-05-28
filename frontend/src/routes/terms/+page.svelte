<svelte:head>
  <title>Terms and Conditions | Hermex</title>
  <meta
    name="description"
    content="Terms and Conditions for Hermex Quest, an open-source astrology learning and reflective self-development app."
  />
</svelte:head>

<main class="legal-shell">
  <article>
    <a class="back" href="/">← Back to Hermex</a>
    <p class="eyebrow">Hermex legal</p>
    <h1>Terms and Conditions</h1>
    <p class="lead">
      Hermex Quest is an open-source astrology learning game for symbolic reflection,
      education, and self-development. By using Hermex, you agree to use the app as a
      reflective tool, not as deterministic advice.
    </p>

    <section>
      <h2>1. Reflective use only</h2>
      <p>
        Hermex may show natal chart data, astrology education, AI-generated summaries,
        career themes, relationship reflections, and roadmap suggestions. These outputs
        are not medical, legal, financial, psychological, or life-critical advice.
      </p>
    </section>

    <section>
      <h2>2. Guest-first product</h2>
      <p>
        The MVP is designed to work as a guest experience. Your browser may store local
        draft data, chart history, XP, streaks, badges, and install preferences so you can
        reopen Hermex easily.
      </p>
    </section>

    <section>
      <h2>3. Google OAuth</h2>
      <p>
        When Google login is enabled, Hermex will request only basic identity scopes such
        as profile and email. Google login is intended for account identity, syncing
        progress, and enabling hosted features. Your Google password is never handled by
        Hermex.
      </p>
    </section>

    <section>
      <h2>4. Open-source and self-hosting</h2>
      <p>
        Self-hosted users can run the community edition with their own storage, domain,
        and AI provider credentials. Hosted Hermex may later offer donation, subscription,
        or premium access for owner-operated services.
      </p>
    </section>

    <section>
      <h2>5. AI provider behavior</h2>
      <p>
        AI responses depend on the configured provider, model, prompt, usage limits, and
        chart payload. Hermex does not guarantee that AI output is complete, error-free,
        or suitable for critical decisions.
      </p>
    </section>

    <section>
      <h2>6. Contact</h2>
      <p>
        For questions about these terms, contact the project maintainer through the public
        repository: <a href="https://github.com/wauputr4/hermex">github.com/wauputr4/hermex</a>.
      </p>
    </section>
  </article>
</main>

<style>
  :global(body) {
    margin: 0;
    color: #45304f;
    background: radial-gradient(circle at 14% 10%, rgba(244, 193, 93, .48), transparent 22rem),
      radial-gradient(circle at 82% 12%, rgba(128, 213, 187, .42), transparent 24rem),
      linear-gradient(145deg, #fff8df, #f5e4ee 54%, #dff5ed);
    font-family: Avenir Next, Nunito, Trebuchet MS, sans-serif;
  }

  .legal-shell {
    min-height: 100vh;
    padding: 28px;
    display: grid;
    place-items: start center;
  }

  article {
    width: min(860px, 100%);
    border: 4px solid rgba(69, 48, 79, .12);
    border-radius: 34px;
    background: rgba(255, 253, 247, .9);
    padding: clamp(22px, 5vw, 44px);
    box-shadow: 0 28px 80px rgba(69, 48, 79, .14);
  }

  .back {
    display: inline-flex;
    margin-bottom: 20px;
    color: #45304f;
    font-weight: 950;
    text-decoration: none;
  }

  .eyebrow {
    margin: 0 0 8px;
    color: #8f6884;
    font-size: .78rem;
    font-weight: 950;
    letter-spacing: .12em;
    text-transform: uppercase;
  }

  h1 {
    margin: 0 0 16px;
    font-size: clamp(2.4rem, 8vw, 5.2rem);
    line-height: .9;
    letter-spacing: -.07em;
  }

  h2 {
    margin: 28px 0 8px;
  }

  p {
    color: rgba(69, 48, 79, .76);
    font-weight: 760;
    line-height: 1.65;
  }

  .lead {
    font-size: 1.1rem;
    color: #45304f;
  }

  a {
    color: #365f90;
    font-weight: 900;
  }
</style>
