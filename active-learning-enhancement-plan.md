# Plan for Task ML-3: Enhance ActiveLearningManager (Sensor-Adaptive & Specific, Research-Aligned)

## 1. Introduction & Task Definition

This document outlines the plan for **Task ML-3: Enhance `ActiveLearningManager`** as specified in the [`digital-twin-sensor-array-development-plan.md`](digital-twin-sensor-array-development-plan.md). Active learning is crucial for EnviroSense to **reduce costs and time to build new machine learning solutions by querying the next data for your pipeline in an intelligent manner**. It plays a vital role in addressing challenges like model drift and the difficulty of capturing rare, critical scenarios in real-world data. The primary goal is to implement and refine the `ActiveLearningManager` to intelligently guide the data generation process, identify model weaknesses, and suggest targeted scenarios or modifications to improve ML model performance.

Key enhancements include making the `ActiveLearningManager` **adaptive to specific sensor types within the Grid Guardian device, computational workload, and data return urgency**. This involves dynamic selection of active learning strategies, tailored scenario generation, and intelligent data management, informed by the actual sensor suite and aligned with established research and best practices.

This involves:
*   Implementing `identify_weak_spots`, `generate_targeted_samples`, and `suggest_scenario_modifications` methods within the `ActiveLearningManager` with sensor-adaptive capabilities.
*   Defining clear interfaces for model performance feedback (`ModelInterface`) and scenario management (`ScenarioRepository`), extended for sensor-specific context based on known Grid Guardian sensors.
*   Ensuring the `ActiveLearningManager` can leverage data produced by the `MLDataGenerator` (compliant with `MLDataSample.avsc`), including `sensor_id` corresponding to actual hardware.
*   Incorporating advanced active learning strategies (Strategy Pattern for prioritization) and MLOps best practices for heterogeneous sensor systems.

## 1.1 Grid Guardian Sensor Suite
Based on [`docs/Manufacturing/MainBoard/grid-guardian-schematic-guide.md`](docs/Manufacturing/MainBoard/grid-guardian-schematic-guide.md) and [`docs/Manufacturing/MainBoard/grid-guardian-bom-complete.md`](docs/Manufacturing/MainBoard/grid-guardian-bom-complete.md), the relevant Grid Guardian sensors are:
*   **VOC Sensor Array**: `TFSGS-MULTI2-ENV (U19)` (8-channel, Custom)
*   **Particulate Matter**: `Sensirion SPS30 (U20)` (PM1.0, 2.5, 10)
*   **Temperature/Humidity**: 2x `Sensirion SHT85 (U21, U22)` (±0.1°C, ±1.5%RH)
*   **Barometric Pressure**: `Bosch BMP388 (U23)` (300-1200 hPa)
*   **Ultrasonic Anemometer**: `FT Technologies FT205 (U24)` (0-75 m/s, Custom Wind Sensor)
*   **Lightning Detector**: `AMS AS3935 (U25)` (40km range)
*   **Thermal Camera**: `FLIR Lepton 3.5 (U26)` (160x120 VOx, Custom)
*   **Acoustic Sensors**: 2x `Knowles SPU0410HR5H (U27, U28)` (20Hz-80kHz)
*   **EMF Sensor**: `TF-EMF-PWR1 (U29)` (AC field detection, Custom)
*   **Accelerometer/Gyroscope (IMU)**: `Bosch BMI270 (U30)` (±16g, ±2000°/s)

These specific sensor identities will inform the design of adaptive strategies.

## 2. Core Components and Interfaces (Sensor-Adaptive & Specific)

### 2.1. `ActiveLearningManager` Overview
The `ActiveLearningManager` is responsible for:
*   Analyzing model performance feedback, potentially specific to sensor types or instances, to identify areas of weakness.
*   Employing dynamic prioritization strategies based on sensor characteristics.
*   Suggesting modifications to existing scenarios or the creation of new scenarios, tailored to target these sensor-specific weaknesses.
*   Orchestrating the generation of new, targeted training samples using the `MLDataGenerator` and `ScenarioRepository`.

### 2.2. `ModelInterface` Abstract Base Class (Sensor-Adaptive & Specific)

