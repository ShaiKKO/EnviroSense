# Plan for Task ML-1: Finalize `MLDataGenerator` Core Methods

**Status: COMPLETED - 2025-05-22**

**Track:** 3: MLDataGenerator & Active Learning Enhancements
**Task:** ML-1: Finalize `MLDataGenerator` Core Methods

**Objective:** Review and refine core methods in `envirosense/simulation_engine/ml_training/data_generator.py` (specifically `generate_training_dataset`, `generate_balanced_dataset`, `generate_temporal_sequences`, `generate_edge_cases`) to ensure their internal data sample structure (the list of Python dicts referred to as `raw_sample`) directly maps to the fields defined in `envirosense/schemas/avro/MLDataSample.avsc`.

---

## Phase 1: Analysis, Verification, and Documentation

1.  **Define and Document the Internal `raw_sample` Contract:**
    *   **Objective:** Establish a clear, documented structure for the `raw_sample` Python dictionary that all `generate_*` methods in `MLDataGenerator` must produce. This internal contract is vital for consistency.
    *   **Details:** The documentation should specify the expected structure for `raw_sample['sensor_readings']` and `raw_sample['labels']`, which are populated by upstream components like `VirtualGridGuardian.generate_training_sample()` and `BaseScenario.get_ground_truth_labels()`. It should also cover how `extracted_class_label` and `sample_metadata` are handled.
    *   **Deliverable:** Internal documentation (e.g., extensive docstrings in `MLDataGenerator` or a dedicated section in a development notes file) detailing the `raw_sample` structure.

2.  **Verify `generate_training_dataset()`, `generate_balanced_dataset()`, and `generate_edge_cases()` Methods:**
    *   **Objective:** Confirm that these methods produce `raw_sample` dictionaries consistent with the defined internal contract and the needs of `MLDataSample.avsc`.
    *   **Details:**
        *   Review how `sensor_readings` and `labels` (or `scenario_and_sensor_labels`, `full_labels`) are obtained and structured.
        *   Confirm that `sensor_readings` is a map of `sensor_id` to individual sensor reading dictionaries that are expected to be Avro-compatible by the time `VirtualGridGuardian` produces them.
        *   Confirm that `labels` contains keys directly mappable to `GroundTruthLabels.avsc` fields.
        *   Note how `extracted_class_label` is populated by `generate_balanced_dataset()` and `generate_edge_cases()`.
    *   **Deliverable:** Confirmation of alignment or identification of minor discrepancies for these methods.

3.  **Analyze `generate_temporal_sequences()` Method:**
    *   **Objective:** Assess the current output structure of this method and determine the necessary changes for `MLDataSample.avsc` compatibility.
    *   **Current State:** This method currently produces a `sequence_sample` dictionary containing a list of time steps (`collected_timesteps_data`) and overall sequence information. This structure is *not* directly a single `MLDataSample`.
    *   **Deliverable:** A clear decision on how temporal sequences will be represented as `MLDataSample` records.

---

## Phase 2: Refinement and Implementation

1.  **Refactor `generate_temporal_sequences()`:**
    *   **Objective:** Modify the method to produce output that aligns with the `MLDataSample.avsc` schema, representing individual time points.
    *   **Proposed Change:** The method should be refactored to iterate through its collected time steps. For each time step, it will construct an individual `raw_sample`-like dictionary compatible with `MLDataSample.avsc`.
    *   Sequence-specific information (e.g., `sequence_id`, `sequence_label`) should be incorporated into the `sample_metadata` field of each generated `MLDataSample` record.
    *   The method will return a flat list of these `MLDataSample`-compatible dictionaries.
    *   **Deliverable:** Updated `generate_temporal_sequences()` method and corresponding unit tests.

