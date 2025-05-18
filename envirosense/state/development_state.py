"""
EnviroSense state management - Development state tracking
"""
import os
import json
from typing import List, Dict, Any, Optional, Set
from datetime import datetime

from envirosense.state.components import Component, ComponentRegistry, ComponentStatus
from envirosense.state.sessions import SessionManager, DevelopmentSession, Checkpoint
from envirosense.state.tasks import TaskManager, Task, TaskStatus, TaskType


class DevelopmentState:
    """
    Manages the overall development state of the EnviroSense system.
    
    This class combines component tracking, session management, and
    development status tracking into a single, cohesive system. It
    provides methods for loading and saving the state, managing
    components and sessions, and creating checkpoints.
    """
    
    def __init__(self):
        """Initialize a new development state."""
        self.registry = ComponentRegistry()
        self.session_manager = SessionManager()
        self.task_manager = TaskManager()
        self.current_component = None
        self.current_version = "0.0.1"
        self.last_modified = datetime.now().isoformat()
        self.development_notes = {}
        
    def start_session(self, focus_components: Optional[List[str]] = None) -> DevelopmentSession:
        """
        Start a new development session.
        
        Args:
            focus_components: List of component names that are the focus of this session
            
        Returns:
            The new development session
        """
        self.last_modified = datetime.now().isoformat()
        return self.session_manager.start_session(focus_components)
    
    def end_session(self) -> None:
        """End the current development session."""
        self.session_manager.end_current_session()
        self.last_modified = datetime.now().isoformat()
    
    def register_component(self, component: Component) -> None:
        """
        Register a component in the registry.
        
        Args:
            component: The component to register
        """
        self.registry.register(component)
        self.last_modified = datetime.now().isoformat()
    
    def create_checkpoint(self, name: str, description: str) -> Checkpoint:
        """
        Create a new checkpoint with the current component states.
        
        Args:
            name: Name of the checkpoint
            description: Description of what this checkpoint represents
            
        Returns:
            The new checkpoint
        """
        components_state = self.registry.to_dict()
        checkpoint = self.session_manager.create_checkpoint(name, description, components_state)
        self.last_modified = datetime.now().isoformat()
        return checkpoint
    
    def set_focus(self, component_names: List[str]) -> None:
        """
        Set the focus components for the current session.
        
        Args:
            component_names: List of component names to focus on
        """
        session = self.session_manager.current_session
        if not session:
            session = self.start_session(component_names)
        else:
            session.focus_components = component_names
        self.last_modified = datetime.now().isoformat()
    
    def get_component(self, name: str) -> Optional[Component]:
        """
        Get a component by name.
        
        Args:
            name: Name of the component
            
        Returns:
            The component, or None if not found
        """
        return self.registry.get_component(name)
    
    def get_by_tag(self, tag: str) -> List[Component]:
        """
        Get all components with a specific tag.
        
        Args:
            tag: Tag to filter by
            
        Returns:
            List of components with the tag
        """
        return self.registry.get_by_tag(tag)
    
    def add_note(self, note: str, component_name: Optional[str] = None) -> None:
        """
        Add a note to the development state or a specific component.
        
        Args:
            note: The note to add
            component_name: Name of the component to add the note to, or None for general notes
        """
        timestamp = datetime.now().isoformat()
        formatted_note = f"[{timestamp}] {note}"
        
        if component_name:
            component = self.get_component(component_name)
            if component:
                component.add_note(note)
        else:
            note_key = datetime.now().strftime("%Y-%m-%d")
            if note_key not in self.development_notes:
                self.development_notes[note_key] = []
            self.development_notes[note_key].append(formatted_note)
        
        self.last_modified = datetime.now().isoformat()
    
    def get_suggested_focus(self) -> List[str]:
        """
        Get a suggested list of components to focus on next.
        
        This is based on the current state of components, their dependencies,
        and their development status.
        
        Returns:
            List of component names that could be focused on next
        """
        # Get components that are in progress
        in_progress = self.registry.get_by_status(ComponentStatus.IN_PROGRESS)
        in_progress_names = [c.name for c in in_progress]
        
        # If we have in-progress components, suggest continuing with those
        if in_progress_names:
            return in_progress_names
        
        # Get components that are not started but have all dependencies satisfied
        not_started = self.registry.get_by_status(ComponentStatus.NOT_STARTED)
        ready_to_start = []
        
        for component in not_started:
            deps = self.registry.get_dependencies(component.name)
            all_deps_ready = True
            
            for dep in deps:
                dep_component = self.registry.get_component(dep)
                if not dep_component or dep_component.status == ComponentStatus.NOT_STARTED:
                    all_deps_ready = False
                    break
            
            if all_deps_ready:
                ready_to_start.append(component.name)
        
        return ready_to_start
    
    def get_component_status_summary(self) -> Dict[str, int]:
        """
        Get a summary of component statuses.
        
        Returns:
            Dictionary mapping status names to count of components with that status
        """
        summary = {}
        for status in ComponentStatus:
            summary[status.value] = len(self.registry.get_by_status(status))
        
        return summary
    
    def get_development_progress(self) -> float:
        """
        Get the overall development progress as a percentage.
        
        Returns:
            Percentage of components that are completed (0.0 to 1.0)
        """
        total_components = len(self.registry.components)
        if total_components == 0:
            return 0.0
        
        completed = len(self.registry.get_by_status(ComponentStatus.COMPLETED))
        return completed / total_components
    
    def update_version(self, version: str) -> None:
        """
        Update the current version of the system.
        
        Args:
            version: New version string
        """
        self.current_version = version
        self.last_modified = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the development state to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the development state
        """
        return {
            "registry": self.registry.to_dict(),
            "session_manager": self.session_manager.to_dict(),
            "task_manager": self.task_manager.to_dict(),
            "current_component": self.current_component,
            "current_version": self.current_version,
            "last_modified": self.last_modified,
            "development_notes": self.development_notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DevelopmentState':
        """
        Create a development state from a dictionary.
        
        Args:
            data: Dictionary representation of the development state
            
        Returns:
            New DevelopmentState instance
        """
        state = cls()
        
        state.registry = ComponentRegistry.from_dict(data.get("registry", {}))
        state.session_manager = SessionManager.from_dict(data.get("session_manager", {}))
        state.task_manager = TaskManager.from_dict(data.get("task_manager", {"tasks": {}}))
        state.current_component = data.get("current_component")
        state.current_version = data.get("current_version", "0.0.1")
        state.last_modified = data.get("last_modified", datetime.now().isoformat())
        state.development_notes = data.get("development_notes", {})
        
        return state
    
    def save_to_file(self, filepath: str) -> None:
        """
        Save the development state to a file.
        
        Args:
            filepath: Path to save the file to
        """
        # Ensure directory exists
        directory = os.path.dirname(filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'DevelopmentState':
        """
        Load the development state from a file.
        
        Args:
            filepath: Path to load the file from
            
        Returns:
            New DevelopmentState instance
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            json.JSONDecodeError: If the file is not valid JSON
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        return cls.from_dict(data)
    
    def print_summary(self) -> str:
        """
        Generate a summary of the development state.
        
        Returns:
            String representation of the summary
        """
        summary = []
        summary.append(f"EnviroSense Development State - v{self.current_version}")
        summary.append(f"Last Modified: {self.last_modified}")
        summary.append("")
        
        # Component status
        status_summary = self.get_component_status_summary()
        summary.append("Component Status:")
        for status, count in status_summary.items():
            summary.append(f"  {status}: {count}")
        
        # Progress
        progress = self.get_development_progress() * 100
        summary.append(f"Overall Progress: {progress:.1f}%")
        summary.append("")
        
        # Current session
        if self.session_manager.current_session:
            session = self.session_manager.current_session
            summary.append(f"Current Session: {session.session_id}")
            summary.append(f"Started: {session.timestamp}")
            if session.focus_components:
                summary.append("Focus Components:")
                for comp in session.focus_components:
                    summary.append(f"  - {comp}")
        
        # Current task
        current_task = self.task_manager.get_current_task()
        if current_task:
            summary.append("\nCurrent Task:")
            summary.append(f"  ID: {current_task.task_id}")
            summary.append(f"  Name: {current_task.name}")
            summary.append(f"  Status: {current_task.status.value}")
            if current_task.components:
                summary.append(f"  Associated Components: {', '.join(current_task.components)}")
        
        # Next tasks
        next_tasks = self.task_manager.get_next_tasks(3)
        if next_tasks:
            summary.append("\nNext Tasks:")
            for task in next_tasks:
                summary.append(f"  - {task.name} ({task.task_id})")
        
        # Suggested focus (component-based)
        suggested = self.get_suggested_focus()
        if suggested:
            summary.append("\nSuggested Component Focus:")
            for comp in suggested:
                summary.append(f"  - {comp}")
        
        return "\n".join(summary)
        
    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """
        Get a task by its ID.
        
        Args:
            task_id: ID of the task to get
            
        Returns:
            The task, or None if not found
        """
        return self.task_manager.get_task(task_id)
    
    def get_tasks_for_component(self, component_name: str) -> List[Task]:
        """
        Get all tasks associated with a component.
        
        Args:
            component_name: Name of the component
            
        Returns:
            List of tasks associated with the component
        """
        return self.task_manager.get_tasks_by_component(component_name)
    
    def set_current_task(self, task_id: str) -> None:
        """
        Set the current task being worked on.
        
        Args:
            task_id: ID of the task to set as current
        """
        self.task_manager.set_current_task(task_id)
        
        # If the task has associated components, set focus to those components
        task = self.task_manager.get_task(task_id)
        if task and task.components:
            self.set_focus(task.components)
        
        self.last_modified = datetime.now().isoformat()
    
    def update_task_status(self, task_id: str, status: TaskStatus) -> None:
        """
        Update the status of a task.
        
        Args:
            task_id: ID of the task to update
            status: New status for the task
        """
        self.task_manager.update_task_status(task_id, status)
        self.last_modified = datetime.now().isoformat()
