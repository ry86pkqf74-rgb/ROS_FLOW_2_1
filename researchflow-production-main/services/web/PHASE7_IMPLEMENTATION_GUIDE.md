# Phase 7 Frontend Integration - Implementation Guide

## Overview

This guide provides step-by-step instructions for integrating Phase 7 Frontend Integration components into your ResearchFlow application. These components enable real-time visualization of agent execution and display RAG-enhanced copilot responses.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    React Application                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Components Layer                        │  │
│  │  ┌────────────────┐  ┌──────────────────────────┐   │  │
│  │  │  AgentStatus   │  │  CopilotResponse         │   │  │
│  │  └────────────────┘  └──────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ▲                                  │
│                           │                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Hooks Layer                            │  │
│  │  ┌──────────────────────────────────────────────┐   │  │
│  │  │         useAgentStatus Hook                   │   │  │
│  │  │  • WebSocket Management                       │   │  │
│  │  │  • Auto-Reconnection                          │   │  │
│  │  │  • Heartbeat Monitoring                       │   │  │
│  │  └──────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ▲                                  │
│                           │ WebSocket                        │
└─────────────────────────┼──────────────────────────────────┘
                          │
                          │ wss://
                          │
        ┌─────────────────▼────────────────┐
        │    Agent Backend Server         │
        │  • Status Updates               │
        │  • Phase Transitions            │
        │  • Progress Tracking            │
        │  • Error Handling               │
        └────────────────────────────────┘
```

## File Structure

```
services/web/src/
├── components/
│   └── ai/
│       ├── AgentStatus.tsx           # Agent status visualization
│       ├── CopilotResponse.tsx       # RAG response display
│       ├── examples.tsx              # Usage examples
│       └── README.md                 # Component documentation
├── hooks/
│   ├── useAgentStatus.ts             # WebSocket hook
│   └── README.md                     # Hook documentation
└── ...other components
```

## Step-by-Step Installation

### Step 1: Verify Dependencies

Ensure your project has the required dependencies:

```bash
npm list react typescript tailwindcss
```

Required versions:
- React: ^18.0.0
- TypeScript: ^4.9.0
- Tailwind CSS: ^3.0.0

If missing:
```bash
npm install react@18 typescript@latest tailwindcss@latest
npm install -D @types/react @types/react-dom
```

### Step 2: Configure Tailwind CSS

Ensure your `tailwind.config.js` includes:

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

Install Tailwind typography plugin if needed:
```bash
npm install -D @tailwindcss/typography
```

### Step 3: Environment Configuration

Create or update `.env` in your frontend root:

```env
# WebSocket Configuration
REACT_APP_AGENT_WS_URL=wss://api.example.com/agent/ws

# Optional: Override connection defaults
REACT_APP_AGENT_RECONNECT_INTERVAL=3000
REACT_APP_AGENT_HEARTBEAT_INTERVAL=30000
```

For local development:
```env
REACT_APP_AGENT_WS_URL=ws://localhost:8080/api/agent/ws
```

### Step 4: Set Up Backend WebSocket Endpoint

Your backend must provide a WebSocket endpoint that:

1. **Accepts connections** at the URL specified in `REACT_APP_AGENT_WS_URL`
2. **Sends messages** in the expected JSON format
3. **Handles heartbeat pings** from the client

Example WebSocket message flow:

```
Client → Server: { type: "ping" }
Server → Client: { type: "status", status: "running" }
Server → Client: { type: "phase", phase: "Analysis" }
Server → Client: { type: "progress", progress: 45 }
Server → Client: { type: "error", message: "Validation failed" }
```

### Step 5: Add to Your Application

**Option A: Using AgentProvider (Recommended for app-wide usage)**

Create a provider context:

```typescript
// src/contexts/AgentContext.tsx
import React from 'react';
import { useAgentStatus } from '../hooks/useAgentStatus';

const AgentContext = React.createContext(null);

export function AgentProvider({ children }: { children: React.ReactNode }) {
  const agentStatus = useAgentStatus();

  return (
    <AgentContext.Provider value={agentStatus}>
      {children}
    </AgentContext.Provider>
  );
}

export function useAgent() {
  const context = React.useContext(AgentContext);
  if (!context) {
    throw new Error('useAgent must be used within AgentProvider');
  }
  return context;
}
```

Wrap your app:

```typescript
// src/index.tsx
import { AgentProvider } from './contexts/AgentContext';

ReactDOM.render(
  <React.StrictMode>
    <AgentProvider>
      <App />
    </AgentProvider>
  </React.StrictMode>,
  document.getElementById('root')
);
```

**Option B: Direct Hook Usage (For specific components)**

```typescript
import { useAgentStatus } from './hooks/useAgentStatus';

