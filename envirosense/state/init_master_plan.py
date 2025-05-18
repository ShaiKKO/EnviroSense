"""
EnviroSense state management - Master plan initialization
"""
import re
from typing import List, Dict, Any, Optional, Tuple

from envirosense.state.components import ComponentStatus
from envirosense.state.tasks import Task, TaskType, TaskStatus, TaskManager
from envirosense.state.development_state import DevelopmentState
from envirosense.state.utils import get_state, save_state


def parse_master_plan() -> Dict[str, Any]:
    """
    Parse the current master plan metadata.
    
    Returns:
        Dictionary with plan metadata
    """
    try:
        with open("envirosense-master-development-plan-refined.md", "r") as f:
            content = f.read()
    except FileNotFoundError:
        print("Master plan file not found.")
        return {}
    
    metadata = {}
    
    # Extract version
    version_match = re.search(r'ENVIROSENSE-PLAN-VERSION: ([\d\.]+)', content)
    if version_match:
        metadata["version"] = version_match.group(1)
    
    # Extract current phase
    phase_match = re.search(r'CURRENT-PHASE: (\d+)', content)
    if phase_match:
        metadata["current_phase"] = phase_match.group(1)
    
    # Extract current task
    task_match = re.search(r'CURRENT-TASK: ([\d\.]+)', content)
    if task_match:
        metadata["current_task"] = task_match.group(1)
    
    # Extract next milestone
    milestone_match = re.search(r'NEXT-MILESTONE: (.+)\(', content)
    if milestone_match:
        metadata["next_milestone"] = milestone_match.group(1).strip()
    
    # Extract target completion
    completion_match = re.search(r'TARGET-COMPLETION: (.+)', content)
    if completion_match:
        metadata["target_completion"] = completion_match.group(1).strip()
    
    return metadata


def extract_tasks_from_plan() -> List[Dict[str, Any]]:
    """
    Extract all tasks from the master development plan.
    
    Returns:
        List of dictionaries with task data
    """
    try:
        with open("envirosense-master-development-plan-refined.md", "r") as f:
            content = f.read()
    except FileNotFoundError:
        print("Master plan file not found.")
        return []
    
    tasks = []
    
    # Extract phases
    phase_matches = re.finditer(r'## PHASE (\d+): (.+?) \(Weeks (\d+)-(\d+)\)\n\*\*STATUS: (.+?)\*\*', content)
    for phase_match in phase_matches:
        phase_num = phase_match.group(1)
        phase_name = phase_match.group(2)
        phase_status = phase_match.group(5)
        
        phase = {
            "task_id": phase_num,
            "name": f"Phase {phase_num}: {phase_name}",
            "description": f"Phase {phase_num} of the EnviroSense development plan: {phase_name}",
            "task_type": TaskType.PHASE.value,
            "status": TaskStatus.IN_PROGRESS.value if phase_status == "IN PROGRESS" else TaskStatus.NOT_STARTED.value,
            "subtasks": []
        }
        
        tasks.append(phase)
        
        # Extract components within this phase
        component_pattern = rf'### {phase_num}\.(\d+) (.+?) \(Days (\d+)-(\d+)\)'
        component_matches = re.finditer(component_pattern, content)
        
        for comp_match in component_matches:
            comp_num = comp_match.group(1)
            comp_name = comp_match.group(2)
            start_day = comp_match.group(3)
            end_day = comp_match.group(4)
            
            component = {
                "task_id": f"{phase_num}.{comp_num}",
                "name": comp_name,
                "description": f"Component {phase_num}.{comp_num} of the EnviroSense system: {comp_name}",
                "task_type": TaskType.COMPONENT.value,
                "parent_id": phase_num,
                "estimated_days": int(end_day) - int(start_day) + 1,
                "status": TaskStatus.NOT_STARTED.value,
                "subtasks": []
            }
            
            tasks.append(component)
            
            # Extract mini-tasks within this component
            task_pattern = rf'- \[ \] \*\*{phase_num}\.{comp_num}\.(\d+): (.+?)\*\*'
            task_matches = re.finditer(task_pattern, content, re.MULTILINE)
            
            for task_match in task_matches:
                task_num = task_match.group(1)
                task_name = task_match.group(2)
                
                # Find the description by looking for the following lines until the next bullet or mini-checkpoint
                start_pos = task_match.end()
                end_pos = content.find("  - **MINI-CHECKPOINT", start_pos)
                if end_pos == -1:
                    end_pos = content.find("- [ ]", start_pos)
                
                if end_pos == -1:
                    # Default to the next 200 characters if we can't find a clear endpoint
                    description = content[start_pos:start_pos + 200].strip()
                else:
                    description = content[start_pos:end_pos].strip()
                
                # Clean up the description
                description = "\n".join([line.strip() for line in description.split("\n")])
                
                mini_task = {
                    "task_id": f"{phase_num}.{comp_num}.{task_num}",
                    "name": task_name,
                    "description": description,
                    "task_type": TaskType.MINI_TASK.value,
                    "parent_id": f"{phase_num}.{comp_num}",
                    "status": TaskStatus.NOT_STARTED.value,
                    "subtasks": []
                }
                
                tasks.append(mini_task)
                
                # Extract mini-checkpoints for this mini-task
                checkpoint_pattern = rf'  - \*\*MINI-CHECKPOINT {phase_num}\.{comp_num}\.{task_num}\*\*: (.+)'
                checkpoint_match = re.search(checkpoint_pattern, content)
                
                if checkpoint_match:
                    checkpoint_desc = checkpoint_match.group(1)
                    
                    mini_checkpoint = {
                        "task_id": f"{phase_num}.{comp_num}.{task_num}.checkpoint",
                        "name": f"Mini-Checkpoint {phase_num}.{comp_num}.{task_num}",
                        "description": checkpoint_desc,
                        "task_type": TaskType.MINI_CHECKPOINT.value,
                        "parent_id": f"{phase_num}.{comp_num}.{task_num}",
                        "status": TaskStatus.NOT_STARTED.value
                    }
                    
                    tasks.append(mini_checkpoint)
            
            # Extract the component checkpoint
            checkpoint_pattern = rf'\*\*CHECKPOINT {phase_num}\*\*: (.+)'
            checkpoint_match = re.search(checkpoint_pattern, content)
            
            if checkpoint_match and phase_num == "1":  # Only add for Phase 1 for now
                checkpoint_desc = checkpoint_match.group(1)
                
                phase_checkpoint = {
                    "task_id": f"{phase_num}.checkpoint",
                    "name": f"Checkpoint {phase_num}",
                    "description": checkpoint_desc,
                    "task_type": TaskType.CHECKPOINT.value,
                    "parent_id": phase_num,
                    "status": TaskStatus.NOT_STARTED.value
                }
                
                tasks.append(phase_checkpoint)
    
    return tasks