2.  **Ensure Upstream Data Contracts (Documentation/Clarification):**
    *   **Objective:** Clearly state the data structure expectations for `sensor_readings` and `labels` that `MLDataGenerator` relies on from `VirtualGridGuardian.generate_training_sample()` and `BaseScenario.get_ground_truth_labels()`.
    *   **Action:** Add explicit comments and docstrings in `MLDataGenerator` detailing these assumed input structures. (Actual changes to `VirtualGridGuardian` or `BaseScenario` are outside ML-1 but dependencies should be noted).
    *   **Deliverable:** Enhanced comments/docstrings in `MLDataGenerator`.

3.  **Standardize Optional Field Population:**
    *   **Objective:** Ensure consistent handling of `extracted_class_label` and `sample_metadata` within all `generate_*` methods when they populate the `raw_sample`.
    *   **Action:** Review and ensure that if these fields are populated, they are done so in a consistent manner that `_export_data` can correctly process.
    *   **Deliverable:** Consistent logic for optional field population in `raw_sample`.

4.  **Review and Plan for `_validate_generated_data()` (Informational for ML-1):**
    *   **Objective:** Acknowledge the current state of data validation and its relation to future task ML-2.
    *   **Details:** The existing validation is basic. Task ML-2 involves more comprehensive validation. For ML-1, ensure the current validation doesn't hinder the primary goal of schema alignment.
    *   **Deliverable:** Notes on current validation status.

---

## Phase 3: Testing

1.  **Develop/Update Unit Tests:**
    *   **Objective:** Create robust unit tests to verify that each `generate_*` method, after its output is processed by the Avro export logic in `_export_data()`, produces valid `MLDataSample` records.
    *   **Details:**
        *   Mock `VirtualGridGuardian` and `BaseScenario` to provide controlled `sensor_readings` and `labels` data structures.
        *   For each `generate_*` method:
            *   Invoke the method to get the list of `raw_sample` dictionaries.
            *   Transform these dictionaries into the `ml_sample_record` format (as done in `_export_data`).
            *   Use `fastavro.validate` (or serialize then deserialize and compare) against the `MLDataSample.avsc` schema and its dependent schemas (`SensorReadingsMap.avsc`, `GroundTruthLabels.avsc`).
            *   Assert that the content of the validated Avro records is as expected.
    *   **Deliverable:** Comprehensive unit tests for all core `MLDataGenerator` methods focusing on Avro schema compliance.

---

## Plan Overview Diagram

```mermaid
graph TD
    A[Task ML-1: Finalize MLDataGenerator Core Methods] --> P1[Phase 1: Analysis & Documentation];
    P1 --> PD1[Define/Document 'raw_sample' Contract];
    P1 --> PV1[Verify generate_training_dataset];
    P1 --> PV2[Verify generate_balanced_dataset];
    P1 --> PV3[Verify generate_edge_cases];
    P1 --> PA1[Analyze generate_temporal_sequences];

    A --> P2[Phase 2: Refinement & Implementation];
    PA1 --> PR1[Refactor generate_temporal_sequences Output];
    P2 --> PR1;
    P2 --> PC1[Clarify Upstream Data Contracts in Docs];
    P2 --> PO1[Standardize Optional Field Population];
    P2 --> PV4[Review _validate_generated_data (Informational)];

    A --> P3[Phase 3: Testing];
    P3 --> PT1[Develop/Update Unit Tests];
    PT1 --> PT2[Mock Upstream Components];
    PT1 --> PT3[Test Avro Serialization & Schema Validation for each generate_* method];

    subgraph Dependencies
        direction LR
        Dep1[VirtualGridGuardian.generate_training_sample()]
        Dep2[BaseScenario.get_ground_truth_labels()]
        PD1 -.-> Dep1;
        PD1 -.-> Dep2;
    end

    subgraph OutputSchema
        direction LR
        S1[MLDataSample.avsc]
        S2[SensorReadingsMap.avsc]
        S3[GroundTruthLabels.avsc]
        PT3 -.-> S1;
        PT3 -.-> S2;
        PT3 -.-> S3;
    end

    style A fill:#c9f,stroke:#333,stroke-width:2px
    style PR1 fill:#f99,stroke:#333,stroke-width:2px