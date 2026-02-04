# Phase 7 Frontend Integration Components

This directory contains the AI/Agent integration components for the ResearchFlow Phase 7 frontend. These components provide real-time visualization of agent execution status and display RAG-enhanced copilot responses.

## Components

### AgentStatus.tsx

A comprehensive React component for displaying the current execution status of the ResearchFlow agent pipeline.

**Features:**
- Real-time phase tracking (DataPrep, Analysis, Quality, IRB, Manuscript)
- Progress indicators with visual feedback
- WebSocket-based live updates
- Detailed phase descriptions and timeline visualization
- Connection status monitoring
- Error alerting
- Compact and full display modes

**Props:**
```typescript
interface AgentStatusProps {
  className?: string;        // Custom CSS class
  showDetails?: boolean;     // Show phase descriptions (default: true)
  compact?: boolean;         // Compact display mode (default: false)
}
```

**Usage:**

```tsx
import { AgentStatus } from './components/ai/AgentStatus';

export function Dashboard() {
  return (
    <div className="p-6">
      <AgentStatus
        showDetails={true}
        compact={false}
      />
    </div>
  );
}
```

**Display Modes:**

1. **Full Mode (default):**
   - Current phase details with icon and description
   - Real-time progress bar
   - Execution timeline with phase history
   - Error alerts
   - Connection status

2. **Compact Mode:**
   - Single-line status display
   - Perfect for sidebars or headers
   - Shows current phase and progress percentage

**Styling:**
- Uses Tailwind CSS with responsive design
- Customizable colors per phase
- Smooth transitions and animations
- Emoji icons for visual clarity

---

### CopilotResponse.tsx

A specialized component for displaying RAG-enhanced (Retrieval-Augmented Generation) copilot responses with source citations.

**Features:**
- Rich text rendering with inline citations
- Source grouping by type (document, dataset, analysis, external)
- Confidence score visualization
- Streaming text support with auto-scroll
- Source relevance indicators
- Clickable source cards for exploration
- Comprehensive metadata display

**Props:**
```typescript
interface CopilotResponseProps {
  content: string;                           // Response text
  sources: SourceCitation[];                 // Array of cited sources
  confidenceScore: number;                   // 0-1 confidence level
  isStreaming?: boolean;                     // Streaming indicator
  onSourceClick?: (sourceId: string) => void; // Source click handler
  className?: string;                        // Custom CSS class
  showConfidenceMetrics?: boolean;           // Show confidence info
}

interface SourceCitation {
  id: string;              // Unique source identifier
  title: string;           // Source title/name
  url?: string;            // Optional URL
  type: 'document' | 'dataset' | 'analysis' | 'external';
  relevanceScore: number;  // 0-1 relevance score
}
```

**Usage:**

```tsx
import { CopilotResponse } from './components/ai/CopilotResponse';

export function AnalysisResponse() {
  const sources = [
    {
      id: 'doc-001',
      title: 'Patient Demographics Study',
      type: 'document' as const,
      relevanceScore: 0.95,
    },
    {
      id: 'ds-001',
      title: 'Clinical Outcomes Dataset',
      type: 'dataset' as const,
      relevanceScore: 0.87,
    },
  ];

  const response = `Based on [ref:doc-001] and [ref:ds-001],
    the analysis shows significant correlation between
    treatment variables and patient outcomes.`;

  return (
    <CopilotResponse
      content={response}
      sources={sources}
      confidenceScore={0.92}
      isStreaming={false}
      onSourceClick={(sourceId) => {
        console.log('Clicked source:', sourceId);
      }}
      showConfidenceMetrics={true}
    />
  );
}
```

**Citation Syntax:**
The component supports multiple citation formats within the response text:
- `[ref:source-id]` - Standard reference format
- `[source:document-001]` - Explicit source type
- `[doc-001]` - Shorthand format

**Source Types:**
- **Document** (📄): Research papers, protocols, reports
- **Dataset** (📊): Raw data, analysis tables
- **Analysis** (🔬): Pre-computed analyses, results
- **External** (🔗): External URLs, references

**Confidence Levels:**
- **High** (>80%): Green indicator
- **Medium** (60-80%): Yellow indicator
- **Low** (<60%): Orange indicator

---

## Custom Hooks

### useAgentStatus.ts

A custom React hook for managing WebSocket connections to the ResearchFlow agent backend, handling real-time status updates and automatic reconnection.

**Features:**
- WebSocket connection management
- Automatic reconnection with exponential backoff
- Heartbeat monitoring for connection health
- Phase change notifications
- Error handling and recovery
- Type-safe message handling
- Configurable reconnection strategies

**Hook Signature:**
```typescript
const useAgentStatus = (config?: UseAgentStatusConfig): AgentStatusState & {
  connect: () => void;
  disconnect: () => void;
}

interface UseAgentStatusConfig {
  wsUrl?: string;                    // WebSocket URL (default: auto-detect)
  autoConnect?: boolean;             // Auto-connect on mount (default: true)
  reconnectInterval?: number;        // Reconnect interval in ms (default: 3000)
  maxReconnectAttempts?: number;     // Max reconnect attempts (default: 10)
  heartbeatInterval?: number;        // Heartbeat check interval (default: 30000)
  onError?: (error: Error) => void;  // Error callback
  onPhaseChange?: (phase: AgentPhase) => void; // Phase change callback
}

interface AgentStatusState {
  status: 'idle' | 'running' | 'paused' | 'completed' | 'failed';
  phase: AgentPhase;
  progress: number;
  error: string | null;
  isConnected: boolean;
  lastUpdate: Date | null;
}
```

