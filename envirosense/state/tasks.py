"""
EnviroSense state management - Task tracking
"""
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime


class TaskStatus(Enum):
    """Status of a task in the development process."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    DEFERRED = "deferred"


class TaskType(Enum):
    """Type of task in the hierarchy."""
    PHASE = "phase"
    COMPONENT = "component"
    TASK = "task"
    MINI_TASK = "mini_task"
    CHECKPOINT = "checkpoint"
    MINI_CHECKPOINT = "mini_checkpoint"


class Task:
    """
    Represents a task or subtask in the EnviroSense development plan.
    
    Tasks can be hierarchical, with phases containing components,
    components containing tasks, and tasks containing mini-tasks.
    Checkpoints are special tasks that represent verification points.
    """
    
    def __init__(self, 
                 task_id: str, 
                 name: str, 
                 description: str, 
                 task_type: TaskType,
                 parent_id: Optional[str] = None):
        """
        Initialize a new task.
        
        Args:
            task_id: Unique identifier for the task (e.g. "1.1.2")
            name: Name of the task
            description: Description of what the task involves
            task_type: Type of task (phase, component, task, mini-task, checkpoint)
            parent_id: ID of the parent task, or None if this is a top-level task
        """
        self.task_id = task_id
        self.name = name
        self.description = description
        self.task_type = task_type
        self.parent_id = parent_id
        self.status = TaskStatus.NOT_STARTED
        self.subtasks = []
        self.dependencies = []
        self.components = []  # Component names associated with this task
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.started_at = None
        self.completed_at = None
        self.assigned_to = None
        self.estimated_days = None
        self.actual_days = None
        self.notes = ""
        self.blockers = []
    
    def add_subtask(self, task_id: str) -> None:
        """Add a subtask to this task."""
        if task_id not in self.subtasks:
            self.subtasks.append(task_id)
            self.updated_at = datetime.now().isoformat()
    
    def remove_subtask(self, task_id: str) -> None:
        """Remove a subtask from this task."""
        if task_id in self.subtasks:
            self.subtasks.remove(task_id)
            self.updated_at = datetime.now().isoformat()
    
    def add_dependency(self, task_id: str) -> None:
        """Add a dependency on another task."""
        if task_id not in self.dependencies:
            self.dependencies.append(task_id)
            self.updated_at = datetime.now().isoformat()
    
    def remove_dependency(self, task_id: str) -> None:
        """Remove a dependency on another task."""
        if task_id in self.dependencies:
            self.dependencies.remove(task_id)
            self.updated_at = datetime.now().isoformat()
    
    def add_component(self, component_name: str) -> None:
        """Associate a component with this task."""
        if component_name not in self.components:
            self.components.append(component_name)
            self.updated_at = datetime.now().isoformat()
    
    def remove_component(self, component_name: str) -> None:
        """Remove a component association from this task."""
        if component_name in self.components:
            self.components.remove(component_name)
            self.updated_at = datetime.now().isoformat()
    
    def update_status(self, status: TaskStatus) -> None:
        """Update the status of the task."""
        old_status = self.status
        self.status = status
        self.updated_at = datetime.now().isoformat()
        
        # Update timestamps based on status changes
        if old_status != TaskStatus.IN_PROGRESS and status == TaskStatus.IN_PROGRESS:
            self.started_at = datetime.now().isoformat()
        
        if status == TaskStatus.COMPLETED and self.completed_at is None:
            self.completed_at = datetime.now().isoformat()
    
    def set_assigned_to(self, assigned_to: str) -> None:
        """Set who the task is assigned to."""
        self.assigned_to = assigned_to
        self.updated_at = datetime.now().isoformat()
    
    def set_estimated_days(self, days: float) -> None:
        """Set the estimated number of days to complete the task."""
        self.estimated_days = days
        self.updated_at = datetime.now().isoformat()
    
    def set_actual_days(self, days: float) -> None:
        """Set the actual number of days taken to complete the task."""
        self.actual_days = days
        self.updated_at = datetime.now().isoformat()
    
    def add_note(self, note: str) -> None:
        """Add a note to the task."""
        self.notes += f"\n[{datetime.now().isoformat()}] {note}"
        self.updated_at = datetime.now().isoformat()
    
    def add_blocker(self, blocker: str) -> None:
        """Add a blocker to the task."""
        self.blockers.append({
            "description": blocker,
            "timestamp": datetime.now().isoformat(),
            "resolved": False,
            "resolved_at": None
        })
        self.updated_at = datetime.now().isoformat()
    
    def resolve_blocker(self, index: int, resolution: str) -> None:
        """Resolve a blocker by index."""
        if 0 <= index < len(self.blockers):
            self.blockers[index]["resolved"] = True
            self.blockers[index]["resolved_at"] = datetime.now().isoformat()
            self.blockers[index]["resolution"] = resolution
            self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the task to a dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "task_type": self.task_type.value,
            "parent_id": self.parent_id,
            "status": self.status.value,
            "subtasks": self.subtasks,
            "dependencies": self.dependencies,
            "components": self.components,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "assigned_to": self.assigned_to,
            "estimated_days": self.estimated_days,
            "actual_days": self.actual_days,
            "notes": self.notes,
            "blockers": self.blockers
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create a task from a dictionary."""
        task = cls(
            task_id=data["task_id"],
            name=data["name"],
            description=data["description"],
            task_type=TaskType(data["task_type"]),
            parent_id=data.get("parent_id")
        )
        
        task.status = TaskStatus(data.get("status", TaskStatus.NOT_STARTED.value))
        task.subtasks = data.get("subtasks", [])
        task.dependencies = data.get("dependencies", [])
        task.components = data.get("components", [])
        task.created_at = data.get("created_at", task.created_at)
        task.updated_at = data.get("updated_at", task.updated_at)
        task.started_at = data.get("started_at")
        task.completed_at = data.get("completed_at")
        task.assigned_to = data.get("assigned_to")
        task.estimated_days = data.get("estimated_days")
        task.actual_days = data.get("actual_days")
        task.notes = data.get("notes", "")
        task.blockers = data.get("blockers", [])
        
        return task


