/**
 * Yjs-Powered Collaborative Editor
 *
 * Features:
 * - Real-time CRDT editing via Y.Text; changes merge conflict-free.
 * - Cursor and selection presence via awareness; other users see position/selection.
 * - Offline-first: IndexedDB persistence (y-indexeddb); edits persist locally and sync on reconnect.
 * - WebSocket provider (y-websocket) connects to Hocuspocus; room name manuscript:{manuscriptId}.
 * - Reconnection handling: status indicators and optional manual reconnect.
 *
 * Uses manuscriptId + sectionId for document/section; exposes onContentChange and onPresenceChange.
 * Word count and optional Save callback for integration with manuscript save flow.
 *
 * ---------------------------------------------------------------------------
 * Behavior
 * ---------------------------------------------------------------------------
 *
 * 1. Document and room
 *    - One Y.Doc per manuscript (manuscriptId). Sections share the same doc; each section
 *      uses a Y.Text keyed by sectionId. Room name for Hocuspocus is manuscript:{manuscriptId}
 *      so auth and persistence align with the collab server.
 *
 * 2. IndexedDB
 *    - IndexeddbPersistence uses db name researchflow-manuscript-{manuscriptId}. All sections
 *      of the manuscript are persisted in the same store. On load, whenSynced fires and
 *      content is applied from local storage before WebSocket sync.
 *
 * 3. WebSocket and sync
 *    - WebsocketProvider connects to VITE_WS_URL / VITE_COLLAB_URL or localhost:1234 (dev)
 *      or /collab (prod). Sync state: connected (transport up) and synced (doc in sync).
 *      When synced becomes true, content is up to date with server.
 *
 * 4. Awareness (presence)
 *    - Local user sets awareness fields: user (id, name, color), cursor (line, ch), selection
 *      (anchor, head). Other clients are exposed as UserPresence[]. onPresenceChange is
 *      called when awareness changes. PresenceIndicator shows avatars and cursor/selection
 *      tooltips.
 *
 * 5. Content flow
 *    - User types -> handleChange -> setLocalValue, setContent (Y.Text), setCursor/setSelection.
 *    - Y.Text observer in hook -> setContentState -> content prop -> useEffect -> setLocalValue.
 *    - Remote or sync update -> same path: content updates -> localValue updates.
 *
 * 6. Offline
 *    - When disconnected, offline is true; edits still go to Y.Text and IndexedDB. On
 *      reconnect, provider syncs and merges; no conflict resolution needed (CRDT).
 *
 * 7. Save
 *    - Optional onSave; showSaveButton shows a toolbar Save button. Ctrl+S / Cmd+S also
 *      triggers onSave when provided.
 *
 * ---------------------------------------------------------------------------
 * Integration
 * ---------------------------------------------------------------------------
 *
 * - Manuscript editor page: pass manuscriptId, sectionId, and user from useAuth(); derive
 *   userName (displayName or firstName/lastName) and assign userColor from a small palette.
 * - For section-level persistence on the backend, continue using PATCH /api/manuscripts/:id/sections
 *   when saving; CollaborativeEditor can call onSave which triggers that API from the parent.
 *
 * ---------------------------------------------------------------------------
 * Reconnection and error handling
 * ---------------------------------------------------------------------------
 *
 * - WebsocketProvider (y-websocket) automatically attempts to reconnect when the connection drops.
 *   Status events: "connecting" | "connected" | "disconnected". When status is "disconnected",
 *   offline is true; when "connected", connected is true. Sync event fires with true when the
 *   document is in sync with the server.
 * - The Reconnect button refetches local value from the hook's content (which may have been
 *   updated after a sync) and clears any error state. It does not force the provider to
 *   reconnect; the provider handles that. Use it to refresh the editor after reconnection.
 * - Error state is optional; set it from parent (e.g. on save failure) or when detecting
 *   repeated disconnects. When connected and synced, we clear error.
 * - Offline hint is shown when disconnected so users know they can keep editing; changes
 *   persist in IndexedDB and sync when reconnected.
 *
 * ---------------------------------------------------------------------------
 * Usage example
 * ---------------------------------------------------------------------------
 *
 * ```tsx
 * const { user } = useAuth();
 * const manuscriptId = params.id ?? 'new';
 * const sectionId = 'introduction';
 *
 * <CollaborativeEditor
 *   manuscriptId={manuscriptId}
 *   sectionId={sectionId}
 *   userId={user?.id ?? 'anonymous'}
 *   userName={user?.displayName ?? user?.firstName ?? 'Anonymous'}
 *   userColor={getUserColor(user?.id)}
 *   onContentChange={(content) => handleContentChange(sectionId, content)}
 *   onPresenceChange={(users) => setPresence(users)}
 *   onSave={(content) => saveSection(sectionId, content)}
 *   showSaveButton
 *   minHeight={400}
 * />
 * ```
 *
 * getUserColor can map user id to a stable color from a small palette (e.g. 8 colors).
 *
 * ---------------------------------------------------------------------------
 * Cursor and selection (awareness)
 * ---------------------------------------------------------------------------
 *
 * - On change (handleChange) we compute cursor from textarea selectionStart and
 *   selection (anchor/head) from selectionStart/selectionEnd. We map offset to line/ch
 *   via getLineChFromOffset (split by newline, count lines and column in last line).
 * - We call setCursor({ line, ch }) and setSelection({ anchor, head }) so other clients
 *   see our position and selection in awareness. PresenceIndicator shows other users'
 *   cursors and selections in tooltips (e.g. "Alice — line 5, col 12").
 * - On blur we clear cursor and selection (setCursor(null), setSelection(null)) so we
 *   don't show a stale position when the user has left the editor.
 * - Other clients' presence is exposed as UserPresence[] with optional cursor and
 *   selection; the hook maps awareness states to this shape and calls onPresenceChange.
 *
 * ---------------------------------------------------------------------------
 * Conflict resolution (CRDT)
 * ---------------------------------------------------------------------------
 *
 * - Yjs uses a CRDT (Y.Text) for the section content; no custom merge logic is needed.
 *   Concurrent edits from multiple users merge automatically and deterministically.
 *   When offline, edits are stored in IndexedDB; on reconnect, the provider syncs
 *   and merges with the server state. The hook does not expose a "dirty" or
 *   "last synced" flag; the parent can track save state if needed (e.g. compare
 *   localValue with last saved content).
 *
 * ---------------------------------------------------------------------------
 * Props
 * ---------------------------------------------------------------------------
 *
 * - manuscriptId: manuscript identifier; used for room name manuscript:{manuscriptId}.
 * - sectionId: section identifier; used for Y.Text key and data-testid.
 * - userId, userName, userColor: local user for awareness (presence).
 * - onContentChange: optional; called when content changes (local or remote).
 * - onPresenceChange: optional; called when other users' presence changes.
 * - onSave: optional; called when user triggers Save (button or Ctrl+S).
 * - showSaveButton: optional; show Save button in toolbar when onSave is provided.
 * - minHeight: optional; minimum height of the textarea in pixels (default 400).
 *
 * ---------------------------------------------------------------------------
 * Testing
 * ---------------------------------------------------------------------------
 *
 * - The textarea has data-testid={`collab-editor-${sectionId}`} for E2E tests.
 * - To test offline behavior, disconnect the WebSocket or use a service worker;
 *   edits should persist and sync when reconnected.
 * - To test presence, open the same document in two tabs or two clients; each
 *   should see the other's avatar and cursor/selection in PresenceIndicator.
 *
 * ---------------------------------------------------------------------------
 * Implementation notes
 * ---------------------------------------------------------------------------
 *
 * - Local value is kept in state (localValue) and synced from hook content when
 *   content changes (remote, sync, or initial load). On user input we update
 *   localValue and setContent (Y.Text); the hook observes Y.Text and updates
 *   content, which triggers useEffect and setLocalValue — no loop because we
 *   set the same value.
 * - Cursor and selection are sent to awareness on change and select; on blur we
 *   clear them so other users don't see a stale position. The hook maps awareness
 *   states to UserPresence[] and calls onPresenceChange.
 * - Word count is computed from localValue via countWords (trim, split by whitespace).
 * - Save: onSave is called when user clicks Save or presses Ctrl+S/Cmd+S; we
 *   pass localValue. Parent can persist to API (e.g. PATCH manuscript section).
 * - Error state is optional; we clear it on reconnect and when connected+synced.
 *   Parent can set error (e.g. on save failure) via a callback or ref if we add one.
 * - Reconnect button refetches local value from content and clears error; the
 *   WebsocketProvider handles actual reconnection. When synced, content is up
 *   to date so localValue will reflect the latest after sync.
 * - IndexedDB persistence is handled in the hook (IndexeddbPersistence with
 *   researchflow-manuscript-{manuscriptId}); we don't touch it here.
 * - Room name manuscript:{manuscriptId} is used so Hocuspocus auth (checkDocumentPermission
 *   with manuscript:* pattern) can allow access. Section content is keyed by
 *   sectionId inside the same Y.Doc so one WebSocket connection per manuscript.
 *
 * ---------------------------------------------------------------------------
 * Dependencies and environment
 * ---------------------------------------------------------------------------
 *
 * - use-collaborative-editing: Y.Doc, IndexeddbPersistence, WebsocketProvider,
 *   awareness, Y.Text(sectionId), content/setContent, setCursor/setSelection.
 * - PresenceIndicator: UserPresence[], avatar badges, cursor/selection tooltips.
 * - WebSocket URL: VITE_WS_URL or VITE_COLLAB_URL; else localhost:1234 (dev)
 *   or current host /collab (prod). Hocuspocus server runs on port 1234 (dev).
 * - IndexedDB: researchflow-manuscript-{manuscriptId}; one store per manuscript.
 * - No HocuspocusProvider or token here; add getToken to hook and use
 *   HocuspocusProvider when LIVE mode requires JWT.
 *
 * ---------------------------------------------------------------------------
 * References
 * ---------------------------------------------------------------------------
 *
 * - Yjs: https://docs.yjs.dev/
 * - y-websocket: https://docs.yjs.dev/ecosystem/connection-provider/y-websocket
 * - y-indexeddb: https://docs.yjs.dev/ecosystem/connection-provider/y-indexeddb
 * - Hocuspocus: https://tiptap.dev/docs/hocuspocus/provider/introduction
 * - Collab server: services/collab (Hocuspocus on port 1234)
 * - Hook: use-collaborative-editing.ts (Y.Doc, IndexedDB, WebSocket, awareness)
 * - PresenceIndicator: PresenceIndicator.tsx (avatars, cursor/selection tooltips)
 * - Artifact editor: ArtifactCollaborativeEditor.tsx (ProseMirror + y-prosemirror)
 *
 * ---------------------------------------------------------------------------
 * Future work
 * ---------------------------------------------------------------------------
 *
 * - Optional rich text mode: use ProseMirror + y-prosemirror with Y.XmlFragment
 *   (e.g. ydoc.getXmlFragment('prosemirror-' + sectionId)); would require
 *   syncing plain text (onContentChange) from ProseMirror doc.textContent or
 *   a separate Y.Text for persistence.
 * - HocuspocusProvider + getToken for LIVE mode JWT auth when collab server
 *   requires authentication.
 * - Last-synced timestamp: hook could expose lastSyncedAt for UI (e.g. "Synced 2 min ago").
 * - Dirty flag: compare localValue with last saved content for "Unsaved changes" indicator.
 * - Retry count: increment on disconnect and show retry hint after N disconnects.
 * - Optional word budget: pass minWords/maxWords and show validation badge (like SectionEditor).
 *
 * ---------------------------------------------------------------------------
 * Glossary
 * ---------------------------------------------------------------------------
 *
 * - Y.Doc: Yjs document; holds shared types (Y.Text, Y.Map, etc.).
 * - Y.Text: CRDT shared type for plain text; used for section content.
 * - IndexeddbPersistence: persists Y.Doc to IndexedDB for offline.
 * - WebsocketProvider: syncs Y.Doc over WebSocket with Hocuspocus.
 * - Awareness: Yjs protocol for ephemeral state (cursors, selection, user info).
 * - Room name: document identifier sent to server (manuscript:{manuscriptId}).
 * - Synced: document is in sync with server (all updates applied).
 * - Connected: WebSocket transport is connected.
 * - Presence: other users' awareness state (cursor, selection, name, color).
 * - UserPresence: id, name, color, optional cursor, optional selection.
 * - Position: { line, ch } (0-based line and column).
 *
 * ---------------------------------------------------------------------------
 * Edge cases and known limitations
 * ---------------------------------------------------------------------------
 *
 * - manuscriptId "new": room name manuscript:new; server may not persist until
 *   manuscript is created; ensure backend creates document when manuscript is saved.
 * - Rapid reconnection: if user reconnects quickly, content may update multiple
 *   times; we always set localValue from content so we stay in sync.
 * - Large documents: Y.Text and IndexedDB handle large text; consider debouncing
 *   onContentChange if parent does heavy work on every change.
 * - Multiple sections: each section uses the same Y.Doc (manuscriptId) but
 *   different Y.Text(sectionId); switching section unmounts/remounts or
 *   changes sectionId; hook effect re-runs and attaches to the correct Y.Text.
 * - Cursor/selection: line/ch are 0-based; PresenceIndicator shows line+1 for
 *   user-facing display. Selection range is anchor to head (may be reversed).
 *
 * ---------------------------------------------------------------------------
 * Accessibility
 * ---------------------------------------------------------------------------
 *
 * - The textarea has aria-label={`Collaborative editor for section ${sectionId}`}
 *   for screen readers. Connection status uses aria-hidden on icons so
 *   the text label is announced. Save and Reconnect buttons have clear labels.
 *
 * @see use-collaborative-editing
 * @see PresenceIndicator
 * @see ArtifactCollaborativeEditor
 */

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useCollaborativeEditing } from '@/hooks/use-collaborative-editing';
import { PresenceIndicator } from './PresenceIndicator';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Wifi,
  WifiOff,
  Loader2,
  RefreshCw,
  CloudOffline,
  Save,
  Type,
  AlertTriangle,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Types (task spec)
