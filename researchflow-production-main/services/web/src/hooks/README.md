# Custom Hooks Documentation

## useAgentStatus Hook

Located in `useAgentStatus.ts`, this is a React custom hook for managing real-time agent status through WebSocket connections.

### Quick Start

```tsx
import { useAgentStatus } from './useAgentStatus';

function MyComponent() {
  const { status, phase, progress, error, isConnected } = useAgentStatus();

  return (
    <div>
      <p>Phase: {phase}</p>
      <p>Progress: {progress}%</p>
      <p>Status: {status}</p>
    </div>
  );
}
```

### Configuration

The hook accepts a `UseAgentStatusConfig` object with the following options:

#### `wsUrl?: string`
The WebSocket URL to connect to. If not provided, automatically constructs from current page origin.

**Default**: `${protocol}://${host}/api/agent/ws`

```tsx
useAgentStatus({
  wsUrl: 'wss://agent-api.example.com/ws'
})
```

#### `autoConnect?: boolean`
Whether to automatically connect on component mount.

**Default**: `true`

```tsx
const hook = useAgentStatus({ autoConnect: false });

// Manually connect when ready
hook.connect();
```

#### `reconnectInterval?: number`
Initial milliseconds to wait before reconnection attempt. Uses exponential backoff.

**Default**: `3000` (3 seconds)

```tsx
useAgentStatus({
  reconnectInterval: 5000 // Start with 5 second delay
})
```

#### `maxReconnectAttempts?: number`
Maximum number of automatic reconnection attempts before giving up.

**Default**: `10`

```tsx
useAgentStatus({
  maxReconnectAttempts: 20 // Try reconnecting up to 20 times
})
```

#### `heartbeatInterval?: number`
Interval in milliseconds between heartbeat pings to detect stale connections.

**Default**: `30000` (30 seconds)

```tsx
useAgentStatus({
  heartbeatInterval: 60000 // Check connection every 60 seconds
})
```

#### `onError?: (error: Error) => void`
Callback function triggered when errors occur.

```tsx
useAgentStatus({
  onError: (error) => {
    console.error('Agent connection error:', error.message);
    // Send error to logging service
    logToSentry(error);
  }
})
```

#### `onPhaseChange?: (phase: AgentPhase) => void`
Callback triggered when the agent transitions to a new phase.

```tsx
useAgentStatus({
  onPhaseChange: (newPhase) => {
    console.log(`Agent entered ${newPhase} phase`);
    // Update analytics
    trackEvent('agent_phase_change', { phase: newPhase });
  }
})
```

### Return Values

The hook returns an object with the following properties:

#### State Properties

```typescript
{
  status: 'idle' | 'running' | 'paused' | 'completed' | 'failed';
  phase: 'DataPrep' | 'Analysis' | 'Quality' | 'IRB' | 'Manuscript';
  progress: number;        // 0-100
  error: string | null;    // Error message if any
  isConnected: boolean;    // WebSocket connection state
  lastUpdate: Date | null; // Timestamp of last update
}
```

#### Control Methods

```typescript
{
  connect(): void;    // Manually establish connection
  disconnect(): void; // Manually close connection
}
```

### Message Types

The hook handles the following WebSocket message types:

#### Status Update
```json
{
  "type": "status",
  "status": "running"
}
```

#### Phase Transition
```json
{
  "type": "phase",
  "phase": "Analysis"
}
```

#### Progress Update
```json
{
  "type": "progress",
  "progress": 45
}
```

#### Error Message
```json
{
  "type": "error",
  "message": "Analysis failed due to invalid data"
}
```

#### Heartbeat Ping
```json
{
  "type": "ping"
}
```

### Advanced Usage

#### Connection Control

```tsx
function AgentController() {
  const { connect, disconnect, isConnected } = useAgentStatus({
    autoConnect: false
  });

  return (
    <div>
      <button
        onClick={connect}
        disabled={isConnected}
      >
        Connect Agent
      </button>
      <button
        onClick={disconnect}
        disabled={!isConnected}
      >
        Disconnect Agent
      </button>
    </div>
  );
}
```

#### Phase-Based Rendering

```tsx
function PhaseSpecificUI() {
  const { phase, progress } = useAgentStatus();

  switch (phase) {
    case 'DataPrep':
      return <DataPreparationUI progress={progress} />;
    case 'Analysis':
      return <AnalysisUI progress={progress} />;
    case 'Quality':
      return <QualityCheckUI progress={progress} />;
    case 'IRB':
      return <IRBReviewUI progress={progress} />;
    case 'Manuscript':
      return <ManuscriptUI progress={progress} />;
    default:
      return null;
  }
}
```

#### Error Handling

