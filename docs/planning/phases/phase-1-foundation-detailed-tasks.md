# EnviroSense - Phase 1 Foundation: Detailed Subtasks

**Phase Objective:** Establish the core data standards. Refactor the Simulation Engine for scalability and high-fidelity data generation (leveraging sensor manufacturer data). Develop the Visual GUI Demonstrator. Implement foundational components and interfaces for the Active Learning Manager.

**Master Plan Reference:** [`envirosense-master-development-plan-v3.md`](../../envirosense-master-development-plan-v3.md)

**Task Status Key:**
*   **TODO:** Task has not started.
*   **DOING:** Task is actively being worked on.
*   **DONE:** Task is completed.
*   **BLOCKED:** Task is blocked by another task or external factor.
*   **REVIEW:** Task is completed and awaiting review/approval.

---

## 1.1. Universal Data Standards & Schema Definition (Overall Status: ⧗ IN PROGRESS)

*   **Task 1.1.1: Finalize `UniversalSensorReading.avsc` Schema.** (Status: TODO)
    *   Subtask 1.1.1.1: Define `timestamp_utc`, `product_type`, `device_id`, `location` fields and Avro types. (Status: TODO)
    *   Subtask 1.1.1.2: Define `SensorReading` sub-record structure: `sensor_id` (string), `capability` (enum), `value` (union type), `unit` (string), `quality_indicators` (map of string to union type), `compensations_applied` (array of strings). (Status: TODO)
    *   Subtask 1.1.1.3: Define `capability` enum values in a separate `SensorCapabilityEnum.avsc` (or inline), including distinct entries for raw vs. processed data (e.g., `ACOUSTIC_RAW_WAVEFORM_PCM`, `ACOUSTIC_FEATURES_MFCC`, `THERMAL_IMAGE_RAW_PIXELS`, `THERMAL_OBJECT_TEMPERATURE_LIST`). (Status: TODO)
    *   Subtask 1.1.1.4: Define `ml_outputs_edge` and `ml_outputs_hub` structures (as an Avro record type: `model_id` (string), `model_version` (string), `prediction` (union type: string, float, map), `confidence` (float), `key_features_contributing` (array of strings)). (Status: TODO)
    *   Subtask 1.1.1.5: Conduct team review and formal approval of `UniversalSensorReading.avsc`. (Status: TODO)
*   **Task 1.1.2: Define `GroundTruthLabels.avsc`.** (Status: TODO)
    *   Subtask 1.1.2.1: Define fields: `event_type` (string/enum), `is_anomaly` (boolean), `fault_severity` (enum: NONE, LOW, MEDIUM, HIGH, CRITICAL), `scenario_specific_details` (map of string to string or JSON string). (Status: TODO)
    *   Subtask 1.1.2.2: Conduct team review and approval. (Status: TODO)
*   **Task 1.1.3: Define `ScenarioDefinition.avsc`.** (Status: TODO)
    *   Subtask 1.1.3.1: Define fields: `scenario_id` (string), `scenario_class_module` (string), `scenario_class_name` (string), `name` (string), `description` (string), `category` (string), `difficulty_level` (enum: EASY, MEDIUM, HARD), `expected_duration_seconds` (double), `specific_params` (map of string to JSON string for simulation parameters). (Status: TODO)
    *   Subtask 1.1.3.2: Conduct team review and approval. (Status: TODO)
*   **Task 1.1.4: Define Supporting Schemas: `SensorReadingsMap.avsc`, `SensorReadingBase.avsc`, `ScenarioRunPackage.avsc`.** (Status: TODO)
    *   Subtask 1.1.4.1: Define `SensorReadingBase.avsc` (common metadata: `timestamp_sensor_local`, `status_flags`, etc. - evaluate if needed or if `UniversalSensorReading` top-level fields suffice). (Status: TODO)
    *   Subtask 1.1.4.2: Define `SensorReadingsMap.avsc` (map of `sensor_id` to `SensorReading` - or determine if `UniversalSensorReading.readings` array is sufficient directly). (Status: TODO)
    *   Subtask 1.1.4.3: Define `ScenarioRunPackage.avsc` (metadata for a simulation run: `package_id`, `package_version`, `generation_timestamp_utc`, `scenario_definition_ref` (string ID or embedded `ScenarioDefinition`), `simulation_engine_version`, `data_generator_version`, `ml_data_samples_file_reference` (string path), `run_metadata` (map)). (Status: TODO)
    *   Subtask 1.1.4.4: Conduct team review and approval for each. (Status: TODO)
