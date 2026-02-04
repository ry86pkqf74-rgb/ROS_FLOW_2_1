/**
 * MSW Handlers Aggregation
 * 
 * Combines all mock handlers for use in browser and server workers
 */

import { workflowHandlers } from './handlers/workflow';
import { governanceHandlers } from './handlers/governance';
import { auditHandlers } from './handlers/audit';
import { manuscriptHandlers } from './handlers/manuscript';
import { libraryHandlers } from './handlers/library';

export const handlers = [
  ...workflowHandlers,
  ...governanceHandlers,
  ...auditHandlers,
  ...manuscriptHandlers,
  ...libraryHandlers,
];

export default handlers;
