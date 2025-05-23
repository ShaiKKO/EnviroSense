# Plan for Concrete Interface Integration with ActiveLearningManager

**Document Version:** 1.1
**Date:** 2025-05-23
**Author:** Roo (AI Architect)
**Status:** Proposed (Updated with User Feedback)

## 1. Introduction

This document outlines the plan for integrating the `ActiveLearningManager` with concrete (non-mocked) implementations of the `ModelInterface` and `ScenarioRepositoryInterface`. This integration is a critical step (Task ML-3.1) towards a fully functional active learning loop, enabling the system to interact with real machine learning models and a persistent scenario store.

## 2. Current State

Currently, the `ActiveLearningManager` ([`envirosense/simulation_engine/ml_training/active_learning.py`](envirosense/simulation_engine/ml_training/active_learning.py:17)) is developed and unit-tested using mock implementations of `ModelInterface` and `ScenarioRepositoryInterface` (as found in [`envirosense/simulation_engine/ml_training/mock_components.py`](envirosense/simulation_engine/ml_training/mock_components.py:1)). These mocks simulate the expected behavior of the interfaces, allowing for the development and testing of the `ActiveLearningManager`'s logic in isolation.

The existing interfaces are defined in [`envirosense/simulation_engine/ml_training/interfaces.py`](envirosense/simulation_engine/ml_training/interfaces.py:1).

## 3. Objectives for Concrete Integration

The primary objectives of integrating with concrete interface implementations are:

*   **Enable End-to-End Active Learning:** Allow the `ActiveLearningManager` to drive data generation based on the performance and uncertainties of actual ML models.
*   **Persistent Scenario Management:** Store, retrieve, and manage scenario definitions in a durable and queryable backend, moving beyond in-memory mock scenarios.
*   **Realistic Model Feedback:** Obtain genuine performance metrics, uncertainty scores, and feature importance data from deployed or accessible ML models.
*   **Dynamic Scenario Adaptation:** Allow the system to create and modify scenarios that are stored and versioned in a real repository, reflecting insights from model feedback.
*   **Validate Interface Robustness:** Ensure the defined `ModelInterface` and `ScenarioRepositoryInterface` are sufficiently comprehensive and practical for real-world use cases.
*   **Facilitate MLOps Integration:** Lay the groundwork for integrating the active learning loop into a broader MLOps pipeline, including model deployment, monitoring, and retraining.
*   **Enhance System Resilience and Observability:** Implement robust error handling, monitoring, and alerting for production readiness.

## 4. ModelInterface Concrete Implementation Considerations

### 4.1. Expected Inputs and Outputs

*   **Input to `get_model_performance_feedback`:**
    *   `evaluation_dataset`: This can be either:
        *   `DatasetType`: A `List[Dict[str, Any]]` representing MLDataSample-like dictionaries.
        *   `FilePathType`: A `str` path to a dataset file (typically Avro).
    *   `model_version_tag`: An optional string to specify a particular model version.

*   **Output from `get_model_performance_feedback` (Detailed `ModelPerformanceData` Structure):**
    The returned dictionary must adhere to the structure outlined in the `active-learning-enhancement-plan.md`. Key components include `overall_metrics`, `per_class_metrics`, `sensor_specific_metrics` (Optional), `uncertain_samples` (with detailed `sample_features_summary` including feature path, raw value, importance score), and `misclassified_samples`.
    *   **Runtime Validation:** The concrete `ModelInterface` implementation should perform runtime validation (e.g., using Pydantic models) on the data it receives from the model endpoint to ensure it conforms to the expected `ModelPerformanceData` structure before returning it to the `ActiveLearningManager`.

### 4.2. Potential Challenges in Interfacing with a Real ML Model

*   **Model Serving:** Adaptability to various serving backends (REST API, direct load, etc.).
    *   **Mitigation:** Configurable backend client; initially focus on one pattern.
*   **Asynchronous Operations & Performance:** Model inference can be slow.
    *   **Mitigation:** Consider internal asynchronous handling or batching of requests for `evaluation_dataset` if it's large. Evaluate if the interface needs to evolve to `async/await`.
*   **Data Format Conversions:** Model endpoints may expect different formats than Avro `MLDataSample`.
    *   **Mitigation:** Implement transformation logic within the concrete `ModelInterface`.
*   **Error Handling and Resilience:** Network issues, model server errors.
    *   **Mitigation:** Implement robust error handling, retries, structured logging, metrics for observability, and alerts for critical failures (see Section 7.1). Implement circuit breakers or fallback mechanisms.
