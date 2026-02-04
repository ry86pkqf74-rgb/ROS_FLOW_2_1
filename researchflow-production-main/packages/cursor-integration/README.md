# Cursor Integration Package

Enables bidirectional communication between Cursor IDE and ResearchFlow AI agents.

## Features

- **Agent Triggers**: Trigger AI agents directly from code comments
- **Code Sync**: Automatic synchronization of code changes
- **Real-time Progress**: Stream task progress back to the editor
- **Inline Suggestions**: Receive AI-generated code suggestions inline

## Installation

```bash
npm install @researchflow/cursor-integration
```

## Usage

### Initialize Configuration

```typescript
import { CursorConfig } from '@researchflow/cursor-integration';

const config: CursorConfig = {
  webhookUrl: 'https://your-ros-instance.com/api',
  apiKey: 'your-api-key',
  workspaceId: 'workspace-123',
};
```

### Trigger AI Agent from Code

Add special comments in your code:

```typescript
// @agent fix-this {"priority": "high"}
function buggyFunction() {
  // problematic code here
}

// @agent review
class ImportantClass {
  // code to review
}

// @agent test {"framework": "jest"}
function needsTests() {
  // code that needs tests
}
```

### Send Code Changes

```typescript
import { sendCodeChangeEvent } from '@researchflow/cursor-integration';

await sendCodeChangeEvent(config, {
  type: 'code-change',
  workspaceId: 'workspace-123',
  filePath: 'src/app.ts',
  language: 'typescript',
  changes: [
    {
      startLine: 10,
      endLine: 15,
      oldText: 'old code...',
      newText: 'new code...',
    },
  ],
  timestamp: new Date().toISOString(),
  userId: 'user-123',
});
```

### Subscribe to Task Progress

```typescript
import { subscribeToTaskProgress } from '@researchflow/cursor-integration';

const unsubscribe = subscribeToTaskProgress(
  config,
  'task-123',
  (notification) => {
    console.log(`Task ${notification.taskId}: ${notification.status}`);
    if (notification.result) {
      // Apply code suggestion or show result
      console.log(notification.result.content);
    }
  },
  (error) => {
    console.error('Progress stream error:', error);
  }
);

// Cleanup when done
unsubscribe();
```

## Available Agent Commands

| Command | Description | Example |
|---------|-------------|---------|
| `fix-this` | Automatically fix bugs | `// @agent fix-this` |
| `review` | Code review with suggestions | `// @agent review` |
| `optimize` | Optimize for performance | `// @agent optimize {"focus": "memory"}` |
| `test` | Generate unit tests | `// @agent test {"framework": "jest"}` |
| `document` | Generate documentation | `// @agent document {"style": "jsdoc"}` |
| `refactor` | Refactor code structure | `// @agent refactor` |
| `explain` | Explain complex code | `// @agent explain` |

## API Reference

See [API Documentation](./docs/api.md) for detailed information.

## License

MIT
