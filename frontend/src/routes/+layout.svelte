<script lang="ts">
  import { afterNavigate } from '$app/navigation';
  import { onMount } from 'svelte';

  const GA_MEASUREMENT_ID = import.meta.env.VITE_GA_MEASUREMENT_ID?.trim() ?? '';
  let lastTrackedPath = '';

  function installGoogleAnalytics() {
    if (!GA_MEASUREMENT_ID || typeof window === 'undefined' || typeof document === 'undefined') return;
    if (document.querySelector(`script[data-hermex-ga="${GA_MEASUREMENT_ID}"]`)) {
      window.dataLayer = window.dataLayer || [];
      window.gtag = window.gtag || function gtag(...args: unknown[]){ window.dataLayer.push(args); };
      return;
    }

    const script = document.createElement('script');
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(GA_MEASUREMENT_ID)}`;
    script.dataset.hermexGa = GA_MEASUREMENT_ID;
    document.head.appendChild(script);

    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || function gtag(...args: unknown[]){ window.dataLayer.push(args); };
    window.gtag('js', new Date());
  }

  function trackPageView(path: string) {
    if (!GA_MEASUREMENT_ID || typeof window === 'undefined' || typeof document === 'undefined') return;
    if (lastTrackedPath === path) return;

    installGoogleAnalytics();
    lastTrackedPath = path;
    window.gtag('config', GA_MEASUREMENT_ID, {
      anonymize_ip: true,
      page_path: path,
      page_title: document.title
    });
  }

  onMount(() => {
    installGoogleAnalytics();
    trackPageView(`${window.location.pathname}${window.location.search}`);
  });

  afterNavigate(({ to }) => {
    if (!to?.url) return;
    trackPageView(`${to.url.pathname}${to.url.search}`);
  });
</script>

<slot />
