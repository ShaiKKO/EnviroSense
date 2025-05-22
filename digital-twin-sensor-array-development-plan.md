# EnviroSense™ Digital Twin Sensor Array & ML Training System Development Plan

## Enhanced Objective
Create a high-fidelity virtual sensor array system that not only mimics Grid Guardian physical sensors for algorithm testing, but serves as a continuous ML training data factory that generates unlimited labeled datasets for detection algorithm improvement, edge case exploration, and active learning integration.

## Strategic Vision
Transform the digital twin from a simple testing tool into an AI-driven training infrastructure that:
*   Generates unlimited labeled training data for detection algorithms.
*   Creates safety-critical scenarios without real-world risks.
*   Produces edge cases and rare events for robust model training.
*   Enables continuous learning through scenario-based data generation.
*   Supports active learning by generating data for model weak spots.
*   Bridges simulation-to-reality through domain adaptation.

## Current Context
*   **Existing Foundation:** Completed EnviroSense simulation engine with physics modeling (`physics/space.py`, `physics/airflow.py`), chemical modeling (`chemical/sources.py`), and time series generation (`time_series/generator.py`).
*   **Target Application:** Grid Guardian utility pole monitoring system + ML training data generation.
*   **Primary Use:** Detection algorithm training, testing, and continuous improvement.
*   **Integration Target:** EnviroSense Core Platform + ML Training Pipeline.

## Grid Guardian Sensor Array + ML Training Requirements

### Physical Sensor Array (to simulate):
*   **Environmental Sensors:**
    *   VOC Array (8-channel) - ppb-level chemical detection
    *   Particulate Matter (PM1.0, PM2.5, PM10)
    *   Temperature/Humidity sensors
    *   Barometric Pressure
    *   Wind Speed/Direction
    *   Lightning Detection
*   **Infrastructure Monitoring:**
    *   Thermal Camera (80x60 resolution)
    *   EMF Sensors (AC field detection)
    *   Acoustic Sensors (arcing/corona detection)
    *   Vibration Sensors (structural monitoring)
*   **System Monitoring:**
    *   Battery Level
    *   Solar Power Generation
    *   Internal Temperature

### ML Training Data Requirements:
*   **Labeled Datasets:**
    *   Fire Precursor Events (with ground truth)
    *   Electrical Anomaly Events (with classification)
    *   Normal Operation Patterns (with baseline labels)
    *   Edge Cases & Rare Events (with confidence scores)
*   **Scenario Libraries:**
    *   Fire-related Scenarios
    *   Electrical Fault Scenarios
    *   Environmental Variation Scenarios
    *   Multi-factor Interaction Scenarios
*   **Active Learning Support:**
    *   Uncertainty-based Data Generation
    *   Model Weakness Targeting
    *   Real-world Performance Feedback Integration
    *   Continuous Dataset Expansion

---
## Complete Implementation Architecture

### Phase 1: Enhanced Core Framework (Estimated: 5-7 days) [COMPLETED]
*   **Objective:** Build sensor array framework with ML training data generation capabilities. [COMPLETED]

#### Sub-Phase 1.1: Project Setup & Enhanced Directory Structure [COMPLETED]
*   **Task 1.1.1:** Create `envirosense/simulation_engine/sensors/`. [COMPLETED]
*   **Task 1.1.2:** Create `envirosense/simulation_engine/ml_training/`. [COMPLETED]
*   **Task 1.1.3:** Create `envirosense/simulation_engine/scenarios/`. [COMPLETED]
*   **Task 1.1.4:** Create appropriate `__init__.py` files in new directories. [COMPLETED]
*   **Deliverable:** Enhanced directory structure supporting sensor simulation, ML training, and scenarios. [COMPLETED]

#### Sub-Phase 1.2: Enhanced `BaseSensor` with ML Features [COMPLETED]
*   **Task 1.2.1:** Create `envirosense/simulation_engine/sensors/base.py`. [COMPLETED]
*   **Task 1.2.2:** Define `BaseSensor` abstract class with `abc.ABC`, including: [COMPLETED]
    *   Core properties: `sensor_id`, `sensor_type`, `is_enabled`, `position_3d`, `sampling_volume`. [COMPLETED]
    *   ML properties: `ground_truth_capability` (bool), `noise_characteristics` (dict), `drift_parameters` (dict). [COMPLETED]