export function MyComponent() {
  const { status, phase, progress } = useAgentStatus();
  // Use the hook directly
}
```

### Step 6: Import and Use Components

```typescript
import React from 'react';
import { AgentStatus } from './components/ai/AgentStatus';
import { CopilotResponse } from './components/ai/CopilotResponse';

export function Dashboard() {
  return (
    <div className="grid grid-cols-3 gap-6 p-6">
      <AgentStatus />
      <CopilotResponse
        content="Your response text..."
        sources={[]}
        confidenceScore={0.85}
      />
    </div>
  );
}
```

## Integration Patterns

### Pattern 1: Dashboard with Agent Status and Results

```typescript
function AnalysisDashboard() {
  const { phase, progress, status } = useAgentStatus();

  return (
    <div className="grid grid-cols-3 gap-6">
      {/* Status Panel */}
      <AgentStatus />

      {/* Results Panel */}
      <div className="col-span-2">
        <CopilotResponse
          content={analysisText}
          sources={sources}
          confidenceScore={0.92}
        />
      </div>
    </div>
  );
}
```

### Pattern 2: Real-time Analysis Updates

```typescript
function LiveAnalysis() {
  const [responses, setResponses] = React.useState([]);
  const { phase } = useAgentStatus();

  // Update responses based on phase changes
  React.useEffect(() => {
    // Fetch or compute response for current phase
    fetchAnalysisResponse(phase).then(setResponses);
  }, [phase]);

  return (
    <div className="space-y-4">
      {responses.map((response) => (
        <CopilotResponse
          key={response.id}
          content={response.content}
          sources={response.sources}
          confidenceScore={response.confidence}
        />
      ))}
    </div>
  );
}
```

### Pattern 3: Phase-Based UI Rendering

```typescript
function PhaseSpecificUI() {
  const { phase } = useAgentStatus();

  const phaseComponents = {
    DataPrep: <DataPreparationPanel />,
    Analysis: <AnalysisPanel />,
    Quality: <QualityAssurancePanel />,
    IRB: <IRBReviewPanel />,
    Manuscript: <ManuscriptPanel />,
  };

  return phaseComponents[phase] || null;
}
```

### Pattern 4: Error Handling and Alerts

```typescript
function ErrorAwareComponent() {
  const [errors, setErrors] = React.useState<Error[]>([]);

  const { error } = useAgentStatus({
    onError: (err) => {
      setErrors(prev => [...prev, err]);
      // Auto-clear after 5 seconds
      setTimeout(() => {
        setErrors(prev => prev.slice(1));
      }, 5000);
    }
  });

  return (
    <>
      {errors.map((err, idx) => (
        <ErrorAlert key={idx} error={err} />
      ))}
      <MainContent />
    </>
  );
}
```

## WebSocket Backend Implementation

### Example: Node.js/Express

```javascript
// server/wsEndpoint.js
const WebSocket = require('ws');

const wss = new WebSocket.Server({ port: 8080 });

wss.on('connection', (ws) => {
  // Send initial status
  ws.send(JSON.stringify({
    type: 'status',
    status: 'idle'
  }));

  // Simulate agent execution
  simulateAgentExecution(ws);

  // Handle client messages
  ws.on('message', (data) => {
    const message = JSON.parse(data);
    if (message.type === 'ping') {
      // Heartbeat acknowledged
    }
  });

  ws.on('close', () => {
    console.log('Client disconnected');
  });
});

async function simulateAgentExecution(ws) {
  const phases = ['DataPrep', 'Analysis', 'Quality', 'IRB', 'Manuscript'];

  for (const phase of phases) {
    ws.send(JSON.stringify({
      type: 'phase',
      phase: phase
    }));

    ws.send(JSON.stringify({
      type: 'status',
      status: 'running'
    }));

    // Simulate progress
    for (let i = 0; i <= 100; i += 10) {
      ws.send(JSON.stringify({
        type: 'progress',
        progress: i
      }));
      await new Promise(r => setTimeout(r, 1000));
    }
  }

  ws.send(JSON.stringify({
    type: 'status',
    status: 'completed'
  }));
}
```

### Example: Python/FastAPI

```python
# main.py
from fastapi import FastAPI, WebSocket
import asyncio
import json

app = FastAPI()