*   **Task 1.1.5: Create Comprehensive Documentation for all Avro Schemas.** (Status: TODO)
    *   Subtask 1.1.5.1: Create/update markdown files in `envirosense/docs/schemas/` for each schema, detailing fields, types, purpose, and usage examples. (Status: TODO)
    *   Subtask 1.1.5.2: Document physics-informed design principles applied and rationale for schema choices. (Status: TODO)
*   **Task 1.1.6: Develop/Enhance `avro_io.py` Utilities.** (Status: TODO)
    *   Subtask 1.1.6.1: Implement robust schema loading from file (and potentially a schema registry later).
    *   Subtask 1.1.6.2: Implement validation function using `fastavro.validate` or `avro.schema.validate`.
    *   Subtask 1.1.6.3: Implement serialization to Avro binary format and Avro JSON format.
    *   Subtask 1.1.6.4: Implement deserialization from Avro binary and Avro JSON.
    *   Subtask 1.1.6.5: Add comprehensive unit tests for `avro_io.py` covering all schemas and operations.
*   **Task 1.1.7: Create JSON Example Instances for Each Core Schema.** (Status: TODO)
    *   Subtask 1.1.7.1: Create a valid, illustrative `.json` example for `UniversalSensorReading.avsc` (e.g., `UniversalSensorReading_example.json`).
    *   Subtask 1.1.7.2: Create example for `GroundTruthLabels.avsc`.
    *   Subtask 1.1.7.3: Create example for `ScenarioDefinition.avsc`.
    *   Subtask 1.1.7.4: Create examples for other key supporting schemas. Store in `envirosense/schemas/avro/examples/`.

---
## 1.2. Simulation Engine Refactoring & High-Fidelity Enhancement (Overall Status: ⧖ PLANNED)

*   **Task 1.2.1: Implement Universal Sensor Abstraction Layer.** (Status: TODO)
    *   Subtask 1.2.1.1: Create `envirosense/simulation_engine/sensors/capabilities.py` and define `SensorCapability` Enum (values derived from Task 1.1.1.3).
    *   Subtask 1.2.1.2: Create `envirosense/simulation_engine/sensors/universal_base_sensor.py`. Define `BaseSensor` ABC with:
        *   `__init__(self, sensor_id: str, product_config: 'ProductConfiguration', sensor_specific_config: Dict)`.
        *   Abstract method `_define_capabilities(self) -> List[SensorCapability]`.
        *   Abstract method `_define_dependencies(self) -> Dict[str, List[SensorCapability]]` (maps dependent sensor IDs to required capabilities).
        *   Abstract method `measure(self, environment_state: 'Environment3DState', other_sensor_outputs: Dict[str, List[Dict]]) -> List[Dict[str, Any]]` (returns list of `SensorReading`-like dicts).
        *   Abstract method `apply_compensation(self, reading_dict: Dict[str, Any], compensating_sensor_outputs: Dict[str, List[Dict]]) -> Dict[str, Any]`.
        *   Abstract method `_load_calibration_data(self) -> Dict[str, Any]`.
