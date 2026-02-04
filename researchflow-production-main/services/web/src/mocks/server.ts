/**
 * MSW Server Worker Setup
 * 
 * Configures MSW for Node.js testing environments (Vitest, Jest)
 * 
 * Usage in test setup:
 * ```typescript
 * import { server } from './mocks/server';
 * 
 * beforeAll(() => server.listen());
 * afterEach(() => server.resetHandlers());
 * afterAll(() => server.close());
 * ```
 */

import { setupServer } from 'msw/node';
import { handlers } from './handlers';

export const server = setupServer(...handlers);

export default server;