@app.websocket("/api/agent/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        # Send initial status
        await websocket.send_json({
            "type": "status",
            "status": "idle"
        })

        # Simulate execution
        phases = ['DataPrep', 'Analysis', 'Quality', 'IRB', 'Manuscript']

        for phase in phases:
            await websocket.send_json({
                "type": "phase",
                "phase": phase
            })

            await websocket.send_json({
                "type": "status",
                "status": "running"
            })

            # Progress simulation
            for progress in range(0, 101, 10):
                await websocket.send_json({
                    "type": "progress",
                    "progress": progress
                })
                await asyncio.sleep(1)

        await websocket.send_json({
            "type": "status",
            "status": "completed"
        })

    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    finally:
        await websocket.close()
```

## Testing

### Unit Tests for Components

```typescript
// __tests__/AgentStatus.test.tsx
import { render, screen } from '@testing-library/react';
import { AgentStatus } from '../AgentStatus';

// Mock the hook
jest.mock('../../hooks/useAgentStatus', () => ({
  useAgentStatus: () => ({
    status: 'running',
    phase: 'Analysis',
    progress: 50,
    error: null,
    isConnected: true,
    lastUpdate: new Date(),
  })
}));

test('renders agent status', () => {
  render(<AgentStatus />);
  expect(screen.getByText('Analysis')).toBeInTheDocument();
  expect(screen.getByText('50%')).toBeInTheDocument();
});
```

### Hook Tests

```typescript
// __tests__/useAgentStatus.test.ts
import { renderHook, act } from '@testing-library/react-hooks';
import { useAgentStatus } from '../useAgentStatus';

test('initializes with default state', () => {
  const { result } = renderHook(() => useAgentStatus({ autoConnect: false }));

  expect(result.current.status).toBe('idle');
  expect(result.current.phase).toBe('DataPrep');
  expect(result.current.progress).toBe(0);
});

test('handles status updates', () => {
  const { result } = renderHook(() => useAgentStatus({ autoConnect: false }));

  // Simulate message
  act(() => {
    const message = new MessageEvent('message', {
      data: JSON.stringify({
        type: 'status',
        status: 'running'
      })
    });
    // Send message to hook
  });

  expect(result.current.status).toBe('running');
});
```

## Performance Optimization

### 1. Use Context to Share State

```typescript
// Avoid multiple hook instances
const AgentProvider = ({ children }) => {
  const agentStatus = useAgentStatus(); // Single instance
  return (
    <AgentContext.Provider value={agentStatus}>
      {children}
    </AgentContext.Provider>
  );
};
```

### 2. Memoize Callbacks

```typescript
const handlePhaseChange = useCallback((phase) => {
  console.log(`Phase changed to: ${phase}`);
}, []);

useAgentStatus({ onPhaseChange: handlePhaseChange });
```

### 3. Lazy Load Heavy Components

```typescript
const AgentStatus = lazy(() => import('./AgentStatus'));
const CopilotResponse = lazy(() => import('./CopilotResponse'));

<Suspense fallback={<div>Loading...</div>}>
  <AgentStatus />
</Suspense>
```

### 4. Use Virtual Scrolling for Large Lists

```typescript
import { FixedSizeList } from 'react-window';

<FixedSizeList
  height={600}
  itemCount={sources.length}
  itemSize={80}
  width="100%"
>
  {({ index, style }) => (
    <SourceCard
      style={style}
      source={sources[index]}
    />
  )}
</FixedSizeList>
```

## Troubleshooting

### WebSocket Connection Issues

**Problem**: "WebSocket connection failed"

**Solutions**:
1. Verify backend is running and accessible
2. Check CORS/proxy settings
3. Ensure WebSocket URL is correct in environment variables
4. Look for firewall/network blocking

```bash
# Test WebSocket connectivity
websocat -E wss://api.example.com/agent/ws
```

### Messages Not Received

**Problem**: Hook state not updating

**Solutions**:
1. Verify message format matches expected JSON
2. Check browser DevTools Network tab for WebSocket traffic
3. Ensure message `type` field is valid
4. Check heartbeat interval isn't too aggressive

### Memory Leaks

**Problem**: Unused WebSocket connections consuming memory

**Solutions**:
1. Call `disconnect()` in cleanup functions
2. Verify hook cleanup runs on unmount
3. Monitor browser DevTools Memory tab
4. Check for multiple hook instances

```typescript
useEffect(() => {
  return () => {
    disconnect(); // Cleanup on unmount
  };
}, [disconnect]);
```

## Production Checklist

- [ ] Environment variables configured
- [ ] Backend WebSocket endpoint implemented and tested
- [ ] Error handling and logging in place
- [ ] Performance optimized (no unnecessary re-renders)
- [ ] Accessibility tested (keyboard navigation, screen readers)
- [ ] Mobile responsive design verified
- [ ] WebSocket reconnection tested
- [ ] Security headers configured (CORS, CSP)
- [ ] Load testing completed
- [ ] Error boundaries implemented
- [ ] Analytics/monitoring integrated
- [ ] Documentation updated
- [ ] Code reviewed and approved

## Support and Documentation

- Component Usage: See [components/ai/README.md](./src/components/ai/README.md)
- Hook Documentation: See [hooks/README.md](./src/hooks/README.md)
- Examples: See [components/ai/examples.tsx](./src/components/ai/examples.tsx)

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-01-30 | Initial release - Phase 7 Frontend Integration |

---

**Last Updated**: January 30, 2025
**Status**: Production Ready
