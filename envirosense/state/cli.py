"""
EnviroSense state management - Command Line Interface
"""
import sys
import argparse
from typing import List, Optional

from envirosense.state.components import ComponentStatus, Tags
from envirosense.state.tasks import TaskStatus, TaskType
from envirosense.state.utils import (
    get_state,
    save_state,
    print_state_summary,
    start_development_session,
    end_development_session,
    create_development_checkpoint,
    record_change,
    update_component_status,
    list_components_by_tag
)
from envirosense.state.initialize import initialize_state
from envirosense.state.init_master_plan import initialize_master_plan


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="EnviroSense Development State Management")
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Initialize command
    init_parser = subparsers.add_parser("init", help="Initialize the development state")
    
    # Initialize master plan command
    init_plan_parser = subparsers.add_parser("init-plan", help="Initialize the master plan tasks")
    
    # Summary command
    summary_parser = subparsers.add_parser("summary", help="Print a summary of the development state")
    
    # Start session command
    start_parser = subparsers.add_parser("start", help="Start a new development session")
    start_parser.add_argument(
        "--focus", 
        nargs="+", 
        help="List of component names to focus on in this session"
    )
    
    # End session command
    end_parser = subparsers.add_parser("end", help="End the current development session")
    end_parser.add_argument(
        "--notes", 
        help="Notes to add to the session"
    )
    
    # Checkpoint command
    checkpoint_parser = subparsers.add_parser("checkpoint", help="Create a development checkpoint")
    checkpoint_parser.add_argument(
        "name", 
        help="Name of the checkpoint"
    )
    checkpoint_parser.add_argument(
        "description", 
        help="Description of the checkpoint"
    )
    
    # Record change command
    change_parser = subparsers.add_parser("change", help="Record a change to a component")
    change_parser.add_argument(
        "component", 
        help="Name of the component that was changed"
    )
    change_parser.add_argument(
        "description", 
        help="Description of the change"
    )
    change_parser.add_argument(
        "--files", 
        nargs="+", 
        help="List of files that were changed"
    )
    change_parser.add_argument(
        "--type", 
        default="implementation",
        help="Type of change (e.g., implementation, refactoring, bugfix)"
    )
    
    # Update component status command
    status_parser = subparsers.add_parser("component-status", help="Update the status of a component")
    status_parser.add_argument(
        "component", 
        help="Name of the component"
    )
    status_parser.add_argument(
        "status", 
        choices=[s.value for s in ComponentStatus],
        help="New status for the component"
    )
    
    # List components command
    list_parser = subparsers.add_parser("list-components", help="List components")
    list_parser.add_argument(
        "--tag", 
        help="Filter by tag"
    )
    
    # List tasks command
    list_tasks_parser = subparsers.add_parser("list-tasks", help="List tasks")
    list_tasks_parser.add_argument(
        "--type", 
        choices=[t.value for t in TaskType],
        help="Filter by task type"
    )
    list_tasks_parser.add_argument(
        "--status", 
        choices=[s.value for s in TaskStatus],
        help="Filter by task status"
    )
    list_tasks_parser.add_argument(
        "--component", 
        help="Filter by associated component"
    )
    list_tasks_parser.add_argument(
        "--parent", 
        help="Filter by parent task ID"
    )
    
    # Task details command
    task_details_parser = subparsers.add_parser("task", help="Show task details")
    task_details_parser.add_argument(
        "task_id", 
        help="ID of the task"
    )
    
    # Set current task command
    set_task_parser = subparsers.add_parser("set-task", help="Set the current task")
    set_task_parser.add_argument(
        "task_id", 
        help="ID of the task to set as current"
    )
    
    # Update task status command
    task_status_parser = subparsers.add_parser("task-status", help="Update the status of a task")
    task_status_parser.add_argument(
        "task_id", 
        help="ID of the task"
    )
    task_status_parser.add_argument(
        "status", 
        choices=[s.value for s in TaskStatus],
        help="New status for the task"
    )
    
    # Add task note command
    task_note_parser = subparsers.add_parser("task-note", help="Add a note to a task")
    task_note_parser.add_argument(
        "task_id", 
        help="ID of the task"
    )
    task_note_parser.add_argument(
        "note", 
        help="Note to add to the task"
    )
    
    # Add task blocker command
    task_blocker_parser = subparsers.add_parser("task-blocker", help="Add a blocker to a task")
    task_blocker_parser.add_argument(
        "task_id", 
        help="ID of the task"
    )
    task_blocker_parser.add_argument(
        "blocker", 
        help="Description of the blocker"
    )
    
    # Resolve task blocker command
    resolve_blocker_parser = subparsers.add_parser("resolve-blocker", help="Resolve a blocker on a task")
    resolve_blocker_parser.add_argument(
        "task_id", 
        help="ID of the task"
    )
    resolve_blocker_parser.add_argument(
        "index", 
        type=int,
        help="Index of the blocker to resolve (0-based)"
    )
    resolve_blocker_parser.add_argument(
        "resolution", 
        help="Description of how the blocker was resolved"
    )
    
    return parser.parse_args()


