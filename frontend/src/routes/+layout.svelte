<script lang="ts">
  import { afterNavigate } from '$app/navigation';
  import { onMount } from 'svelte';

  const GA_MEASUREMENT_ID = import.meta.env.VITE_GA_MEASUREMENT_ID?.trim() ?? '';
  const HOSTED_HOSTNAMES = new Set(['hermex.fun', 'www.hermex.fun']);
  let lastTrackedPath = '';
  let gaConfigured = false;

  function analyticsEnabled() {
    return Boolean(
      GA_MEASUREMENT_ID
      && typeof window !== 'undefined'
      && typeof document !== 'undefined'
      && HOSTED_HOSTNAMES.has(window.location.hostname)
    );
  }

  function installGoogleAnalytics() {
    if (!analyticsEnabled()) return;
    if (!document.querySelector(`script[data-hermex-ga="${GA_MEASUREMENT_ID}"]`)) {
      const script = document.createElement('script');
      script.async = true;
      script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(GA_MEASUREMENT_ID)}`;
      script.dataset.hermexGa = GA_MEASUREMENT_ID;
      document.head.appendChild(script);
    }

    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || function gtag(...args: unknown[]) { window.dataLayer.push(args); };
    if (!gaConfigured) {
      window.gtag('js', new Date());
      window.gtag('config', GA_MEASUREMENT_ID, { send_page_view: false, anonymize_ip: true });
      gaConfigured = true;
    }
  }

  function trackPageView(path: string) {
    if (!analyticsEnabled()) return;
    installGoogleAnalytics();
    if (lastTrackedPath === path) return;

    lastTrackedPath = path;
    window.gtag('event', 'page_view', {
      anonymize_ip: true,
      page_path: path,
      page_title: document.title,
      page_location: `${window.location.origin}${path}`
    });
  }

  onMount(() => {
    trackPageView(`${window.location.pathname}${window.location.search}`);
  });

  afterNavigate(({ to }) => {
    if (!to?.url) return;
    trackPageView(`${to.url.pathname}${to.url.search}`);
  });
</script>

<slot />
