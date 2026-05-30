import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    proxy: {
      '/api/v1': 'http://127.0.0.1:5667',
      '/admin': 'http://127.0.0.1:5667'
    }
  }
});
