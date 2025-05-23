# EnviroSense™: Interim Phase & EMF Sensor Finalization Plan

This document outlines the next steps for the EnviroSense™ project, focusing on the finalization of the EMF Sensor (Sub-Phase 3.4) and the concurrent tracks of the Interim Phase.

## 1. Finalize EMF Sensor (Sub-Phase 3.4)

**Objective:** Ensure the `EMFSensor` is fully reviewed, documented, and ready for broader integration.

*   **Task 3.4.1: Review & Refine Code**
    *   Conduct a thorough code review of `envirosense/simulation_engine/sensors/infrastructure.py` for the `EMFSensor`.
    *   Confirm implementation details for frequency spectrum analysis and calibration/orientation errors.
*   **Task 3.4.2: ML-Specific Features Integration**
    *   Clarify and plan the implementation for "Support for labeling EMF anomaly patterns in ground truth."
    *   Ensure scenario definitions (e.g., in `electrical_scenarios.py` and `BaseScenario`) can provide these specific labels.
    *   Verify that `EMFSensor.get_ground_truth()` provides all necessary raw data to support this labeling by the scenario.
*   **Task 3.4.3: Documentation**
    *   Update all docstrings and comments within `EMFSensor` in `infrastructure.py`.
    *   Ensure `test_infrastructure_sensors.py` is well-commented.
    *   Add usage examples or notes for ML data generation specific to the `EMFSensor`'s advanced features.

## 2. Interim Phase: Advancing Data Infrastructure & Core Functionality (Concurrent Tracks)

**Overall Objective:** Establish robust Avro-based data handling while concurrently completing core scenario logic and ML data generation capabilities.

### Track 1: Avro Schema & Data Governance Foundation (Sub-Phase 2.A Continuation)

*   **Task 2.A.3: Data Versioning and MLOps Strategy Outline**
    *   Define and document a policy for evolving Avro schemas (schema versioning).
    *   Outline the chosen approach for versioning generated Avro datasets (dataset versioning).
    *   Document how dataset and schema versions will be logged and linked with ML experiments (experiment tracking integration).
    *   *Deliverable: A document section in `digital-twin-sensor-array-development-plan.md` or a new `DATA_GOVERNANCE.md`.*
*   **Task 2.A.4: Initial Validation Rules (Conceptual)**
    *   Define a preliminary set of physics-informed validation rules for key data fields.
    *   Outline how these rules would be applied (e.g., as part of `MLDataGenerator._validate_generated_data()`).
    *   *Deliverable: Documented initial validation rules.*

### Track 2: Scenario Logic Completion [COMPLETED]

*   **Task SC-1: Finalize Key Scenario Implementations & Parameter Alignment [COMPLETED]**
    *   Reviewed and refined `DiurnalCycleScenario`, `ArcingEventScenario`, `EarlyCombustionScenario`.
    *   Ensured their parameters are defined in Pydantic models and are serializable to JSON.
*   **Task SC-2: Implement Remaining Stubbed Scenarios [COMPLETED]**
    *   Completed logic for `SeasonalVariationScenario`, `WeatherEventScenario`, `BaselineOperationScenario` in `normal_scenarios.py`.
    *   Completed logic for `CoronaDischargeScenario`, `InsulationBreakdownScenario`, `EquipmentOverheatScenario` in `electrical_scenarios.py`.
    *   Completed logic for `CellulosePyrolysisScenario`, `LigninDecompositionScenario`, `FirePrecursorComboScenario` in `fire_scenarios.py`.
    *   All implementations now use Pydantic models for parameters.
*   **Task SC-3: Update/Verify `BaseScenario.to_dict()` and `from_dict()` [COMPLETED]**
    *   Verified robust handling of `specific_params` as JSON strings, aligning with `ScenarioDefinition.avsc`. [Implicitly verified by successful refactoring of all scenarios to use Pydantic models].

### Track 3: MLDataGenerator & Active Learning Enhancements

*   **Task ML-1: Finalize `MLDataGenerator` Core Methods** [COMPLETED - 2025-05-22]
    *   Review and refine `generate_training_dataset`, `generate_balanced_dataset`, `generate_temporal_sequences`, `generate_edge_cases`. [COMPLETED]
    *   Ensure their internal data sample structure (list of Python dicts) directly maps to the fields defined in `MLDataSample.avsc`. [COMPLETED]
*   **Task ML-2: Complete `MLDataGenerator._export_data()` and `_validate_generated_data()`**
    *   Finalize Pandas DataFrame/CSV export.
    *   Implement `_validate_generated_data` based on rules from Task 2.A.4.
*   **Task ML-3: Enhance `ActiveLearningManager`**
    *   Implement stubbed methods: `identify_weak_spots`, `generate_targeted_samples`, `suggest_scenario_modifications`.
    *   Define interfaces for model performance feedback.
*   **Task ML-4: Standardize ML-Ready Export Format Documentation**
    *   Create/update documentation (e.g., `DATA_FORMAT.md` or in the main plan) detailing the Avro schemas (`MLDataSample.avsc`, `ScenarioRunPackage.avsc`) and usage for ML pipelines.

## Visual Summary of Concurrent Tracks

```mermaid
gantt
    dateFormat YYYY-MM-DD
    title Interim Phase: Concurrent Development Tracks
    axisFormat %m/%d

    section Finalize EMF Sensor (Sub-Phase 3.4)
    Review & Refine Code             :crit, active, p3.4.1, 2025-05-23, 2d
    ML Features (Labeling)           :p3.4.2, after p3.4.1, 3d
    Documentation                    :p3.4.3, after p3.4.2, 2d

    section Track 1: Avro & Data Governance (2.A cont.)
    Task 2.A.3: Versioning/MLOps Doc :crit, active, t1.1, 2025-05-23, 3d
    Task 2.A.4: Validation Rules Doc :crit, t1.2, after t1.1, 2d

    section Track 2: Scenario Logic
    Task SC-1: Finalize Key Scenarios    :done, t2.1, 2025-05-23, 4d
    Task SC-2: Implement Stubbed Scenarios :done, t2.2, after t2.1, 7d
    Task SC-3: Verify BaseScenario dicts  :done, t2.3, after t2.1, 1d

    section Track 3: MLDataGenerator & Active Learning
    Task ML-1: Finalize MLDataGen Core :done, t3.1, 2025-05-22, 3d
    Task ML-2: Complete Export/Validate :t3.2, after t1.2, after t3.1, 3d
    Task ML-3: Enhance ActiveLearningMgr :t3.3, after t3.1, 5d
    Task ML-4: ML Export Format Docs    :t3.4, after t3.2, 2d