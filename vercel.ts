import type { VercelConfig } from '@vercel/config/v1';

export const config: VercelConfig = {
  framework: 'nextjs',
  buildCommand: 'turbo run build --filter=web',
  crons: [
    { path: '/api/cron/fetch', schedule: '0 3 * * *' },
    { path: '/api/cron/classify', schedule: '0 6 * * *' },
    { path: '/api/cron/purge', schedule: '30 6 * * *' },
  ],
};
