"""
EnviroSense state management - Utility functions
"""
import os
import json
from typing import List, Dict, Any, Optional, Callable, TypeVar, Union
from datetime import datetime

from envirosense.state.components import Component, ComponentRegistry, ComponentStatus, Tags
from envirosense.state.sessions import SessionManager, DevelopmentSession, Checkpoint
from envirosense.state.development_state import DevelopmentState


# Default path for the development state file
DEFAULT_STATE_PATH = "dev_state.json"

# Global state instance
_state_instance = None


def get_state(filepath: Optional[str] = None) -> DevelopmentState:
    """
    Get the development state instance.
    
    If the instance doesn't exist yet, it will be created and loaded
    from the specified file if it exists. If the file doesn't exist,
    a new instance will be created.
    
    Args:
        filepath: Path to the development state file (defaults to DEFAULT_STATE_PATH)
        
    Returns:
        DevelopmentState instance
    """
    global _state_instance
    
    if _state_instance is not None:
        return _state_instance
    
    filepath = filepath or DEFAULT_STATE_PATH
    
    if os.path.exists(filepath):
        try:
            _state_instance = DevelopmentState.load_from_file(filepath)
        except (FileNotFoundError, json.JSONDecodeError):
            _state_instance = DevelopmentState()
    else:
        _state_instance = DevelopmentState()
    
    return _state_instance


def save_state(filepath: Optional[str] = None) -> None:
    """
    Save the development state to a file.
    
    Args:
        filepath: Path to save the file to (defaults to DEFAULT_STATE_PATH)
    """
    filepath = filepath or DEFAULT_STATE_PATH
    state = get_state()
    state.save_to_file(filepath)


def reset_state() -> None:
    """Reset the global state instance."""
    global _state_instance
    _state_instance = None


def initialize_components(components_data: List[Dict[str, Any]]) -> None:
    """
    Initialize components from a list of dictionaries.
    
    Args:
        components_data: List of dictionaries with component data (name, description, tags)
    """
    state = get_state()
    
    for data in components_data:
        component = Component(
            name=data["name"],
            description=data["description"],
            tags=data.get("tags", [])
        )
        
        # Add dependencies if specified
        for dep in data.get("dependencies", []):
            component.add_dependency(dep)
        
        # Set status if specified
        if "status" in data:
            component.update_status(ComponentStatus(data["status"]))
        
        state.register_component(component)
    
    save_state()


def start_development_session(focus_components: Optional[List[str]] = None) -> None:
    """
    Start a new development session.
    
    Args:
        focus_components: List of component names to focus on
    """
    state = get_state()
    state.start_session(focus_components)
    save_state()
    
    # Print a summary of the session
    print(f"Started development session with focus on:")
    for comp in focus_components or []:
        component = state.get_component(comp)
        if component:
            status_str = component.status.value
            print(f"  - {comp} ({status_str})")
        else:
            print(f"  - {comp} (not registered)")


def end_development_session(notes: Optional[str] = None) -> None:
    """
    End the current development session.
    
    Args:
        notes: Optional notes to add to the session
    """
    state = get_state()
    
    if notes:
        current_session = state.session_manager.current_session
        if current_session:
            current_session.add_note(notes)
    
    state.end_session()
    save_state()
    print("Development session ended.")


def create_development_checkpoint(name: str, description: str) -> None:
    """
    Create a development checkpoint.
    
    Args:
        name: Name of the checkpoint
        description: Description of the checkpoint
    """
    state = get_state()
    checkpoint = state.create_checkpoint(name, description)
    save_state()
    print(f"Created checkpoint: {name}")
    print(f"Description: {description}")
    print(f"Timestamp: {checkpoint.timestamp}")


def record_change(component_name: str, 
                 description: str, 
                 files_changed: List[str],
                 change_type: str = "implementation") -> None:
    """
    Record a change to a component.
    
    Args:
        component_name: Name of the component that was changed
        description: Description of the change
        files_changed: List of files that were changed
        change_type: Type of change (e.g., "implementation", "refactoring", "bugfix")
    """
    state = get_state()
    
    # Ensure we have an active session
    if not state.session_manager.current_session:
        state.start_session([component_name])
    
    # Record the change
    state.session_manager.current_session.add_change(
        component=component_name,
        description=description,
        files_changed=files_changed,
        change_type=change_type
    )
    
    # Update the component status if needed
    component = state.get_component(component_name)
    if component and component.status == ComponentStatus.NOT_STARTED:
        component.update_status(ComponentStatus.IN_PROGRESS)
    
    save_state()


def update_component_status(component_name: str, status: ComponentStatus) -> None:
    """
    Update the status of a component.
    
    Args:
        component_name: Name of the component
        status: New status for the component
    """
    state = get_state()
    component = state.get_component(component_name)
    
    if component:
        component.update_status(status)
        save_state()
        print(f"Updated status of '{component_name}' to '{status.value}'")
    else:
        print(f"Component '{component_name}' not found.")


def print_state_summary() -> None:
    """Print a summary of the development state."""
    state = get_state()
    print(state.print_summary())


def list_components_by_tag(tag: str) -> None:
    """
    List all components with a specific tag.
    
    Args:
        tag: Tag to filter by
    """
    state = get_state()
    components = state.get_by_tag(tag)
    
    print(f"Components with tag '{tag}':")
    for component in components:
        print(f"  - {component.name} ({component.status.value})")
        print(f"    {component.description}")
