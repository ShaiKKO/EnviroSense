"""
Script to register the ExposureTrackingSystem component in the EnviroSense system.
This version works directly with the dev_state.json file to avoid import issues.
"""
import os
import json
import datetime
from enum import Enum
from typing import Dict, Any, List


# Define enums to match the ones in the state system
class ComponentStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    IMPLEMENTED = "implemented"
    TESTED = "tested"
    OPTIMIZED = "optimized"
    DOCUMENTED = "documented"
    COMPLETED = "completed"


class TaskStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    VERIFIED = "verified"


class Tags:
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


def load_state() -> Dict[str, Any]:
    """Load the development state from disk."""
    state_file = os.path.join("envirosense", "dev_state.json")
    
    if not os.path.exists(state_file):
        print(f"State file not found: {state_file}")
        return {}
    
    try:
        with open(state_file, "r") as f:
            state = json.load(f)
        return state
    except Exception as e:
        print(f"Error loading state: {e}")
        return {}


def save_state(state: Dict[str, Any]) -> bool:
    """Save the development state to disk."""
    state_file = os.path.join("envirosense", "dev_state.json")
    
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        
        # Write the file
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error saving state: {e}")
        return False


def register_exposure_system():
    """
    Register the ExposureTrackingSystem component and update related task status.
    """
    print("Registering ExposureTrackingSystem component...")
    
    # Load development state
    state = load_state()
    
    # Ensure needed structures exist in state
    if "component_registry" not in state:
        state["component_registry"] = {"components": {}}
    
    # Create or update the component
    component_name = "ExposureTrackingSystem"
    registry = state["component_registry"]
    
    # Check if component exists
    if component_name not in registry["components"]:
        # Create new component
        component = {
            "name": component_name,
            "description": "System for tracking, assessing, and managing exposure to chemicals and environmental parameters, with integration to sensitivity profiles.",
            "tags": [Tags.CORE, Tags.PHYSIOLOGICAL, Tags.CHEMICAL],
            "dependencies": ["ChemicalBehaviorModels", "SensitivityProfileModel"],
            "interfaces": [],
            "implementations": [],
            "test_files": [],
            "status": ComponentStatus.IMPLEMENTED.value,
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat(),
            "notes": ""
        }
        registry["components"][component_name] = component
        print(f"Created new component: {component_name}")
    else:
        # Update existing component
        component = registry["components"][component_name]
        component["status"] = ComponentStatus.IMPLEMENTED.value
        component["updated_at"] = datetime.datetime.now().isoformat()
        print(f"Updated existing component: {component_name}")
    
    # Add implementation files
    module_files = [
        "envirosense/core/exposure/__init__.py",
        "envirosense/core/exposure/records.py",
        "envirosense/core/exposure/assessment.py",
        "envirosense/core/exposure/storage.py",
        "envirosense/core/exposure/profile_integrated_demo.py",
        "envirosense/core/exposure/run_exposure_system.py"
    ]
    
    if "implementations" not in component:
        component["implementations"] = []
    
    for file_path in module_files:
        if file_path not in component["implementations"]:
            component["implementations"].append(file_path)
    
    # Add test files
    test_files = [
        "envirosense/core/exposure/test_exposure_tracking.py"
    ]
    
    if "test_files" not in component:
        component["test_files"] = []
    
    for file_path in test_files:
        if file_path not in component["test_files"]:
            component["test_files"].append(file_path)
    
    # Add documentation
    note = f"\n[{datetime.datetime.now().isoformat()}] Initial implementation complete. " \
           f"The system provides exposure tracking, assessment against standards, " \
           f"personalized risk calculation based on sensitivity profiles, and data " \
           f"storage mechanisms. Integration with ChemicalBehaviorModels and " \
           f"SensitivityProfileModel provides a complete risk assessment pipeline."
    
    component["notes"] += note
    
    # Update task status if task manager exists
    if "task_manager" in state and "tasks" in state["task_manager"]:
        tasks = state["task_manager"]["tasks"]
        
        if "1.3.1" in tasks:
            tasks["1.3.1"]["status"] = TaskStatus.COMPLETED.value
            print("Updated task 1.3.1 status to COMPLETED")
        else:
            print("Task 1.3.1 not found in task manager")
    
    # Save the state
    if save_state(state):
        print(f"Component {component_name} registered successfully!")
        print("Development state updated and saved.")
    else:
        print("Failed to save development state.")


if __name__ == "__main__":
    register_exposure_system()