def create_component_associations() -> Dict[str, List[str]]:
    """
    Create associations between tasks and components.
    
    Returns:
        Dictionary mapping task IDs to component names
    """
    # This is a mapping of task patterns to component names
    task_to_component = {
        "1.1": ["TimeSeriesGenerator"],
        "1.1.1": ["TimeSeriesGenerator"],
        "1.1.2": ["TimeSeriesGenerator"],
        "1.1.3": ["TimeSeriesGenerator"],
        
        "1.2": ["EnvironmentalPhysicsEngine"],
        "1.2.1": ["EnvironmentalPhysicsEngine"],
        "1.2.2": ["EnvironmentalPhysicsEngine", "ChemicalBehaviorModels"],
        "1.2.3": ["EnvironmentalPhysicsEngine", "ChemicalBehaviorModels"],
        "1.2.4": ["EnvironmentalPhysicsEngine", "ChemicalBehaviorModels"],
        
        "1.3": ["PhysiologicalResponseCorrelator"],
        "1.3.1": ["PhysiologicalResponseCorrelator", "SensitivityProfileModel"],
        "1.3.2": ["PhysiologicalResponseCorrelator"],
        "1.3.3": ["PhysiologicalResponseCorrelator"],
        "1.3.4": ["PhysiologicalResponseCorrelator"],
        
        "1.4": ["DataExportService"],
        "1.4.1": ["DataExportService"],
        "1.4.2": ["DataExportService"],
        "1.4.3": ["DataExportService"],
        
        "1.5": ["ScenarioManager", "ScenarioModel"],
        "1.5.1": ["ScenarioManager", "ScenarioModel"],
        "1.5.2": ["ScenarioManager", "ScenarioModel"],
        "1.5.3": ["ScenarioManager", "ScenarioModel"],
        "1.5.4": ["ScenarioManager", "ScenarioModel"],
        
        "1.6": ["ParameterController"],
        "1.6.1": ["ParameterController"],
        "1.6.2": ["ParameterController"],
        "1.6.3": ["ParameterController"],
        
        "1.7": ["APILayer"],
        "1.7.1": ["APILayer"],
        "1.7.2": ["APILayer", "ScenarioManager"],
        "1.7.3": ["APILayer", "ParameterController"],
        "1.7.4": ["APILayer", "DataExportService"],
        
        "1.8": ["APILayer"],
        "1.8.1": ["APILayer"],
        "1.8.2": ["APILayer", "DataExportService"],
        "1.8.3": ["APILayer"],
        
        "1.9": ["VisualizationComponents"],
        "1.9.1": ["VisualizationComponents"],
        "1.9.2": ["VisualizationComponents"],
        "1.9.3": ["VisualizationComponents"],
        "1.9.4": ["VisualizationComponents", "SimulationControlUI"],
        
        "1.10": ["ProjectSetup"],
        "1.10.1": ["ProjectSetup"],
        "1.10.2": ["ProjectSetup"],
        "1.10.3": ["ProjectSetup"],
        "1.10.4": ["ProjectSetup"],
        
        "1.11": ["SimulationControlUI"],
        "1.11.1": ["SimulationControlUI"],
        "1.11.2": ["SimulationControlUI"],
        "1.11.3": ["SimulationControlUI"],
        "1.11.4": ["SimulationControlUI"],
        "1.11.5": ["SimulationControlUI"],
        "1.11.6": ["SimulationControlUI"],
        "1.11.7": ["SimulationControlUI"],
        
        "1.12": ["APILayer", "DataExportService"],
        "1.12.1": ["APILayer"],
        "1.12.2": ["DataExportService"],
        "1.12.3": ["DataStorage"],
        "1.12.4": ["APILayer"],
        "1.12.5": ["APILayer"],
        "1.12.6": ["TimeSeriesGenerator"],
        "1.12.7": ["DataExportService"],
        
        "1.13": ["APILayer", "DataStorage"],
        "1.13.1": ["APILayer"],
        "1.13.2": ["APILayer", "SensitivityProfileModel"],
        "1.13.3": ["APILayer"],
        "1.13.4": ["DataStorage"],
        "1.13.5": ["APILayer"],
        "1.13.6": ["APILayer"],
        "1.13.7": ["APILayer"],
        
        "1.14": ["DataExportService", "DataStorage"],
        "1.14.1": ["DataExportService"],
        "1.14.2": ["DataExportService"],
        "1.14.3": ["DataExportService"],
        "1.14.4": ["TestingFramework"]
    }
    
    return task_to_component


