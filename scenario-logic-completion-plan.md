# Plan: Scenario Logic Completion

**Overall Objective:** Ensure all defined simulation scenarios are fully implemented, their parameters are compatible with `ScenarioDefinition.avsc` for serialization, and `BaseScenario` handles these parameters correctly.

**Guiding Principle for Scenario Parameters:** All scenario-specific parameters **must** be defined as Pydantic models to ensure clear structure, validation, and ease of serialization to JSON for the `specific_params` field in `ScenarioDefinition.avsc`.

---

**Key Tasks (from `digital-twin-sensor-array-development-plan.md`):**

1.  **Task SC-1: Finalize Key Scenario Implementations & Parameter Alignment [COMPLETED]**
    *   **Objective:** Review and refine `DiurnalCycleScenario`, `ArcingEventScenario`, `EarlyCombustionScenario`. Ensure their specific parameters are defined in Pydantic models and can be easily serialized to the JSON string format required by `ScenarioDefinition.avsc`.
    *   **Steps:**
        1.  For `DiurnalCycleScenario` ([`normal_scenarios.py`](envirosense/simulation_engine/scenarios/normal_scenarios.py:1)):
            *   Review existing implementation.
            *   Identify all specific parameters (e.g., temperature range, humidity variation, light intensity curve parameters).
            *   Ensure these parameters are grouped into a Pydantic model (e.g., `DiurnalCycleParams`).
            *   Update the scenario's `__init__` and logic to use these structured parameters.
        2.  For `ArcingEventScenario` ([`electrical_scenarios.py`](envirosense/simulation_engine/scenarios/electrical_scenarios.py:1)):
            *   Review existing implementation.
            *   Identify parameters (e.g., arc duration, intensity, location, affected components).
            *   Structure into a Pydantic model (e.g., `ArcingEventParams`).
            *   Update scenario logic.
        3.  For `EarlyCombustionScenario` ([`fire_scenarios.py`](envirosense/simulation_engine/scenarios/fire_scenarios.py:1)):
            *   Review existing implementation.
            *   Identify parameters (e.g., material type, ignition temperature, smoldering duration, initial VOC release profile).
            *   Structure into a Pydantic model (e.g., `EarlyCombustionParams`).
            *   Update scenario logic.
    *   **Verification:** For each scenario, test serialization of its Pydantic parameter model to a JSON string and ensure it matches the expected structure for `ScenarioDefinition.avsc`.

2.  **Task SC-2: Implement Remaining Stubbed Scenarios [COMPLETED]**
    *   **Objective:** Complete the implementation logic for all scenarios currently defined as stubs. Ensure their parameters are defined in Pydantic models and structured for JSON serialization.
    *   **General Approach for each stubbed scenario:**
        *   Define the core simulation logic within the `update()` method.
        *   Define how it `setup_environment()`.
        *   Define how it determines `get_ground_truth_labels()`.
        *   Define its completion condition in `is_completed()`.
        *   Define its specific parameters, structure them in a Pydantic model (e.g., `[ScenarioName]Params`), and ensure they are used by the scenario and can be JSON serialized.
    *   **Prioritized Sub-Tasks:**

        *   **High Priority:**
            1.  **`EquipmentOverheatScenario`** ([`electrical_scenarios.py`](envirosense/simulation_engine/scenarios/electrical_scenarios.py:1)): Implement logic. Define parameters (e.g., equipment type, load, ambient temperature, cooling failure mechanism, heat generation rate).
            2.  **`InsulationBreakdownScenario`** ([`electrical_scenarios.py`](envirosense/simulation_engine/scenarios/electrical_scenarios.py:1)): Implement logic. Define parameters (e.g., insulation material, age, environmental stressors like moisture/temperature, applied voltage, breakdown progression model).
            3.  **`CoronaDischargeScenario`** ([`electrical_scenarios.py`](envirosense/simulation_engine/scenarios/electrical_scenarios.py:1)): Implement logic. Define parameters (e.g., voltage level, conductor geometry, humidity, atmospheric pressure, signature characteristics like pulse repetition rate/amplitude).
            4.  **`CellulosePyrolysisScenario`** ([`fire_scenarios.py`](envirosense/simulation_engine/scenarios/fire_scenarios.py:1)): Implement logic. Define parameters (e.g., temperature profile, material quantity, type of cellulose, pyrolysis product yields and rates).
            5.  **`FirePrecursorComboScenario`** ([`fire_scenarios.py`](envirosense/simulation_engine/scenarios/fire_scenarios.py:1)): Implement logic to combine multiple precursor conditions (e.g., overheating + specific VOC presence). Define parameters for selecting, configuring, and timing the combined elements.

        *   **Medium Priority:**
            1.  **`WeatherEventScenario`** ([`normal_scenarios.py`](envirosense/simulation_engine/scenarios/normal_scenarios.py:1)): Implement logic for events like rain, high wind, sudden temperature drops/increases. Define parameters (e.g., event type, intensity profile over time, duration, spatial extent, impact on sensor readings like noise or direct interference).
            2.  **`SeasonalVariationScenario`** ([`normal_scenarios.py`](envirosense/simulation_engine/scenarios/normal_scenarios.py:1)): Implement logic for long-term, gradual changes in baseline environmental conditions. Define parameters (e.g., seasonal temperature/humidity/pressure curves, duration of seasons, impact on vegetation or ground conditions if relevant).

        *   **Lower Priority:**
            1.  **`LigninDecompositionScenario`** ([`fire_scenarios.py`](envirosense/simulation_engine/scenarios/fire_scenarios.py:1)): Implement logic. Define parameters (similar to cellulose, but specific to lignin decomposition pathways and products).
            2.  **`BaselineOperationScenario`** ([`normal_scenarios.py`](envirosense/simulation_engine/scenarios/normal_scenarios.py:1)):
                *   **Clarification:** This scenario should model normal operational states of specific equipment or systems that are not purely tied to diurnal environmental cycles. Examples: normal HVAC cycling patterns, periodic data transmissions from pole equipment, stable power load fluctuations. This distinguishes it from `DiurnalCycleScenario` which is primarily environmentally driven.
                *   Implement logic. Define parameters (e.g., equipment states, operational schedules, normal energy consumption patterns).