// ---------------------------------------------------------------------------

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

export interface CollaborativeEditorProps {
  manuscriptId: string;
  sectionId: string;
  userId: string;
  userName: string;
  userColor: string;
  onContentChange?: (content: string) => void;
  onPresenceChange?: (users: UserPresence[]) => void;
  /** Optional: called when user triggers Save (e.g. Ctrl+S or Save button) */
  onSave?: (content: string) => void;
  /** Optional: show Save button in toolbar */
  showSaveButton?: boolean;
  /** Optional: minimum height of the textarea in pixels */
  minHeight?: number;
}

// ---------------------------------------------------------------------------
// Helpers: map textarea selection to line/ch; word count
// ---------------------------------------------------------------------------

function getLineChFromOffset(text: string, offset: number): { line: number; ch: number } {
  const lines = text.slice(0, offset).split('\n');
  const line = lines.length - 1;
  const ch = lines[lines.length - 1]?.length ?? 0;
  return { line, ch };
}

function countWords(text: string): number {
  if (!text || !text.trim()) return 0;
  return text.trim().split(/\s+/).filter(Boolean).length;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function CollaborativeEditor({
  manuscriptId,
  sectionId,
  userId,
  userName,
  userColor,
  onContentChange,
  onPresenceChange,
  onSave,
  showSaveButton = false,
  minHeight = 400,
}: CollaborativeEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [localValue, setLocalValue] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    connected,
    synced,
    offline,
    presence,
    content,
    setContent,
    setCursor,
    setSelection,
  } = useCollaborativeEditing({
    manuscriptId,
    sectionId,
    userId,
    userName,
    userColor,
    onContentChange,
    onPresenceChange,
  });

  const wordCount = countWords(localValue);

  // ---------------------------------------------------------------------------
  // Content sync: hook content is source of truth for remote/sync/initial load.
  // When content changes (from hook), we update localValue so the textarea stays in sync.
  // ---------------------------------------------------------------------------
  useEffect(() => {
    setLocalValue(content);
  }, [content]);

  // ---------------------------------------------------------------------------
  // Keyboard: Ctrl+S / Cmd+S to save (when onSave is provided).
  // We preventDefault so the browser does not open Save dialog.
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        if (onSave) {
          setSaving(true);
          Promise.resolve(onSave(localValue)).finally(() => setSaving(false));
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onSave, localValue]);

  const handleSaveClick = useCallback(() => {
    if (!onSave) return;
    setSaving(true);
    Promise.resolve(onSave(localValue)).finally(() => setSaving(false));
  }, [onSave, localValue]);

  // ---------------------------------------------------------------------------
  // Content change: update local value, Y.Text via setContent, and awareness
  // (cursor/selection) so other users see our position and selection.
  // ---------------------------------------------------------------------------
  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const value = e.target.value;
      setLocalValue(value);
      setContent(value);
      onContentChange?.(value);
      // Update cursor position in awareness
      const ta = e.target;
      const start = getLineChFromOffset(value, ta.selectionStart);
      setCursor(start);
      setSelection({ anchor: start, head: getLineChFromOffset(value, ta.selectionEnd) });
    },
    [setContent, setCursor, setSelection, onContentChange]
  );

  // ---------------------------------------------------------------------------
  // Selection change: update awareness cursor/selection when user selects text
  // (without typing). Anchor and head are computed from selectionStart/End.
  // ---------------------------------------------------------------------------
  const handleSelect = useCallback(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    const text = localValue;
    const anchor = getLineChFromOffset(text, ta.selectionStart);
    const head = getLineChFromOffset(text, ta.selectionEnd);
    setCursor(anchor);
    setSelection({ anchor, head });
  }, [localValue, setCursor, setSelection]);

  // ---------------------------------------------------------------------------
  // Reconnection: refetch local value from hook content and clear error.
  // WebsocketProvider handles actual reconnection; we just refresh the editor.
  // ---------------------------------------------------------------------------
  const handleReconnect = useCallback(() => {
    setError(null);
    setLocalValue(content);
  }, [content]);

  // Clear error when connection or sync recovers (e.g. after reconnect)
  useEffect(() => {
    if (connected && synced && error) setError(null);
  }, [connected, synced, error]);

  // Show offline hint when disconnected so user knows they can keep editing
  // and that changes will sync when reconnected
  const showOfflineHint = !connected;

  // ---------------------------------------------------------------------------
  // Blur: clear cursor/selection in awareness so we don't show stale position
  // when the user has left the editor (e.g. clicked elsewhere).
  // ---------------------------------------------------------------------------
  const handleBlur = useCallback(() => {
    setCursor(null);
    setSelection(null);
  }, [setCursor, setSelection]);

  // Status message for connection: Disconnected | Synced | Syncing...
  // Used in toolbar next to the connection icon.
  const statusMessage = !connected
    ? 'Disconnected'
    : synced
      ? 'Synced'
      : 'Syncing...';

  // ---------------------------------------------------------------------------
  // Render: toolbar (connection, presence, word count, save), editor, helper.
  // Toolbar shows connection status, presence indicator, word count, optional
  // Save and Reconnect. Editor is a textarea bound to localValue.
  // ---------------------------------------------------------------------------
  return (
    <div className="space-y-4">
      {/* Toolbar: connection status, presence indicator, offline badge, word count, reconnect/save */}
      <Card className="p-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-4">
            {/* Connection status (connected/synced or disconnected) */}
            <div className="flex items-center gap-2">
              {connected ? (
                <>
                  <Wifi className="h-4 w-4 text-green-600" aria-hidden />
                  <span className="text-sm text-green-600">{statusMessage}</span>
                </>
              ) : (
                <>
                  <WifiOff className="h-4 w-4 text-red-600" aria-hidden />
                  <span className="text-sm text-red-600">Disconnected</span>
                </>
              )}
            </div>

            {/* Presence: other users' avatars and cursor/selection tooltips */}
            <PresenceIndicator users={presence} />

            {/* Offline badge when disconnected */}
            {offline && (
              <Badge variant="outline" className="gap-1 border-amber-500 text-amber-700">
                <CloudOffline className="h-3 w-3" />
                Offline — changes will sync when reconnected
              </Badge>
            )}
          </div>

          <div className="flex items-center gap-2">
            {/* Word count (from local value) */}
            <Badge variant="outline" className="gap-1 font-mono">
              <Type className="h-3 w-3" />
              {wordCount} words
            </Badge>

            {/* Reconnect: refetch content and clear error when disconnected */}
            {!connected && (
              <Button variant="outline" size="sm" onClick={handleReconnect} className="gap-2">
                <RefreshCw className="h-4 w-4" />
                Reconnect
              </Button>
            )}

            {/* Optional Save button (triggers onSave with current content) */}
            {showSaveButton && onSave && (
              <Button
                size="sm"
                onClick={handleSaveClick}
                disabled={saving}
                className="gap-2"
              >
                {saving ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Save className="h-4 w-4" />
                )}
                Save
              </Button>
            )}
          </div>
        </div>

        {/* Syncing indicator: show when connected but not yet synced */}
        {connected && !synced && (
          <div className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Syncing with server…
          </div>
        )}

        {/* Error banner: optional; parent can set error (e.g. save failure) */}
        {error && (
          <Alert variant="destructive" className="mt-2">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Offline hint when disconnected: encourage user to keep editing or reconnect */}
        {showOfflineHint && (
          <p className="mt-2 text-sm text-amber-600">
            Connection lost. Check your network and click Reconnect, or continue editing offline —
            changes will sync when reconnected.
          </p>
        )}
      </Card>

      {/* Editor area: textarea bound to local value; changes go to Y.Text via setContent */}
      <Card className="p-6">
        <textarea
          ref={textareaRef}
          value={localValue}
          onChange={handleChange}
          onSelect={handleSelect}
          onBlur={handleBlur}
          placeholder="Start writing…"
          style={{ minHeight: `${minHeight}px` }}
          className="w-full resize-y rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          data-testid={`collab-editor-${sectionId}`}
          aria-label={`Collaborative editor for section ${sectionId}`}
        />
      </Card>

      {/* Helper text and keyboard shortcut hint */}
      <div className="space-y-1 text-sm text-muted-foreground">
        <p>
          Real-time collaborative editing. Changes are synced automatically and stored locally when
          offline.
        </p>
        {onSave && (
          <p>
            Press <kbd className="rounded border bg-muted px-1.5 py-0.5 font-mono text-xs">Ctrl+S</kbd> (or <kbd className="rounded border bg-muted px-1.5 py-0.5 font-mono text-xs">Cmd+S</kbd>) to save.
          </p>
        )}
      </div>
    </div>
  );
}