def initialize_master_plan():
    """Initialize the task manager with tasks from the master plan."""
    # Get the development state
    state = get_state()
    
    # Create a task manager if it doesn't exist yet
    if not hasattr(state, "task_manager"):
        state.task_manager = TaskManager()
    
    # Get metadata from the plan
    metadata = parse_master_plan()
    print("Parsed master plan:")
    for key, value in metadata.items():
        print(f"  {key}: {value}")
    
    # Extract tasks from the plan
    task_data = extract_tasks_from_plan()
    print(f"Extracted {len(task_data)} tasks from the master plan")
    
    # Get component associations
    component_associations = create_component_associations()
    
    # Create tasks and add them to the manager
    for data in task_data:
        task = Task(
            task_id=data["task_id"],
            name=data["name"],
            description=data["description"],
            task_type=TaskType(data["task_type"]),
            parent_id=data.get("parent_id")
        )
        
        # Set status if specified
        if "status" in data:
            task.update_status(TaskStatus(data["status"]))
        
        # Set estimated days if specified
        if "estimated_days" in data:
            task.set_estimated_days(data["estimated_days"])
        
        # Add component associations
        if task.task_id in component_associations:
            for component_name in component_associations[task.task_id]:
                task.add_component(component_name)
        
        # Add to manager
        state.task_manager.add_task(task)
    
    # Set the current task if specified in metadata
    if "current_task" in metadata:
        state.task_manager.set_current_task(metadata["current_task"])
    
    # Save the state
    save_state()
    
    # Print a summary
    current_task = state.task_manager.get_current_task()
    if current_task:
        print(f"Current task: {current_task.name} ({current_task.task_id})")
        print(f"Description: {current_task.description}")
        if current_task.components:
            print(f"Associated components: {', '.join(current_task.components)}")
    
    print("Next tasks:")
    for task in state.task_manager.get_next_tasks(5):
        print(f"  - {task.name} ({task.task_id})")
    
    print("EnviroSense master plan initialized successfully!")


if __name__ == "__main__":
    initialize_master_plan()
