<svelte:head>
  <title>Privacy Policy | Hermex</title>
  <meta
    name="description"
    content="Privacy Policy for Hermex Fun, including guest storage, Google OAuth, AI provider data, and self-hosting boundaries."
  />
</svelte:head>

<main class="legal-shell">
  <article>
    <a class="back" href="/">← Back to Hermex</a>
    <p class="eyebrow">Hermex legal</p>
    <h1>Privacy Policy</h1>
    <p class="lead">
      Hermex is guest-first and open-source. This policy explains what data may be used
      by the app, what stays local, and how hosted login features are expected to work.
    </p>

    <section>
      <h2>1. Local guest storage</h2>
      <p>
        Hermex may save draft birth data, selected city, guest chart history, XP, streaks,
        badges, and install preferences in your browser storage. This helps the app feel
        installable and easy to reopen.
      </p>
    </section>

    <section>
      <h2>2. Backend records</h2>
      <p>
        When you generate a chart or AI interpretation, the backend may store profile
        records, chart payloads, prompt payloads, AI responses, and feedback in SQLite so
        the admin dashboard can audit local usage.
      </p>
    </section>

    <section>
      <h2>3. Google OAuth</h2>
      <p>
        When enabled, Google OAuth is used for account identity. Hermex should request
        only basic profile and email scopes. Hermex does not receive your Google password.
      </p>
    </section>

    <section>
      <h2>4. AI providers</h2>
      <p>
        If Hermex is configured with an external AI provider, chart context and prompt
        payloads may be sent to that provider to generate interpretations. Self-hosted
        users control their own provider, keys, and storage.
      </p>
    </section>

    <section>
      <h2>5. Hosted and self-hosted boundary</h2>
      <p>
        Self-hosted deployments are controlled by the operator who runs them. Hosted
        Hermex at hermex.fun may later add account sync, donation, subscription, and
        payment-related records.
      </p>
    </section>

    <section>
      <h2>6. Contact</h2>
      <p>
        For privacy questions, contact the project maintainer through the repository:
        <a href="https://github.com/wauputr4/hermex">github.com/wauputr4/hermex</a>.
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
