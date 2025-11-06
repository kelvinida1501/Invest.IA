
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const explicitApi = env.VITE_API_URL ? env.VITE_API_URL.replace(/\/+$/, '') : undefined;
  const proxyTarget =
    env.VITE_BACKEND_PROXY ||
    (explicitApi ? explicitApi.replace(/\/api$/, '') : undefined) ||
    'http://localhost:8000';

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: true,
          secure: false,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },
  };
});