*   **Authentication and Authorization:** Secure access to model endpoints.
    *   **Mitigation:** Secure credential management (e.g., environment variables, secrets manager like HashiCorp Vault, AWS Secrets Manager) and least-privilege access strategies.
*   **Security:** Ensure secure communication and data handling, especially with remote model endpoints.

### 4.3. How Will Different Model Versions or Types Be Handled?

*   **Model Versioning:** Use `model_version_tag` to look up/load specific model versions via a registry or naming convention.
*   **Model Types (Architectures):** The interface is agnostic, but different types might require conditional logic or separate concrete implementations if I/O processing varies significantly.

## 5. ScenarioRepositoryInterface Concrete Implementation Considerations

### 5.1. How Will Scenarios Be Stored and Retrieved?

*   **Storage Options:**
    *   **PostgreSQL Database:** Given the existing PostgreSQL setup, this is the preferred backend. It offers efficient querying, transactional integrity, and scalability. A new table (e.g., `simulation.scenario_definitions`) will be required to store scenario data structured according to `ScenarioDefinition.avsc`.
    *   **Retrieval Mechanisms:** Translate interface methods to SQL queries against the PostgreSQL database.
        *   **Performance:** Evaluate caching strategies for frequently accessed scenario definitions if performance becomes a bottleneck. Indexing on key query fields (e.g., `scenario_id`, `category`, `tags`) will be crucial.
    *   **Runtime Validation:** The concrete `ScenarioRepositoryInterface` should perform runtime validation (e.g., using Pydantic models) on scenario definition dictionaries before saving or instantiation to ensure they conform to `ScenarioDefinition.avsc` and any additional business rules.

### 5.2. Expected Mechanisms for `create_scenario_variation` and `craft_scenario_from_features`

*   **`create_scenario_variation`:** Convert `base_scenario` object to dict, apply modifications, save, and return a new re-instantiated `BaseScenario` object.
*   **`craft_scenario_from_features`:**
    *   Analyze `features_summary` to construct a new scenario definition dictionary.
    *   **Extensibility:** Design with a pluggable or strategy pattern to allow different "crafting algorithms" (e.g., rule-based, optimization-based) to be swapped or selected based on context (e.g., `target_class`, `sensor_type`).
    *   Save and return a new `BaseScenario` object.
*   **`save_scenario_definition` and `update_scenario_definition`:** Direct interaction with the backend, ensuring schema conformance.

### 5.3. Data Consistency and Versioning for Scenario Definitions

*   **Consistency:** Enforce schema conformance (`ScenarioDefinition.avsc`) and unique `scenario_id`. Use transactions for DBs.
*   **Versioning:**
    *   **Scenario Definition Versioning:** Use Git/DVC for file systems, or a `version` field / history tables for DBs.
    *   **Schema Versioning:** Follow Avro evolution rules.
    *   **Bidirectional Linkage:** Ensure a clear mechanism to link generated `MLDataSamples` (or the `ScenarioRunPackage` they belong to) back to the specific `weak_spot_id` (from `ActiveLearningManager`) that triggered their generation. This can be achieved by including `originating_weak_spot_ids` or similar metadata in the `ScenarioRunPackage` or the scenario definition itself when modified/created by ALM.

## 6. Proposed Integration Steps/Phases

### Phase 1: Initial Stubs & Basic Concrete Implementations (Focus: PostgreSQL Scenario Repository, Local Model Loading) [IN PROGRESS]

*   **Step 1.1: Define and Create `simulation.scenario_definitions` Table in PostgreSQL:** [COMPLETED - 2025-05-23]
    *   Designed the SQL table schema for `simulation.scenario_definitions` to align with `ScenarioDefinition.avsc`. Key fields include:
        *   `scenario_id` (UUID, PRIMARY KEY)
        *   `scenario_class_module` (TEXT)
        *   `scenario_class_name` (TEXT)
        *   `name` (TEXT NOT NULL)
        *   `description` (TEXT)
        *   `category` (TEXT)
        *   `difficulty_level` (TEXT)
        *   `expected_duration_seconds` (DOUBLE PRECISION)
        *   `specific_params` (JSONB)
        *   `tags` (TEXT[])
        *   `version` (INTEGER DEFAULT 1)
        *   `created_at` (TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW())
        *   `updated_at` (TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW())
    *   Added this table definition to [`schema_setup.py`](./schema_setup.py:1).
    *   Ensured appropriate indexes are created (on `scenario_id`, `category`, `tags`).