def main():
    """Main entry point for the CLI."""
    args = parse_args()
    
    if args.command == "init":
        # Initialize the development state
        initialize_state()
    
    elif args.command == "init-plan":
        # Initialize the master plan tasks
        initialize_master_plan()
    
    elif args.command == "summary":
        # Print a summary of the development state
        print_state_summary()
    
    elif args.command == "start":
        # Start a new development session
        start_development_session(args.focus)
    
    elif args.command == "end":
        # End the current development session
        end_development_session(args.notes)
    
    elif args.command == "checkpoint":
        # Create a development checkpoint
        create_development_checkpoint(args.name, args.description)
    
    elif args.command == "change":
        # Record a change to a component
        record_change(
            args.component,
            args.description,
            args.files or [],
            args.type
        )
    
    elif args.command == "component-status":
        # Update the status of a component
        update_component_status(args.component, ComponentStatus(args.status))
    
    elif args.command == "list-components":
        # List components
        if args.tag:
            list_components_by_tag(args.tag)
        else:
            # If no tag specified, print component summary
            state = get_state()
            print(f"EnviroSense Components:")
            for name, component in sorted(state.registry.components.items()):
                print(f"  - {name} ({component.status.value})")
                print(f"    {component.description}")
    
    elif args.command == "list-tasks":
        # List tasks
        state = get_state()
        task_manager = state.task_manager
        
        # Filter tasks by type
        if args.type:
            tasks = task_manager.get_tasks_by_type(TaskType(args.type))
        else:
            tasks = list(task_manager.tasks.values())
        
        # Further filter by status
        if args.status:
            tasks = [t for t in tasks if t.status == TaskStatus(args.status)]
        
        # Further filter by component
        if args.component:
            tasks = [t for t in tasks if args.component in t.components]
        
        # Further filter by parent
        if args.parent:
            tasks = [t for t in tasks if t.parent_id == args.parent]
        
        # Print tasks
        if tasks:
            print("EnviroSense Tasks:")
            for task in sorted(tasks, key=lambda t: t.task_id):
                print(f"  - [{task.status.value}] {task.task_id}: {task.name}")
        else:
            print("No tasks found matching the criteria.")
    
    elif args.command == "task":
        # Show task details
        state = get_state()
        task = state.get_task_by_id(args.task_id)
        
        if task:
            print(f"Task {task.task_id}: {task.name}")
            print(f"Type: {task.task_type.value}")
            print(f"Status: {task.status.value}")
            print(f"Description: {task.description}")
            
            if task.parent_id:
                parent = state.get_task_by_id(task.parent_id)
                if parent:
                    print(f"Parent: {task.parent_id} ({parent.name})")
            
            if task.subtasks:
                print("Subtasks:")
                for subtask_id in task.subtasks:
                    subtask = state.get_task_by_id(subtask_id)
                    if subtask:
                        print(f"  - {subtask_id}: {subtask.name} ({subtask.status.value})")
            
            if task.components:
                print("Associated Components:")
                for component_name in task.components:
                    component = state.get_component(component_name)
                    if component:
                        print(f"  - {component_name} ({component.status.value})")
            
            if task.dependencies:
                print("Dependencies:")
                for dep_id in task.dependencies:
                    dep = state.get_task_by_id(dep_id)
                    if dep:
                        print(f"  - {dep_id}: {dep.name} ({dep.status.value})")
            
            if task.started_at:
                print(f"Started: {task.started_at}")
            
            if task.completed_at:
                print(f"Completed: {task.completed_at}")
            
            if task.estimated_days is not None:
                print(f"Estimated Days: {task.estimated_days}")
            
            if task.actual_days is not None:
                print(f"Actual Days: {task.actual_days}")
            
            if task.assigned_to:
                print(f"Assigned To: {task.assigned_to}")
            
            if task.blockers:
                print("Blockers:")
                for i, blocker in enumerate(task.blockers):
                    status = "RESOLVED" if blocker.get("resolved", False) else "OPEN"
                    print(f"  {i}. [{status}] {blocker['description']}")
                    if blocker.get("resolved", False):
                        print(f"     Resolved at: {blocker.get('resolved_at')}")
                        print(f"     Resolution: {blocker.get('resolution')}")
            
            if task.notes:
                print("Notes:")
                print(task.notes)
        else:
            print(f"Task with ID '{args.task_id}' not found.")
    
    elif args.command == "set-task":
        # Set the current task
        state = get_state()
        task = state.get_task_by_id(args.task_id)
        
        if task:
            state.set_current_task(args.task_id)
            save_state()
            print(f"Current task set to: {task.task_id} ({task.name})")
            if task.components:
                print(f"Focus components set to: {', '.join(task.components)}")
        else:
            print(f"Task with ID '{args.task_id}' not found.")
    
    elif args.command == "task-status":
        # Update the status of a task
        state = get_state()
        task = state.get_task_by_id(args.task_id)
        
        if task:
            state.update_task_status(args.task_id, TaskStatus(args.status))
            save_state()
            print(f"Updated status of task '{args.task_id}' to '{args.status}'")
        else:
            print(f"Task with ID '{args.task_id}' not found.")
    
    elif args.command == "task-note":
        # Add a note to a task
        state = get_state()
        task = state.get_task_by_id(args.task_id)
        
        if task:
            task.add_note(args.note)
            save_state()
            print(f"Added note to task '{args.task_id}'")
        else:
            print(f"Task with ID '{args.task_id}' not found.")
    
    elif args.command == "task-blocker":
        # Add a blocker to a task
        state = get_state()
        task = state.get_task_by_id(args.task_id)
        
        if task:
            task.add_blocker(args.blocker)
            save_state()
            print(f"Added blocker to task '{args.task_id}'")
        else:
            print(f"Task with ID '{args.task_id}' not found.")
    
    elif args.command == "resolve-blocker":
        # Resolve a blocker on a task
        state = get_state()
        task = state.get_task_by_id(args.task_id)
        
        if task:
            if 0 <= args.index < len(task.blockers):
                task.resolve_blocker(args.index, args.resolution)
                save_state()
                print(f"Resolved blocker {args.index} on task '{args.task_id}'")
            else:
                print(f"Invalid blocker index: {args.index}")
        else:
            print(f"Task with ID '{args.task_id}' not found.")
    
    else:
        # If no command specified, print a summary
        print_state_summary()


if __name__ == "__main__":
    main()
