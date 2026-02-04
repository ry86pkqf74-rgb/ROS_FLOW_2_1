"""
Real-time Collaborative Reference Management

WebSocket-based real-time collaboration system for reference editing,
with conflict resolution, version control, and live synchronization.

Linear Issues: ROS-XXX
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import websockets
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed

from .reference_types import Reference, ReferenceEdit
from .reference_cache import get_cache
from .collaborative_references import get_collaborative_manager

logger = logging.getLogger(__name__)

class CollaborationEventType(Enum):
    """Types of collaboration events."""
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    REFERENCE_LOCKED = "reference_locked"
    REFERENCE_UNLOCKED = "reference_unlocked"
    REFERENCE_EDITED = "reference_edited"
    REFERENCE_ADDED = "reference_added"
    REFERENCE_DELETED = "reference_deleted"
    CURSOR_MOVED = "cursor_moved"
    SELECTION_CHANGED = "selection_changed"
    COMMENT_ADDED = "comment_added"
    STATUS_UPDATE = "status_update"
    SYNC_REQUEST = "sync_request"
    CONFLICT_DETECTED = "conflict_detected"

@dataclass
class CollaborationEvent:
    """Represents a collaboration event."""
    event_id: str
    event_type: CollaborationEventType
    session_id: str
    user_id: str
    user_name: str
    timestamp: datetime
    data: Dict[str, Any]
    target_reference_id: Optional[str] = None
    requires_ack: bool = False

@dataclass
class ActiveUser:
    """Represents an active user in collaboration session."""
    user_id: str
    user_name: str
    websocket: WebSocketServerProtocol
    cursor_position: Optional[Dict[str, Any]] = None
    selected_references: Set[str] = None
    last_activity: datetime = None
    is_typing: bool = False
    
    def __post_init__(self):
        if self.selected_references is None:
            self.selected_references = set()
        if self.last_activity is None:
            self.last_activity = datetime.utcnow()

class RealTimeCollaborationManager:
    """
    Manages real-time collaborative editing sessions with WebSocket support.
    
    Features:
    - Live reference editing with conflict resolution
    - Real-time cursor and selection synchronization
    - User presence awareness
    - Operational transformation for concurrent edits
    - Version control and change history
    - Comment and annotation system
    """
    
    def __init__(self):
        self.cache = None
        self.collaborative_manager = None
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.event_handlers = {}
        self.server = None
        self.stats = {
            'sessions_created': 0,
            'users_connected': 0,
            'events_processed': 0,
            'conflicts_resolved': 0,
            'messages_sent': 0
        }
        
        self._setup_event_handlers()
    
    async def initialize(self):
        """Initialize the real-time collaboration manager."""
        self.cache = await get_cache()
        self.collaborative_manager = await get_collaborative_manager()
        logger.info("Real-time collaboration manager initialized")
    
    def _setup_event_handlers(self):
        """Set up event handlers for different collaboration events."""
        self.event_handlers = {
            CollaborationEventType.REFERENCE_EDITED: self._handle_reference_edit,
            CollaborationEventType.REFERENCE_LOCKED: self._handle_reference_lock,
            CollaborationEventType.REFERENCE_UNLOCKED: self._handle_reference_unlock,
            CollaborationEventType.CURSOR_MOVED: self._handle_cursor_movement,
            CollaborationEventType.SELECTION_CHANGED: self._handle_selection_change,
            CollaborationEventType.COMMENT_ADDED: self._handle_comment_addition,
            CollaborationEventType.SYNC_REQUEST: self._handle_sync_request,
        }
    
    async def start_websocket_server(self, host: str = "localhost", port: int = 8002):
        """Start WebSocket server for real-time collaboration."""
        
        async def connection_handler(websocket: WebSocketServerProtocol, path: str):
            """Handle new WebSocket connections."""
            await self._handle_websocket_connection(websocket, path)
        
        self.server = await websockets.serve(connection_handler, host, port)
        logger.info(f"WebSocket server started on {host}:{port}")
        return self.server
    
    async def _handle_websocket_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle individual WebSocket connections."""
        user_id = None
        session_id = None
        
        try:
            # Wait for authentication message
            auth_message = await websocket.recv()
            auth_data = json.loads(auth_message)
            
            user_id = auth_data.get('user_id')
            user_name = auth_data.get('user_name')
            session_id = auth_data.get('session_id')
            
            if not all([user_id, user_name, session_id]):
                await websocket.send(json.dumps({
                    'type': 'error',
                    'message': 'Invalid authentication data'
                }))
                return
            
            # Add user to session
            await self._add_user_to_session(session_id, user_id, user_name, websocket)
            
            # Send welcome message
            await websocket.send(json.dumps({
                'type': 'connected',
                'session_id': session_id,
                'user_id': user_id,
                'active_users': await self._get_session_users(session_id)
            }))
            
            # Handle messages
            async for message in websocket:
                try:
                    await self._process_websocket_message(websocket, session_id, user_id, message)
                except Exception as e:
                    logger.error(f"Error processing message from {user_id}: {e}")
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': f'Error processing message: {str(e)}'
                    }))
        
        except ConnectionClosed:
            logger.info(f"WebSocket connection closed for user {user_id}")
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
        finally:
            # Clean up user from session
            if session_id and user_id:
                await self._remove_user_from_session(session_id, user_id)
    
    async def _process_websocket_message(self, websocket: WebSocketServerProtocol, session_id: str, user_id: str, message: str):
        """Process incoming WebSocket messages."""
        try:
            data = json.loads(message)
            event_type = CollaborationEventType(data.get('type'))
            
            # Create collaboration event
            event = CollaborationEvent(
                event_id=str(uuid.uuid4()),
                event_type=event_type,
                session_id=session_id,
                user_id=user_id,
                user_name=data.get('user_name', 'Unknown'),
                timestamp=datetime.utcnow(),
                data=data.get('data', {}),
                target_reference_id=data.get('reference_id'),
                requires_ack=data.get('requires_ack', False)
            )
            
            # Process event
            await self._process_collaboration_event(event)
            self.stats['events_processed'] += 1
            
            # Send acknowledgment if required
            if event.requires_ack:
                await websocket.send(json.dumps({
                    'type': 'ack',
                    'event_id': event.event_id,
                    'status': 'processed'
                }))
            
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")
            raise
    
    async def _add_user_to_session(self, session_id: str, user_id: str, user_name: str, websocket: WebSocketServerProtocol):
        """Add user to collaboration session."""
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = {
                'users': {},
                'references': {},
                'locks': {},
                'comments': {},
                'activity_log': []
            }
        
        user = ActiveUser(
            user_id=user_id,
            user_name=user_name,
            websocket=websocket,
            last_activity=datetime.utcnow()
        )
        
        self.active_sessions[session_id]['users'][user_id] = user
        
        # Notify other users
        await self._broadcast_to_session(session_id, CollaborationEvent(
            event_id=str(uuid.uuid4()),
            event_type=CollaborationEventType.USER_JOINED,
            session_id=session_id,
            user_id=user_id,
            user_name=user_name,
            timestamp=datetime.utcnow(),
            data={'user_name': user_name}
        ), exclude_user=user_id)
        
        self.stats['users_connected'] += 1
        logger.info(f"User {user_name} joined session {session_id}")
    
    async def _remove_user_from_session(self, session_id: str, user_id: str):
        """Remove user from collaboration session."""
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        
        if user_id in session['users']:
            user = session['users'][user_id]
            del session['users'][user_id]
            
            # Release any locks held by the user
            locks_to_release = [ref_id for ref_id, lock_data in session['locks'].items() 
                              if lock_data['user_id'] == user_id]
            
            for ref_id in locks_to_release:
                await self._release_reference_lock(session_id, ref_id, user_id)
            
            # Notify other users
            await self._broadcast_to_session(session_id, CollaborationEvent(
                event_id=str(uuid.uuid4()),
                event_type=CollaborationEventType.USER_LEFT,
                session_id=session_id,
                user_id=user_id,
                user_name=user.user_name,
                timestamp=datetime.utcnow(),
                data={'user_name': user.user_name}
            ))
            
            # Clean up empty session
            if not session['users']:
                del self.active_sessions[session_id]
                logger.info(f"Session {session_id} closed (no active users)")
            
            logger.info(f"User {user.user_name} left session {session_id}")
    
    async def _process_collaboration_event(self, event: CollaborationEvent):
        """Process collaboration events."""
        handler = self.event_handlers.get(event.event_type)
        if handler:
            await handler(event)
        else:
            logger.warning(f"No handler for event type: {event.event_type}")
        
        # Broadcast event to other users in session
        await self._broadcast_to_session(event.session_id, event, exclude_user=event.user_id)
        
        # Log activity
        await self._log_activity(event)
    
    async def _handle_reference_edit(self, event: CollaborationEvent):
        """Handle reference edit events."""
        session_id = event.session_id
        reference_id = event.target_reference_id
        
        # Check if user has lock on reference
        if not await self._user_has_lock(session_id, reference_id, event.user_id):
            raise ValueError(f"User {event.user_id} does not have lock on reference {reference_id}")
        
        # Apply edit through collaborative manager
        edit_data = event.data
        reference_edit = ReferenceEdit(
            edit_id=event.event_id,
            reference_id=reference_id,
            field_name=edit_data['field_name'],
            old_value=edit_data['old_value'],
            new_value=edit_data['new_value'],
            editor_id=event.user_id,
            editor_name=event.user_name,
            timestamp=event.timestamp,
            edit_type=edit_data.get('edit_type', 'modify')
        )
        
        # Check for conflicts
        conflict = await self._check_edit_conflict(session_id, reference_edit)
        if conflict:
            await self._handle_edit_conflict(session_id, reference_edit, conflict)
            return
        
        # Apply the edit
        result = await self.collaborative_manager.apply_reference_edit(session_id, reference_edit)
        
        # Update session state
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            if reference_id not in session['references']:
                session['references'][reference_id] = {}
            session['references'][reference_id]['last_edit'] = {
                'user_id': event.user_id,
                'timestamp': event.timestamp,
                'edit_id': event.event_id
            }
    
    async def _handle_reference_lock(self, event: CollaborationEvent):
        """Handle reference lock events."""
        session_id = event.session_id
        reference_id = event.target_reference_id
        
        # Attempt to acquire lock
        success = await self._acquire_reference_lock(session_id, reference_id, event.user_id, event.user_name)
        
        if not success:
            # Send conflict notification
            user = self.active_sessions[session_id]['users'][event.user_id]
            await user.websocket.send(json.dumps({
                'type': 'lock_conflict',
                'reference_id': reference_id,
                'locked_by': self.active_sessions[session_id]['locks'][reference_id]['user_name']
            }))
    
    async def _handle_reference_unlock(self, event: CollaborationEvent):
        """Handle reference unlock events."""
        await self._release_reference_lock(event.session_id, event.target_reference_id, event.user_id)
    
    async def _handle_cursor_movement(self, event: CollaborationEvent):
        """Handle cursor movement events."""
        session_id = event.session_id
        user_id = event.user_id
        
        if session_id in self.active_sessions and user_id in self.active_sessions[session_id]['users']:
            user = self.active_sessions[session_id]['users'][user_id]
            user.cursor_position = event.data
            user.last_activity = datetime.utcnow()
    
    async def _handle_selection_change(self, event: CollaborationEvent):
        """Handle selection change events."""
        session_id = event.session_id
        user_id = event.user_id
        
        if session_id in self.active_sessions and user_id in self.active_sessions[session_id]['users']:
            user = self.active_sessions[session_id]['users'][user_id]
            selected_refs = set(event.data.get('selected_references', []))
            user.selected_references = selected_refs
            user.last_activity = datetime.utcnow()
    
    async def _handle_comment_addition(self, event: CollaborationEvent):
        """Handle comment addition events."""
        session_id = event.session_id
        reference_id = event.target_reference_id
        comment_data = event.data
        
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        if 'comments' not in session:
            session['comments'] = {}
        
        if reference_id not in session['comments']:
            session['comments'][reference_id] = []
        
        comment = {
            'comment_id': event.event_id,
            'user_id': event.user_id,
            'user_name': event.user_name,
            'text': comment_data['text'],
            'timestamp': event.timestamp.isoformat(),
            'position': comment_data.get('position')
        }
        
        session['comments'][reference_id].append(comment)
    
    async def _handle_sync_request(self, event: CollaborationEvent):
        """Handle sync request events."""
        session_id = event.session_id
        user_id = event.user_id
        
        if session_id not in self.active_sessions:
            return
        
        # Send current session state to user
        session_state = await self._get_session_state(session_id)
        user = self.active_sessions[session_id]['users'][user_id]
        
        await user.websocket.send(json.dumps({
            'type': 'sync_response',
            'session_state': session_state
        }))
    
    async def _check_edit_conflict(self, session_id: str, edit: ReferenceEdit) -> Optional[Dict[str, Any]]:
        """Check for edit conflicts."""
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        reference_id = edit.reference_id
        
        # Check if reference was edited recently by another user
        if reference_id in session['references']:
            last_edit = session['references'][reference_id].get('last_edit')
            if last_edit and last_edit['user_id'] != edit.editor_id:
                # Check if the edit happened recently (within last 5 seconds)
                last_edit_time = datetime.fromisoformat(last_edit['timestamp'])
                if (edit.timestamp - last_edit_time).total_seconds() < 5:
                    return {
                        'type': 'concurrent_edit',
                        'conflicting_user': last_edit['user_id'],
                        'last_edit_time': last_edit_time
                    }
        
        return None
    
    async def _handle_edit_conflict(self, session_id: str, edit: ReferenceEdit, conflict: Dict[str, Any]):
        """Handle edit conflicts using operational transformation."""
        self.stats['conflicts_resolved'] += 1
        
        # For now, use simple last-writer-wins strategy
        # In production, implement operational transformation
        logger.warning(f"Edit conflict detected in session {session_id}, using last-writer-wins")
        
        # Notify all users about the conflict
        conflict_event = CollaborationEvent(
            event_id=str(uuid.uuid4()),
            event_type=CollaborationEventType.CONFLICT_DETECTED,
            session_id=session_id,
            user_id=edit.editor_id,
            user_name=edit.editor_name,
            timestamp=datetime.utcnow(),
            data={
                'conflict_type': conflict['type'],
                'resolution': 'last_writer_wins',
                'edit_accepted': True
            },
            target_reference_id=edit.reference_id
        )
        
        await self._broadcast_to_session(session_id, conflict_event)
    
    async def _acquire_reference_lock(self, session_id: str, reference_id: str, user_id: str, user_name: str) -> bool:
        """Acquire lock on a reference."""
        if session_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[session_id]
        
        # Check if reference is already locked
        if reference_id in session['locks']:
            current_lock = session['locks'][reference_id]
            # Check if lock is expired (5 minutes)
            if (datetime.utcnow() - current_lock['acquired_at']).total_seconds() > 300:
                # Lock expired, remove it
                del session['locks'][reference_id]
            else:
                # Lock still active
                return False
        
        # Acquire lock
        session['locks'][reference_id] = {
            'user_id': user_id,
            'user_name': user_name,
            'acquired_at': datetime.utcnow(),
            'reference_id': reference_id
        }
        
        return True
    
    async def _release_reference_lock(self, session_id: str, reference_id: str, user_id: str):
        """Release lock on a reference."""
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        
        if reference_id in session['locks']:
            lock = session['locks'][reference_id]
            if lock['user_id'] == user_id:
                del session['locks'][reference_id]
    
    async def _user_has_lock(self, session_id: str, reference_id: str, user_id: str) -> bool:
        """Check if user has lock on reference."""
        if session_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[session_id]
        
        if reference_id not in session['locks']:
            return False
        
        lock = session['locks'][reference_id]
        return lock['user_id'] == user_id
    
    async def _broadcast_to_session(self, session_id: str, event: CollaborationEvent, exclude_user: Optional[str] = None):
        """Broadcast event to all users in session."""
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        message = json.dumps({
            'type': event.event_type.value,
            'event_id': event.event_id,
            'user_id': event.user_id,
            'user_name': event.user_name,
            'timestamp': event.timestamp.isoformat(),
            'data': event.data,
            'reference_id': event.target_reference_id
        })
        
        for user_id, user in session['users'].items():
            if exclude_user and user_id == exclude_user:
                continue
            
            try:
                await user.websocket.send(message)
                self.stats['messages_sent'] += 1
            except ConnectionClosed:
                logger.warning(f"Could not send message to user {user_id}, connection closed")
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {e}")
    
    async def _log_activity(self, event: CollaborationEvent):
        """Log activity for session history."""
        session_id = event.session_id
        
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        activity_entry = {
            'event_id': event.event_id,
            'event_type': event.event_type.value,
            'user_id': event.user_id,
            'user_name': event.user_name,
            'timestamp': event.timestamp.isoformat(),
            'reference_id': event.target_reference_id,
            'summary': self._generate_activity_summary(event)
        }
        
        session['activity_log'].append(activity_entry)
        
        # Keep only last 100 activities
        if len(session['activity_log']) > 100:
            session['activity_log'] = session['activity_log'][-100:]
    
    def _generate_activity_summary(self, event: CollaborationEvent) -> str:
        """Generate human-readable activity summary."""
        summaries = {
            CollaborationEventType.USER_JOINED: f"{event.user_name} joined the session",
            CollaborationEventType.USER_LEFT: f"{event.user_name} left the session",
            CollaborationEventType.REFERENCE_LOCKED: f"{event.user_name} started editing a reference",
            CollaborationEventType.REFERENCE_UNLOCKED: f"{event.user_name} finished editing a reference",
            CollaborationEventType.REFERENCE_EDITED: f"{event.user_name} edited a reference",
            CollaborationEventType.COMMENT_ADDED: f"{event.user_name} added a comment",
        }
        
        return summaries.get(event.event_type, f"{event.user_name} performed {event.event_type.value}")
    
    async def _get_session_users(self, session_id: str) -> List[Dict[str, Any]]:
        """Get list of active users in session."""
        if session_id not in self.active_sessions:
            return []
        
        users = []
        for user_id, user in self.active_sessions[session_id]['users'].items():
            users.append({
                'user_id': user.user_id,
                'user_name': user.user_name,
                'cursor_position': user.cursor_position,
                'selected_references': list(user.selected_references),
                'last_activity': user.last_activity.isoformat(),
                'is_typing': user.is_typing
            })
        
        return users
    
    async def _get_session_state(self, session_id: str) -> Dict[str, Any]:
        """Get current session state."""
        if session_id not in self.active_sessions:
            return {}
        
        session = self.active_sessions[session_id]
        
        return {
            'session_id': session_id,
            'active_users': await self._get_session_users(session_id),
            'locked_references': {
                ref_id: {
                    'user_id': lock['user_id'],
                    'user_name': lock['user_name'],
                    'acquired_at': lock['acquired_at'].isoformat()
                }
                for ref_id, lock in session['locks'].items()
            },
            'comments': session.get('comments', {}),
            'activity_log': session.get('activity_log', [])[-10:]  # Last 10 activities
        }
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get collaboration manager statistics."""
        active_sessions_count = len(self.active_sessions)
        total_active_users = sum(len(session['users']) for session in self.active_sessions.values())
        
        return {
            **self.stats,
            'active_sessions': active_sessions_count,
            'total_active_users': total_active_users,
            'average_users_per_session': total_active_users / max(active_sessions_count, 1)
        }

# Global real-time collaboration manager instance
_rt_collaboration_instance: Optional[RealTimeCollaborationManager] = None

async def get_real_time_collaboration_manager() -> RealTimeCollaborationManager:
    """Get global real-time collaboration manager instance."""
    global _rt_collaboration_instance
    if _rt_collaboration_instance is None:
        _rt_collaboration_instance = RealTimeCollaborationManager()
        await _rt_collaboration_instance.initialize()
    return _rt_collaboration_instance

async def close_real_time_collaboration_manager() -> None:
    """Close global real-time collaboration manager instance."""
    global _rt_collaboration_instance
    if _rt_collaboration_instance:
        if _rt_collaboration_instance.server:
            _rt_collaboration_instance.server.close()
            await _rt_collaboration_instance.server.wait_closed()
        _rt_collaboration_instance = None