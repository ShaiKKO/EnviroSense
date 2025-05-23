import unittest
from unittest.mock import MagicMock, patch, call
import os
import datetime
import uuid
import fastavro
# fastavro.ValidationError is the correct exception for validation issues.
# No separate import is needed if we catch fastavro.ValidationError.
import json

import envirosense # Added for robust path finding
# Assuming the MLDataGenerator and related classes are in the parent directory
# Adjust imports based on actual project structure and sys.path if necessary
from envirosense.simulation_engine.ml_training.data_generator import MLDataGenerator
from envirosense.simulation_engine.scenarios.base import BaseScenario
# We will mock VirtualGridGuardian and Environment3DOrchestrator

# Define schema names for clarity (matching namespaces and names in .avsc files)
# These should align with those in data_generator.py
SRB_SCHEMA_NAME = "com.envirosense.schema.sensor.SensorReadingBase"
TR_SCHEMA_NAME = "com.envirosense.schema.sensor.ThermalReading"
VR_SCHEMA_NAME = "com.envirosense.schema.sensor.VOCReading"
EMFR_SCHEMA_NAME = "com.envirosense.schema.sensor.EMFReading"
AR_SCHEMA_NAME = "com.envirosense.schema.sensor.AcousticReading"
PMR_SCHEMA_NAME = "com.envirosense.schema.sensor.ParticulateMatterReading"
SRM_SCHEMA_NAME = "com.envirosense.schema.collection.SensorReadingsMap"
GTL_SCHEMA_NAME = "com.envirosense.schema.ml.GroundTruthLabels"
MLS_SCHEMA_NAME = "com.envirosense.schema.ml.MLDataSample"
SD_SCHEMA_NAME = "com.envirosense.schema.scenario.ScenarioDefinition"
SRP_SCHEMA_NAME = "com.envirosense.schema.scenario.ScenarioRunPackage"

# More robust way to get the schemas directory, assuming 'envirosense' is a package
try:
    SCHEMA_BASE_DIR_FOR_TESTS = os.path.join(
        os.path.dirname(envirosense.__file__), "schemas", "avro"
    )
    if not os.path.isdir(SCHEMA_BASE_DIR_FOR_TESTS): # Check if the path is valid
        raise NotADirectoryError
except (ImportError, AttributeError, NotADirectoryError):
    # Fallback if 'envirosense' package structure is not as expected or __file__ is not set
    # This might happen if tests are run in a very unusual context.
    # The original relative path logic can be a fallback here, or raise a clearer error.
    print("Warning: Could not determine schema path using envirosense package. Falling back to relative path.")
    # Fallback to original logic if needed, or make it stricter
    # For now, let's keep the original fallback as a last resort, though it's less ideal.
    _test_file_dir = os.path.dirname(__file__)
    _project_root_approx = os.path.abspath(os.path.join(_test_file_dir, "..", "..", "..", ".."))
    SCHEMA_BASE_DIR_FOR_TESTS = os.path.join(_project_root_approx, "envirosense", "schemas", "avro")
    if not os.path.isdir(SCHEMA_BASE_DIR_FOR_TESTS):
         _project_root_approx_alt = os.path.abspath(os.path.join(_test_file_dir, "..", "..", "..", "..", ".."))
         SCHEMA_BASE_DIR_FOR_TESTS = os.path.join(_project_root_approx_alt, "envirosense", "schemas", "avro")
         if not os.path.isdir(SCHEMA_BASE_DIR_FOR_TESTS):
             raise NotADirectoryError(f"Schema directory not found using robust or fallback paths. Checked: {SCHEMA_BASE_DIR_FOR_TESTS}")

