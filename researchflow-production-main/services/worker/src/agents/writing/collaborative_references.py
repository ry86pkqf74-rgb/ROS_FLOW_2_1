"""
Real-time Collaborative Reference Management

Enables multiple researchers to work on references simultaneously with conflict resolution
and change tracking.

Linear Issues: ROS-XXX
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import hashlib

from .reference_types import Reference, Citation, QualityScore
from .reference_cache import get_cache

logger = logging.getLogger(__name__)

@dataclass
class ReferenceEdit:
    """Represents an edit to a reference."""
    edit_id: str
    reference_id: str
    field_name: str
    old_value: str
    new_value: str
    editor_id: str
    editor_name: str
    timestamp: datetime
    edit_type: str  # 'add', 'modify', 'delete'
    conflict_resolution: Optional[str] = None  # 'accepted', 'rejected', 'merged'

@dataclass
class CollaborativeSession:
    """Collaborative editing session."""
    session_id: str
    study_id: str
    active_editors: Set[str]
    locked_references: Dict[str, str]  # ref_id -> editor_id
    pending_edits: List[ReferenceEdit]
    edit_history: List[ReferenceEdit]
    created_at: datetime
    last_activity: datetime

@dataclass
class ConflictResolution:
    """Represents a conflict between edits."""
    conflict_id: str
    reference_id: str
    field_name: str
    conflicting_edits: List[ReferenceEdit]
    resolution_strategy: str  # 'manual', 'auto_merge', 'latest_wins'
    resolved_value: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None

class CollaborativeReferenceManager:
    """Manages collaborative reference editing with real-time sync."""
    
    def __init__(self):
        self.cache = None
        self.active_sessions: Dict[str, CollaborativeSession] = {}
        self.conflict_resolver = ConflictResolver()
    
    async def initialize(self):
        """Initialize collaborative manager."""
        self.cache = await get_cache()
        logger.info("Collaborative reference manager initialized")
    
    async def start_session(self, study_id: str, editor_id: str, editor_name: str) -> str:
        """Start collaborative editing session."""
        session_id = f"collab_{study_id}_{int(datetime.utcnow().timestamp())}"
        
        session = CollaborativeSession(
            session_id=session_id,
            study_id=study_id,
            active_editors={editor_id},
            locked_references={},
            pending_edits=[],
            edit_history=[],
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow()
        )
        
        self.active_sessions[session_id] = session
        await self._persist_session(session)
        await self._broadcast_session_update(session, f"{editor_name} started collaborative session")
        
        logger.info(f"Started collaborative session {session_id} for study {study_id}")
        return session_id
    
    async def join_session(self, session_id: str, editor_id: str, editor_name: str) -> bool:
        """Join existing collaborative session."""
        session = await self._get_session(session_id)
        if session:
            session.active_editors.add(editor_id)
            session.last_activity = datetime.utcnow()
            await self._persist_session(session)
            await self._broadcast_session_update(session, f"{editor_name} joined the session")
            logger.info(f"Editor {editor_id} joined session {session_id}")
            return True
        return False
    
    async def leave_session(self, session_id: str, editor_id: str, editor_name: str) -> bool:
        """Leave collaborative session."""
        session = await self._get_session(session_id)
        if session and editor_id in session.active_editors:
            session.active_editors.discard(editor_id)
            session.last_activity = datetime.utcnow()
            
            # Release any locks held by this editor
            locks_to_release = [ref_id for ref_id, lock_editor in session.locked_references.items() 
                              if lock_editor == editor_id]
            for ref_id in locks_to_release:
                del session.locked_references[ref_id]
            
            await self._persist_session(session)
            await self._broadcast_session_update(session, f"{editor_name} left the session")
            
            # Clean up empty session
            if not session.active_editors:
                await self._cleanup_session(session_id)
            
            logger.info(f"Editor {editor_id} left session {session_id}")
            return True
        return False
    
    async def request_reference_lock(
        self, 
        session_id: str, 
        reference_id: str, 
        editor_id: str,
        editor_name: str
    ) -> Dict[str, any]:
        """Request exclusive lock on reference for editing."""
        session = await self._get_session(session_id)
        if not session:
            return {'success': False, 'reason': 'Session not found'}
        
        # Check if reference is already locked
        if reference_id in session.locked_references:
            current_editor = session.locked_references[reference_id]
            if current_editor == editor_id:
                return {'success': True, 'reason': 'Already locked by you'}
            else:
                return {'success': False, 'reason': f'Reference locked by another editor'}
        
        # Grant lock
        session.locked_references[reference_id] = editor_id
        session.last_activity = datetime.utcnow()
        await self._persist_session(session)
        await self._broadcast_lock_update(session, reference_id, editor_id, editor_name, 'locked')
        
        logger.info(f"Lock granted on reference {reference_id} to editor {editor_id} in session {session_id}")
        return {'success': True, 'reason': 'Lock granted'}
    
    async def release_reference_lock(
        self, 
        session_id: str, 
        reference_id: str, 
        editor_id: str,
        editor_name: str
    ) -> bool:
        """Release lock on reference."""
        session = await self._get_session(session_id)
        if not session:
            return False
        
        # Check if editor owns the lock
        if session.locked_references.get(reference_id) == editor_id:
            del session.locked_references[reference_id]
            session.last_activity = datetime.utcnow()
            await self._persist_session(session)
            await self._broadcast_lock_update(session, reference_id, editor_id, editor_name, 'released')
            logger.info(f"Lock released on reference {reference_id} by editor {editor_id}")
            return True
        
        return False
    
    async def apply_reference_edit(
        self, 
        session_id: str, 
        edit: ReferenceEdit
    ) -> Dict[str, any]:
        """Apply collaborative edit to reference with conflict detection."""
        session = await self._get_session(session_id)
        if not session:
            return {'success': False, 'reason': 'Session not found'}
        
        # Verify editor has lock (for non-additive operations)
        if edit.edit_type in ['modify', 'delete']:
            if session.locked_references.get(edit.reference_id) != edit.editor_id:
                return {'success': False, 'reason': 'Reference not locked by editor'}
        
        # Check for conflicts
        conflicts = await self._detect_conflicts(session, edit)
        
        if conflicts:
            # Handle conflicts
            resolution = await self.conflict_resolver.resolve_conflicts(conflicts, edit)
            if not resolution.resolved_value:
                return {
                    'success': False, 
                    'reason': 'Conflict detected', 
                    'conflicts': conflicts,
                    'requires_manual_resolution': True
                }
            edit.new_value = resolution.resolved_value
            edit.conflict_resolution = 'auto_resolved'
        
        # Generate edit ID
        edit.edit_id = hashlib.md5(f"{edit.reference_id}_{edit.field_name}_{edit.timestamp}".encode()).hexdigest()[:16]
        
        # Apply edit
        session.pending_edits.append(edit)
        session.edit_history.append(edit)
        session.last_activity = datetime.utcnow()
        
        await self._persist_session(session)
        await self._broadcast_edit_update(session, edit)
        
        logger.info(f"Applied edit {edit.edit_id} to reference {edit.reference_id} in session {session_id}")
        return {'success': True, 'edit_id': edit.edit_id}
    
    async def get_reference_edit_history(self, session_id: str, reference_id: str) -> List[Dict[str, any]]:
        """Get edit history for a specific reference."""
        session = await self._get_session(session_id)
        if not session:
            return []
        
        ref_edits = [edit for edit in session.edit_history if edit.reference_id == reference_id]
        
        return [
            {
                'edit_id': edit.edit_id,
                'field_name': edit.field_name,
                'old_value': edit.old_value,
                'new_value': edit.new_value,
                'editor_name': edit.editor_name,
                'timestamp': edit.timestamp.isoformat(),
                'edit_type': edit.edit_type,
                'conflict_resolution': edit.conflict_resolution
            }
            for edit in sorted(ref_edits, key=lambda x: x.timestamp, reverse=True)
        ]
    
    async def get_session_status(self, session_id: str) -> Optional[Dict[str, any]]:
        """Get current session status."""
        session = await self._get_session(session_id)
        if not session:
            return None
        
        return {
            'session_id': session.session_id,
            'study_id': session.study_id,
            'active_editors': list(session.active_editors),
            'locked_references': session.locked_references,
            'pending_edits_count': len(session.pending_edits),
            'total_edits': len(session.edit_history),
            'created_at': session.created_at.isoformat(),
            'last_activity': session.last_activity.isoformat()
        }
    
    async def _get_session(self, session_id: str) -> Optional[CollaborativeSession]:
        """Get session from cache or memory."""
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]
        
        # Try to load from cache
        if self.cache:
            cached_session = await self.cache.get('api_responses', f"collab_session_{session_id}")
            if cached_session:
                session = CollaborativeSession(**cached_session)
                self.active_sessions[session_id] = session
                return session
        
        return None
    
    async def _persist_session(self, session: CollaborativeSession):
        """Persist session to cache."""
        if self.cache:
            session_data = {
                'session_id': session.session_id,
                'study_id': session.study_id,
                'active_editors': list(session.active_editors),
                'locked_references': session.locked_references,
                'pending_edits': [
                    {
                        'edit_id': edit.edit_id,
                        'reference_id': edit.reference_id,
                        'field_name': edit.field_name,
                        'old_value': edit.old_value,
                        'new_value': edit.new_value,
                        'editor_id': edit.editor_id,
                        'editor_name': edit.editor_name,
                        'timestamp': edit.timestamp.isoformat(),
                        'edit_type': edit.edit_type,
                        'conflict_resolution': edit.conflict_resolution
                    }
                    for edit in session.pending_edits
                ],
                'edit_history': [
                    {
                        'edit_id': edit.edit_id,
                        'reference_id': edit.reference_id,
                        'field_name': edit.field_name,
                        'old_value': edit.old_value,
                        'new_value': edit.new_value,
                        'editor_id': edit.editor_id,
                        'editor_name': edit.editor_name,
                        'timestamp': edit.timestamp.isoformat(),
                        'edit_type': edit.edit_type,
                        'conflict_resolution': edit.conflict_resolution
                    }
                    for edit in session.edit_history
                ],
                'created_at': session.created_at.isoformat(),
                'last_activity': session.last_activity.isoformat()
            }
            
            await self.cache.set(
                'api_responses', 
                f"collab_session_{session.session_id}", 
                session_data, 
                ttl_override=24*3600  # 24 hour TTL
            )
    
    async def _detect_conflicts(self, session: CollaborativeSession, edit: ReferenceEdit) -> List[ConflictResolution]:
        """Detect conflicts with pending edits."""
        conflicts = []
        
        # Check for conflicting edits on the same field
        conflicting_edits = [
            existing_edit for existing_edit in session.pending_edits
            if (existing_edit.reference_id == edit.reference_id and 
                existing_edit.field_name == edit.field_name and
                existing_edit.editor_id != edit.editor_id)
        ]
        
        if conflicting_edits:
            conflict_id = hashlib.md5(f"{edit.reference_id}_{edit.field_name}_{datetime.utcnow()}".encode()).hexdigest()[:16]
            conflicts.append(ConflictResolution(
                conflict_id=conflict_id,
                reference_id=edit.reference_id,
                field_name=edit.field_name,
                conflicting_edits=conflicting_edits + [edit],
                resolution_strategy='auto_merge'  # Default strategy
            ))
        
        return conflicts
    
    async def _broadcast_session_update(self, session: CollaborativeSession, message: str):
        """Broadcast session updates to all participants."""
        update = {
            'type': 'session_update',
            'session_id': session.session_id,
            'message': message,
            'active_editors': list(session.active_editors),
            'locked_references': session.locked_references,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Store for WebSocket/real-time system pickup
        await self.cache.set(
            'api_responses', 
            f"broadcast_session_{session.session_id}", 
            update, 
            ttl_override=60  # 1 minute TTL
        )
    
    async def _broadcast_lock_update(self, session: CollaborativeSession, ref_id: str, editor_id: str, editor_name: str, action: str):
        """Broadcast reference lock updates."""
        update = {
            'type': 'lock_update',
            'session_id': session.session_id,
            'reference_id': ref_id,
            'editor_id': editor_id,
            'editor_name': editor_name,
            'action': action,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self.cache.set(
            'api_responses', 
            f"broadcast_lock_{session.session_id}", 
            update, 
            ttl_override=60
        )
    
    async def _broadcast_edit_update(self, session: CollaborativeSession, edit: ReferenceEdit):
        """Broadcast reference edit updates."""
        update = {
            'type': 'edit_update',
            'session_id': session.session_id,
            'edit': {
                'edit_id': edit.edit_id,
                'reference_id': edit.reference_id,
                'field_name': edit.field_name,
                'new_value': edit.new_value,
                'editor_id': edit.editor_id,
                'editor_name': edit.editor_name,
                'timestamp': edit.timestamp.isoformat(),
                'edit_type': edit.edit_type,
                'conflict_resolution': edit.conflict_resolution
            }
        }
        
        await self.cache.set(
            'api_responses', 
            f"broadcast_edit_{session.session_id}", 
            update, 
            ttl_override=60
        )
    
    async def _cleanup_session(self, session_id: str):
        """Clean up empty or expired sessions."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        
        # Remove from cache
        if self.cache:
            await self.cache.delete('api_responses', f"collab_session_{session_id}")
        
        logger.info(f"Cleaned up session {session_id}")


