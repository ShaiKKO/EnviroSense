"""
Script to register the ExposureTrackingSystem component in the EnviroSense system.
"""
import os
import sys

# Add project root to path to allow importing from envirosense
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

from envirosense.state.components import Component, ComponentStatus, Tags, ComponentRegistry
from envirosense.state.tasks import TaskStatus
from envirosense.state.utils import get_state, save_state


def register_exposure_system():
    """
    Register the ExposureTrackingSystem component and update related task status.
    """
    print("Registering ExposureTrackingSystem component...")
    
    # Get development state
    state = get_state()
    
    # Check if component registry exists
    if not hasattr(state, "component_registry"):
        state.component_registry = ComponentRegistry()
    
    # Create component if it doesn't exist yet
    component_name = "ExposureTrackingSystem"
    component = state.component_registry.get_component(component_name)
    
    if not component:
        component = Component(
            name=component_name,
            description="System for tracking, assessing, and managing exposure to chemicals and environmental parameters, with integration to sensitivity profiles.",
            tags=[Tags.CORE, Tags.PHYSIOLOGICAL, Tags.CHEMICAL]
        )
        
        # Add dependencies
        component.add_dependency("ChemicalBehaviorModels")
        component.add_dependency("SensitivityProfileModel")
        
        print(f"Created new component: {component_name}")
    else:
        print(f"Component already exists: {component_name}")
    
    # Update component properties
    component.update_status(ComponentStatus.IMPLEMENTED)
    
    # Add implementation files
    module_files = [
        "envirosense/core/exposure/__init__.py",
        "envirosense/core/exposure/records.py",
        "envirosense/core/exposure/assessment.py",
        "envirosense/core/exposure/storage.py",
        "envirosense/core/exposure/profile_integrated_demo.py",
        "envirosense/core/exposure/run_exposure_system.py"
    ]
    
    for file_path in module_files:
        if file_path not in component.implementations:
            component.implementations.append(file_path)
    
    # Add test files
    test_files = [
        "envirosense/core/exposure/test_exposure_tracking.py"
    ]
    
    for file_path in test_files:
        if file_path not in component.test_files:
            component.test_files.append(file_path)
    
    # Add documentation
    component.add_note(
        "Initial implementation complete. The system provides exposure tracking, "
        "assessment against standards, personalized risk calculation based on sensitivity "
        "profiles, and data storage mechanisms. Integration with ChemicalBehaviorModels and "
        "SensitivityProfileModel provides a complete risk assessment pipeline."
    )
    
    # Register component
    state.component_registry.register(component)
    
    # Update task status if task manager exists
    if hasattr(state, "task_manager"):
        task = state.task_manager.get_task("1.3.1")
        if task:
            task.update_status(TaskStatus.COMPLETED)
            print(f"Updated task 1.3.1 status to {TaskStatus.COMPLETED.value}")
        else:
            print("Task 1.3.1 not found in task manager")
    
    # Save the state
    save_state()
    print(f"Component {component_name} registered successfully!")
    print("Development state updated and saved.")


if __name__ == "__main__":
    register_exposure_system()
