"""
Concrete implementation of the ScenarioRepositoryInterface using PostgreSQL.
"""
import psycopg2
import psycopg2.extras # For dict cursor
import json
import os
import uuid
from typing import Dict, Any, List, Optional
from copy import deepcopy # For create_scenario_variation

from .interfaces import ScenarioRepositoryInterface
# Assuming BaseScenario will be available for type hinting and instantiation
# from ..scenarios.base import BaseScenario # This will cause circular import if BaseScenario imports this
# For now, we'll use 'Any' for BaseScenario type hints in method signatures
# and handle instantiation carefully.

def load_db_config():
    """Load database configuration from config file"""
    # Adjust path relative to this file's location if necessary,
    # or use an absolute path or environment variable.
    # Assuming config is in the root directory for now.
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'config', 'database.json')
    if not os.path.exists(config_path):
        # Fallback for common project structures if the above is too specific
        config_path = os.path.join(os.getcwd(), 'config', 'database.json')

    with open(config_path, 'r') as f:
        return json.load(f)

class PostgresScenarioRepository(ScenarioRepositoryInterface):
    """
    PostgreSQL implementation of the ScenarioRepositoryInterface.
    Manages scenario definitions stored in a PostgreSQL database.
    """

    def __init__(self, db_config: Optional[Dict[str, Any]] = None):
        """
        Initializes the repository and establishes a database connection.

        Args:
            db_config: Optional dictionary with database connection parameters.
                       If None, loads from 'config/database.json'.
        """
        if db_config is None:
            self.db_config = load_db_config()
        else:
            self.db_config = db_config
        
        self.conn = None
        self._connect()

    def _connect(self):
        """Establishes a new database connection."""
        try:
            self.conn = psycopg2.connect(
                host=self.db_config['writer_host'],
                port=self.db_config['port'],
                database=self.db_config['database'],
                user=self.db_config['username'],
                password=self.db_config['password']
            )
        except psycopg2.Error as e:
            print(f"Error connecting to PostgreSQL database: {e}")
            # Consider raising a custom exception or handling more gracefully
            raise

    def _get_cursor(self, dict_cursor: bool = False):
        """
        Ensures the connection is active and returns a cursor.
        Reconnects if the connection is closed.
        """
        if self.conn is None or self.conn.closed:
            self._connect()
        
        if self.conn: # Should not be None if _connect succeeded or didn't raise
            if dict_cursor:
                return self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            return self.conn.cursor()
        else:
            # This case should ideally be prevented by _connect raising an error
            raise ConnectionError("Database connection is not available.")


    def get_scenario_by_id(self, scenario_id: str) -> Optional[Any]: # -> Optional[BaseScenario]
        """Retrieves a scenario by its unique identifier."""
        sql = """
            SELECT scenario_id, scenario_class_module, scenario_class_name, 
                   name, description, category, difficulty_level, 
                   expected_duration_seconds, specific_params, tags, version, 
                   created_at, updated_at
            FROM simulation.scenario_definitions
            WHERE scenario_id = %s;
        """
        try:
            with self._get_cursor(dict_cursor=True) as cur:
                cur.execute(sql, (uuid.UUID(scenario_id),)) # Assuming scenario_id is a UUID
                row = cur.fetchone()
                if row:
                    # Here we would ideally instantiate a BaseScenario or specific scenario class
                    # from row data. For now, returning the dict.
                    # from ..scenarios.base import BaseScenario # Delayed import
                    # return BaseScenario.from_scenario_definition_dict(dict(row))
                    return dict(row) 
            return None
        except psycopg2.Error as e:
            print(f"Error fetching scenario by ID '{scenario_id}': {e}")
            return None
        except ValueError: # Handle invalid UUID format for scenario_id
            print(f"Invalid scenario_id format: {scenario_id}")
            return None


    def save_scenario_definition(self, scenario_def: Dict[str, Any]) -> str:
        """
        Saves a scenario definition (conforming to ScenarioDefinition.avsc)
        and returns its unique identifier.
        """
        # Ensure all required fields are present or provide defaults
        # This should align with the Avro schema and DB table constraints
        
        # Generate UUID if not provided or if it's not a valid UUID
        scenario_uuid_str = scenario_def.get('scenario_id')
        try:
            if scenario_uuid_str:
                scenario_uuid = uuid.UUID(scenario_uuid_str)
            else:
                scenario_uuid = uuid.uuid4()
        except ValueError:
            scenario_uuid = uuid.uuid4()

        sql = """
            INSERT INTO simulation.scenario_definitions (
                scenario_id, scenario_class_module, scenario_class_name, name, 
                description, category, difficulty_level, expected_duration_seconds, 
                specific_params, tags, version, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
            )
            ON CONFLICT (scenario_id) DO UPDATE SET
                scenario_class_module = EXCLUDED.scenario_class_module,
                scenario_class_name = EXCLUDED.scenario_class_name,
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                category = EXCLUDED.category,
                difficulty_level = EXCLUDED.difficulty_level,
                expected_duration_seconds = EXCLUDED.expected_duration_seconds,
                specific_params = EXCLUDED.specific_params,
                tags = EXCLUDED.tags,
                version = EXCLUDED.version + 1, 
                updated_at = NOW()
            RETURNING scenario_id;
        """
        try:
            with self._get_cursor() as cur:
                cur.execute(sql, (
                    scenario_uuid,
                    scenario_def.get('scenario_class_module'),
                    scenario_def.get('scenario_class_name'),
                    scenario_def.get('name'),
                    scenario_def.get('description'),
                    scenario_def.get('category'),
                    scenario_def.get('difficulty_level'),
                    scenario_def.get('expected_duration_seconds'),
                    json.dumps(scenario_def.get('specific_params')) if scenario_def.get('specific_params') is not None else None,
                    scenario_def.get('tags'), # Assuming tags is a list of strings, matching TEXT[]
                    scenario_def.get('version', 1)
                ))
                returned_id = cur.fetchone()[0]
                self.conn.commit()
                return str(returned_id)
        except psycopg2.Error as e:
            print(f"Error saving scenario definition: {e}")
            if self.conn:
                self.conn.rollback()
            # Consider re-raising or returning a specific error indicator
            raise # Or return None / False

    # --- Placeholder implementations for other interface methods ---

    def get_scenarios_by_category(self, category: str, sensor_type: Optional[str] = None, num_to_get: int = 5) -> List[Any]:
        """Retrieves scenarios by category, optionally filtered by sensor_type (e.g., in tags)."""
        # Sensor_type filtering via tags is a simple approach. More complex filtering might involve specific_params.
        results = []
        base_sql = """
            SELECT scenario_id, scenario_class_module, scenario_class_name,
                   name, description, category, difficulty_level,
                   expected_duration_seconds, specific_params, tags, version,
                   created_at, updated_at
            FROM simulation.scenario_definitions
            WHERE category = %s
        """
        params = [category]

        if sensor_type:
            # Assuming sensor_type might be a tag like 'sensor_thermal' or 'sensor_voc'
            sensor_tag = f"sensor_{sensor_type}"
            base_sql += " AND %s = ANY(tags)"
            params.append(sensor_tag)
        
        base_sql += " ORDER BY updated_at DESC LIMIT %s;"
        params.append(num_to_get)

        try:
            with self._get_cursor(dict_cursor=True) as cur:
                cur.execute(base_sql, tuple(params))
                for row in cur.fetchall():
                    results.append(dict(row)) # Convert DictRow to dict
            return results
        except psycopg2.Error as e:
            print(f"Error fetching scenarios by category '{category}': {e}")
            return []

    def get_scenarios_by_class_label(self, class_label: str, sensor_type: Optional[str] = None, num_to_get: int = 5) -> List[Any]:
        """Retrieves scenarios known to produce a given class label (via tags), optionally filtered by sensor_type."""
        results = []
        # Assuming class_label is stored as a tag, e.g., "class_fire_precursor"
        class_label_tag = f"class_{class_label}"
        
        base_sql = """
            SELECT scenario_id, scenario_class_module, scenario_class_name,
                   name, description, category, difficulty_level,
                   expected_duration_seconds, specific_params, tags, version,
                   created_at, updated_at
            FROM simulation.scenario_definitions
            WHERE %s = ANY(tags)
        """
        params = [class_label_tag]

        if sensor_type:
            sensor_tag = f"sensor_{sensor_type}"
            base_sql += " AND %s = ANY(tags)"
            params.append(sensor_tag)
        
        base_sql += " ORDER BY updated_at DESC LIMIT %s;"
        params.append(num_to_get)
        
        try:
            with self._get_cursor(dict_cursor=True) as cur:
                cur.execute(base_sql, tuple(params))
                for row in cur.fetchall():
                    results.append(dict(row))
            return results
        except psycopg2.Error as e:
            print(f"Error fetching scenarios by class_label_tag '{class_label_tag}': {e}")
            return []

    def _deep_merge_specific_params(self, base_params: Optional[Dict], mod_params: Optional[Dict]) -> Optional[Dict]:
        """Helper to recursively merge specific_params."""
        if base_params is None:
            return deepcopy(mod_params) if mod_params is not None else None
        if mod_params is None:
            return deepcopy(base_params)

        merged = deepcopy(base_params)
        for key, value in mod_params.items():
            if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
                merged[key] = self._deep_merge_specific_params(merged[key], value)
            else:
                merged[key] = deepcopy(value) # Overwrite or add new
        return merged

    def create_scenario_variation(
        self,
        base_scenario_data: Any,
        new_id_suffix: str, # Suffix is for name, new ID will be UUID
        param_modifications: Dict[str, Any],
        sensor_context: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        if not isinstance(base_scenario_data, dict):
            if hasattr(base_scenario_data, 'to_scenario_definition_dict'):
                base_dict = base_scenario_data.to_scenario_definition_dict()
            else:
                print("Error: base_scenario_data is not a dict and has no to_scenario_definition_dict method.")
                return None
        else:
            # Ensure we are working with a copy that can be modified
            base_dict = deepcopy(base_scenario_data)

        # Apply modifications
        # Top-level modifications
        for key, value in param_modifications.items():
            if key == 'specific_params' and isinstance(value, dict):
                base_dict['specific_params'] = self._deep_merge_specific_params(
                    base_dict.get('specific_params'),
                    value
                )
            elif not key.startswith("specific_params."): # Avoid double processing if flat keys are also used
                base_dict[key] = value
        
        # Handle dot-notation modifications for specific_params (basic support)
        # This is a simplified approach. For true deep path updates, a more robust utility is needed.
        current_specific_params = base_dict.get('specific_params', {})
        if current_specific_params is None: # Ensure it's a dict if it was None
            current_specific_params = {}

        for key, value in param_modifications.items():
            if key.startswith("specific_params."):
                path_parts = key.split('.')[1:]
                temp_dict = current_specific_params
                for i, part in enumerate(path_parts):
                    if i == len(path_parts) - 1: # Last part, set the value
                        temp_dict[part] = value
                    else: # Traverse or create dict
                        temp_dict = temp_dict.setdefault(part, {})
                        if not isinstance(temp_dict, dict): # Path conflict
                            print(f"Warning: Path conflict in specific_params for key {key}. Overwriting non-dict.")
                            temp_dict = {} # Reset conflicting part
                            # Re-assign to parent if necessary (tricky without full path tracking)
                            # For simplicity, this basic dot notation might fail on deep conflicts.
                            break
        base_dict['specific_params'] = current_specific_params

        # Generate a new unique UUID for the variation
        base_dict['scenario_id'] = str(uuid.uuid4())
        base_dict['name'] = base_dict.get('name', "Untitled Scenario") + f" (Variation {new_id_suffix})"
        
        # Reset versioning and timestamps for the new variation
        base_dict.pop('version', None)
        base_dict.pop('created_at', None)
        base_dict.pop('updated_at', None)
        
        # Add sensor_context to tags if provided
        if sensor_context and sensor_context.get("sensor_type"):
            sensor_tag = f"variation_for_sensor_{sensor_context['sensor_type']}"
            if 'tags' not in base_dict or base_dict['tags'] is None:
                base_dict['tags'] = []
            if sensor_tag not in base_dict['tags']:
                 base_dict['tags'].append(sensor_tag)


        try:
            new_scenario_id = self.save_scenario_definition(base_dict)
            if new_scenario_id:
                return self.get_scenario_by_id(new_scenario_id)
            return None
        except Exception as e:
            print(f"Error creating scenario variation: {e}")
            return None

    def craft_scenario_from_features(
        self,
        features_summary: Dict[str, Any],
        base_id_suggestion: str, # Suggested part of ID/name, actual ID will be UUID
        target_class: Optional[str] = None,
        sensor_type: Optional[str] = None
    ) -> Optional[Any]:
        new_scenario_id = str(uuid.uuid4())
        name = f"Crafted Scenario for {target_class or 'target'} ({sensor_type or 'any sensor'}) - {base_id_suggestion}"
        
        tags = ["crafted_by_alm"]
        if target_class:
            tags.append(f"target_class_{target_class}")
        if sensor_type:
            tags.append(f"target_sensor_{sensor_type}")

        new_scenario_def = {
            "scenario_id": new_scenario_id,
            "name": name,
            "description": f"Auto-crafted by ALM based on features: {json.dumps(features_summary)[:200]}...",
            "category": "ACTIVE_LEARNING_CRAFTED",
            "specific_params": {
                "originating_features_summary": features_summary,
                "intended_target_class": target_class,
                "intended_sensor_type": sensor_type,
                "generation_reason": "Model weakness identified via feature analysis."
            },
            "tags": tags,
            "scenario_class_module": "envirosense.simulation_engine.scenarios.base", # Generic
            "scenario_class_name": "BaseScenario", # Generic, or a dedicated "CraftedScenario" type
        }
        try:
            saved_id = self.save_scenario_definition(new_scenario_def)
            if saved_id:
                print(f"Successfully crafted and saved scenario: {saved_id}")
                return self.get_scenario_by_id(saved_id)
            return None
        except Exception as e:
            print(f"Error crafting scenario from features: {e}")
            return None

    def get_default_exploration_scenario(
        self,
        scenario_id_suggestion: str, # Suggestion for name, actual ID will be UUID
        sensor_type: Optional[str] = None
    ) -> Optional[Any]:
        new_scenario_id = str(uuid.uuid4())
        name = f"Default Exploration ({sensor_type or 'General'}) - {scenario_id_suggestion}"
        
        tags = ["default_exploration_alm"]
        if sensor_type:
            tags.append(f"exploration_sensor_{sensor_type}")

        default_def = {
            "scenario_id": new_scenario_id,
            "name": name,
            "description": f"Default exploration scenario generated by ALM, potentially for {sensor_type}.",
            "category": "EXPLORATION",
            "specific_params": {"exploration_target_sensor_type": sensor_type, "exploration_intensity": "medium"},
            "tags": tags,
            "scenario_class_module": "envirosense.simulation_engine.scenarios.normal_scenarios", # Example
            "scenario_class_name": "DiurnalCycleScenario", # Example, make this configurable or more generic
        }
        try:
            saved_id = self.save_scenario_definition(default_def)
            if saved_id:
                print(f"Successfully created/retrieved default exploration scenario: {saved_id}")
                return self.get_scenario_by_id(saved_id)
            return None
        except Exception as e:
            print(f"Error getting/creating default exploration scenario: {e}")
            return None

    def update_scenario_definition(self, scenario_def_id: str, updates: Dict[str, Any]) -> bool:
        """
        Updates an existing scenario definition.
        'updates' is a dictionary of fields to update.
        For 'specific_params' or 'tags', this will overwrite the existing value.
        More granular updates to JSONB fields would require more complex SQL.
        """
        # Construct the SET clause dynamically
        set_clauses = []
        update_values = []

        for key, value in updates.items():
            if key == "scenario_id": # Cannot update primary key
                continue
            if key == "specific_params" and value is not None:
                set_clauses.append(f"{key} = %s")
                update_values.append(json.dumps(value))
            elif key == "tags" and isinstance(value, list): # Assuming tags is TEXT[]
                set_clauses.append(f"{key} = %s")
                update_values.append(value)
            else: # Standard fields
                set_clauses.append(f"{key} = %s")
                update_values.append(value)
        
        if not set_clauses:
            print("No valid fields to update.")
            return False

        set_clauses.append("updated_at = NOW()")
        # Increment version on update if not explicitly provided in updates
        if 'version' not in updates:
             set_clauses.append("version = version + 1")


        sql = f"""
            UPDATE simulation.scenario_definitions
            SET {', '.join(set_clauses)}
            WHERE scenario_id = %s;
        """
        update_values.append(uuid.UUID(scenario_def_id))

        try:
            with self._get_cursor() as cur:
                cur.execute(sql, tuple(update_values))
                updated_rows = cur.rowcount
                self.conn.commit()
                return updated_rows > 0
        except psycopg2.Error as e:
            print(f"Error updating scenario definition '{scenario_def_id}': {e}")
            if self.conn:
                self.conn.rollback()
            return False
        except ValueError: # Handle invalid UUID format for scenario_id
            print(f"Invalid scenario_id format for update: {scenario_def_id}")
            return False

    def close_connection(self):
        """Closes the database connection."""
        if self.conn and not self.conn.closed:
            self.conn.close()
            print("PostgresScenarioRepository connection closed.")

    def __del__(self):
        """Ensure connection is closed when the object is deleted."""
        self.close_connection()

if __name__ == '__main__':
    # Example Usage (requires a running PostgreSQL database with the schema)
    print("PostgresScenarioRepository module loaded. Example usage:")
    
    repo = None
    try:
        repo = PostgresScenarioRepository()
        print("Successfully connected to the database.")

        # Example: Save a new scenario
        new_scenario_data = {
            "scenario_class_module": "envirosense.simulation_engine.scenarios.normal_scenarios",
            "scenario_class_name": "DiurnalCycleScenario",
            "name": "Test Diurnal Cycle via Repo",
            "description": "A test scenario for diurnal cycle saved via repository.",
            "category": "NORMAL_OPERATION",
            "difficulty_level": "EASY",
            "expected_duration_seconds": 3600.0,
            "specific_params": {"time_of_day_start_hr": 6, "cycle_duration_hr": 24},
            "tags": ["test", "diurnal", "normal"]
            # scenario_id will be generated if not provided
        }
        print(f"\nAttempting to save new scenario: {new_scenario_data['name']}")
        saved_id = repo.save_scenario_definition(new_scenario_data)
        print(f"Scenario saved with ID: {saved_id}")

        # Example: Retrieve the saved scenario
        if saved_id:
            print(f"\nAttempting to retrieve scenario with ID: {saved_id}")
            retrieved_scenario = repo.get_scenario_by_id(saved_id)
            if retrieved_scenario:
                print("Retrieved scenario:")
                for key, value in retrieved_scenario.items():
                    print(f"  {key}: {value}")
            else:
                print(f"Could not retrieve scenario with ID: {saved_id}")

        # Example: Update the scenario
        if saved_id:
            updates_to_apply = {
                "description": "Updated description: This diurnal cycle now has more details.",
                "difficulty_level": "MEDIUM",
                "tags": ["test", "diurnal", "normal", "updated"],
                "specific_params": {"time_of_day_start_hr": 7, "cycle_duration_hr": 23, "intensity_factor": 1.1}
            }
            print(f"\nAttempting to update scenario ID: {saved_id}")
            success = repo.update_scenario_definition(saved_id, updates_to_apply)
            if success:
                print("Scenario updated successfully.")
                updated_scenario = repo.get_scenario_by_id(saved_id)
                if updated_scenario:
                    print("Updated scenario details:")
                    for key, value in updated_scenario.items():
                        print(f"  {key}: {value}")
            else:
                print("Scenario update failed.")
        
        # Example: Create a variation
        if retrieved_scenario: # Use the first retrieved scenario as base
            print(f"\nAttempting to create variation for scenario ID: {retrieved_scenario['scenario_id']}")
            variation_params = {
                "specific_params.time_of_day_start_hr": 5, # Example of trying to modify a nested param
                "description": "This is a variation with an earlier start."
            }
            # Note: The current create_scenario_variation is basic for param_modifications
            # It might need to be more robust for deep specific_params updates.
            # For this example, let's assume param_modifications targets top-level or simple specific_params.
            
            # Let's try a simpler modification for the example
            simple_variation_mods = {
                 "specific_params": {"time_of_day_start_hr": 5, "cycle_duration_hr": 20, "variation_specific_flag": True},
                 "difficulty_level": "HARD"
            }

            variation = repo.create_scenario_variation(
                base_scenario_data=retrieved_scenario, 
                new_id_suffix="_var001",
                param_modifications=simple_variation_mods
            )
            if variation:
                print(f"Variation created with ID: {variation['scenario_id']}")
                print("Variation details:")
                for key, value in variation.items():
                    print(f"  {key}: {value}")
            else:
                print("Failed to create variation.")


    except psycopg2.Error as db_err:
        print(f"Database operation failed: {db_err}")
    except ConnectionError as conn_err:
        print(f"Database connection failed: {conn_err}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if repo:
            repo.close_connection()