class ConflictResolver:
    """Handles conflict resolution strategies."""
    
    async def resolve_conflicts(self, conflicts: List[ConflictResolution], new_edit: ReferenceEdit) -> ConflictResolution:
        """Resolve conflicts using appropriate strategy."""
        
        if not conflicts:
            return ConflictResolution(
                conflict_id='no_conflict',
                reference_id=new_edit.reference_id,
                field_name=new_edit.field_name,
                conflicting_edits=[],
                resolution_strategy='none',
                resolved_value=new_edit.new_value
            )
        
        primary_conflict = conflicts[0]
        
        if primary_conflict.resolution_strategy == 'auto_merge':
            return await self._auto_merge_strategy(primary_conflict)
        elif primary_conflict.resolution_strategy == 'latest_wins':
            return await self._latest_wins_strategy(primary_conflict)
        else:
            # Manual resolution required
            return primary_conflict
    
    async def _auto_merge_strategy(self, conflict: ConflictResolution) -> ConflictResolution:
        """Attempt automatic merge of conflicting values."""
        
        # For simple fields, use latest edit
        if conflict.field_name in ['title', 'journal', 'year']:
            latest_edit = max(conflict.conflicting_edits, key=lambda x: x.timestamp)
            conflict.resolved_value = latest_edit.new_value
            conflict.resolved_by = 'auto_merge'
            conflict.resolved_at = datetime.utcnow()
        
        # For lists (authors, keywords), attempt merge
        elif conflict.field_name in ['authors', 'keywords']:
            merged_values = set()
            for edit in conflict.conflicting_edits:
                if isinstance(edit.new_value, list):
                    merged_values.update(edit.new_value)
                elif isinstance(edit.new_value, str):
                    # Try to parse as comma-separated list
                    merged_values.update([v.strip() for v in edit.new_value.split(',') if v.strip()])
            
            conflict.resolved_value = list(merged_values)
            conflict.resolved_by = 'auto_merge'
            conflict.resolved_at = datetime.utcnow()
        
        # For other fields, require manual resolution
        else:
            conflict.resolution_strategy = 'manual'
        
        return conflict
    
    async def _latest_wins_strategy(self, conflict: ConflictResolution) -> ConflictResolution:
        """Use latest edit as resolution."""
        latest_edit = max(conflict.conflicting_edits, key=lambda x: x.timestamp)
        conflict.resolved_value = latest_edit.new_value
        conflict.resolved_by = 'latest_wins'
        conflict.resolved_at = datetime.utcnow()
        return conflict


# Global collaborative manager instance
_collab_manager_instance: Optional[CollaborativeReferenceManager] = None


async def get_collaborative_manager() -> CollaborativeReferenceManager:
    """Get global collaborative manager instance."""
    global _collab_manager_instance
    if _collab_manager_instance is None:
        _collab_manager_instance = CollaborativeReferenceManager()
        await _collab_manager_instance.initialize()
    return _collab_manager_instance


async def close_collaborative_manager() -> None:
    """Close global collaborative manager instance."""
    global _collab_manager_instance
    if _collab_manager_instance:
        # Clean up active sessions
        for session in _collab_manager_instance.active_sessions.values():
            await _collab_manager_instance._cleanup_session(session.session_id)
        _collab_manager_instance = None