3.  **Task SC-3: Update/Verify `BaseScenario` Serialization/Deserialization Methods [COMPLETED]**
    *   **Objective:** Ensure that the `BaseScenario` methods for converting to and from a dictionary (which then gets serialized/deserialized for Avro's `ScenarioDefinition.avsc`) correctly handle the `specific_params` field as a JSON string. [Verified implicitly through successful refactoring of all scenarios to use Pydantic models, which are correctly handled by the existing `BaseScenario` serialization/deserialization logic.]
    *   **Action:** Verify method names (e.g., `to_scenario_definition_dict()`, `from_scenario_definition_dict()`, or actual names in [`BaseScenario`](envirosense/simulation_engine/scenarios/base.py:1)) and their implementation.
    *   **Steps:**
        1.  Review `BaseScenario.to_scenario_definition_dict()` (or actual equivalent):
            *   Confirm it takes the scenario-specific Pydantic parameter model, converts it to a JSON string (e.g., using `model_dump_json()`), and places it in the `specific_params` field of the output dictionary.
        2.  Review `BaseScenario.from_scenario_definition_dict()` (or actual equivalent factory/classmethod):
            *   Confirm it correctly retrieves the scenario class (based on `scenario_class_module` and `scenario_class_name`), then parses the JSON string from `specific_params` back into the appropriate Pydantic model for that specific scenario type (e.g., using `parse_raw` or `model_validate_json` on the Pydantic model).
            *   **Error Handling:** Implement robust error handling. For critical parsing errors (malformed JSON, Pydantic validation failure), raise specific custom exceptions (e.g., `ScenarioParameterError`). Log warnings for less critical issues if applicable. Avoid silent failures.
    *   **Verification:** Test round-trip serialization/deserialization for each implemented scenario type, ensuring all parameters are preserved and correctly typed.

---
## Mermaid Diagram for Scenario Logic Completion (reflecting prioritization):
```mermaid
graph TD
    Start_SC[Start Scenario Logic Completion] --> SC1{Task SC-1: Finalize Key Scenarios};
    SC1 --> SC1_Diurnal(DiurnalCycleScenario Review & Param Update);
    SC1 --> SC1_Arcing(ArcingEventScenario Review & Param Update);
    SC1 --> SC1_Combustion(EarlyCombustionScenario Review & Param Update);

    Start_SC --> SC2{Task SC-2: Implement Stubbed Scenarios - PRIORITIZED};
    
    subgraph SC2_HighPriority [High Priority]
        direction LR
        SC2_Elec_Overheat(EquipmentOverheatScenario);
        SC2_Elec_Insulation(InsulationBreakdownScenario);
        SC2_Elec_Corona(CoronaDischargeScenario);
        SC2_Fire_Cellulose(CellulosePyrolysisScenario);
        SC2_Fire_Combo(FirePrecursorComboScenario);
    end

    subgraph SC2_MediumPriority [Medium Priority]
        direction LR
        SC2_Norm_Weather(WeatherEventScenario);
        SC2_Norm_Seasonal(SeasonalVariationScenario);
    end

    subgraph SC2_LowPriority [Low Priority]
        direction LR
        SC2_Fire_Lignin(LigninDecompositionScenario);
        SC2_Norm_Baseline(BaselineOperationScenario);
    end

    SC2 --> SC2_HighPriority;
    SC2_HighPriority --> SC2_MediumPriority;
    SC2_MediumPriority --> SC2_LowPriority;

    Start_SC --> SC3{Task SC-3: Verify BaseScenario Dict Methods};
    SC3 --> SC3_ToDict(Verify to_dict with JSON params);
    SC3 --> SC3_FromDict(Verify from_dict with JSON params & Error Handling);

    SC1_Diurnal --> End_SC_Logic;
    SC1_Arcing --> End_SC_Logic;
    SC1_Combustion --> End_SC_Logic;
    SC2_LowPriority --> End_SC_Logic;
    SC3_ToDict --> End_SC_Logic;
    SC3_FromDict --> End_SC_Logic;
    End_SC_Logic[Scenario Logic Completion Done];