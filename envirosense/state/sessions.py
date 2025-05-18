"""
EnviroSense state management - Session and checkpoint tracking
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid


class DevelopmentSession:
    """
    Represents a development session.
    
    A session is a period of time during which development work is done.
    It tracks what components were focused on, what changes were made,
    and any notes about the session.
    """
    
    def __init__(self, 
                 session_id: Optional[str] = None, 
                 timestamp: Optional[str] = None, 
                 focus_components: Optional[List[str]] = None):
        """
        Initialize a new development session.
        
        Args:
            session_id: Unique identifier for the session, generated if not provided
            timestamp: ISO format timestamp for when the session started
            focus_components: List of component names that are the focus of this session
        """
        self.session_id = session_id or str(uuid.uuid4())
        self.timestamp = timestamp or datetime.now().isoformat()
        self.focus_components = focus_components or []
        self.changes = []
        self.notes = ""
        self.end_timestamp = None
    
    def add_change(self, 
                   component: str, 
                   description: str, 
                   files_changed: List[str],
                   change_type: str = "implementation") -> None:
        """
        Add a change to the session.
        
        Args:
            component: Name of the component that was changed
            description: Description of the change
            files_changed: List of files that were changed
            change_type: Type of change (e.g., "implementation", "refactoring", "bugfix")
        """
        self.changes.append({
            "component": component,
            "description": description,
            "files_changed": files_changed,
            "timestamp": datetime.now().isoformat(),
            "change_type": change_type
        })
    
    def add_note(self, note: str) -> None:
        """Add a note to the session."""
        timestamp = datetime.now().isoformat()
        self.notes += f"\n[{timestamp}] {note}"
    
    def end_session(self) -> None:
        """End the session and record the end timestamp."""
        self.end_timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the session to a dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "end_timestamp": self.end_timestamp,
            "focus_components": self.focus_components,
            "changes": self.changes,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DevelopmentSession':
        """Create a session from a dictionary."""
        session = cls(
            session_id=data.get("session_id"),
            timestamp=data.get("timestamp"),
            focus_components=data.get("focus_components", [])
        )
        session.changes = data.get("changes", [])
        session.notes = data.get("notes", "")
        session.end_timestamp = data.get("end_timestamp")
        return session


class Checkpoint:
    """
    Represents a development checkpoint.
    
    A checkpoint marks a specific point in development, such as a
    milestone or a version release. It includes a snapshot of the
    component state at that point.
    """
    
    def __init__(self, 
                 name: str, 
                 description: str, 
                 components_state: Dict[str, Any], 
                 timestamp: Optional[str] = None):
        """
        Initialize a new checkpoint.
        
        Args:
            name: Name of the checkpoint
            description: Description of what this checkpoint represents
            components_state: Dictionary of component states
            timestamp: ISO format timestamp for when the checkpoint was created
        """
        self.name = name
        self.description = description
        self.components_state = components_state.copy()
        self.timestamp = timestamp or datetime.now().isoformat()
        self.git_commit = None
        self.checkpoint_id = str(uuid.uuid4())
    
    def set_git_commit(self, commit_hash: str) -> None:
        """Set the Git commit hash associated with this checkpoint."""
        self.git_commit = commit_hash
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the checkpoint to a dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "components_state": self.components_state,
            "timestamp": self.timestamp,
            "git_commit": self.git_commit,
            "checkpoint_id": self.checkpoint_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Checkpoint':
        """Create a checkpoint from a dictionary."""
        checkpoint = cls(
            name=data["name"],
            description=data["description"],
            components_state=data["components_state"],
            timestamp=data.get("timestamp")
        )
        checkpoint.git_commit = data.get("git_commit")
        checkpoint.checkpoint_id = data.get("checkpoint_id", str(uuid.uuid4()))
        return checkpoint


class SessionManager:
    """
    Manages development sessions and checkpoints.
    
    Provides methods for creating, retrieving, and managing sessions
    and checkpoints.
    """
    
    def __init__(self):
        """Initialize a new session manager."""
        self.sessions = []
        self.checkpoints = []
        self.current_session = None
    
    def start_session(self, focus_components: Optional[List[str]] = None) -> DevelopmentSession:
        """
        Start a new development session.
        
        Args:
            focus_components: List of component names that are the focus of this session
            
        Returns:
            The new development session
        """
        # End current session if there is one
        if self.current_session:
            self.current_session.end_session()
        
        # Create new session
        self.current_session = DevelopmentSession(focus_components=focus_components)
        self.sessions.append(self.current_session)
        return self.current_session
    
    def end_current_session(self) -> None:
        """End the current development session."""
        if self.current_session:
            self.current_session.end_session()
            self.current_session = None
    
    def create_checkpoint(self, 
                          name: str, 
                          description: str, 
                          components_state: Dict[str, Any]) -> Checkpoint:
        """
        Create a new checkpoint.
        
        Args:
            name: Name of the checkpoint
            description: Description of what this checkpoint represents
            components_state: Dictionary of component states
            
        Returns:
            The new checkpoint
        """
        checkpoint = Checkpoint(name, description, components_state)
        self.checkpoints.append(checkpoint)
        return checkpoint
    
    def get_checkpoint_by_name(self, name: str) -> Optional[Checkpoint]:
        """Get a checkpoint by name."""
        for checkpoint in self.checkpoints:
            if checkpoint.name == name:
                return checkpoint
        return None
    
    def get_latest_checkpoint(self) -> Optional[Checkpoint]:
        """Get the most recent checkpoint."""
        if not self.checkpoints:
            return None
        
        # Sort by timestamp and return the most recent
        return sorted(self.checkpoints, key=lambda c: c.timestamp, reverse=True)[0]
    
    def get_checkpoints_in_timerange(self, 
                                     start_time: str, 
                                     end_time: str) -> List[Checkpoint]:
        """Get all checkpoints within a time range."""
        return [
            c for c in self.checkpoints 
            if start_time <= c.timestamp <= end_time
        ]
    
    def get_session_by_id(self, session_id: str) -> Optional[DevelopmentSession]:
        """Get a session by ID."""
        for session in self.sessions:
            if session.session_id == session_id:
                return session
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the session manager to a dictionary for serialization."""
        return {
            "sessions": [s.to_dict() for s in self.sessions],
            "checkpoints": [c.to_dict() for c in self.checkpoints],
            "current_session_id": self.current_session.session_id if self.current_session else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionManager':
        """Create a session manager from a dictionary."""
        manager = cls()
        
        # Load sessions
        manager.sessions = [
            DevelopmentSession.from_dict(s) for s in data.get("sessions", [])
        ]
        
        # Load checkpoints
        manager.checkpoints = [
            Checkpoint.from_dict(c) for c in data.get("checkpoints", [])
        ]
        
        # Set current session
        current_session_id = data.get("current_session_id")
        if current_session_id:
            manager.current_session = manager.get_session_by_id(current_session_id)
        
        return manager
