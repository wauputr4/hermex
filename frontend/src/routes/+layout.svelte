<script lang="ts">
  import { onMount } from 'svelte';

  const GA_MEASUREMENT_ID = import.meta.env.VITE_GA_MEASUREMENT_ID?.trim() ?? '';

  function installGoogleAnalytics() {
    if (!GA_MEASUREMENT_ID || typeof window === 'undefined' || typeof document === 'undefined') return;
    if (document.querySelector(`script[data-hermex-ga="${GA_MEASUREMENT_ID}"]`)) return;

    const script = document.createElement('script');
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(GA_MEASUREMENT_ID)}`;
    script.dataset.hermexGa = GA_MEASUREMENT_ID;
    document.head.appendChild(script);

    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || function gtag(...args: unknown[]){ window.dataLayer.push(args); };
    window.gtag('js', new Date());
    window.gtag('config', GA_MEASUREMENT_ID, { anonymize_ip: true });
  }

  onMount(() => {
    installGoogleAnalytics();
  });
</script>

<slot />