*   **Step 1.2: Develop `PostgresScenarioRepository`:** [COMPLETED - 2025-05-23]
    *   Implemented `ScenarioRepositoryInterface` in [`envirosense/simulation_engine/ml_training/postgres_scenario_repository.py`](envirosense/simulation_engine/ml_training/postgres_scenario_repository.py:1).
    *   Used `psycopg2` for database interaction with the `simulation.scenario_definitions` table.
    *   Implemented functional versions of all interface methods, including `save_scenario_definition`, `get_scenario_by_id`, `get_scenarios_by_category`, `get_scenarios_by_class_label`, `create_scenario_variation`, `craft_scenario_from_features`, `get_default_exploration_scenario`, and `update_scenario_definition`.
*   **Step 1.3: Develop `LocalModelInterface`:** [COMPLETED - 2025-05-23]
    *   Implemented `ModelInterface` in [`envirosense/simulation_engine/ml_training/local_model_interface.py`](envirosense/simulation_engine/ml_training/local_model_interface.py:1) for models loaded from local file paths.
    *   `get_model_performance_feedback` loads the model, processes evaluation datasets (from list or Avro file path via `load_avro_data`), performs predictions, and calculates actual metrics (accuracy, F1, log-loss, classification report via `sklearn.metrics`).
    *   Populates `misclassified_samples` and a basic version of `uncertain_samples` (using least confidence from `predict_proba` if available). `sample_features_summary` includes raw features as a starting point.
*   **Step 1.4: Initial Integration with `ActiveLearningManager`:** [PENDING]
    *   Update `ActiveLearningManager` instantiation to use these new concrete implementations (`PostgresScenarioRepository`, `LocalModelInterface`).
    *   Perform basic end-to-end tests:
        *   ALM identifies a (mocked or simple) weak spot.
        *   ALM requests scenario creation/variation from `PostgresScenarioRepository`.
        *   ALM requests data generation (using existing `MLDataGenerator`).
        *   ALM requests model evaluation from `LocalModelInterface` using the newly generated data.
*   **Step 1.5: Testing Strategy for Phase 1:**
    *   Unit tests for `PostgresScenarioRepository` methods (saving, loading, querying against a test DB instance).
    *   Unit tests for `LocalModelInterface` (loading a dummy model, basic evaluation, output formatting).
    *   Simple integration tests for the ALM loop with these components.
*   **Step 1.6: Documentation:** Begin drafting setup guides and examples for these initial implementations, including the new DB table schema.

### Phase 2: Enhancing Concrete Implementations (Focus: API-based Model, Richer Feedback, Mature DB Repository)

*   **Step 2.1: Develop `ApiBasedModelInterface`:**
    *   Implement `ModelInterface` to interact with a model served via a REST API (e.g., FastAPI, TF Serving).
    *   Handle data serialization/deserialization for API requests/responses.
    *   Implement proper parsing of API responses to populate `ModelPerformanceData`, including more realistic uncertainty scores and basic feature importance if the API provides it.
    *   Address authentication if required by the API.
*   **Step 2.2: Mature `PostgresScenarioRepository`:**
    *   Enhance querying capabilities (e.g., full-text search on description, advanced filtering on `specific_params` or `tags`).
    *   Implement robust versioning for scenario definitions within the table.
    *   Optimize performance for large numbers of scenarios.
*   **Step 2.3: Enhance `sample_features_summary` in `ModelInterface`:**
    *   Work with ML team to define how feature importance (e.g., SHAP, LIME) can be extracted from their models or model APIs.
    *   Update `ModelInterface` implementations to populate `sample_features_summary` with meaningful data.
*   **Step 2.4: Refine `craft_scenario_from_features` in `ScenarioRepositoryInterface`:**
    *   Based on the richer `sample_features_summary`, implement more intelligent logic for crafting new scenarios. This might involve rule-based systems or templates.
*   **Step 2.5: Testing Strategy for Phase 2:**
    *   Integration tests for `ApiBasedModelInterface` against a mock or real model API.
    *   Unit and integration tests for `PostgresScenarioRepository`.
    *   More comprehensive end-to-end tests of the ALM loop, focusing on the quality of generated scenarios and the feedback loop.
*   **Step 2.6: Documentation:** Update documentation with new implementations and advanced features.

### Phase 3: Full Integration, MLOps Alignment, and Robustness