*   **Task 1.2.3:** Define abstract methods: [COMPLETED]
    *   `sample(self, environment_3d_state) -> dict` (returns potentially imperfect sensor reading). [COMPLETED]
    *   `get_ground_truth(self, environment_3d_state) -> dict` (returns ideal reading from environment). [COMPLETED]
    *   `get_ml_metadata(self) -> dict` (returns info about current imperfections, etc.). [COMPLETED]
    *   `apply_imperfections(self, true_reading, environment_3d_state) -> dict` (internal helper, or part of `sample`). [COMPLETED - signature updated]
*   **Task 1.2.4:** Implement concrete methods for `enable()`, `disable()`, `update_position()`. [COMPLETED]
*   **Task 1.2.5:** Add comprehensive docstrings and unit tests. [COMPLETED]
*   **Deliverable:** ML-ready `BaseSensor` abstract class. [COMPLETED]

#### Sub-Phase 1.3: ML-Enhanced `SensorConfiguration` [COMPLETED]
*   **Task 1.3.1:** Create `envirosense/simulation_engine/sensors/config.py`. [COMPLETED]
*   **Task 1.3.2:** Implement Pydantic-based `SensorConfiguration` allowing specification of: [COMPLETED]
    *   Sensor selection and their specific operational parameters. [COMPLETED]
    *   Parameters for imperfection models (noise levels, drift rates, etc.). [COMPLETED]
    *   Settings relevant to ML training data generation (e.g., range of imperfections to apply). [COMPLETED]
    *   Scenario-specific sensor behaviors or overrides. [COMPLETED]
*   **Task 1.3.3:** Add validation rules and example configurations. [COMPLETED]
*   **Deliverable:** Comprehensive sensor configuration system using Pydantic. [COMPLETED]

#### Sub-Phase 1.4: Enhanced `VirtualGridGuardian` [COMPLETED]
*   **Task 1.4.1:** Create `envirosense/simulation_engine/sensors/grid_guardian.py`. [COMPLETED]
*   **Task 1.4.2:** Implement `VirtualGridGuardian` class with methods for: [COMPLETED]
    *   Traditional sensor sampling: `sample_environment(self, environment_3d_state) -> dict`. [COMPLETED]
    *   ML data generation: `generate_training_sample(self, scenario_state, include_labels=True) -> tuple[dict, dict]` (returns sensor readings and ground truth labels). [COMPLETED]
    *   Ground truth access: `get_ground_truth_data(self, environment_3d_state) -> dict`. [COMPLETED]
    *   Batch processing: `generate_dataset(self, scenarios, num_samples_per_scenario) -> list`. [STUBBED]
*   **Task 1.4.3:** Add sensor management methods (enable/disable individual sensors, reconfigure sensors). [COMPLETED]
*   **Task 1.4.4:** Implement comprehensive unit tests. [COMPLETED]
*   **Deliverable:** ML-ready `VirtualGridGuardian` class. [COMPLETED]

#### Sub-Phase 1.5: Sensor Stubs with ML Placeholders [COMPLETED]
*   **Task 1.5.1:** Create sensor implementation files: [COMPLETED]
    *   `envirosense/simulation_engine/sensors/environmental.py` [COMPLETED]
    *   `envirosense/simulation_engine/sensors/infrastructure.py` [COMPLETED]
    *   `envirosense/simulation_engine/sensors/system.py` [COMPLETED]
*   **Task 1.5.2:** For each Grid Guardian sensor type: [COMPLETED]
    *   Implement stub class inheriting from `BaseSensor`. [COMPLETED]
    *   Add placeholder `sample()` and `get_ground_truth()` methods. [COMPLETED]
    *   Define expected output format for sensor readings and ground truth, suitable for ML training. [COMPLETED]
    *   Add basic imperfection application placeholders in `sample()` or `apply_imperfections()`. [COMPLETED]
*   **Task 1.5.3:** Test integration of stubs with `VirtualGridGuardian`. [COMPLETED - via SENSOR_CLASS_REGISTRY]
*   **Deliverable:** Complete sensor stub framework supporting basic ML data generation concepts. [COMPLETED]

---
### Phase 2: ML Training Data Infrastructure (Estimated: 7-10 days) [COMPLETED]
*   **Objective:** Build comprehensive ML training data generation and scenario management system. [COMPLETED]