class TaskManager:
    """
    Manages tasks in the development plan.
    
    Provides methods for creating, retrieving, and managing tasks.
    Handles task hierarchy, dependencies, and status updates.
    """
    
    def __init__(self):
        """Initialize a new task manager."""
        self.tasks = {}  # Dictionary mapping task_id to Task
        self.current_task_id = None
    
    def add_task(self, task: Task) -> None:
        """
        Add a task to the manager.
        
        Args:
            task: The task to add
        """
        self.tasks[task.task_id] = task
        
        # If this task has a parent, add it as a subtask of the parent
        if task.parent_id and task.parent_id in self.tasks:
            self.tasks[task.parent_id].add_subtask(task.task_id)
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task by ID.
        
        Args:
            task_id: ID of the task to get
            
        Returns:
            The task, or None if not found
        """
        return self.tasks.get(task_id)
    
    def get_tasks_by_type(self, task_type: TaskType) -> List[Task]:
        """
        Get all tasks of a specific type.
        
        Args:
            task_type: Type of tasks to get
            
        Returns:
            List of tasks of the specified type
        """
        return [
            task for task in self.tasks.values()
            if task.task_type == task_type
        ]
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """
        Get all tasks with a specific status.
        
        Args:
            status: Status of tasks to get
            
        Returns:
            List of tasks with the specified status
        """
        return [
            task for task in self.tasks.values()
            if task.status == status
        ]
    
    def get_tasks_by_component(self, component_name: str) -> List[Task]:
        """
        Get all tasks associated with a specific component.
        
        Args:
            component_name: Name of the component
            
        Returns:
            List of tasks associated with the component
        """
        return [
            task for task in self.tasks.values()
            if component_name in task.components
        ]
    
    def get_subtasks(self, task_id: str) -> List[Task]:
        """
        Get all subtasks of a task.
        
        Args:
            task_id: ID of the parent task
            
        Returns:
            List of subtasks
        """
        task = self.get_task(task_id)
        if not task:
            return []
        
        return [self.get_task(subtask_id) for subtask_id in task.subtasks]
    
    def get_blocked_tasks(self) -> List[Task]:
        """
        Get all tasks that are blocked.
        
        Returns:
            List of blocked tasks
        """
        return [
            task for task in self.tasks.values()
            if task.status == TaskStatus.BLOCKED or task.blockers
        ]
    
    def get_ready_tasks(self) -> List[Task]:
        """
        Get all tasks that are ready to be worked on.
        
        A task is ready if:
        1. It is not started or in progress
        2. All of its dependencies are completed
        3. It is not blocked
        
        Returns:
            List of ready tasks
        """
        ready_tasks = []
        
        for task in self.tasks.values():
            if task.status not in [TaskStatus.NOT_STARTED, TaskStatus.IN_PROGRESS]:
                continue
            
            if task.blockers and any(not blocker["resolved"] for blocker in task.blockers):
                continue
            
            all_deps_completed = True
            for dep_id in task.dependencies:
                dep_task = self.get_task(dep_id)
                if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                    all_deps_completed = False
                    break
            
            if all_deps_completed:
                ready_tasks.append(task)
        
        return ready_tasks
    
    def get_current_task(self) -> Optional[Task]:
        """
        Get the current task being worked on.
        
        Returns:
            The current task, or None if no task is set
        """
        if not self.current_task_id:
            return None
        
        return self.get_task(self.current_task_id)
    
    def set_current_task(self, task_id: str) -> None:
        """
        Set the current task being worked on.
        
        Args:
            task_id: ID of the task to set as current
        """
        if task_id in self.tasks:
            self.current_task_id = task_id
            
            # Automatically mark the task as in progress if it's not completed
            task = self.tasks[task_id]
            if task.status == TaskStatus.NOT_STARTED:
                task.update_status(TaskStatus.IN_PROGRESS)
    
    def clear_current_task(self) -> None:
        """Clear the current task."""
        self.current_task_id = None
    
    def update_task_status(self, task_id: str, status: TaskStatus) -> None:
        """
        Update the status of a task.
        
        Args:
            task_id: ID of the task to update
            status: New status for the task
        """
        task = self.get_task(task_id)
        if task:
            task.update_status(status)
    
    def get_task_progress(self, task_id: str) -> float:
        """
        Get the progress of a task as a percentage.
        
        For leaf tasks (no subtasks), progress is binary: 0% or 100%.
        For non-leaf tasks, progress is the average of the progress of all subtasks.
        
        Args:
            task_id: ID of the task to get progress for
            
        Returns:
            Progress as a percentage (0.0 to 1.0)
        """
        task = self.get_task(task_id)
        if not task:
            return 0.0
        
        # If the task is completed, it's 100% done
        if task.status == TaskStatus.COMPLETED:
            return 1.0
        
        # If the task has no subtasks, it's either 0% or 100% done
        if not task.subtasks:
            return 0.0
        
        # Calculate progress based on subtask completion
        subtasks = self.get_subtasks(task_id)
        if not subtasks:
            return 0.0
        
        subtask_progress = [self.get_task_progress(subtask.task_id) for subtask in subtasks]
        return sum(subtask_progress) / len(subtask_progress)
    
    def get_next_tasks(self, limit: int = 5) -> List[Task]:
        """
        Get the next tasks that should be worked on.
        
        Args:
            limit: Maximum number of tasks to return
            
        Returns:
            List of next tasks to work on, prioritized by readiness and dependency order
        """
        ready_tasks = self.get_ready_tasks()
        
        # Sort by dependency depth (tasks with no dependencies first)
        def get_dependency_depth(task: Task) -> int:
            if not task.dependencies:
                return 0
            
            max_depth = 0
            for dep_id in task.dependencies:
                dep_task = self.get_task(dep_id)
                if dep_task:
                    max_depth = max(max_depth, 1 + get_dependency_depth(dep_task))
            
            return max_depth
        
        ready_tasks.sort(key=get_dependency_depth)
        
        return ready_tasks[:limit]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the task manager to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the task manager
        """
        return {
            "tasks": {task_id: task.to_dict() for task_id, task in self.tasks.items()},
            "current_task_id": self.current_task_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskManager':
        """
        Create a task manager from a dictionary.
        
        Args:
            data: Dictionary representation of the task manager
            
        Returns:
            New TaskManager instance
        """
        manager = cls()
        
        # Load tasks
        for task_id, task_data in data.get("tasks", {}).items():
            manager.tasks[task_id] = Task.from_dict(task_data)
        
        # Set current task
        manager.current_task_id = data.get("current_task_id")
        
        return manager
