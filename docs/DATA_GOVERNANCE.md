# EnviroSense™ Data Governance

## 1. Introduction

This document outlines the data governance policies and strategies for the EnviroSense™ project. Effective data governance is crucial for ensuring data quality, consistency, traceability, and security, particularly as the project scales and integrates with Machine Learning Operations (MLOps) pipelines.

This document covers:
- Avro schema management and versioning.
- Dataset versioning strategies.
- Integration with MLOps for experiment tracking.
- Initial data validation rules.
- Data security and privacy considerations.

## 2. Avro Schema Management

Robust schema management is foundational for data integrity and interoperability.

### 2.1. Schema Versioning Policy

-   **Versioning Standard:** Avro schemas will adhere to Semantic Versioning (SemVer) `MAJOR.MINOR.PATCH`.
    -   `MAJOR` version increment for incompatible schema changes (e.g., removing a field, changing a field's type incompatibly).
    -   `MINOR` version increment for backward-compatible additions (e.g., adding a new optional field, adding a new field with a default value).
    -   `PATCH` version increment for backward-compatible bug fixes or documentation changes within the schema definition itself (e.g., correcting a comment, clarifying a field description).
-   **Evolution Guidelines:**
    -   Backward compatibility is highly preferred to minimize disruption to downstream consumers.
    -   Adding new fields: New fields should ideally be optional or have a default value to maintain backward compatibility.
    -   Removing fields: Removing fields is a `MAJOR` (breaking) change. Consider deprecating fields before removal.
    -   Renaming fields: This is a `MAJOR` (breaking) change. It's often better to add a new field with the new name and deprecate the old one.
    -   Changing field types: If the change is not implicitly compatible (e.g., `int` to `long` is okay, `int` to `string` is not), it's a `MAJOR` change.
-   **Canonical Location:** Master Avro schema definitions (`.avsc` files) are located in the `envirosense/schemas/avro/` directory within the project repository.

### 2.2. Schema Registry (Conceptual Future Enhancement)

While not implemented initially, a Schema Registry (e.g., Confluent Schema Registry, Apicurio Registry) is a planned future enhancement.
-   **Role:** A centralized service for storing, versioning, and managing Avro schemas.
-   **Benefits:**
    -   Enforces schema compatibility rules.
    -   Provides a single source of truth for schemas.
    -   Facilitates schema discovery and sharing across services.
    -   Can prevent producers from sending data that consumers cannot read.

## 3. Dataset Versioning

Clear dataset versioning is essential for reproducibility in ML experiments and data analysis.

### 3.1. Dataset Versioning Strategy

-   **Method:** Datasets generated for ML or other analytical purposes will be versioned using a combination of:
    1.  **Timestamp:** An ISO 8601 timestamp (e.g., `YYYYMMDDTHHMMSSZ`) indicating when the dataset generation process was initiated.
    2.  **Content Hash (Optional but Recommended):** A hash (e.g., SHA-256) of the dataset's content or a manifest file listing its contents can provide a unique fingerprint. Tools like DVC (Data Version Control) can manage this.
    3.  **Descriptive Tag/Name:** A human-readable tag or name indicating the purpose or key characteristics of the dataset (e.g., `emf_anomaly_training_v1.2_balanced`).
-   **Naming Convention (Example):** `[Purpose]_[SourceInfo]_[Timestamp]_[OptionalHashShort]_[VersionTag].avro` or a directory structure like `datasets/[Purpose]/[VersionTag]/[Timestamp]/data.avro`.
-   **Storage:** Versioned datasets will initially be stored in a designated directory structure within the project (e.g., `envirosense/data/versioned_datasets/`). For larger scale, cloud storage solutions (e.g., S3, Azure Blob Storage) with DVC or Git LFS integration will be considered.

### 3.2. Linking Datasets to Schemas

Each versioned dataset must be unambiguously linked to the Avro schema version(s) used for its generation and validation.
-   **Mechanism:**
    -   Embed the full Avro schema (as JSON string) or at least the schema's unique identifier (e.g., name and version, or a fingerprint/hash of the schema definition) within the metadata of the dataset file or a companion metadata file.
    -   For Avro container files, the schema is typically embedded within the file itself. Ensure this embedded schema accurately reflects the version used.
    -   When using tools like DVC, schema file versions can be tracked as dependencies of the dataset.

## 4. MLOps Integration: Experiment Tracking

Integrating data versioning with MLOps practices ensures reproducibility and auditability of ML experiments.

### 4.1. Logging Requirements

For each ML experiment, the following information must be logged:
-   **Dataset(s) Used:**
    -   Unique identifier or version of each dataset (e.g., path to DVC-tracked data, dataset version tag).
-   **Avro Schema Version(s):**
    -   The specific version(s) of Avro schemas (`SensorReadingBase.avsc`, `MLDataSample.avsc`, etc.) that define the structure of the input data.
-   **Source Code Version:**
    -   Git commit hash of the training scripts, model definitions, and data processing code.
-   **Model Configuration:**
    -   Parameters, hyperparameters, and architecture of the model.
-   **Environment Configuration:**
    -   Key library versions (e.g., Python, scikit-learn, TensorFlow/PyTorch).
    -   Hardware used (if relevant, e.g., GPU type).
-   **Evaluation Metrics:**
    -   All relevant performance metrics (e.g., accuracy, precision, recall, F1-score, AUC, loss).
-   **Experiment Artifacts:**
    -   Path to the trained model, visualizations, and any other output files.

### 4.2. Tooling Considerations (Conceptual)

-   MLflow is a strong candidate for experiment tracking, model registry, and MLOps lifecycle management.
-   DVC can be used for data and model versioning, and pipeline management, integrating well with Git.
-   Other tools like Kubeflow Pipelines, Weights & Biases, or Neptune can also be considered based on evolving needs.

### 4.3. Traceability

The primary goal is to achieve end-to-end traceability:
-   From a deployed model back to the specific experiment that produced it.
-   From an experiment back to the exact dataset versions, schema versions, code, and configurations used.

## 5. Data Validation

Data validation ensures the quality, correctness, and usability of data fed into ML models and analytical processes.

### 5.1. Introduction to Data Validation

-   **Importance:** High-quality data is paramount for reliable ML models. Validation helps identify and mitigate issues early.
-   **Types of Validation:**
    -   **Syntactic Validation:** Checks if data conforms to the expected format and structure (e.g., schema compliance).
    -   **Semantic Validation:** Checks if data values are meaningful and correct within their context (e.g., range checks, consistency checks).
    -   **Physics-Informed Validation:** Leverages domain knowledge (physical laws, expected sensor behavior) to validate data plausibility.

### 5.2. Preliminary Physics-Informed Validation Rules (Conceptual)

These are initial conceptual rules. Specific thresholds and ranges will need refinement based on sensor specifications and domain expertise. These rules would ideally be applied to data corresponding to the following schemas:
-   [`AcousticReading.avsc`](../envirosense/schemas/avro/AcousticReading.avsc)
-   [`EMFReading.avsc`](../envirosense/schemas/avro/EMFReading.avsc)
-   [`GroundTruthLabels.avsc`](../envirosense/schemas/avro/GroundTruthLabels.avsc)
-   [`MLDataSample.avsc`](../envirosense/schemas/avro/MLDataSample.avsc)
-   [`ParticulateMatterReading.avsc`](../envirosense/schemas/avro/ParticulateMatterReading.avsc)
-   [`SensorReadingBase.avsc`](../envirosense/schemas/avro/SensorReadingBase.avsc) (as common fields are inherited)
-   [`SensorReadingsMap.avsc`](../envirosense/schemas/avro/SensorReadingsMap.avsc) (as it contains other readings)
-   [`ThermalReading.avsc`](../envirosense/schemas/avro/ThermalReading.avsc)
-   [`VOCReading.avsc`](../envirosense/schemas/avro/VOCReading.avsc)

**General Rules (applicable to `SensorReadingBase` and thus most readings):**
-   `timestamp_usec`: Must be a positive integer representing microseconds since epoch. Should be within a reasonable project timeframe (e.g., not in the distant past or future). For sequences, timestamps should generally be monotonically increasing.
-   `sensor_id`: Must be a non-empty string. Should conform to a defined ID format or be present in a registry of known sensor IDs.
-   `latitude`, `longitude`: If present, must be valid WGS84 coordinates (latitude: -90 to +90, longitude: -180 to +180).
-   `altitude_m`: If present, must be a number within a plausible range for terrestrial applications (e.g., -500m to 10000m).

**Specific Reading Rules:**
-   **`AcousticReading.avsc`:**
    -   `spl_dba`: Must be non-negative. Plausible range (e.g., 0 dBA to 194 dBA - physical limit in Earth's atmosphere).
    -   `frequency_bands_hz_spl_dba`: Keys (frequencies) should be positive. Values (SPLs) should be non-negative.
-   **`EMFReading.avsc`:**
    -   `frequency_hz`: Must be positive.
    -   `magnitude_v_m` (Electric field) / `magnitude_t` (Magnetic field): Must be non-negative.
    -   `orientation_quaternion`: Array of 4 numbers, should represent a valid unit quaternion (norm close to 1).
-   **`ParticulateMatterReading.avsc`:**
    -   `pm1_0_ug_m3`, `pm2_5_ug_m3`, `pm10_0_ug_m3`: Must be non-negative.
    -   Generally, `pm1_0 <= pm2_5 <= pm10_0` should hold.
-   **`ThermalReading.avsc`:**
    -   `temperature_c`: Must be within a physically plausible range (e.g., -273.15°C is absolute zero, upper limits based on sensor/environment). For environmental sensors, perhaps -50°C to +100°C.
-   **`VOCReading.avsc`:**
    -   `compound_id`: Must be a recognized identifier from a defined list of VOCs.
    -   `concentration_ppb`: Must be non-negative.

**`MLDataSample.avsc` Specifics:**
-   `sample_id`: Must be a unique, non-empty string.
-   `scenario_id`: Should reference a valid scenario definition.
-   `readings`: The map of sensor readings should conform to the validation rules for each respective reading type.
-   `ground_truth`: If present, `GroundTruthLabels.avsc` fields should be validated (e.g., `anomaly_type` from a predefined set).

### 5.3. Application of Validation Rules

-   **Location:**
    -   During data generation (e.g., within `MLDataGenerator._validate_generated_data()` as suggested in `interim-phase-plan.md`).
    -   Upon ingestion into a data lake or warehouse.
    -   Before model training or analysis.
-   **Tools:** Libraries like Pandera, Great Expectations, or custom validation logic can be used.
-   **Actions on Failure:**
    -   Log the validation error with details.
    -   Quarantine the invalid data for review.
    -   Alert developers or data stewards.
    -   Potentially halt a processing pipeline if data quality is critical.

## 6. Data Security and Privacy

Ensuring the security and privacy of data is paramount.

### 6.1. General Principles

-   **Least Privilege:** Users and systems should only have access to the data and operations necessary for their legitimate tasks.
-   **Defense in Depth:** Employ multiple layers of security controls.
-   **Compliance:** Adhere to relevant data protection regulations (e.g., GDPR, CCPA if applicable based on data origin and use, otherwise general best practices for sensitive information). Currently, EnviroSense data is simulated, but these principles apply if real-world data is integrated.

### 6.2. Access Control

-   **Role-Based Access Control (RBAC):** Implement RBAC for accessing datasets, schemas, and MLOps platforms.
-   **Data at Rest:** Encrypt sensitive datasets stored in databases or file systems.
-   **Data in Transit:** Use secure protocols (e.g., TLS/SSL) for data transfer.

### 6.3. Data Anonymization/Pseudonymization

-   While current simulated data does not contain PII, if future scenarios involve user data or other sensitive information, techniques such as anonymization (removing identifiers) or pseudonymization (replacing identifiers with reversible or irreversible tokens) must be evaluated and implemented.
-   Consider differential privacy techniques for aggregated analyses if PII is involved.

### 6.4. Secure Storage

-   Utilize storage solutions that offer robust security features, including encryption, access logging, and backup/recovery options.
-   Regularly review and update security configurations.

### 6.5. Data Breach Response (Conceptual)

-   Although detailed planning is premature, a conceptual framework for responding to data breaches should be considered as the system matures. This includes identification, containment, eradication, recovery, and lessons learned.

## 7. Future Considerations

This data governance plan will evolve with the EnviroSense™ project. Future enhancements may include:
-   **Automated Data Lineage Tracking:** Tools to automatically track data transformations from source to final use.
-   **Data Quality Monitoring Dashboards:** Real-time monitoring of data quality metrics.
-   **Formalized Schema Change Management:** A more rigorous process for proposing, reviewing, and approving schema changes, potentially involving a governance committee.
-   **Data Retention Policies:** Defining how long different types of data should be stored and processes for secure disposal.
-   **Ethical AI Guidelines:** As ML models are developed, establishing guidelines for fairness, bias detection, and ethical use of the generated insights.