import type { VercelConfig } from '@vercel/config/v1';

// UWAGA: Vercel Cron używa UTC. Polska CEST = UTC+2 (lato), CET = UTC+1 (zima).
// Harmonogram dopasowany do 6:00 rano Warsaw w czasie letnim (CEST).
// W zimie przesunie się o godzinę wcześniej (5:00 rano) — do akceptacji.
export const config: VercelConfig = {
  framework: 'nextjs',
  buildCommand: 'turbo run build --filter=web',
  crons: [
    // purge = hard-rules auto-cleanup (spam domains + grace-expired transactional)
    // 04:00 UTC = 06:00 Warsaw (CEST) / 05:00 Warsaw (CET)
    { path: '/api/cron/purge', schedule: '0 4 * * *' },
    // Stuby — jeszcze nie zaimplementowane (endpoint zwróci 404):
    { path: '/api/cron/fetch', schedule: '0 1 * * *' },       // 03:00 Warsaw CEST
    { path: '/api/cron/classify', schedule: '30 3 * * *' },    // 05:30 Warsaw CEST
  ],
};
