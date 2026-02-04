import { Server } from 'socket.io';

type TypingState = {
  timeout?: NodeJS.Timeout;
  isTyping: boolean;
};

/**
 * Presence / collaboration websocket server.
 *
 * Enhancements:
 * - cursor:update / selection:update broadcasting
 * - typing indicators with debounce
 * - presence:heartbeat with stale connection timeout
 */
export function createWebsocketServer(io: Server) {
  // Track per-socket typing state for debouncing typing indicators
  const typingBySocket = new Map<string, TypingState>();

  // Track heartbeat timestamps for presence
  const lastHeartbeatBySocket = new Map<string, number>();

  const HEARTBEAT_TIMEOUT_MS = 30_000;
  const TYPING_DEBOUNCE_MS = 1_000;

  function roomFor(manuscriptId: string) {
    return `manuscript:${manuscriptId}`;
  }

  function markHeartbeat(socketId: string) {
    lastHeartbeatBySocket.set(socketId, Date.now());
  }

  function clearTyping(socketId: string) {
    const state = typingBySocket.get(socketId);
    if (state?.timeout) clearTimeout(state.timeout);
    typingBySocket.delete(socketId);
  }

  // Periodically disconnect stale sockets
  const interval = setInterval(() => {
    const now = Date.now();

    for (const [socketId, last] of lastHeartbeatBySocket.entries()) {
      if (now - last > HEARTBEAT_TIMEOUT_MS) {
        const socket = io.sockets.sockets.get(socketId);
        if (socket) {
          socket.emit('presence:stale', { reason: 'heartbeat_timeout' });
          socket.disconnect(true);
        }

        lastHeartbeatBySocket.delete(socketId);
        clearTyping(socketId);
      }
    }
  }, 5_000);

  io.on('connection', (socket) => {
    // Initialize heartbeat so freshly connected sockets are not immediately stale.
    markHeartbeat(socket.id);

    socket.on('join', ({ manuscriptId, userId }: { manuscriptId: string; userId: string }) => {
      socket.join(roomFor(manuscriptId));
      socket.data.manuscriptId = manuscriptId;
      socket.data.userId = userId;

      markHeartbeat(socket.id);

      socket.to(roomFor(manuscriptId)).emit('presence:join', {
        userId,
        socketId: socket.id,
        manuscriptId,
      });
    });

    socket.on('leave', ({ manuscriptId, userId }: { manuscriptId: string; userId: string }) => {
      socket.leave(roomFor(manuscriptId));
      markHeartbeat(socket.id);

      socket.to(roomFor(manuscriptId)).emit('presence:leave', {
        userId,
        socketId: socket.id,
        manuscriptId,
      });
    });

    /**
     * Cursor positions broadcast.
     * Client should send: { manuscriptId, userId, sectionId?, cursor: { x,y, pos? } }
     */
    socket.on(
      'cursor:update',
      (payload: {
        manuscriptId: string;
        userId: string;
        sectionId?: string;
        cursor: Record<string, any>;
      }) => {
        const { manuscriptId } = payload;
        if (!manuscriptId) return;

        markHeartbeat(socket.id);
        socket.to(roomFor(manuscriptId)).emit('cursor:update', {
          ...payload,
          socketId: socket.id,
          ts: Date.now(),
        });
      },
    );

    /**
     * Selection ranges broadcast.
     * Client should send: { manuscriptId, userId, sectionId?, selection: { start,end } }
     */
    socket.on(
      'selection:update',
      (payload: {
        manuscriptId: string;
        userId: string;
        sectionId?: string;
        selection: Record<string, any>;
      }) => {
        const { manuscriptId } = payload;
        if (!manuscriptId) return;

        markHeartbeat(socket.id);
        socket.to(roomFor(manuscriptId)).emit('selection:update', {
          ...payload,
          socketId: socket.id,
          ts: Date.now(),
        });
      },
    );

    /**
     * Typing indicators.
     * typing:start -> broadcast immediately and schedule auto typing:stop after debounce.
     * typing:stop  -> clear timer and broadcast stop.
     */
    socket.on(
      'typing:start',
      (payload: { manuscriptId: string; userId: string; sectionId?: string }) => {
        if (!payload?.manuscriptId) return;

        markHeartbeat(socket.id);

        const current = typingBySocket.get(socket.id);
        if (!current?.isTyping) {
          socket.to(roomFor(payload.manuscriptId)).emit('typing:start', {
            ...payload,
            socketId: socket.id,
            ts: Date.now(),
          });
        }

        // Debounce stop
        if (current?.timeout) clearTimeout(current.timeout);
        const timeout = setTimeout(() => {
          typingBySocket.set(socket.id, { isTyping: false });
          socket.to(roomFor(payload.manuscriptId)).emit('typing:stop', {
            ...payload,
            socketId: socket.id,
            ts: Date.now(),
            reason: 'debounce',
          });
        }, TYPING_DEBOUNCE_MS);

        typingBySocket.set(socket.id, { isTyping: true, timeout });
      },
    );

    socket.on(
      'typing:stop',
      (payload: { manuscriptId: string; userId: string; sectionId?: string }) => {
        if (!payload?.manuscriptId) return;

        markHeartbeat(socket.id);
        clearTyping(socket.id);

        socket.to(roomFor(payload.manuscriptId)).emit('typing:stop', {
          ...payload,
          socketId: socket.id,
          ts: Date.now(),
        });
      },
    );

    /**
     * Heartbeat: clients should send every ~10s.
     */
    socket.on(
      'presence:heartbeat',
      (payload: { manuscriptId?: string; userId?: string }) => {
        markHeartbeat(socket.id);

        // Optional: echo ack
        socket.emit('presence:heartbeat:ack', {
          ts: Date.now(),
          manuscriptId: payload?.manuscriptId ?? socket.data.manuscriptId,
          userId: payload?.userId ?? socket.data.userId,
        });
      },
    );

    socket.on('disconnect', () => {
      lastHeartbeatBySocket.delete(socket.id);
      clearTyping(socket.id);
    });
  });

  // Best-effort cleanup if parent disposes io (no official hook here)
  io.engine.on('close', () => {
    clearInterval(interval);
    typingBySocket.clear();
    lastHeartbeatBySocket.clear();
  });
}