*   **Step 3.1: Production-Harden Implementations:**
    *   Implement comprehensive error handling, structured logging, metrics, and alerting (see Section 7.1).
    *   Implement circuit breakers and graceful degradation strategies.
    *   Optimize performance and implement security best practices (secure credential management, least-privilege access).
*   **Step 3.2: Advanced Versioning and Reproducibility:** Ensure full traceability for scenarios, models, and generated data, including linkage to weak spots.
*   **Step 3.3: Integration with ML Experiment Tracking Tools:** Log ALM activities and artifacts.
*   **Step 3.4: Testing Strategy for Phase 3:** Stress tests, performance tests, end-to-end ALM cycle simulations, MLOps integration validation.
*   **Step 3.5: Finalize Comprehensive Documentation:** Include setup, configuration, troubleshooting, and concrete data examples.

## 7. Enhanced Operational Considerations (Challenges & Mitigations)

### 7.1. Error Handling, Observability, and Alerting

*   **Challenge:** Ensuring reliability and quick issue diagnosis in a complex, automated loop.
*   **Mitigation:**
    *   **Structured Logging:** Implement parsable logs (e.g., JSON) with context (e.g., `scenario_id`, `model_version_tag`, `weak_spot_id`, error codes) for all components.
    *   **Metrics:** Instrument key operations (e.g., `get_model_performance_feedback` duration/success/failure, `generate_targeted_samples` rates, scenario creation/retrieval times, number of weaknesses identified) using a system like Prometheus via OpenTelemetry.
    *   **Alerting:** Define alerts for critical failures (e.g., model evaluation failing repeatedly, scenario repository unavailable, `craft_scenario_from_features` consistently failing) and significant deviations from expected behavior.
    *   **Graceful Degradation & Circuit Breaking:** Implement mechanisms for `ActiveLearningManager` to handle temporary unavailability of downstream services (model server, scenario repository) to prevent cascading failures. Log issues and potentially skip a cycle or operate with limited functionality.

### 7.2. Other Potential Challenges & Mitigation

*   **Complexity of `ModelPerformanceData`:**
    *   **Mitigation:** Close collaboration with ML team; incremental development; clear schemas/examples.
*   **"Inverse Design" for `craft_scenario_from_features`:**
    *   **Mitigation:** Start simple; use pluggable strategies; human-in-the-loop review initially.
*   **Schema Evolution:**
    *   **Mitigation:** Use Avro evolution; clear versioning; flexible interface design.
*   **Dependency on External Teams/Services:**
    *   **Mitigation:** Clear communication/SLAs; robust mock services for testing.
*   **Performance Bottlenecks:**
    *   **Mitigation:** Optimize critical paths; consider asynchronous operations; batching; caching.

## 8. Impact on ActiveLearningManager

The `ActiveLearningManager`'s core logic should remain largely unchanged. Impacts will primarily be in configuration and potentially minor adjustments for error handling based on concrete implementation behaviors. The current interfaces appear robust for this integration.

## 9. Dependencies

*   **ML Modeling Team:** Access to models, definition of `ModelPerformanceData` extraction, consumption of generated data.
*   **Data Storage/Infrastructure Team:** Support for DB setup if chosen.
*   **MLOps Team:** Integration into CI/CD/CT pipelines and experiment tracking.
*   **`MLDataGenerator` Component.**
*   **Avro Schemas (`ScenarioDefinition.avsc`, `MLDataSample.avsc`).**

## 10. Documentation Strategy (Cross-cutting)

Comprehensive documentation is crucial and will be developed iteratively alongside the concrete implementations. This includes:

*   **Setup Guides:** For configuring and deploying each concrete `ModelInterface` and `ScenarioRepositoryInterface`.
*   **Configuration Examples:** Illustrative configs for various environments.
*   **API Documentation (for interfaces):** Clear explanation of methods, parameters, and expected return structures.
*   **Data Structure Examples:** Concrete JSON examples for `ModelPerformanceData` and `ScenarioDefinition`.
*   **Troubleshooting Guides:** Common issues and resolutions.
*   **Architectural Diagrams:** Illustrating the flow of data and control.

## 11. Next Steps

1.  Review and approve this updated integration plan.
2.  Prioritize Phase 1 implementation: Define `simulation.scenario_definitions` table, develop `PostgresScenarioRepository` and `LocalModelInterface`.
3.  Begin development, incorporating enhanced validation, logging, and initial documentation from the outset.