**Usage:**

```tsx
import { useAgentStatus } from './hooks/useAgentStatus';

export function AgentMonitor() {
  const {
    status,
    phase,
    progress,
    error,
    isConnected,
    connect,
    disconnect
  } = useAgentStatus({
    wsUrl: 'wss://api.example.com/agent/ws',
    reconnectInterval: 5000,
    onPhaseChange: (newPhase) => {
      console.log(`Transitioned to: ${newPhase}`);
    },
    onError: (error) => {
      console.error('Agent error:', error);
    }
  });

  return (
    <div>
      <h2>{phase} - {progress}%</h2>
      <p>Status: {status}</p>
      <p>Connected: {isConnected ? 'Yes' : 'No'}</p>
      {error && <p>Error: {error}</p>}

      <button onClick={connect}>Connect</button>
      <button onClick={disconnect}>Disconnect</button>
    </div>
  );
}
```

**WebSocket Message Format:**

The hook expects messages in the following JSON format:

```typescript
// Status update
{
  type: 'status',
  status: 'running' | 'idle' | 'paused' | 'completed' | 'failed'
}

// Phase transition
{
  type: 'phase',
  phase: 'DataPrep' | 'Analysis' | 'Quality' | 'IRB' | 'Manuscript'
}

// Progress update
{
  type: 'progress',
  progress: 0-100
}

// Error message
{
  type: 'error',
  message: 'Error description'
}

// Heartbeat ping
{
  type: 'ping'
}
```

**Automatic Reconnection:**
- Initial attempt immediately on disconnect
- Exponential backoff: 3s, 4.5s, 6.75s, ... (capped at 30s)
- Maximum 10 reconnection attempts by default
- Configurable via `maxReconnectAttempts`

**Connection Health:**
- Heartbeat sent every 30 seconds (configurable)
- Timeout after 35 seconds of no messages
- Automatic disconnection and reconnection on timeout

---

## Integration Example

Here's a complete example showing how to use all components together:

```tsx
import React from 'react';
import { AgentStatus } from './components/ai/AgentStatus';
import { CopilotResponse } from './components/ai/CopilotResponse';
import { useAgentStatus } from './hooks/useAgentStatus';

export function ResearchAnalysisDashboard() {
  const { status, phase, progress } = useAgentStatus({
    wsUrl: process.env.REACT_APP_AGENT_WS_URL,
    onPhaseChange: (newPhase) => {
      // Handle phase transitions
    },
  });

  const [copilotResponse, setCopilotResponse] = React.useState({
    content: '',
    sources: [],
    confidence: 0,
  });

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 p-6">
      {/* Left column: Agent status */}
      <div className="lg:col-span-1">
        <AgentStatus compact={false} />
      </div>

      {/* Right column: Copilot response */}
      <div className="lg:col-span-2">
        <div className="bg-gray-50 rounded-lg p-6">
          <h2 className="text-2xl font-bold mb-4">Analysis Results</h2>
          <CopilotResponse
            content={copilotResponse.content}
            sources={copilotResponse.sources}
            confidenceScore={copilotResponse.confidence}
            onSourceClick={(sourceId) => {
              // Handle source navigation
            }}
          />
        </div>
      </div>
    </div>
  );
}
```

---

## Environment Variables

For the `useAgentStatus` hook to work properly, configure these optional environment variables:

```bash
# WebSocket URL for agent connection
REACT_APP_AGENT_WS_URL=wss://api.example.com/agent/ws

# Optional: Override default configuration
REACT_APP_AGENT_RECONNECT_INTERVAL=3000
REACT_APP_AGENT_HEARTBEAT_INTERVAL=30000
```

---

## Dependencies

These components require the following libraries (typically already in a React 18+ project):

- **react** ^18.0.0
- **typescript** ^4.9.0
- **tailwindcss** ^3.0.0

---

## Styling Notes

All components use **Tailwind CSS** for styling. Ensure your project has:

1. Tailwind CSS installed and configured
2. Prose plugin enabled (for `CopilotResponse` text rendering)
3. Animation utilities enabled in `tailwind.config.js`

Example config:
```javascript
module.exports = {
  content: [
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    extend: {
      animation: {
        pulse: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
};
```

---

## Type Definitions

All TypeScript types are exported for use in your application:

```typescript
import type { AgentPhase, AgentStatusProps } from './components/ai/AgentStatus';
import type {
  CopilotResponseProps,
  SourceCitation
} from './components/ai/CopilotResponse';
```

---

## Performance Considerations

- **AgentStatus**: Lightweight component, memoized phase configs
- **CopilotResponse**: Efficiently parses citations, source grouping optimized
- **useAgentStatus**: Minimal overhead, single WebSocket connection per hook instance

For multiple instances needing the same agent status, consider using a context provider to share the hook state across your component tree.

---

## Browser Compatibility

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- WebSocket support required for `useAgentStatus`

---

## License

MIT - Part of ResearchFlow Phase 7 Frontend Integration
