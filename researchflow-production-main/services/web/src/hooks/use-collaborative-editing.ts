/**
 * use-collaborative-editing
 *
 * Yjs document management, WebSocket provider, IndexedDB persistence,
 * awareness (presence), and content binding for the collaborative editor.
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import * as Y from 'yjs';
import { WebsocketProvider } from 'y-websocket';
import { IndexeddbPersistence } from 'y-indexeddb';

export interface Position {
  line: number;
  ch: number;
}

export interface UserPresence {
  id: string;
  name: string;
  color: string;
  cursor?: { line: number; ch: number };
  selection?: { anchor: Position; head: Position };
}

export interface UseCollaborativeEditingOptions {
  manuscriptId: string;
  sectionId: string;
  userId: string;
  userName: string;
  userColor: string;
  onContentChange?: (content: string) => void;
  onPresenceChange?: (users: UserPresence[]) => void;
  /** Optional: token for Hocuspocus auth (LIVE mode) */
  getToken?: () => Promise<string | null>;
}

function getWebSocketUrl(): string {
  const isDev = import.meta.env.DEV;
  const isHttps = typeof window !== 'undefined' && window.location.protocol === 'https:';
  const wsProtocol = isHttps ? 'wss:' : 'ws:';

  const wsUrl = import.meta.env.VITE_WS_URL || import.meta.env.VITE_COLLAB_URL;
  if (wsUrl) return wsUrl;

  if (isDev) {
    return 'ws://localhost:1234';
  }
  if (typeof window !== 'undefined') {
    const wsHost = window.location.host;
    return `${wsProtocol}//${wsHost}/collab`;
  }
  return 'ws://localhost:1234';
}

/**
 * Hook for Yjs collaborative editing: document, IndexedDB, WebSocket, awareness, content.
 */
export function useCollaborativeEditing({
  manuscriptId,
  sectionId,
  userId,
  userName,
  userColor,
  onContentChange,
  onPresenceChange,
  getToken,
}: UseCollaborativeEditingOptions) {
  const [connected, setConnected] = useState(false);
  const [synced, setSynced] = useState(false);
  const [offline, setOffline] = useState(false);
  const [presence, setPresence] = useState<UserPresence[]>([]);
  const [content, setContentState] = useState('');

  const ydocRef = useRef<Y.Doc | null>(null);
  const providerRef = useRef<WebsocketProvider | null>(null);
  const persistenceRef = useRef<IndexeddbPersistence | null>(null);
  const observerRef = useRef<(() => void) | null>(null);
  const onContentChangeRef = useRef(onContentChange);
  const onPresenceChangeRef = useRef(onPresenceChange);

  onContentChangeRef.current = onContentChange;
  onPresenceChangeRef.current = onPresenceChange;

  // Stable room name for Hocuspocus (auth expects manuscript:uuid)
  const roomName = `manuscript:${manuscriptId}`;

  // Content: Y.Text for this section (available after effect runs)
  const getYText = useCallback((): Y.Text => {
    const ydoc = ydocRef.current;
    if (!ydoc) return new Y.Doc().getText(sectionId); // fallback for type safety; effect will attach real doc
    return ydoc.getText(sectionId);
  }, [sectionId]);

  // Initialize IndexedDB persistence and WebSocket provider
  useEffect(() => {
    if (!manuscriptId || !sectionId) return;

    let cancelled = false;
    const ydoc = new Y.Doc();
    ydocRef.current = ydoc;
    const dbName = `researchflow-manuscript-${manuscriptId}`;

    const persistence = new IndexeddbPersistence(dbName, ydoc);
    persistenceRef.current = persistence;

    persistence.whenSynced.then(() => {
      const yText = ydoc.getText(sectionId);
      const text = yText.toString();
      setContentState(text);
      onContentChangeRef.current?.(text);
    });

    const wsUrl = getWebSocketUrl();

    void (async () => {
      const token = await getToken?.() ?? null;
      if (cancelled) return;
      const urlWithAuth = token
        ? `${wsUrl}${wsUrl.includes('?') ? '&' : '?'}token=${encodeURIComponent(token)}`
        : wsUrl;
      const provider = new WebsocketProvider(urlWithAuth, roomName, ydoc, {
        connect: true,
      });
      if (cancelled) {
        provider.destroy();
        return;
      }
      providerRef.current = provider;

      provider.on('status', (event: { status: string }) => {
        setConnected(event.status === 'connected');
        setOffline(event.status === 'disconnected');
      });

      provider.on('sync', (isSynced: boolean) => {
        setSynced(isSynced);
        if (isSynced) {
          const yText = ydoc.getText(sectionId);
          const text = yText.toString();
          setContentState(text);
          onContentChangeRef.current?.(text);
        }
      });

      // Awareness: local user
      const awareness = provider.awareness;
      awareness.setLocalStateField('user', {
        id: userId,
        name: userName,
        color: userColor,
      });

      awareness.on('change', () => {
        const states = awareness.getStates();
        const users: UserPresence[] = [];
        states.forEach((state, clientId) => {
          if (clientId === awareness.clientID) return;
          const user = state.user as
            | { id: string; name: string; color: string; cursor?: { line: number; ch: number }; selection?: { anchor: Position; head: Position } }
            | undefined;
          if (user) {
            users.push({
              id: user.id,
              name: user.name,
              color: user.color,
              cursor: user.cursor,
              selection: user.selection,
            });
          }
        });
        setPresence(users);
        onPresenceChangeRef.current?.(users);
      });

      // Observe Y.Text for this section
      const yText = ydoc.getText(sectionId);
      const observer = () => {
        const text = yText.toString();
        setContentState(text);
        onContentChangeRef.current?.(text);
      };
      observerRef.current = observer;
      yText.observe(observer);

      // Initial content
      const initial = yText.toString();
      if (initial) {
        setContentState(initial);
        onContentChangeRef.current?.(initial);
      }
    })();

    return () => {
      cancelled = true;
      const provider = providerRef.current;
      const observer = observerRef.current;
      if (observer) {
        try {
          ydoc.getText(sectionId).unobserve(observer);
        } catch {
          // ignore if already unobserved
        }
        observerRef.current = null;
      }
      if (provider) {
        provider.destroy();
        providerRef.current = null;
      }
      persistence.destroy();
      persistenceRef.current = null;
      ydocRef.current = null;
    };
  }, [manuscriptId, sectionId, roomName, userId, userName, userColor, getToken]);

  // Update content (insert/replace) in Y.Text
  const setContent = useCallback(
    (text: string) => {
      const ydoc = ydocRef.current;
      if (!ydoc) return;
      const yText = ydoc.getText(sectionId);
      const current = yText.toString();
      if (current === text) return;
      ydoc.transact(() => {
        yText.delete(0, current.length);
        yText.insert(0, text);
      });
    },
    [sectionId]
  );

  // Update local awareness cursor/selection (for ProseMirror or textarea binding)
  const setCursor = useCallback(
    (cursor: { line: number; ch: number } | null) => {
      providerRef.current?.awareness.setLocalStateField('cursor', cursor ?? undefined);
    },
    []
  );

  const setSelection = useCallback(
    (selection: { anchor: Position; head: Position } | null) => {
      providerRef.current?.awareness.setLocalStateField('selection', selection ?? undefined);
    },
    []
  );

  return {
    ydoc: ydocRef.current,
    getYText,
    connected,
    synced,
    offline,
    presence,
    content,
    setContent,
    setCursor,
    setSelection,
    provider: providerRef.current,
  };
}
