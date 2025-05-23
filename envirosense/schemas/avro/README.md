# EnviroSense Avro Schemas: Physics-Informed Design Principles

This document outlines the key principles and conventions adopted for designing the Apache Avro schemas used in the EnviroSense project, particularly for generating ML training data. The goal is to ensure data integrity, reproducibility, physical realism, and long-term maintainability.

## Core Principles

1.  **Modularity and Reusability:**
    *   Base schemas (e.g., `SensorReadingBase.avsc`) are defined for common fields and are referenced by more specific schemas. This promotes consistency and reduces redundancy.
    *   Namespaces (e.g., `com.envirosense.schema.sensor`, `com.envirosense.schema.ml`) are used to organize schemas logically.

2.  **Self-Describing Data:**
    *   Schemas aim to be as self-describing as possible.
    *   Explicit fields for dimensions (e.g., `image_height_pixels`, `image_width_pixels` in `ThermalReading.avsc`) are included even if a primary target hardware exists.
    *   The `doc` attribute for every field, record, and enum is mandatory and should clearly explain the field's purpose, expected units, and any important context.

3.  **Physics-Informed and Unit-Aware:**
    *   **Units:** All physical quantities must have their units clearly specified in the `doc` attribute (e.g., "degrees Celsius", "micrograms per cubic meter (µg/m³)", "ppb").
    *   **Data Types:** Appropriate Avro primitive types (`float`, `double`, `int`, `long`, `string`, `boolean`, `bytes`) are chosen based on the nature and precision requirements of the data.
    *   **Logical Types:** Standard Avro logical types are used where applicable (e.g., `timestamp-millis` for time, `uuid` for unique identifiers).
    *   **Plausible Ranges:** While Avro schemas do not enforce value ranges directly (e.g., temperature > absolute zero), the `doc` attributes may note expected or typical ranges. Comprehensive validation of physical plausibility is intended to be handled by a separate data validation layer external to Avro.

4.  **Handling Optionality and Defaults:**
    *   Fields that may not always be present are defined as a union with `null` (e.g., `["null", "float"]`).
    *   A `default: null` is typically provided for such optional fields. For optional arrays or maps, `default: []` or `default: {}` is used respectively.

5.  **Representing Complex Data:**
    *   **Arrays and Maps:** Used for lists of items or key-value pairs.
    *   **Nested Records:** Used to structure complex data logically (e.g., `FrequencyBin` within `EMFReading.avsc`).
    *   **Unions for Polymorphism:** Map values or fields that can hold different types of records use Avro unions (e.g., the `values` in `SensorReadingsMap.avsc`).
    *   **JSON Strings for Ultimate Flexibility:** For highly variable or scenario-specific structures (e.g., `specific_params_json` in `ScenarioDefinition.avsc`, `value_json` in `SensorGroundTruthValue`), a JSON string is used. The consuming application is responsible for parsing this JSON based on context (e.g., `scenario_class_name` or `value_type`).

6.  **ML Data Readiness:**
    *   **Raw vs. Derived Data:** Schemas generally aim to capture data at a level of detail suitable for ML models to learn features, while also allowing for the inclusion of pre-calculated derived values (e.g., `derived_max_temp_celsius` in `ThermalReading.avsc`) that might be useful for direct telemetry or simpler models.
    *   **Ground Truth:** `GroundTruthLabels.avsc` is designed to be comprehensive, covering event types, anomaly status, severity, and allowing for flexible scenario-specific and sensor-specific ground truth.
    *   **Quality and Confidence:** Fields like `reading_quality_score` and `reading_confidence` are included to provide insights into the reliability of sensor readings.
    *   **Status Flags:** `status_flags` (both general in `SensorReadingBase.avsc` and specific in sensor schemas) provide operational context about the sensor's state during data capture.

7.  **Versioning and Evolution:**
    *   Schema evolution will follow Avro's compatibility rules (backward and forward compatibility where possible).
    *   The `ScenarioRunPackage.avsc` includes a `data_schema_versions` map to track the versions of key schemas used for a particular dataset.
    *   Individual schemas (like `ScenarioDefinition.avsc`) may also contain their own `version` field.

## Specific Conventions Examples

*   **Timestamps:** Always UTC, typically `{"type": "long", "logicalType": "timestamp-millis"}`.
*   **Identifiers:** Often `string`, with `{"logicalType": "uuid"}` where appropriate.
*   **Enumerations:** Used for fixed sets of values (e.g., `ThermalCameraModel`, `ScenarioComplexityLevel`). Enum symbols are typically uppercase with underscores.
*   **Sensor Models/Types:** Specific sensor schemas include an enum for the particular model (e.g., `thermal_sensor_type_specific` in `ThermalReading.avsc`) to complement the `sensor_type_general` string in `SensorReadingBase.avsc`.

## Initial Review Status

The core schemas (`SensorReadingBase.avsc`, `ThermalReading.avsc`, `VOCReading.avsc`, `EMFReading.avsc`, `AcousticReading.avsc`, `ParticulateMatterReading.avsc`, `SensorReadingsMap.avsc`, `GroundTruthLabels.avsc`, `MLDataSample.avsc`, `ScenarioDefinition.avsc`, `ScenarioRunPackage.avsc`) have been drafted as of 2025-05-22. These drafts were developed through an iterative process incorporating feedback and information from project documentation including:
    *   `digital-twin-sensor-array-development-plan.md`
    *   Hardware Bill of Materials (`docs/Manufacturing/MainBoard/grid-guardian-bom-complete.md`)
    *   Schematic Design Guide (`docs/Manufacturing/MainBoard/grid-guardian-schematic-guide.md`)
    *   Firmware & Software Technical Specification (`docs/grid-guardian-firmware-software-spec.md`)

Further review by the broader team is anticipated as part of the ongoing development process.