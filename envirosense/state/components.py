"""
EnviroSense state management - Component system
"""
from enum import Enum
from typing import List, Dict, Optional
from datetime import datetime


class ComponentStatus(Enum):
    """Status of a component in the development lifecycle."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    IMPLEMENTED = "implemented"
    TESTED = "tested"
    OPTIMIZED = "optimized"
    DOCUMENTED = "documented"
    COMPLETED = "completed"


class Tags:
    """Common tags for categorizing components."""
    CORE = "core"
    UI = "ui"
    API = "api"
    DATA = "data"
    SIMULATION = "simulation"
    PHYSICS = "physics"
    CHEMICAL = "chemical"
    PHYSIOLOGICAL = "physiological"
    UTILITY = "utility"
    INFRASTRUCTURE = "infrastructure"


class Component:
    """
    Represents a component in the EnviroSense system.
    Components are the building blocks of the system and can be
    tagged, have dependencies, and have a development status.
    """
    
    def __init__(self, name: str, description: str, tags: Optional[List[str]] = None):
        """
        Initialize a new component.
        
        Args:
            name: Unique name of the component
            description: Description of the component's purpose
            tags: List of tags for categorizing the component
        """
        self.name = name
        self.description = description
        self.tags = tags or []
        self.dependencies = []
        self.interfaces = []
        self.implementations = []
        self.test_files = []
        self.status = ComponentStatus.NOT_STARTED
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.notes = ""
    
    def add_dependency(self, component_name: str) -> None:
        """Add a dependency on another component."""
        if component_name not in self.dependencies:
            self.dependencies.append(component_name)
            self.updated_at = datetime.now().isoformat()
    
    def remove_dependency(self, component_name: str) -> None:
        """Remove a dependency on another component."""
        if component_name in self.dependencies:
            self.dependencies.remove(component_name)
            self.updated_at = datetime.now().isoformat()
    
    def update_status(self, status: ComponentStatus) -> None:
        """Update the status of the component."""
        self.status = status
        self.updated_at = datetime.now().isoformat()
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the component."""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now().isoformat()
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the component."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.now().isoformat()
    
    def add_note(self, note: str) -> None:
        """Add a note to the component."""
        self.notes += f"\n[{datetime.now().isoformat()}] {note}"
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        """Convert the component to a dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "dependencies": self.dependencies,
            "interfaces": self.interfaces,
            "implementations": self.implementations,
            "test_files": self.test_files,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Component':
        """Create a component from a dictionary."""
        component = cls(
            name=data["name"],
            description=data["description"],
            tags=data.get("tags", [])
        )
        component.dependencies = data.get("dependencies", [])
        component.interfaces = data.get("interfaces", [])
        component.implementations = data.get("implementations", [])
        component.test_files = data.get("test_files", [])
        component.status = ComponentStatus(data.get("status", ComponentStatus.NOT_STARTED.value))
        component.created_at = data.get("created_at", component.created_at)
        component.updated_at = data.get("updated_at", component.updated_at)
        component.notes = data.get("notes", "")
        return component


class ComponentRegistry:
    """
    Registry of all components in the system.
    Provides methods for registering, retrieving, and querying components.
    """
    
    def __init__(self):
        """Initialize a new component registry."""
        self.components = {}
    
    def register(self, component: Component) -> None:
        """Register a component in the registry."""
        self.components[component.name] = component
    
    def get_component(self, name: str) -> Optional[Component]:
        """Get a component by name."""
        return self.components.get(name)
    
    def get_by_tag(self, tag: str) -> List[Component]:
        """Get all components with a specific tag."""
        return [comp for comp in self.components.values() if tag in comp.tags]
    
    def get_by_status(self, status: ComponentStatus) -> List[Component]:
        """Get all components with a specific status."""
        return [comp for comp in self.components.values() if comp.status == status]
    
    def get_dependencies(self, component_name: str, recursive: bool = False) -> List[str]:
        """
        Get dependencies of a component.
        
        Args:
            component_name: Name of the component
            recursive: Whether to include indirect dependencies
            
        Returns:
            List of component names that are dependencies
        """
        component = self.get_component(component_name)
        if not component:
            return []
        
        if not recursive:
            return component.dependencies
        
        # Recursive implementation
        all_deps = set(component.dependencies)
        for dep_name in component.dependencies:
            all_deps.update(self.get_dependencies(dep_name, recursive=True))
        
        return list(all_deps)
    
    def get_dependents(self, component_name: str) -> List[str]:
        """Get all components that depend on the specified component."""
        return [
            comp.name for comp in self.components.values()
            if component_name in comp.dependencies
        ]
    
    def to_dict(self) -> Dict:
        """Convert the registry to a dictionary for serialization."""
        return {
            name: component.to_dict() 
            for name, component in self.components.items()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ComponentRegistry':
        """Create a registry from a dictionary."""
        registry = cls()
        for name, comp_data in data.items():
            registry.register(Component.from_dict(comp_data))
        return registry
