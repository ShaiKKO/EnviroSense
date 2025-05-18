"""
EnviroSense state management - State initialization
"""
import sys
from typing import List, Dict, Any

from envirosense.state.components import Component, ComponentStatus, Tags
from envirosense.state.utils import (
    get_state, 
    save_state, 
    initialize_components, 
    create_development_checkpoint,
    start_development_session
)


def define_components() -> List[Dict[str, Any]]:
    """
    Define all components for the EnviroSense system.
    
    Returns:
        List of component definitions
    """
    components = []
    
    # Core Simulation Engine components
    components.append({
        "name": "TimeSeriesGenerator",
        "description": "Generates temporally coherent data series for all sensor types",
        "tags": [Tags.CORE, Tags.SIMULATION, "time_series"],
        "dependencies": []
    })
    
    components.append({
        "name": "EnvironmentalPhysicsEngine",
        "description": "Models dispersion and diffusion of chemicals in 3D space",
        "tags": [Tags.CORE, Tags.SIMULATION, Tags.PHYSICS],
        "dependencies": ["TimeSeriesGenerator"]
    })
    
    components.append({
        "name": "ChemicalBehaviorModels",
        "description": "Models behavior of specific VOCs and chemical compounds",
        "tags": [Tags.CORE, Tags.SIMULATION, Tags.CHEMICAL],
        "dependencies": ["EnvironmentalPhysicsEngine"]
    })
    
    components.append({
        "name": "PhysiologicalResponseCorrelator",
        "description": "Implements dose-response models for various sensitivity profiles",
        "tags": [Tags.CORE, Tags.SIMULATION, Tags.PHYSIOLOGICAL],
        "dependencies": ["ChemicalBehaviorModels"]
    })
    
    # Configuration & Control components
    components.append({
        "name": "ScenarioManager",
        "description": "Defines and stores simulation scenarios",
        "tags": [Tags.CORE, "configuration"],
        "dependencies": ["TimeSeriesGenerator", "EnvironmentalPhysicsEngine"]
    })
    
    components.append({
        "name": "ParameterController",
        "description": "Manages all simulation parameters",
        "tags": [Tags.CORE, "configuration"],
        "dependencies": ["TimeSeriesGenerator", "EnvironmentalPhysicsEngine", "ChemicalBehaviorModels", "PhysiologicalResponseCorrelator"]
    })
    
    # Data Services components
    components.append({
        "name": "DataExportService",
        "description": "Formats data for consumption by other system components",
        "tags": [Tags.DATA, "export"],
        "dependencies": ["PhysiologicalResponseCorrelator"]
    })
    
    components.append({
        "name": "APILayer",
        "description": "RESTful API for configuration and data retrieval",
        "tags": [Tags.API, Tags.DATA],
        "dependencies": ["DataExportService"]
    })
    
    components.append({
        "name": "DataStorage",
        "description": "Stores simulation results for replay and analysis",
        "tags": [Tags.DATA, "storage"],
        "dependencies": ["DataExportService"]
    })
    
    # User Interface components
    components.append({
        "name": "SimulationControlUI",
        "description": "Web-based interface for controlling simulations",
        "tags": [Tags.UI, "control"],
        "dependencies": ["ScenarioManager", "ParameterController"]
    })
    
    components.append({
        "name": "VisualizationComponents",
        "description": "Real-time visualization of environmental data",
        "tags": [Tags.UI, "visualization"],
        "dependencies": ["DataExportService", "APILayer"]
    })
    
    # Data Models
    components.append({
        "name": "EnvironmentalReadingModel",
        "description": "Data model for environmental sensor readings",
        "tags": [Tags.DATA, "model"],
        "dependencies": []
    })
    
    components.append({
        "name": "PhysiologicalReadingModel",
        "description": "Data model for physiological sensor readings",
        "tags": [Tags.DATA, "model"],
        "dependencies": []
    })
    
    components.append({
        "name": "ScenarioModel",
        "description": "Data model for simulation scenarios",
        "tags": [Tags.DATA, "model"],
        "dependencies": ["EnvironmentalReadingModel", "PhysiologicalReadingModel"]
    })
    
    components.append({
        "name": "CompoundProfileModel",
        "description": "Data model for chemical compound profiles",
        "tags": [Tags.DATA, "model", Tags.CHEMICAL],
        "dependencies": []
    })
    
    components.append({
        "name": "SensitivityProfileModel",
        "description": "Data model for user sensitivity profiles",
        "tags": [Tags.DATA, "model", Tags.PHYSIOLOGICAL],
        "dependencies": ["CompoundProfileModel"]
    })
    
    # Development Infrastructure
    components.append({
        "name": "ProjectSetup",
        "description": "Initialize project structure and development environment",
        "tags": [Tags.INFRASTRUCTURE, "setup"],
        "dependencies": []
    })
    
    components.append({
        "name": "TestingFramework",
        "description": "Framework for unit and integration testing",
        "tags": [Tags.INFRASTRUCTURE, "testing"],
        "dependencies": []
    })
    
    components.append({
        "name": "DockerSetup",
        "description": "Docker containerization for the EnviroSense system",
        "tags": [Tags.INFRASTRUCTURE, "deployment"],
        "dependencies": []
    })
    
    return components


def initialize_state():
    """Initialize the development state with EnviroSense components."""
    # Get all component definitions
    components = define_components()
    
    # Initialize the components in the state
    initialize_components(components)
    
    # Create an initial checkpoint
    create_development_checkpoint(
        name="initial_setup",
        description="Initial project setup and component definitions"
    )
    
    # Start a development session focused on project setup
    start_development_session(["ProjectSetup"])
    
    # Print a success message
    print("EnviroSense development state initialized successfully!")
    print(f"Defined {len(components)} components")
    print("Ready to begin development")


if __name__ == "__main__":
    initialize_state()