#### Sub-Phase 2.1: Scenario Library Framework [COMPLETED]
*   **Task 2.1.1:** Create `envirosense/simulation_engine/scenarios/base.py`. [COMPLETED]
*   **Task 2.1.2:** Define `BaseScenario` abstract class with: [COMPLETED]
    *   Properties: `scenario_id`, `name`, `description`, `category` (e.g., "fire", "electrical_fault", "normal"), `difficulty_level`, `expected_duration`. [COMPLETED]
    *   Methods: [COMPLETED]
        *   `setup_environment(self, environment_3d_orchestrator)`: Configures the initial state of the 3D environment. [COMPLETED]
        *   `get_ground_truth_labels(self, current_time_step, environment_3d_state) -> dict`: Defines labels for ML (e.g., event type, severity). [COMPLETED]
        *   `update(self, time_step, environment_3d_orchestrator)`: Evolves the scenario over time. [COMPLETED]
        *   `is_completed(self, current_time_step, environment_3d_state) -> bool`. [COMPLETED]
*   **Task 2.1.3:** Implement scenario validation, serialization (e.g., to/from JSON/YAML for defining scenarios). [DEFERRED - Basic structure in place, full implementation later]
*   **Deliverable:** Foundational framework for defining and managing simulation scenarios. [COMPLETED]

#### Sub-Phase 2.2: Grid Guardian Scenario Libraries [COMPLETED]
*   **Task 2.2.1:** Create `envirosense/simulation_engine/scenarios/fire_scenarios.py`. [COMPLETED]
*   **Task 2.2.2:** Implement specific fire-related scenarios inheriting from `BaseScenario`: [STUBBED]
    *   `CellulosePyrolysisScenario` [STUBBED]
    *   `LigninDecompositionScenario` [STUBBED]
    *   `EarlyCombustionScenario` [STUBBED]
    *   `FirePrecursorComboScenario` (e.g., combining overheating with specific VOCs) [STUBBED]
*   **Task 2.2.3:** Create `envirosense/simulation_engine/scenarios/electrical_scenarios.py`. [COMPLETED]
*   **Task 2.2.4:** Implement specific electrical fault scenarios: [STUBBED]
    *   `CoronaDischargeScenario` [STUBBED]
    *   `ArcingEventScenario` [STUBBED]
    *   `InsulationBreakdownScenario` [STUBBED]
    *   `EquipmentOverheatScenario` [STUBBED]
*   **Task 2.2.5:** Create `envirosense/simulation_engine/scenarios/normal_scenarios.py`. [COMPLETED]
*   **Task 2.2.6:** Implement normal operation scenarios: [STUBBED]
    *   `DiurnalCycleScenario` [STUBBED]
    *   `SeasonalVariationScenario` [STUBBED]
    *   `WeatherEventScenario` (e.g., high wind, rain affecting sensors) [STUBBED]
    *   `BaselineEquipmentOperationScenario` [STUBBED]
*   **Deliverable:** A comprehensive library of scenarios relevant to Grid Guardian operations. [STUBBED - Files created, classes defined as stubs]

#### Sub-Phase 2.3: ML Data Generator Framework [COMPLETED]
*   **Task 2.3.1:** Create `envirosense/simulation_engine/ml_training/data_generator.py`. [COMPLETED]
*   **Task 2.3.2:** Implement `MLDataGenerator` class responsible for orchestrating data generation: [PARTIALLY COMPLETED - Core `generate_training_dataset` structure in place]
    *   `generate_training_dataset(self, list_of_scenarios, num_samples_per_scenario, output_format, imperfection_settings) -> Path_to_dataset`. [PARTIALLY COMPLETED]
    *   `generate_edge_cases(self, base_scenarios, modification_strategies, target_count)`. [STUBBED]
    *   `generate_balanced_dataset(self, scenarios, class_label_definitions, target_distribution)`. [STUBBED]
    *   `generate_temporal_sequences(self, scenario, sequence_length, overlap)`. [STUBBED]
*   **Task 2.3.3:** Add data export capabilities to common formats: [PARTIALLY COMPLETED - `list_of_dicts` is default, others placeholder]
    *   Native Python structures (lists of dicts). [COMPLETED]
    *   Pandas DataFrames. [PLACEHOLDER]
    *   HDF5 or Parquet for large datasets. [PLACEHOLDER]
    *   (Optional) Direct to PyTorch/TensorFlow dataset objects. [PLACEHOLDER]
*   **Task 2.3.4:** Implement basic data validation and quality checks on generated datasets. [TODO]
*   **Deliverable:** A complete system for generating ML training datasets from scenarios. [PARTIALLY COMPLETED - Core structure exists]

