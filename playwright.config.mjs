import { defineConfig } from '@playwright/test';
import { existsSync } from 'node:fs';

const executablePath = process.env.PANTHEON_CHROME ?? (existsSync('/usr/bin/chromium') ? '/usr/bin/chromium' : undefined);
export default defineConfig({
  testDir: 'tests/browser',
  fullyParallel: false,
  workers: 1,
  timeout: 165_000,
  use: {
    baseURL: process.env.PANTHEON_URL ?? 'http://127.0.0.1:4173',
    viewport: { width: 1390, height: 910 },
    browserName: 'chromium',
    launchOptions: { executablePath, args: ['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'] },
    trace: 'retain-on-failure',
  },
});