**Purpose**: To abstract interaction with ML model(s), retrieving sensor-specific performance data, predictions, and uncertainty scores, aware of the Grid Guardian sensor suite. This well-defined interface abstracts the complexities of interacting with the actual ML model, making the `ActiveLearningManager` model-agnostic and enhancing reusability across various ML models within EnviroSense.

**Conceptual Signature (Pythonic representation for planning)**:
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Union, Optional

# Represents a list of MLDataSample-like dictionaries
DatasetType = List[Dict[str, Any]]
FilePathType = str

class ModelInterface(ABC):
    @abstractmethod
    def get_model_performance_feedback(
        self,
        evaluation_dataset: Union[DatasetType, FilePathType],
        model_version_tag: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluates the model and returns structured feedback, detailed below.
        The implementation will be aware of specific sensor data paths (e.g., for U20_SPS30).
        """
        # Concrete implementation will handle model interaction.
        pass
```

**Detailed Return Structure for `get_model_performance_feedback` (Sensor-Adaptive & Specific)**:
```json
{
    "model_version_evaluated": "string_model_version_identifier",
    "dataset_identifier": "string_dataset_identifier",
    "overall_metrics": {
        "accuracy": 0.85,
        "macro_f1_score": 0.82,
        "weighted_f1_score": 0.83
    },
    "per_class_metrics": {
        "class_A": {"recall": 0.7, "precision": 0.6, "f1_score": 0.65, "support": 100 },
        "class_B": {"recall": 0.9, "precision": 0.88, "f1_score": 0.89, "support": 150 }
    },
    "sensor_specific_metrics": {
        "U20_SPS30": {
            "overall_accuracy_for_SPS30_data": 0.88,
            "per_class_metrics_for_SPS30_data": {
                 "class_A": {"recall": 0.78, "precision": 0.70, "f1_score": 0.74, "support": 40 }
            }
        },
        "U26_Lepton35": {
            "overall_accuracy_for_Lepton35_data": 0.92,
            "per_class_metrics_for_Lepton35_data": {
                 "class_B": {"recall": 0.95, "precision": 0.90, "f1_score": 0.92, "support": 60 }
            }
        }
    },
    "uncertain_samples": [
        {
            "raw_sample_id": "uuid_sample_1",
            "sensor_id": "U26_Lepton35",
            "uncertainty_score": 0.45,
            "epistemic_uncertainty_score": 0.3,
            "aleatoric_uncertainty_score": 0.15,
            "disagreement_score": 0.5,
            "predicted_label_distribution": {"class_A": 0.4, "class_B": 0.35, "class_C": 0.25 },
            "sample_features_summary": {
                "method": "SHAP",
                "top_n_features": [
                    {"feature_path": "sensor_readings_map.U26_Lepton35.thermal_matrix[10][15]", "importance_score": 0.6, "raw_value": 75.5},
                    {"feature_path": "sensor_readings_map.U20_SPS30.pm2_5_ug_m3", "importance_score": 0.2, "raw_value": 150.2}
                ],
                "target_class_for_explanation": "class_A"
            },
            "original_scenario_id": "scenario_abc",
            "scenario_timestep_seconds": 60.5
        }
    ],
    "misclassified_samples": [
        {
            "raw_sample_id": "uuid_sample_2",
            "sensor_id": "U20_SPS30",
            "true_label": "class_B",
            "predicted_label": "class_A",
            "confidence_of_prediction": 0.65,
            "sample_features_summary": {
                "method": "LIME",
                "top_n_features": [
                    {"feature_path": "sensor_readings_map.U20_SPS30.pm10_0_ug_m3", "importance_score": 0.7, "raw_value": 250.0}
                ],
                "target_class_for_explanation": "class_A"
            },
            "original_scenario_id": "scenario_def",
            "scenario_timestep_seconds": 120.0
        }
    ]
}
```
*   **`sample_features_summary` (Approach 4 - Feature Importance)**: This approach provides interpretable insights into model weaknesses by identifying "where accuracy is lowest" in the feature space and understanding "feature interactions". This directly supports the "inverse design" principle by pinpointing which features are most problematic.
*   **Uncertainty Scores**:
    *   `epistemic_uncertainty_score`: Quantifies the model's lack of knowledge that can be reduced by acquiring more data, making it highly informative for active learning.
    *   `aleatoric_uncertainty_score`: Represents inherent, irreducible noise in the data. Prioritizing samples with high epistemic and relatively low aleatoric uncertainty maximizes learning gain.
    *   `disagreement_score`: (For Query-by-Committee) Effective because it identifies samples where an ensemble of models struggles to converge on a consistent prediction, signaling valuable information for improvement, especially in class-unbalanced data.

### 2.3. `ScenarioRepository` Interface (Sensor-Adaptive & Specific)
**Purpose**: To manage scenario definitions, aware of specific Grid Guardian sensor types. The inclusion of `create_scenario_variation` and `craft_scenario_from_features` moves beyond traditional "pool-based sampling" towards "membership query synthesis" or "data synthesis for purpose," allowing the system to generate new, highly targeted data crucial for rare events.

**Conceptual Key Methods Extended**:
*   `get_scenario_by_id(scenario_id: str) -> Optional[BaseScenario]`
*   `get_scenarios_by_category(category: str, sensor_type: Optional[str] = None, num_to_get: int = 5) -> List[BaseScenario]`
*   `get_scenarios_by_class_label(class_label: str, sensor_type: Optional[str] = None, num_to_get: int = 5) -> List[BaseScenario]`
*   `create_scenario_variation(base_scenario: BaseScenario, new_id_suffix: str, param_modifications: Dict[str, Any], sensor_context: Optional[Dict[str, Any]] = None) -> Optional[BaseScenario]`
*   `craft_scenario_from_features(features_summary: Dict[str, Any], base_id: str, target_class: Optional[str] = None, sensor_type: Optional[str] = None) -> Optional[BaseScenario]`
*   `get_default_exploration_scenario(scenario_id: str, sensor_type: Optional[str] = None) -> Optional[BaseScenario]`
*   `save_scenario_definition(scenario_def: Dict[str, Any]) -> str`
*   `update_scenario_definition(scenario_def_id: str, updates: Dict[str, Any]) -> bool`

## 3. Enhancements to `ActiveLearningManager` Methods (Sensor-Adaptive & Specific)

### 3.1. `identify_weak_spots()` - Dynamic Prioritization with Strategy Pattern

*   **Input**: `model_performance_data` (sensor-adaptive structure from `ModelInterface`).
*   **Strategy Pattern Rationale**: The Strategy Pattern is ideal as it allows us to "define a family of algorithms, put each of them into a separate class, and make their objects interchangeable," directly supporting adaptation to different sensor characteristics and computational trade-offs.
*   **Strategy Pattern Implementation**:
    *   `ActiveLearningManager` dynamically selects a `PrioritizationStrategy` based on `sensor_id` or its characteristics.
    *   **Conceptual `PrioritizationStrategy` Interface**:
        ```python
        class PrioritizationStrategy(ABC):
            @abstractmethod
            def calculate_priority(self, sample_info: Dict[str, Any], class_metrics: Optional[Dict[str, Any]]) -> float:
                # Calculates priority based on the strategy's logic
                pass

            @abstractmethod
            def identify_weaknesses_from_sample(self, sample_info: Dict[str, Any]) -> List[Dict[str, Any]]:
                # Generates weakness dictionaries from a single sample's info
                pass

            @abstractmethod
            def identify_weaknesses_from_class_metrics(self, class_name: str, metrics: Dict[str, Any], sensor_id: Optional[str]) -> List[Dict[str, Any]]:
                # Generates weakness dictionaries from aggregated class metrics
                pass
        ```
    *   **Concrete Prioritization Strategies (Examples mapped to Grid Guardian sensors)**:
        1.  `RealTimeSensorPrioritizationStrategy`: For `AS3935` (Lightning), `BMI270` (IMU sudden events), `SPU0410HR5H` (Acoustic immediate alerts). Aligns with **stream-based active learning**. Prefers simpler, computationally less intensive strategies like Uncertainty Sampling (least confidence, smallest margin, entropy) for low latency.
        2.  `HighFidelitySensorPrioritizationStrategy`: For `FLIR Lepton 3.5` (Thermal Camera), `TFSGS-MULTI2-ENV` (VOC array), `SPS30` (PM trends), `TF-EMF-PWR1` (EMF). Aligns with **pool-based active learning**, suitable for low-frequency, high-value data where more complex calculations (e.g., QBC, Expected Error Reduction) are acceptable.
        3.  `HeterogeneousSensorPrioritizationStrategy`: Manages the mix, potentially using concepts from **Partitioned Active Learning** or **Adaptive Continual Learning (AdaptCL)** to handle varying data complexity, size, and similarity across different sensor types, balancing informativeness and representativeness.
*   **Prioritization Logic**: Chosen strategy calculates `priority` using configurable, weighted combinations of factors, aware of the specific sensor's typical data patterns and failure modes.
*   **Output Structure (Refined Weakness Dictionary - includes specific `sensor_id`)**:
    ```json
    {
        "weakness_id": "unique_weakness_identifier",
        "type": "high_uncertainty_sample",
        "priority": 0.85,
        "sensor_id": "U26_Lepton35",
        "details": {
            "uncertainty_score": 0.45,
            "epistemic_uncertainty_score": 0.3,
            "aleatoric_uncertainty_score": 0.15,
            "disagreement_score": 0.5,
            "sample_features_summary": {
                "method": "SHAP",
                "top_n_features": [{"feature_path": "sensor_readings_map.U26_Lepton35.thermal_matrix[10][15]", "importance_score": 0.6, "raw_value": 75.5}]
            },
            "original_scenario_id": "scenario_abc",
            "scenario_timestep_seconds": 60.5,
            "raw_sample_id": "uuid_sample_1",
            "class_name": "class_A",
            "current_recall": 0.6,
            "predicted_label": "class_C",
            "true_label": "class_A"
        }
    }
    ```

### 3.2. `generate_targeted_samples()` - Sensor-Specific Scenario Crafting
*   **Input**: List of sensor-adaptive weak spot dictionaries.
*   **Logic**:
    *   Leverage specific `sensor_id` (e.g., "U19_TFSGS", "U24_FT205") and `sample_features_summary` to request highly tailored scenario variations or new scenarios from `ScenarioRepository`.
    *   **Inverse Design Principle**: This is fundamentally an "inverse problem" where we work backward from a desired outcome (problematic features) to determine optimal input parameters. Inverse problems are often "ill-posed" (multiple solutions). ML models can act as "efficient simulators" or "surrogate models" to infer parameters from observed features. This process is analogous to automated root cause analysis, where `sample_features_summary` acts as "symptoms" and `specific_params_json` modifications are "root causes". Initially heuristic/rule-based.
    *   **Builder Pattern Rationale**: The Builder Pattern is ideal for constructing complex `ScenarioDefinition` objects with many optional parameters, as it "separates the construction of a complex object from its representation" and ensures "consistency and validity" by requiring all necessary properties to be set before finalization. This will be used by `ScenarioRepository` or an internal factory.
    *   Pass tailored `BaseScenario` objects to `MLDataGenerator.generate_training_dataset()`.
*   **Synthetic Data Generation**: Crucial for training and testing, especially for rare/dangerous scenarios. Techniques like computer graphics modeling/simulation (controlled by `ScenarioDefinition.specific_params_json`) and generative AI models (GANs, VAEs - future direction) are key.

### 3.3. `suggest_scenario_modifications()` - Sensor-Specific Suggestions
*   **Input**: List of sensor-adaptive weak spot dictionaries.
*   **Output Structure**: The previously defined detailed structure for suggestions, with modifications and new scenario bases explicitly considering the specific `sensor_id` (e.g., "U23_BMP388") and its data characteristics.

## 4. Advanced Concepts and Considerations (Sensor-Adaptive & Specific)

### 4.1. Intelligent Scenario Generation (Sensor-Adaptive & Specific)
*   **Inverse Design**: Focus on mapping features from specific sensors (e.g., `SHT85` humidity readings) to relevant scenario parameters (e.g., simulated weather conditions, HVAC controls).
*   **Builder Pattern**: Used by `ScenarioRepository` for constructing `ScenarioDefinition` objects tailored for specific sensor behaviors (e.g., generating scenarios to test the `AS3935` lightning detector under various atmospheric conditions).

### 4.2. MLOps and Data Management (Sensor-Adaptive & Specific)
*   **Schema Versioning**: Schema evolution is an "inevitable aspect of data engineering". Avro schemas are designed to support schema evolution (backward/forward compatibility). The concept of "data contracts" will be used to formalize agreements on data structure and evolution rules.
*   **Data Versioning (DVC)**: DVC tracks changes in data and pipelines by creating lightweight metadata files (`.dvc` files) that Git versions, pointing to the actual data stored externally. `dvc.yaml` defines multi-stage pipelines for reproducibility. Track `ScenarioDefinition` instances and `MLDataSample` outputs, linking them to specific Grid Guardian `sensor_id`s.
*   **Experiment Tracking (MLflow)**: MLflow logs parameters, metrics, and artifacts (including generated scenarios and data) for experiment tracking. This combined DVC/MLflow approach ensures a complete lineage.
*   **Data Lineage**: Automated data lineage tracking is essential for traceability, regulatory compliance, and operational efficiency, especially with heterogeneous sensor data.

### 4.3. Avro Schema Evolution
Adherence to Avro best practices is key.

## 5. Testing Strategy (Sensor-Adaptive & Specific)
*   **General ML Testing Best Practices**: Incorporate various ML testing types: Syntax Testing, Data Creation Testing (Unit, Property-Based, Component), Model Creation Testing, End-to-End (E2E) Testing, and Artifact Testing.
*   **Unit Tests**:
    *   Validate dynamic selection of `PrioritizationStrategy` based on known Grid Guardian sensor IDs.
    *   Test `identify_weak_spots` with `model_performance_data` containing specific sensor IDs (e.g., "U30_BMI270") to ensure correct strategy application and output.
*   **Integration Tests**:
    *   Verify `generate_targeted_samples` produces valid Avro datasets for scenarios focused on specific sensors (e.g., a thermal event for `U26_Lepton35`).
*   **Continuous Testing (CT) and Automated Retraining**: MLOps extends CI/CD to include CT of data and models. `ActiveLearningManager` outputs (weak spots, new data) will serve as triggers for automated retraining based on model performance degradation or data drift.
*   **Evaluating Synthetic Data Quality**: Assess on three key dimensions:
    1.  **Fidelity**: How well it mimics statistical properties of real data (statistical similarity, distributions).
    2.  **Utility**: How effectively it performs on downstream ML tasks (e.g., "Train on Synthetic Test on Real" (TSTR) vs. "Train on Real Test on Real" (TRTR) comparisons).
    3.  **Privacy**: How well it conceals sensitive information (if applicable).
*   **Evaluating Scenario Generation Effectiveness**: Beyond standard model metrics, also consider:
    1.  **Criticalness/Informativeness**: Does the scenario effectively target weak spots and explore critical edge cases?
    2.  **Diversity/Uniqueness**: Are new scenarios sufficiently diverse and non-redundant?

## 6. Mermaid Diagram: Active Learning Loop (Conceptual)
```mermaid
graph TD
    A[ML Model Training] --> B{Evaluate Model};
    B -- Performance Metrics & Uncertain Samples --> C[ActiveLearningManager: identify_weak_spots (Sensor-Adaptive Strategies)];
    C -- Identified Weak Spots (incl. sensor_id) --> D[ActiveLearningManager: suggest_scenario_modifications (Sensor-Specific Suggestions)];
    D -- Scenario Suggestions --> E{Human Review / Automated Scenario Update};
    E -- Approved Scenario Changes --> F[Scenario Repository: Update/Create Scenarios (Sensor-Aware)];
    C -- Identified Weak Spots --> G[ActiveLearningManager: generate_targeted_samples (Sensor-Specific Crafting)];
    G -- Scenario Requests --> F;
    F -- Scenarios (BaseScenario objects) --> H[MLDataGenerator: generate_training_dataset];
    H -- New Targeted Data (Avro MLDataSample incl. sensor_id) --> A;

    subgraph ModelInteraction
        direction LR
        MI[ModelInterface (Sensor-Adaptive Feedback)]
        MI -- Gets Performance Data --> C
        B -- Provides Raw Data/Metrics to --> MI
    end

    subgraph ScenarioManagement
        direction LR
        SR[Scenario Repository (Sensor-Aware Methods)]
        SR -- Provides/Stores Scenarios --> G
        F -- Updates/Creates in --> SR
    end

    subgraph DataGeneration
        direction LR
        MDG[MLDataGenerator]
        H -- Uses --> MDG
    end
```

This enhanced plan, incorporating direct knowledge of the Grid Guardian's sensor suite and research-aligned best practices, makes the `ActiveLearningManager` a significantly more targeted, robust, and powerful component.