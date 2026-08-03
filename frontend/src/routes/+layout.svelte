<script lang="ts">
  import { afterNavigate } from '$app/navigation';

  const GA_MEASUREMENT_ID = 'G-GSGD3Y264X';
  let lastTrackedPath = typeof window === 'undefined' ? '' : `${window.location.pathname}${window.location.search}`;

  function trackPageView(path: string) {
    if (typeof window === 'undefined' || typeof document === 'undefined' || typeof window.gtag !== 'function') return;
    if (lastTrackedPath === path) return;

    lastTrackedPath = path;
    window.gtag('config', GA_MEASUREMENT_ID, {
      anonymize_ip: true,
      page_path: path,
      page_title: document.title
    });
  }

  afterNavigate(({ to }) => {
    if (!to?.url) return;
    trackPageView(`${to.url.pathname}${to.url.search}`);
  });
</script>

<slot />