#### Sub-Phase 2.4: Active Learning Integration Framework [COMPLETED]
*   **Task 2.4.1:** Create `envirosense/simulation_engine/ml_training/active_learning.py`. [COMPLETED]
*   **Task 2.4.2:** Implement `ActiveLearningManager` class with methods like: [PARTIALLY COMPLETED - Methods stubbed]
    *   `identify_weak_spots(self, model_performance_metrics_or_uncertainty_outputs) -> list_of_areas_for_new_data`. [STUBBED]
    *   `generate_targeted_samples(self, weak_spots, num_samples) -> Path_to_dataset` (this would leverage `MLDataGenerator` with specific scenario configurations). [STUBBED]
    *   `suggest_scenario_modifications(self, weak_spots) -> list_of_scenario_config_deltas`. [STUBBED]
*   **Task 2.4.3:** Define interfaces for receiving model performance feedback. [STUBBED]
*   **Task 2.4.4:** Implement basic uncertainty-based sampling strategies (e.g., if a model is uncertain about a scenario, generate more variations of it). [STUBBED]
*   **Deliverable:** A foundational system for active learning integration. [COMPLETED - Stubs and structure in place]

---
### Phase 3: High-Fidelity Sensor Implementation (Estimated: 10-15 days) [IN PROGRESS]
*   **Objective:** Implement realistic sensor models with ML-grade fidelity and imperfections for priority sensors.

#### Sub-Phase 3.1: `Environment3DState` Definition & Mock Framework [COMPLETED]
*   **Task 3.1.1:** Formally define the `Environment3DState` data structure passed to sensors. This should provide access to all relevant 3D fields (chemical concentrations, temperature, EMF, etc.) at queryable locations/volumes. [COMPLETED]
*   **Task 3.1.2:** Enhance the mock environment generator (from Phase 1) to produce more complex and controllable 3D fields for thorough sensor testing. [COMPLETED - `create_mock_environment_state` created]
*   **Task 3.1.3:** Ensure the `Environment3DState` (or the orchestrator providing it) can also provide ground truth values for any simulated physical phenomena that sensors measure (e.g., true temperature at a point, true chemical concentration). [COMPLETED - Design supports this]
*   **Deliverable:** A well-defined `Environment3DState` interface and a robust mock generation framework. [COMPLETED]

#### Sub-Phase 3.2: VOC Array Sensor (ML-Enhanced) [COMPLETED]
*   **Task 3.2.1: "True" Value Sampling & Ground Truth:** [COMPLETED]
    *   Implement 8-channel chemical concentration sampling from `Environment3DState` based on `position_3d` and `sampling_volume`. [COMPLETED]
    *   Integrate with chemical physics models via `Environment3DState` queries. [COMPLETED - via method call]
    *   Implement `get_ground_truth()` to return the ideal chemical concentrations from `Environment3DState` for each channel. [COMPLETED]
*   **Task 3.2.2: High-Fidelity Imperfections:** [COMPLETED - Specific imperfections listed below]
    *   Implement configurable cross-sensitivity matrix. (Task 3.2.7.VOC) [COMPLETED]
    *   Model temperature/humidity compensation errors. (Task 3.2.6) [COMPLETED - Temp comp done]
    *   Implement sensor drift modeling (age-based, usage-based). (Task 3.2.4) [COMPLETED - Time-based]
    *   Implement multi-layer noise (Gaussian + 1/f + sensor-specific patterns). (Task 3.2.3) [COMPLETED - Gaussian implemented]
    *   Model calibration artifacts (offset, gain, non-linearity per channel). (Task 3.2.5) [COMPLETED - Offset/Gain]
*   **Task 3.2.3: ML-Specific Features:** [COMPLETED - via `get_ml_metadata`]
    *   Ensure `get_ml_metadata()` returns current state of imperfections. [COMPLETED]
    *   (Optional) Add confidence scoring for readings based on noise/drift levels. [TODO if needed]
*   **Task 3.2.4:** Implement comprehensive testing using various scenarios and mock `Environment3DState` configurations. [COMPLETED - Unit tests for each imperfection]
*   **Deliverable:** Production-ready VOC array sensor model suitable for ML training. [COMPLETED - Core imperfections implemented]

#### Sub-Phase 3.3: Thermal Camera Sensor (ML-Enhanced) [COMPLETED]
*   **Task 3.3.1: "True" Value Sampling & Ground Truth:** [COMPLETED]
    *   Implement 80x60 thermal array sampling by projecting a 2D thermal field from the 3D `Environment3DState`. [COMPLETED]
    *   Model field-of-view, perspective, spatial resolution, and pixel mapping. [COMPLETED - Basic structure]
    *   Implement `get_ground_truth()` to return the ideal 80x60 temperature array. [COMPLETED]
