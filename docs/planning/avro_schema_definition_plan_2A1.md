# Plan for Task 2.A.1: Define Core Avro Schemas (.avsc files)

This document outlines the sequential sub-tasks for completing **Task 2.A.1: Define Core Avro Schemas (.avsc files)** as detailed in the main `digital-twin-sensor-array-development-plan.md`.

## Sub-Tasks Checklist

-   [ ] **Task 2.A.1.1: Define `SensorReadingBase.avsc` (Reusable Record Type)**
    -   Objective: Create a base Avro record schema for common sensor reading metadata.
    -   Key Fields: `sensor_id`, `sensor_type_general`, `timestamp_sensor_local`, `status_flags`, `reading_quality_score`, `reading_confidence`.
    -   Status: Design discussed and drafted.

-   [ ] **Task 2.A.1.2: Define Specific Sensor Reading Schemas**
    -   Objective: For each key sensor type, define an Avro record schema for its specific output, referencing `SensorReadingBase.avsc`.
    -   Examples:
        -   [ ] `ThermalReading.avsc` (Design discussed and drafted for FLIR Lepton 3.5, 160x120 resolution)
        -   [ ] `EMFReading.avsc`
        -   [ ] `VOCReading.avsc`
        -   [ ] `AcousticReading.avsc`
        -   [ ] `ParticulateMatterReading.avsc`
        -   [ ] (Other sensor types as needed)
    -   Details: Incorporate physics-informed principles, units, and expected ranges in `doc` attributes.

-   [ ] **Task 2.A.1.3: Define `SensorReadingsMap.avsc` (Wrapper Record)**
    -   Objective: Define an Avro schema representing a collection of all sensor readings at a given timestamp.
    -   Details: Likely a map where keys are sensor instance IDs (strings) and values are a union of all defined specific sensor reading schemas.

-   [ ] **Task 2.A.1.4: Define `GroundTruthLabels.avsc` (Reusable Record Type)**
    -   Objective: Create an Avro record schema for common and scenario-specific ground truth labels.
    -   Details: Include fields like `event_type`, `is_anomaly`, `fault_severity`, `scenario_specific_details`, `sensor_specific_ground_truth`.

-   [ ] **Task 2.A.1.5: Define `MLDataSample.avsc` (Primary Data Point Schema)**
    -   Objective: Define the top-level schema for a single data sample.
    -   Details: Include `timestamp_scenario_seconds`, `scenario_id`, `sensor_readings_map` (referencing `SensorReadingsMap.avsc`), `ground_truth_labels` (referencing `GroundTruthLabels.avsc`), and `extracted_class_label`.

-   [ ] **Task 2.A.1.6: Define `ScenarioDefinition.avsc` (For Scenario-as-Data)**
    -   Objective: Define an Avro schema to represent the full definition and parameters of a scenario instance.
    -   Details: Include `scenario_class_module`, `scenario_class_name`, `scenario_id`, `name`, `description`, `category`, `difficulty_level`, `expected_duration_seconds`, `specific_params` (map of string to JSON string).

-   [ ] **Task 2.A.1.7: Define `ScenarioRunPackage.avsc` (Scenario-as-Data Wrapper)**
    -   Objective: Define the top-level schema for a complete scenario run package.
    -   Details: Include `package_id`, `package_version`, `generation_timestamp_utc`, `scenario_definition` (referencing `ScenarioDefinition.avsc`), `simulation_engine_version`, `data_generator_version`, `ml_data_samples_file_reference` or `ml_data_samples_embedded`, `run_metadata`.

-   [ ] **Task 2.A.1.8: Document Physics-Informed Schema Principles & Initial Review**
    -   Objective: Consolidate and document principles for embedding physical realism into Avro schemas.
    -   Action: Conduct an initial review of all defined `.avsc` files with the team.

-   [ ] **Task 2.A.1.9: Create Example JSON Instances for Each Schema**
    -   Objective: For each `.avsc` file created, provide a corresponding `.json` file with a valid example instance.
    -   Benefit: Aids understanding, validation, testing, and serves as a reference.

## Deliverables for Task 2.A.1
- Initial set of `.avsc` files for all defined schemas committed to Git.
- Corresponding example `.json` files for each defined Avro schema.
- Documented principles for physics-informed schema design.
- Record of initial review completion.