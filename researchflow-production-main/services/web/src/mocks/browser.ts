/**
 * MSW Browser Worker Setup
 * 
 * Configures MSW for browser-based mocking (development/prototyping)
 * 
 * Usage in main.tsx:
 * ```typescript
 * if (import.meta.env.VITE_MOCK_API === 'true') {
 *   const { worker } = await import('./mocks/browser');
 *   await worker.start({
 *     onUnhandledRequest: 'bypass',
 *   });
 * }
 * ```
 */

import { setupWorker } from 'msw/browser';
import { handlers } from './handlers';

export const worker = setupWorker(...handlers);

// Enable MSW logging in development
if (import.meta.env.DEV) {
  worker.events.on('request:start', ({ request }) => {
    console.log('[MSW] %s %s', request.method, request.url);
  });

  worker.events.on('request:match', ({ request }) => {
    console.log('[MSW] Matched: %s %s', request.method, request.url);
  });

  worker.events.on('request:unhandled', ({ request }) => {
    console.log('[MSW] Unhandled: %s %s', request.method, request.url);
  });
}

export default worker;