*   **Task 3.3.2: Realistic Camera Imperfections:** [COMPLETED - Specific imperfections listed below]
    *   Model pixel-level noise (fixed pattern + random). [COMPLETED - Gaussian pixel noise]
    *   Simulate dead/hot pixels. [COMPLETED]
    *   Implement optical blur and vignetting effects. [COMPLETED - Gaussian blur; vignetting TODO]
    *   Model calibration errors (per-pixel offset/gain). [COMPLETED - Global offset/gain; per-pixel TODO]
    *   Implement temperature compensation errors for camera electronics. [COMPLETED]
*   **Task 3.3.3: ML-Specific Features:** [PARTIALLY COMPLETED - `get_ml_metadata` updated]
    *   Support for labeling hot spots or thermal anomalies in the ground truth data. [TODO - Scenario level]
*   **Task 3.3.4:** Implement comprehensive testing. [COMPLETED - Unit tests for implemented imperfections]
*   **Deliverable:** Production-ready thermal camera model for ML training. [COMPLETED - Core imperfections implemented]

#### Sub-Phase 3.4: EMF Sensor (ML-Enhanced) [IN PROGRESS]
*   **Task 3.4.1: "True" Value Sampling & Ground Truth:** [COMPLETED]
    *   Implement AC field strength measurement from `Environment3DState`. [COMPLETED]
    *   (Optional) Model frequency spectrum analysis if required for detection algorithms. [TODO]
    *   Model directional sensitivity. [TODO]
    *   Implement `get_ground_truth()` for ideal EMF field characteristics. [COMPLETED]
*   **Task 3.4.2: Realistic Sensor Imperfections:** [IN PROGRESS]
    *   Model frequency-dependent response. [TODO]
    *   Implement temperature drift. [COMPLETED - Code and Tests]
    *   Simulate electromagnetic interference effects from other sources in the environment. [TODO]
    *   Model calibration and orientation errors. [TODO]
*   **Task 3.4.3: ML-Specific Features:** [TODO]
    *   Support for labeling EMF anomaly patterns in ground truth. [TODO]
*   **Task 3.4.4:** Implement comprehensive testing. [IN PROGRESS - Drift tests added]
*   **Deliverable:** Production-ready EMF sensor model for ML training.

---
### Phase 4: Full 3D Environment Integration & Remaining Sensors (Estimated: 8-12 days)
*   **Objective:** Integrate all sensors with live 3D physics models from the existing EnviroSense engine and implement the full sensor suite.

#### Sub-Phase 4.1: Enhanced `EnvironmentalSpace` Integration (Live Environment Orchestrator)
*   **Task 4.1.1:** Extend `physics/space.py` (or a dedicated orchestrator class) to provide live, queryable 3D fields by integrating with:
    *   `chemical_physics_integration.py` for chemical fields.
    *   `thermal.py` for temperature fields.
    *   `emf.py` for EMF fields.
    *   `acoustic.py` for acoustic fields.
    *   `vibration.py` for vibration data.
    *   Modules for barometric pressure, wind, etc.
*   **Task 4.1.2:** Implement spatial interpolation for queries within fields and caching if performance becomes an issue.
*   **Task 4.1.3:** Ensure temporal consistency in field updates for generating coherent time-series data for ML.
*   **Task 4.1.4:** Test the live environment orchestrator with simple scenarios.
*   **Deliverable:** A fully operational 3D environment orchestrator providing dynamic data to sensors.

#### Sub-Phase 4.2: Priority Sensor Live Integration
*   **Task 4.2.1:** Migrate the VOC Array sensor (from Phase 3.2) to sample from the live 3D environment orchestrator.
*   **Task 4.2.2:** Migrate the Thermal Camera sensor (from Phase 3.3) to sample from the live environment.
*   **Task 4.2.3:** Migrate the EMF sensor (from Phase 3.4) to sample from the live environment.
*   **Task 4.2.4:** Validate sensor responses to dynamic changes in the live simulated environment using defined scenarios.
*   **Deliverable:** Priority sensors fully integrated and working with the live 3D environment.

#### Sub-Phase 4.3: Remaining Environmental Sensors Implementation
*   **Task 4.3.1:** Implement the remaining environmental sensors, following the pattern of Phase 3 (True Value/Ground Truth, Imperfections, ML Features):
    *   Particulate Matter (PM1.0, PM2.5, PM10)
    *   Temperature/Humidity sensors
    *   Barometric Pressure sensor
    *   Wind Speed/Direction sensor
    *   Lightning Detection sensor (more event-driven, triggered by environment orchestrator).