*   **Task 1.2.2: Refactor Key Simulated Sensors for Grid Guardian.** (Status: TODO)
    *   Subtask 1.2.2.1: Refactor `VOCSensorArray` (from `environmental.py`) to inherit `BaseSensor`, implement methods, use manufacturer spec data for realism, output `UniversalSensorReading` compatible dicts for its capabilities.
    *   Subtask 1.2.2.2: Refactor `TemperatureHumiditySensor` (from `environmental.py`) similarly.
    *   Subtask 1.2.2.3: Refactor `ThermalCameraSensor` (from `infrastructure.py`) similarly (consider outputting both raw pixel array and processed object list capabilities).
    *   Subtask 1.2.2.4: Refactor/Create `InternalBoardTemperatureSensor` (in `system.py` or new) similarly.
    *   Subtask 1.2.2.5: Refactor `AcousticSensor` (from `infrastructure.py`) similarly (outputting raw waveform and/or feature set capabilities).
    *   Subtask 1.2.2.6: Refactor/Create `WindSensor` (from `environmental.py`) similarly.
    *   Subtask 1.2.2.7: Implement `apply_compensation()` for:
        *   `VOCSensorArray` using `TemperatureHumiditySensor` output.
        *   `ThermalCameraSensor` using `InternalBoardTemperatureSensor` output.
        *   `AcousticSensor` using `WindSensor` output.
*   **Task 1.2.3: Implement Product Configuration System for Simulation.** (Status: TODO)
    *   Subtask 1.2.3.1: Create `envirosense/config/product_registry.py`.
    *   Subtask 1.2.3.2: Define `ProductConfiguration` Dataclass (fields: `product_type` (str), `sensor_suite: List[Dict]` (each dict: `sensor_id_template`, `sensor_class_path`, `capabilities_provided`, `specific_config`), `physics_modules_required: List[str]`, `ml_models_edge_default: List[Dict]` (each dict: `model_name`, `model_type_indicator`), `operational_logic_stubs: Dict`).
    *   Subtask 1.2.3.3: Implement `ProductRegistry` Singleton to load YAML/JSON configurations from `envirosense/config/products/`.
    *   Subtask 1.2.3.4: Create `envirosense/config/products/grid_guardian.yaml` defining its sensor suite (mapping to refactored sensor classes), default edge models (names/types for simulation), and relevant physics modules.
*   **Task 1.2.4: Refactor `VirtualGridGuardian` (Simulation Component).** (Status: TODO)
    *   Subtask 1.2.4.1: Update `VirtualGridGuardian.__init__` to accept `product_type: str`, then load its full configuration via `ProductRegistry`.
    *   Subtask 1.2.4.2: Dynamically instantiate `BaseSensor` implementations based on the `sensor_suite` in the loaded `ProductConfiguration`.
    *   Subtask 1.2.4.3: Implement logic to orchestrate `measure()` calls for all managed sensors, respecting dependencies and providing `other_sensor_outputs` for compensation.
    *   Subtask 1.2.4.4: Implement `generate_training_sample()` method to aggregate all sensor outputs from a timestep into a single `UniversalSensorReading`-like dictionary.
    *   Subtask 1.2.4.5: Simulate execution of `ml_models_edge_default` (from product config) on the aggregated sensor data and populate the `ml_outputs_edge` field in the output dictionary.