class TestMLDataGenerator(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Load Avro schemas once for all tests."""
        cls.parsed_schemas = {}
        cls.schema_files = {
            SRB_SCHEMA_NAME: "SensorReadingBase.avsc",
            GTL_SCHEMA_NAME: "GroundTruthLabels.avsc",
            SD_SCHEMA_NAME: "ScenarioDefinition.avsc",
            TR_SCHEMA_NAME: "ThermalReading.avsc",
            VR_SCHEMA_NAME: "VOCReading.avsc",
            EMFR_SCHEMA_NAME: "EMFReading.avsc",
            AR_SCHEMA_NAME: "AcousticReading.avsc",
            PMR_SCHEMA_NAME: "ParticulateMatterReading.avsc",
            SRM_SCHEMA_NAME: "SensorReadingsMap.avsc",
            MLS_SCHEMA_NAME: "MLDataSample.avsc",
            SRP_SCHEMA_NAME: "ScenarioRunPackage.avsc",
        }
        # Load in dependency order
        ordered_load = [
            SRB_SCHEMA_NAME, GTL_SCHEMA_NAME, SD_SCHEMA_NAME, # Bases
            TR_SCHEMA_NAME, VR_SCHEMA_NAME, EMFR_SCHEMA_NAME, AR_SCHEMA_NAME, PMR_SCHEMA_NAME, # Specific sensors
            SRM_SCHEMA_NAME, MLS_SCHEMA_NAME, SRP_SCHEMA_NAME # Composites
        ]

        for schema_name in ordered_load:
            file_name = cls.schema_files[schema_name]
            path = os.path.join(SCHEMA_BASE_DIR_FOR_TESTS, file_name)
            try:
                with open(path, 'r') as f:
                    schema_json_def = json.load(f)
                cls.parsed_schemas[schema_name] = fastavro.parse_schema(schema_json_def, cls.parsed_schemas)
            except Exception as e:
                raise RuntimeError(f"Error loading/parsing schema {schema_name} from {path} in setUpClass: {e}")
        
        cls.ml_data_sample_schema_obj = cls.parsed_schemas.get(MLS_SCHEMA_NAME)
        if not cls.ml_data_sample_schema_obj:
            raise RuntimeError(f"Critical schema {MLS_SCHEMA_NAME} not loaded in setUpClass.")

    def setUp(self):
        """Set up for each test."""
        self.mock_grid_guardian = MagicMock()
        self.mock_env_orchestrator = MagicMock()
        self.mock_env_orchestrator.get_current_state = MagicMock(return_value={"time": 0.0}) # Simple state

        # Patch os.makedirs to prevent actual directory creation during tests.
        self.patcher_makedirs = patch('os.makedirs', MagicMock())
        self.mock_makedirs = self.patcher_makedirs.start()
        
        # Since MLDataGenerator now accepts _parsed_schemas_for_testing,
        # we don't need to patch its _load_all_schemas method anymore.
        # self.patcher_load_schemas = patch.object(MLDataGenerator, '_load_all_schemas', MagicMock())
        # self.mock_load_schemas = self.patcher_load_schemas.start()


        self.generator = MLDataGenerator(
            grid_guardian=self.mock_grid_guardian,
            environment_orchestrator=self.mock_env_orchestrator,
            schema_base_dir=SCHEMA_BASE_DIR_FOR_TESTS, # Still pass for completeness, though not used if _parsed_schemas_for_testing is provided
            _parsed_schemas_for_testing=self.parsed_schemas # Pass pre-loaded schemas
        )
        # The MLDataGenerator.__init__ will now use these directly.

    def tearDown(self):
        # if hasattr(self, 'patcher_load_schemas'): # Stop only if it was started
        #    self.patcher_load_schemas.stop()
        self.mock_makedirs.stop()

    def _create_mock_scenario(self, scenario_id="test_scenario_1", name="Test Scenario"):
        mock_scenario = MagicMock(spec=BaseScenario)
        mock_scenario.scenario_id = scenario_id
        mock_scenario.name = name
        mock_scenario.current_time_seconds = 0.0
        
        # Mock methods used by the generator
        mock_scenario.setup_environment = MagicMock()
        mock_scenario.update = MagicMock()
        mock_scenario.is_completed = MagicMock(return_value=False) # Default to not completed
        mock_scenario.get_ground_truth_labels = MagicMock(return_value={
            "event_type": "NORMAL_OPERATION",
            "is_anomaly": False
        }) # Basic labels
        return mock_scenario

    def _common_avro_validation(self, raw_samples_list):
        """
        Transforms raw_samples to Avro-compatible records and validates them.
        This mimics the relevant parts of _export_data for validation purposes.
        """
        ml_data_samples_for_avro = []
        for raw_sample in raw_samples_list:
            current_utc_ts = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)
            
            srm_readings_dict = raw_sample.get("sensor_readings", {})
            sensor_readings_map_record = {
                "map_timestamp_utc": current_utc_ts,
                "readings": srm_readings_dict 
            }

            raw_labels = raw_sample.get("labels", {})
            ground_truth_labels_record = {
                "label_timestamp_utc": current_utc_ts,
                "scenario_id": raw_sample.get("scenario_id", "unknown_scenario"),
                "event_type": raw_labels.get("event_type"),
                "event_subtype": raw_labels.get("event_subtype"),
                "is_anomaly": raw_labels.get("is_anomaly", False),
                "anomaly_severity_score": raw_labels.get("anomaly_severity_score"),
                "anomaly_tags": raw_labels.get("anomaly_tags", []),
                "scenario_specific_details": raw_labels.get("scenario_specific_details"),
                "sensor_specific_ground_truth": raw_labels.get("sensor_specific_ground_truth")
            }
            
            ml_sample_record = {
                "sample_id": str(uuid.uuid4()),
                "scenario_id": raw_sample.get("scenario_id", "unknown_scenario"),
                "scenario_timestep_seconds": raw_sample.get("timestamp_scenario_seconds", 0.0),
                "generation_timestamp_utc": current_utc_ts,
                "sensor_readings_map": sensor_readings_map_record,
                "ground_truth_labels": ground_truth_labels_record,
                "extracted_class_label": raw_sample.get("extracted_class_label"),
                "sample_metadata": raw_sample.get("sample_metadata")
            }
            # Validate each record individually
            try:
                fastavro.validate(ml_sample_record, self.ml_data_sample_schema_obj, raise_errors=True)
            except ValueError as e: # Catching ValueError as per user feedback for fastavro.validate
                self.fail(f"Avro validation failed for sample: {ml_sample_record}\nError: {e}")
            ml_data_samples_for_avro.append(ml_sample_record)
        return ml_data_samples_for_avro

    # --- Test cases for each generate_* method will go here ---

    def test_generate_training_dataset_avro_compliance(self):
        # 1. Setup Mocks
        mock_scenario = self._create_mock_scenario()
        
        # Mock VirtualGridGuardian's output
        # Ensure this output structure matches what MLDataSample.avsc expects
        # for sensor_readings (map of sensor_id to Avro-compatible sensor dicts)
        # and labels (dict mappable to GroundTruthLabels.avsc)
        mock_sensor_readings = {
            "thermal_cam_01": { # Conforms to ThermalReading.avsc (simplified)
                "sensor_id": "thermal_cam_01", "sensor_type": "THERMAL_CAMERA", 
                "timestamp_sensor_local": int(datetime.datetime.now().timestamp()*1000),
                "status_flags": [],
                "image_width": 2, "image_height": 1,
                "temperature_data_celsius": [25.0, 26.1],
                "emissivity_setting": 0.95
            }
        }
        mock_labels = {
            "event_type": "NORMAL_OPERATION", "is_anomaly": False, "anomaly_tags": []
        }
        self.mock_grid_guardian.generate_training_sample.return_value = (mock_sensor_readings, mock_labels)

        # Make scenario complete after a few steps
        scenario_steps = 0
        def mock_update_scenario(time_step, env_orchestrator):
            nonlocal scenario_steps
            mock_scenario.current_time_seconds += time_step
            scenario_steps +=1
            if scenario_steps >= 3:
                mock_scenario.is_completed.return_value = True
        mock_scenario.update = MagicMock(side_effect=mock_update_scenario)

        # 2. Call the method
        raw_samples = self.generator.generate_training_dataset(
            scenarios=[mock_scenario],
            samples_per_scenario=2, # Ask for 2, should get 2 before it completes
            output_format="list_of_dicts" # Get the raw internal list
        )
        
        # 3. Assertions
        self.assertIsInstance(raw_samples, list)
        self.assertEqual(len(raw_samples), 2) # Should generate 2 samples
        
        # Validate Avro compliance
        validated_avro_records = self._common_avro_validation(raw_samples)
        self.assertEqual(len(validated_avro_records), 2)

        # Check specific content based on mocks
        for i, sample in enumerate(raw_samples):
            self.assertEqual(sample["scenario_id"], "test_scenario_1")
            self.assertIn("sensor_readings", sample)
            self.assertEqual(sample["sensor_readings"], mock_sensor_readings)
            self.assertIn("labels", sample)
            self.assertEqual(sample["labels"], mock_labels)
            self.assertIsNone(sample.get("extracted_class_label"))
            self.assertIsNone(sample.get("sample_metadata"))
            self.assertEqual(validated_avro_records[i]["sensor_readings_map"]["readings"], mock_sensor_readings)
            # Add more specific checks for ground_truth_labels content if necessary

    def test_generate_balanced_dataset_avro_compliance(self):
        # 1. Setup Mocks
        mock_scenario_normal = self._create_mock_scenario(scenario_id="normal_op", name="Normal Scenario")
        # Ensure the anomaly scenario's get_ground_truth_labels returns labels that will trigger the anomaly path
        mock_scenario_anomaly = self._create_mock_scenario(scenario_id="anomaly_op", name="Anomaly Scenario")
        mock_scenario_anomaly.get_ground_truth_labels = MagicMock(return_value={
            "event_type": "ANOMALY", # This is what mock_gg_output_for_balanced checks
            "is_anomaly": True
        })

        # Mock VirtualGridGuardian's output
        mock_sensor_readings = {
            "voc_sensor_01": { # Conforms to VOCReading.avsc (simplified)
                "sensor_id": "voc_sensor_01", "sensor_type": "VOC_SENSOR_ARRAY",
                "timestamp_sensor_local": int(datetime.datetime.now().timestamp()*1000),
                "status_flags": [], "channel_count": 1, "voc_channel_data_ppb": [10.5]
            }
        }
        normal_labels = {"event_type": "NORMAL", "is_anomaly": False}
        anomaly_labels = {"event_type": "ANOMALY", "is_anomaly": True, "anomaly_severity_score": 0.7}
        
        # Configure mock_grid_guardian to return different labels based on scenario
        def mock_gg_output_for_balanced(env_state, scenario_labels):
            if scenario_labels["event_type"] == "ANOMALY":
                return (mock_sensor_readings, anomaly_labels)
            return (mock_sensor_readings, normal_labels)
        self.mock_grid_guardian.generate_training_sample.side_effect = mock_gg_output_for_balanced
        
        # Label extractor function
        def simple_label_extractor(labels_dict):
            return labels_dict.get("event_type", "UNKNOWN")

        # Scenario configurations for balancing
        scenarios_and_configs = [
            {"scenario": mock_scenario_normal, "target_label_key": "event_type", "target_label_value": "NORMAL", "samples_needed": 1},
            {"scenario": mock_scenario_anomaly, "target_label_key": "event_type", "target_label_value": "ANOMALY", "samples_needed": 1},
        ]

        # Make scenarios complete after a few steps
        normal_steps = 0
        def mock_update_normal_scenario(time_step, env_orchestrator):
            nonlocal normal_steps
            mock_scenario_normal.current_time_seconds += time_step
            normal_steps +=1
            if normal_steps >= 2: # Ensure it runs enough to get a sample
                mock_scenario_normal.is_completed.return_value = True
        mock_scenario_normal.update = MagicMock(side_effect=mock_update_normal_scenario)
        
        anomaly_steps = 0
        def mock_update_anomaly_scenario(time_step, env_orchestrator):
            nonlocal anomaly_steps
            mock_scenario_anomaly.current_time_seconds += time_step
            anomaly_steps +=1
            if anomaly_steps >= 2: # Ensure it runs enough to get a sample
                mock_scenario_anomaly.is_completed.return_value = True
        mock_scenario_anomaly.update = MagicMock(side_effect=mock_update_anomaly_scenario)


        # 2. Call the method
        raw_samples = self.generator.generate_balanced_dataset(
            scenarios_and_configs=scenarios_and_configs,
            label_extractor=simple_label_extractor,
            output_format="list_of_dicts",
            max_samples_per_scenario_run=1 # Ensure we get one of each
        )

        # 3. Assertions
        self.assertIsInstance(raw_samples, list)
        self.assertEqual(len(raw_samples), 2) # Should get 1 normal, 1 anomaly

        # Validate Avro compliance
        validated_avro_records = self._common_avro_validation(raw_samples)
        self.assertEqual(len(validated_avro_records), 2)

        # Check specific content
        normal_sample_found = False
        anomaly_sample_found = False
        for i, sample in enumerate(raw_samples):
            self.assertIn("extracted_class_label", sample)
            if sample["extracted_class_label"] == "NORMAL":
                self.assertEqual(sample["labels"], normal_labels)
                normal_sample_found = True
            elif sample["extracted_class_label"] == "ANOMALY":
                self.assertEqual(sample["labels"], anomaly_labels)
                anomaly_sample_found = True
            
            self.assertIsNone(sample.get("sample_metadata")) # Not populated by this method
            self.assertEqual(validated_avro_records[i]["extracted_class_label"], sample["extracted_class_label"])

        self.assertTrue(normal_sample_found, "Normal sample not found in balanced dataset")
        self.assertTrue(anomaly_sample_found, "Anomaly sample not found in balanced dataset")

    def test_generate_edge_cases_avro_compliance(self):
        # 1. Setup Mocks
        mock_base_scenario = self._create_mock_scenario(scenario_id="base_for_edge", name="Base Edge Scenario")
        # Mock the to_scenario_definition_dict and from_scenario_definition_dict for copying
        mock_base_scenario.to_scenario_definition_dict = MagicMock(return_value={
            "scenario_class_module": "test.module", "scenario_class_name": "MockScenario",
            "scenario_id": "base_for_edge", "name": "Base Edge Scenario", "category": "test",
            "difficulty_level": "EASY", "specific_params": "{}"
        })
        
        # This is a bit tricky as from_scenario_definition_dict is a classmethod on BaseScenario
        # For this test, we'll mock it on the *instance's type* if BaseScenario itself isn't directly mockable this way.
        # A more robust way might be to have a concrete mock scenario class.
        # For now, let's assume the type() approach works or we use a real instantiable (but simple) scenario.
        
        # Let's create a simple concrete scenario for testing copy mechanism
        class ConcreteMockScenario(BaseScenario):
            def __init__(self, scenario_id="default_concrete", name="Default Concrete", specific_param="default"):
                super().__init__(scenario_id, name, "test_cat", "EASY")
                self.specific_param = specific_param
                self.copied_from_dict = False

            def setup_environment(self, environment_3d_orchestrator): pass
            def update(self, time_step, environment_3d_orchestrator): self.current_time_seconds += time_step
            def get_ground_truth_labels(self, current_env_state): return {"event_type": "CONCRETE_NORMAL"}
            def is_completed(self, current_env_state): return self.current_time_seconds >= 1.0 # Completes after 1 sec
            
            def _get_specific_params(self) -> Dict[str, Any]: return {"specific_param": self.specific_param}

            @classmethod
            def _create_from_specific_params(cls, scenario_id: str, name: str, category: str, difficulty_level: str,
                                             expected_duration_seconds: Optional[float], specific_params_dict: Dict[str, Any]) -> 'BaseScenario':
                instance = cls(scenario_id, name, specific_params_dict.get("specific_param", "from_dict"))
                instance.copied_from_dict = True # Mark that it was copied
                return instance

        concrete_base_scenario = ConcreteMockScenario(scenario_id="concrete_base", name="Concrete Base")

        def simple_modification_strategy(scenario_instance):
            # This strategy modifies a parameter if the scenario is of the expected type
            if hasattr(scenario_instance, 'specific_param'):
                scenario_instance.specific_param = "modified_by_strategy"
            scenario_instance.name = scenario_instance.name + "_MODIFIED"
            return scenario_instance
        simple_modification_strategy.__name__ = "SimpleModStrategy"


        # Mock VirtualGridGuardian's output
        mock_sensor_readings = {"emf_sensor_01": {"sensor_id": "emf_sensor_01", "sensor_type": "EMF_SENSOR", "timestamp_sensor_local": int(datetime.datetime.now().timestamp()*1000), "status_flags": [], "ac_field_strength_v_per_m": 5.0}}
        mock_labels = {"event_type": "EDGE_CASE_EVENT", "is_anomaly": True}
        self.mock_grid_guardian.generate_training_sample.return_value = (mock_sensor_readings, mock_labels)

        # 2. Call the method
        raw_samples = self.generator.generate_edge_cases(
            base_scenarios=[concrete_base_scenario],
            modification_strategies=[simple_modification_strategy],
            target_count_per_strategy=1, # Expect 1 sample from the one modified scenario
            output_format="list_of_dicts",
            samples_per_modified_scenario=1 # Get 1 sample from the modified scenario
        )

        # 3. Assertions
        self.assertIsInstance(raw_samples, list)
        self.assertEqual(len(raw_samples), 1)

        # Validate Avro compliance
        validated_avro_records = self._common_avro_validation(raw_samples)
        self.assertEqual(len(validated_avro_records), 1)

        # Check specific content
        sample = raw_samples[0]
        self.assertTrue(sample["scenario_id"].startswith("concrete_base_edge_s1_b0"))
        self.assertIn("sample_metadata", sample)
        self.assertIsNotNone(sample["sample_metadata"])
        self.assertEqual(sample["sample_metadata"].get("edge_case_strategy"), "SimpleModStrategy")
        self.assertIsNone(sample.get("extracted_class_label")) # Not populated by this method
        
        # Verify the Avro record also has this metadata
        avro_sample = validated_avro_records[0]
        self.assertIn("sample_metadata", avro_sample)
        self.assertIsNotNone(avro_sample["sample_metadata"])
        self.assertEqual(avro_sample["sample_metadata"].get("edge_case_strategy"), "SimpleModStrategy")


    def test_generate_temporal_sequences_avro_compliance(self):
        # 1. Setup Mocks
        mock_scenario = self._create_mock_scenario(scenario_id="temporal_scenario")
        
        mock_sensor_readings = {"pm_sensor_01": {"sensor_id": "pm_sensor_01", "sensor_type": "PM_SENSOR", "timestamp_sensor_local": int(datetime.datetime.now().timestamp()*1000), "status_flags": [], "pm2_5_concentration_ug_m3": 12.5}}
        mock_labels = {"event_type": "TEMPORAL_EVENT", "is_anomaly": False}
        
        # Simulate VirtualGridGuardian returning slightly different data for each step if needed, or just the same
        call_count = 0
        def mock_gg_temporal_output(env_state, scenario_labels):
            nonlocal call_count
            call_count+=1
            # Example: make sensor reading change slightly over time
            current_readings = mock_sensor_readings.copy()
            current_readings["pm_sensor_01"] = current_readings["pm_sensor_01"].copy()
            current_readings["pm_sensor_01"]["pm2_5_concentration_ug_m3"] = 12.5 + call_count * 0.1
            return (current_readings, mock_labels)

        self.mock_grid_guardian.generate_training_sample.side_effect = mock_gg_temporal_output

        # Make scenario complete after enough steps to form a few sequences
        scenario_steps = 0
        total_steps_for_test = 5 # Enough for a few sequences
        def mock_update_temporal_scenario(time_step, env_orchestrator):
            nonlocal scenario_steps
            mock_scenario.current_time_seconds += time_step
            scenario_steps +=1
            if scenario_steps >= total_steps_for_test:
                mock_scenario.is_completed.return_value = True
        mock_scenario.update = MagicMock(side_effect=mock_update_temporal_scenario)

        sequence_length = 3
        overlap = 1
        expected_num_sequences = 0
        if total_steps_for_test >= sequence_length:
            expected_num_sequences = 1 + (total_steps_for_test - sequence_length) // (sequence_length - overlap)
        
        expected_total_samples = expected_num_sequences * sequence_length


        # 2. Call the method
        raw_samples = self.generator.generate_temporal_sequences(
            scenario=mock_scenario,
            sequence_length=sequence_length,
            overlap=overlap,
            output_format="list_of_dicts", # Get the flat list of raw_sample dicts
            max_total_samples=100 # Safety
        )

        # 3. Assertions
        self.assertIsInstance(raw_samples, list)
        self.assertEqual(len(raw_samples), expected_total_samples)

        # Validate Avro compliance
        validated_avro_records = self._common_avro_validation(raw_samples)
        self.assertEqual(len(validated_avro_records), expected_total_samples)

        # Check specific content for sequence metadata
        current_sequence_id = None
        current_sequence_index = 0
        for i, sample in enumerate(raw_samples):
            self.assertEqual(sample["scenario_id"], "temporal_scenario")
            self.assertIn("sample_metadata", sample)
            self.assertIsNotNone(sample["sample_metadata"])
            
            seq_id = sample["sample_metadata"].get("sequence_id")
            seq_idx = sample["sample_metadata"].get("sequence_index")
            seq_len = sample["sample_metadata"].get("sequence_total_length")

            self.assertIsNotNone(seq_id)
            self.assertIsNotNone(seq_idx)
            self.assertEqual(seq_len, sequence_length)

            if current_sequence_id is None or seq_id != current_sequence_id:
                # Start of a new sequence
                current_sequence_id = seq_id
                current_sequence_index = 0
                self.assertTrue(seq_id.startswith(f"{mock_scenario.scenario_id}_seq"))
            
            self.assertEqual(seq_idx, current_sequence_index)
            current_sequence_index += 1
            
            self.assertIsNone(sample.get("extracted_class_label")) # Not populated by this method

            # Verify Avro record also has this metadata
            avro_sample = validated_avro_records[i]
            self.assertIn("sample_metadata", avro_sample)
            self.assertIsNotNone(avro_sample["sample_metadata"])
            self.assertEqual(avro_sample["sample_metadata"].get("sequence_id"), seq_id)
            self.assertEqual(avro_sample["sample_metadata"].get("sequence_index"), seq_idx)
            self.assertEqual(avro_sample["sample_metadata"].get("sequence_total_length"), seq_len)

if __name__ == '__main__':
    unittest.main()