```tsx
function RobustAgent() {
  const [errors, setErrors] = React.useState<string[]>([]);

  const { error } = useAgentStatus({
    onError: (err) => {
      setErrors(prev => [...prev, err.message]);
      // Clear errors after 5 seconds
      setTimeout(() => {
        setErrors(prev => prev.slice(1));
      }, 5000);
    }
  });

  return (
    <div>
      {errors.map((err, idx) => (
        <div key={idx} className="alert alert-error">
          {err}
        </div>
      ))}
    </div>
  );
}
```

#### Auto-Reconnection Strategy

The hook implements exponential backoff for reconnection:

1. **Attempt 1**: 3 seconds
2. **Attempt 2**: 4.5 seconds (3 × 1.5)
3. **Attempt 3**: 6.75 seconds (4.5 × 1.5)
4. **Attempt 4+**: Continues doubling until capped at 30 seconds

Configure the strategy:

```tsx
useAgentStatus({
  reconnectInterval: 1000,      // Start with 1 second
  maxReconnectAttempts: 20,     // Try up to 20 times
  heartbeatInterval: 10000,     // Check every 10 seconds
})
```

#### Multiple Instances

For multiple independent agents, create separate hook instances:

```tsx
function MultiAgentDashboard() {
  const agent1 = useAgentStatus({
    wsUrl: 'wss://agent1.example.com/ws'
  });

  const agent2 = useAgentStatus({
    wsUrl: 'wss://agent2.example.com/ws'
  });

  return (
    <div>
      <AgentPanel {...agent1} title="Agent 1" />
      <AgentPanel {...agent2} title="Agent 2" />
    </div>
  );
}
```

#### Shared State with Context

To share agent status across your app, create a context:

```tsx
import React, { createContext, useContext } from 'react';
import { useAgentStatus } from './useAgentStatus';

const AgentContext = createContext(null);

export function AgentProvider({ children }) {
  const agentStatus = useAgentStatus();

  return (
    <AgentContext.Provider value={agentStatus}>
      {children}
    </AgentContext.Provider>
  );
}

export function useAgent() {
  const context = useContext(AgentContext);
  if (!context) {
    throw new Error('useAgent must be used within AgentProvider');
  }
  return context;
}
```

Then wrap your app:

```tsx
function App() {
  return (
    <AgentProvider>
      <Dashboard />
    </AgentProvider>
  );
}
```

And use in any component:

```tsx
function MyComponent() {
  const { status, phase } = useAgent();
  return <div>{phase}: {status}</div>;
}
```

### Lifecycle

The hook manages the following lifecycle:

1. **Initialization**: On component mount
2. **Connection**: Establishes WebSocket connection if `autoConnect` is true
3. **Listening**: Receives and processes messages
4. **Heartbeat**: Sends periodic pings to maintain connection
5. **Reconnection**: Attempts reconnection with backoff on disconnection
6. **Cleanup**: Closes connection and clears timers on unmount

### Performance Tips

1. **Use Context for Shared State**: Avoid multiple hook instances listening to the same agent
2. **Memoize Callbacks**: Use `useCallback` for `onError` and `onPhaseChange`
3. **Conditional Rendering**: Only render status components when connected
4. **Debounce Updates**: Use `useMemo` to limit re-renders from frequent updates

```tsx
function OptimizedComponent() {
  const { status, phase, progress } = useAgentStatus();

  const memoizedConfig = React.useMemo(() => ({
    status,
    phase,
    progress
  }), [status, phase, progress]);

  return <StatusDisplay config={memoizedConfig} />;
}
```

### Troubleshooting

#### Connection not established
- Check browser console for WebSocket errors
- Verify `wsUrl` is correct
- Ensure backend server is running and accessible
- Check CORS/WebSocket proxy settings

#### Messages not received
- Verify backend is sending messages in correct JSON format
- Check heartbeat interval isn't too aggressive
- Look for timeout errors in console
- Ensure message `type` field is one of: `status`, `progress`, `phase`, `error`, `ping`

#### Rapid reconnection
- Check if `maxReconnectAttempts` is being exceeded
- Look for backend errors in server logs
- Increase `reconnectInterval` for slower reconnection
- Check network connectivity

#### Memory leaks
- Verify hook cleanup runs on unmount
- Check that `disconnect()` is called in cleanup functions
- Look for multiple instances of the hook unintentionally created
- Monitor browser DevTools for unclosed WebSocket connections

### Testing

Example test setup:

```typescript
// Mock WebSocket
global.WebSocket = jest.fn(() => ({
  send: jest.fn(),
  close: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
}));

test('updates status on message', () => {
  const { result } = renderHook(() => useAgentStatus());

  // Simulate message
  const message = new MessageEvent('message', {
    data: JSON.stringify({ type: 'status', status: 'running' })
  });
  result.current.ws?.onmessage?.(message);

  expect(result.current.status).toBe('running');
});
```

---

For more information, see the main [README.md](../README.md) in the components directory.