*   **Task 1.2.5: Develop `VirtualEdgeHub` (Simulation Component).** (Status: TODO)
    *   Subtask 1.2.5.1: Define `VirtualEdgeHub` class structure.
    *   Subtask 1.2.5.2: Implement method to accept a list of `UniversalSensorReading`-like dicts (one per connected `VirtualGridGuardian`).
    *   Subtask 1.2.5.3: Implement basic data aggregation logic (e.g., averaging specific fields, identifying max values across GGs).
    *   Subtask 1.2.5.4: Simulate execution of conceptual cluster-level ML models (e.g., if 3 out of 5 GGs report X, then Hub detects Y).
    *   Subtask 1.2.5.5: Output a `ClusterSummary`-like dict or a `UniversalSensorReading`-like dict (representing the Hub's perspective) including `ml_outputs_hub`.
*   **Task 1.2.6: Refactor Physics Engine into `ModularPhysicsEngine`.** (Status: TODO)
    *   Subtask 1.2.6.1: Create `envirosense/simulation_engine/physics/modular_engine.py`. Define `PhysicsModule` ABC (methods: `applies_to_product(product_type: str) -> bool`, `initialize(self, params: Dict, environment_state: 'Environment3DState')`, `update(self, environment_state: 'Environment3DState', dt: float) -> None`).
    *   Subtask 1.2.6.2: Implement `ModularPhysicsEngine` class to load, initialize (based on `ProductConfiguration.physics_modules_required`), and execute active `PhysicsModule`s.
    *   Subtask 1.2.6.3: Create initial stub/refactored `PhysicsModule`s (e.g., `ChemicalDispersionModule`, `ThermalPropagationModule`, `AcousticEnvironmentModule`) relevant to Grid Guardian scenarios. Update `Environment3DState` accordingly.
*   **Task 1.2.7: Refactor Scenario System.** (Status: TODO)
    *   Subtask 1.2.7.1: Create `envirosense/simulation_engine/scenarios/templates.py` and define `ScenarioTemplate` ABC (method: `instantiate(self, product_type: str, scenario_definition: Dict) -> 'BaseScenario'`).
    *   Subtask 1.2.7.2: Update `BaseScenario` (in `envirosense/simulation_engine/scenarios/base.py`) to be initialized with parameters from a `ScenarioDefinition.avsc`-like dictionary.
    *   Subtask 1.2.7.3: Ensure `BaseScenario.get_ground_truth_labels(self, current_time: float) -> Dict` returns data compatible with `GroundTruthLabels.avsc`.
    *   Subtask 1.2.7.4: Create initial stub `ScenarioTemplate` implementations for Grid Guardian (e.g., `ArcingEventTemplate`, `OverheatingTransformerTemplate`).
*   **Task 1.2.8: Unit Tests for all Refactored Simulation Components.** (Status: TODO)
    *   Subtask 1.2.8.1: Write unit tests for each refactored `BaseSensor` implementation.
    *   Subtask 1.2.8.2: Write unit tests for `ProductRegistry` and `ProductConfiguration` loading.
    *   Subtask 1.2.8.3: Write unit tests for `VirtualGridGuardian` (instantiation, data aggregation, edge ML simulation).
    *   Subtask 1.2.8.4: Write unit tests for `VirtualEdgeHub` (data reception, aggregation, hub ML simulation).
    *   Subtask 1.2.8.5: Write unit tests for `ModularPhysicsEngine` and individual `PhysicsModule` stubs.
    *   Subtask 1.2.8.6: Write unit tests for `BaseScenario` initialization and `get_ground_truth_labels`.

---
## 1.3. Visual GUI Test / Simulation Demonstrator Development (Overall Status: ⧖ PLANNED)

*   **Task 1.3.1: Design Demonstrator Architecture, UI/UX, and Technology Stack.** (Status: TODO)
    *   Subtask 1.3.1.1: Evaluate and select GUI framework (e.g., Streamlit for rapid development, PyQT for desktop, or Electron/Web-based for broader accessibility).
    *   Subtask 1.3.1.2: Create UI mockups/wireframes for key views: scenario selection, map/environment view, device (GG/Hub) status panels, data visualization panels (charts, tables), AI decision/explanation panels, event log, simulation controls.
    *   Subtask 1.3.1.3: Define data flow architecture: how the GUI interacts with the refactored Simulation Engine components (`ModularPhysicsEngine`, `VirtualGridGuardian`, `VirtualEdgeHub`, `BaseScenario`).
*   **Task 1.3.2: Develop Core Visualization Elements.** (Status: TODO)
    *   Subtask 1.3.2.1: Implement a simplified 2D map rendering component for displaying utility segments or relevant areas.
    *   Subtask 1.3.2.2: Develop dynamic icons/markers for Grid Guardian units and Edge Hubs, showing placement and basic status (e.g., online, offline, alerting).
    *   Subtask 1.3.2.3: Create reusable data display panels for real-time sensor readings (e.g., line charts for time-series, gauges for current values, text readouts).
    *   Subtask 1.3.2.4: Implement sensor activity indicators on device icons (e.g., highlighting active sensors).
*   **Task 1.3.3: Implement Scenario Management Interface.** (Status: TODO)
    *   Subtask 1.3.3.1: Develop functionality to browse and load `ScenarioDefinition.avsc` files from a predefined library directory.
    *   Subtask 1.3.3.2: Implement GUI controls for selecting a scenario to run.
    *   Subtask 1.3.3.3: Implement simulation controls (Play, Pause, Reset, Speed Adjustment) that interact with the Simulation Engine's main loop.
    *   Subtask 1.3.3.4: Develop a dynamic event timeline and detailed event log display panel.
*   **Task 1.3.4: Implement Visualization for `VirtualGridGuardian` Instances.** (Status: TODO)
    *   Subtask 1.3.4.1: For each simulated GG, display its active sensors and their key current readings in its dedicated panel.
    *   Subtask 1.3.4.2: Indicate which local ML models (from `ml_outputs_edge`) are active/triggered on each GG.
    *   Subtask 1.3.4.3: Display key input features/sensor readings that contributed to a GG's local model decision.
    *   Subtask 1.3.4.4: Clearly visualize local alerts and decisions (e.g., simulated targeted shutoff recommendation) originating from each GG.
*   **Task 1.3.5: Implement Visualization for `VirtualEdgeHub` Instance.** (Status: TODO)
    *   Subtask 1.3.5.1: Visually represent data flows from connected GGs to the simulated Edge Hub on the map/diagram.
    *   Subtask 1.3.5.2: Create display panels for aggregated data views at the Hub level (e.g., average temperature in cluster, max VOC reading).
    *   Subtask 1.3.5.3: Indicate which cluster-level ML models (from `ml_outputs_hub`) are active/triggered on the Hub.
    *   Subtask 1.3.5.4: Display key aggregated input features contributing to Hub model decisions.
    *   Subtask 1.3.5.5: Clearly visualize cluster-level alerts and decisions originating from the Hub, differentiating them from GG-local alerts.
*   **Task 1.3.6: Implement AI Decision Explanation Interface.** (Status: TODO)
    *   Subtask 1.3.6.1: Design a structured format for simplified reasoning strings (e.g., "Alert: High Fire Risk. Reason: GG1 reports VOC Profile A (Confidence: 0.85), GG2 reports Thermal Anomaly (Confidence: 0.90), Wind SE at 15mph from Hub Weather Data").
    *   Subtask 1.3.6.2: Integrate these explanations into the AI decision panels for both GGs and the Edge Hub.
*   **Task 1.3.7: Implement ALM Data Export Feature.** (Status: TODO)
    *   Subtask 1.3.7.1: Add a GUI button/option to "Export Scenario Run Data for ALM".
    *   Subtask 1.3.7.2: Implement backend logic for the demonstrator to collect all `UniversalSensorReading` data (from all VGGs, and the VHub's perspective) and corresponding `GroundTruthLabels` for the completed/current run, then serialize this into an Avro dataset file according to `ScenarioRunPackage.avsc` (or a simple collection of `MLDataSample.avsc` records).
*   **Task 1.3.8: Testing and Refinement of the Demonstrator.** (Status: TODO)
    *   Subtask 1.3.8.1: Conduct unit tests for individual GUI components and their backend interaction logic.
    *   Subtask 1.3.8.2: Perform internal user acceptance testing (UAT) with the development team to ensure usability and correctness.
    *   Subtask 1.3.8.3: Iterate on UI/UX design and functionality based on UAT feedback.

---
## 1.4. Active Learning Manager (ALM) - Foundational Backend & Interfaces (Overall Status: ⧗ IN PROGRESS)

*   **Task 1.4.1: Finalize `PostgresScenarioRepository` Implementation.** (Status: ⧗ IN PROGRESS)
    *   Subtask 1.4.1.1: Verify all `ScenarioRepositoryInterface` methods are fully implemented and robustly tested against PostgreSQL. (✓ Some methods exist from `ml_concrete_interface_integration_plan.md`)
    *   Subtask 1.4.1.2: Ensure seamless serialization/deserialization of `ScenarioDefinition.avsc` structures (especially `specific_params` map to/from JSONB). (⧖ PLANNED)
    *   Subtask 1.4.1.3: Implement appropriate database indexing for common query patterns (by ID, category, tags) and conduct performance tuning. (⧖ PLANNED)
*   **Task 1.4.2: Finalize `LocalModelInterface` Implementation.** (Status: ⧗ IN PROGRESS)
    *   Subtask 1.4.2.1: Confirm `get_model_performance_feedback` correctly loads models (e.g., `.joblib`), processes Avro evaluation datasets (list of `UniversalSensorReading` dicts), and calculates all required metrics (accuracy, F1, log-loss, classification report). (✓ Avro consumption exists from `ml_concrete_interface_integration_plan.md`)
    *   Subtask 1.4.2.2: Implement detailed population of the `ModelPerformanceData` structure, including `uncertain_samples` (with `sample_id`, `true_label`, `predicted_label`, `uncertainty_score`) and `misclassified_samples`. Ensure `sample_features_summary` (with feature path, raw value, importance score - initially raw features) is populated. (⧖ PLANNED)
    *   Subtask 1.4.2.3: Implement robust error handling (e.g., model file not found, data format mismatch) and detailed logging. (⧖ PLANNED)
*   **Task 1.4.3: Refine `MLDataGenerator` for ALM Orchestration.** (Status: ⧗ IN PROGRESS)
    *   Subtask 1.4.3.1: Ensure `MLDataGenerator.generate_training_dataset()` method is callable by ALM, accepting `ScenarioDefinition`(s) (retrieved by ALM via `ScenarioRepositoryInterface`), `product_type` (for `ProductRegistry`), `num_samples`, and `output_format="avro"`. (✓ Schema alignment done in ML-1)
    *   Subtask 1.4.3.2: Integrate `MLDataGenerator` to use the refactored Simulation Engine components (`VirtualGridGuardian`, `VirtualEdgeHub`, `ModularPhysicsEngine`, `BaseScenario` initialized with `ScenarioDefinition`) to produce the targeted Avro datasets. (⧖ PLANNED)
*   **Task 1.4.4: Develop/Update Baseline ML Models for ALM Testing.** (Status: ⧖ PLANNED)
    *   Subtask 1.4.4.1: Create simple, trainable Scikit-learn models for key Grid Guardian detections (e.g., arcing classification, thermal anomaly regression/classification) that consume features derivable from `UniversalSensorReading` data.
    *   Subtask 1.4.4.2: Document feature extraction logic for these baseline models.
    *   Subtask 1.4.4.3: Save these models (e.g., as `.joblib` files) to be loaded by `LocalModelInterface`.
*   **Task 1.4.5: Generate Initial Evaluation Avro Datasets from Simulator for ALM loop testing.** (Status: ⧖ PLANNED)
    *   Subtask 1.4.5.1: Use the refactored Simulation Engine (via `MLDataGenerator` or directly) to generate a small (e.g., 100-500 samples) but diverse evaluation dataset (`initial_eval_data.avro`) containing `UniversalSensorReading` records with corresponding `GroundTruthLabels`. This dataset should include examples of normal operation and various fault/event conditions for Grid Guardian.
*   **Task 1.4.6: Develop `run_active_learning_loop_concrete.py` Test Script.** (Status: ⧖ PLANNED)
    *   Subtask 1.4.6.1: Create the Python script `envirosense/simulation_engine/ml_training/examples/run_active_learning_loop_concrete.py`.
    *   Subtask 1.4.6.2: Script to instantiate `ActiveLearningManager`, `ProductRegistry`, `PostgresScenarioRepository`, `LocalModelInterface` (loading a baseline model), and `MLDataGenerator`.
    *   Subtask 1.4.6.3: Implement logic for one full ALM cycle within the script:
        1.  Invoke `LocalModelInterface.get_model_performance_feedback()` using `initial_eval_data.avro`.
        2.  Invoke `ActiveLearningManager.identify_weak_spots()` using the performance data.
        3.  Invoke `ActiveLearningManager.suggest_scenario_modifications()` using the identified weak spots.
        4.  Invoke `ActiveLearningManager.generate_targeted_samples()` (which internally calls `MLDataGenerator` with new/modified `ScenarioDefinition`s).
        5.  (Conceptual step for testing) Load the newly generated targeted samples and re-evaluate the baseline model to observe if performance on weak spots improves (or simply verify data generation).
    *   Subtask 1.4.6.4: Add detailed logging output and assertions at each step to validate the data flow, component interactions, and correctness of outputs (e.g., format of `ModelPerformanceData`, structure of `ScenarioDefinition` modifications, content of generated Avro samples).

---