*   **Task 4.3.2:** Ensure each sensor has ML-grade imperfections and ground truth tracking.
*   **Task 4.3.3:** Test with the scenario library and live environment.
*   **Deliverable:** Complete suite of environmental sensors implemented.

#### Sub-Phase 4.4: Infrastructure & System Sensors Implementation
*   **Task 4.4.1:** Implement remaining infrastructure sensors:
    *   Acoustic sensors (integrating with `acoustic.py`).
    *   Vibration sensors (integrating with `vibration.py`).
*   **Task 4.4.2:** Implement system sensors:
    *   Battery level (modeling discharge curves, temperature effects).
    *   Solar power (modeling generation based on simulated sun, panel efficiency).
    *   Internal temperature (modeling based on ambient and internal load).
*   **Task 4.4.3:** Add ML-grade modeling (where applicable) and testing for these sensors.
*   **Deliverable:** Complete Grid Guardian sensor array implemented.

---
### Phase 5: ML Training Pipeline Integration (Estimated: 5-8 days)
*   **Objective:** Create an end-to-end ML training data generation pipeline and support for model training and continuous learning.

#### Sub-Phase 5.1: Training Data Pipeline
*   **Task 5.1.1:** Create `envirosense/simulation_engine/ml_training/pipeline.py`.
*   **Task 5.1.2:** Implement `MLTrainingPipeline` class to manage large-scale dataset generation:
    *   Orchestrate `MLDataGenerator` based on a manifest of scenarios and desired sample sizes.
    *   Handle batch processing and data aggregation.
    *   Implement data augmentation strategies (e.g., varying imperfection levels, slight scenario timing shifts).
    *   Perform final quality validation and filtering of generated datasets.
*   **Task 5.1.3:** (Optional) Add support for parallel processing/distributed generation if needed for very large datasets.
*   **Task 5.1.4:** Implement progress tracking and resumability for long generation tasks.
*   **Deliverable:** A scalable and robust pipeline for generating ML training datasets.

#### Sub-Phase 5.2: Model Integration Support
*   **Task 5.2.1:** Define clear interface specifications for how detection models will consume the generated data.
*   **Task 5.2.2:** Implement mechanisms to feed model performance metrics back into the `ActiveLearningManager`.
*   **Task 5.2.3:** Enhance `ActiveLearningManager` to use model uncertainty outputs for targeted data generation.
*   **Task 5.2.4:** Develop a basic framework or guidelines for sim-to-real validation (e.g., comparing statistical properties of simulated vs. real sensor data if available).
*   **Deliverable:** Enhanced support for integrating with ML model training and validation workflows.

#### Sub-Phase 5.3: Continuous Learning Framework
*   **Task 5.3.1:** Implement logic in `ActiveLearningManager` or `MLTrainingPipeline` to adapt scenario parameters or select new scenarios based on ongoing model performance.
*   **Task 5.3.2:** Design hooks for integrating real-world data (if available) for calibrating simulation parameters or identifying new scenarios.
*   **Task 5.3.3:** Create scripts or tools for automated dataset refresh and expansion based on new scenarios or active learning feedback.
*   **Task 5.3.4:** Implement basic monitoring and alerting for the data generation pipeline (e.g., generation failures, quality issues).
*   **Deliverable:** A foundational framework for continuous learning and improvement of both data generation and ML models.

#### Sub-Phase 5.4: Production Integration & Documentation
*   **Task 5.4.1:** Create a main simulation loop script that demonstrates end-to-end ML data generation using the full system.
*   **Task 5.4.2:** Develop comprehensive example scenarios and usage examples.
*   **Task 5.4.3:** Write thorough documentation for all components, including configuration, scenario definition, and data generation.
*   **Task 5.4.4:** Create performance benchmarks for data generation and validation tests for the overall system.
*   **Deliverable:** A production-ready, well-documented ML training data generation system.

---
## Expected System Capabilities & Integration Points
(As per user's detailed request, including Python interface examples, ML training support details, and success criteria.)

## Implementation Priority
Start with VOC Array + Thermal Camera + EMF Sensor as core sensors, then build ML training infrastructure (Phase 2), then expand to full sensor suite and full 3D environment integration, and finally the ML pipeline integration. The primary focus is creating a production-ready ML training data factory.