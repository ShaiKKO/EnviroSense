"""
Utilities for reading and writing Apache Avro data files,
particularly for EnviroSense project schemas.
"""
from typing import List, Dict, Any, Optional
import fastavro
import os
import json

# It might be useful to have a central place to load/cache parsed schemas
# if these utilities are used frequently outside of MLDataGenerator.
# For now, we assume schemas might be passed or loaded ad-hoc.

def load_avro_data(file_path: str, schema: Optional[Any] = None) -> List[Dict[str, Any]]:
    """
    Loads records from an Avro data file.

    Args:
        file_path: Path to the Avro data file.
        schema: Optional parsed Avro schema. If not provided, fastavro will
                attempt to use the schema embedded in the file. Providing it
                can be useful for validation or if the file has no embedded schema.

    Returns:
        A list of records (dictionaries) from the Avro file.
        Returns an empty list if the file is empty or an error occurs.
    """
    records: List[Dict[str, Any]] = []
    if not os.path.exists(file_path):
        print(f"Error: Avro file not found at {file_path}")
        return records
    
    try:
        with open(file_path, 'rb') as fo:
            # The reader is an iterator
            for record in fastavro.reader(fo, reader_schema=schema):
                records.append(record)
        print(f"Successfully loaded {len(records)} records from {file_path}")
    except Exception as e:
        print(f"Error reading Avro file {file_path}: {e}")
        # Optionally, re-raise or handle more gracefully
    return records

def load_named_schema(schema_path: str, named_schemas: Optional[Dict[str, Any]] = None) -> Optional[Any]:
    """
    Loads and parses a single named Avro schema from a .avsc JSON file.

    Args:
        schema_path: Path to the .avsc file.
        named_schemas: A dictionary of already known named schemas, which can be
                       used to resolve dependencies if this schema refers to others.
                       This dictionary will be updated with the loaded schema.

    Returns:
        The parsed schema object, or None if an error occurs.
    """
    if named_schemas is None:
        named_schemas = {}
    try:
        with open(schema_path, 'r') as f:
            schema_json_def = json.load(f)
        # The name of the schema defined in the file (e.g., "com.envirosense.schema.ml.MLDataSample")
        # is implicitly used by fastavro when it's added to the named_schemas dict.
        parsed_schema = fastavro.parse_schema(schema_json_def, named_schemas)
        # To ensure it's retrievable by its full name if it's a record/enum/fixed:
        if hasattr(parsed_schema, '__fastavro_fullname__'):
             named_schemas[parsed_schema.__fastavro_fullname__] = parsed_schema
        elif isinstance(schema_json_def, dict) and 'name' in schema_json_def and 'namespace' in schema_json_def:
             full_name = f"{schema_json_def['namespace']}.{schema_json_def['name']}"
             named_schemas[full_name] = parsed_schema

        print(f"Successfully loaded and parsed schema from: {schema_path}")
        return parsed_schema
    except FileNotFoundError:
        print(f"Error: Schema file not found: {schema_path}")
    except Exception as e:
        print(f"Error loading/parsing schema from {schema_path}: {e}")
    return None

# Example usage (can be removed or moved to a test/example script):
if __name__ == '__main__':
    # This assumes you run this from the project root or adjust paths.
    # Create a dummy schema and data for testing.
    dummy_schema_path = "dummy_sensor_reading.avsc"
    dummy_data_path = "dummy_sensor_data.avro"

    dummy_schema_def = {
        "type": "record",
        "name": "DummySensorReading",
        "namespace": "com.example.dummy",
        "fields": [
            {"name": "sensor_id", "type": "string"},
            {"name": "value", "type": "double"},
            {"name": "timestamp", "type": {"type": "long", "logicalType": "timestamp-millis"}}
        ]
    }
    with open(dummy_schema_path, "w") as f:
        json.dump(dummy_schema_def, f, indent=2)

    parsed_dummy_schema = load_named_schema(dummy_schema_path)

    if parsed_dummy_schema:
        dummy_records = [
            {"sensor_id": "temp01", "value": 25.5, "timestamp": int(datetime.datetime.now().timestamp()*1000)},
            {"sensor_id": "hum01", "value": 60.1, "timestamp": int(datetime.datetime.now().timestamp()*1000 + 1000)}
        ]
        try:
            with open(dummy_data_path, "wb") as fo:
                fastavro.writer(fo, parsed_dummy_schema, dummy_records)
            print(f"Dummy Avro data written to {dummy_data_path}")

            loaded_records = load_avro_data(dummy_data_path, schema=parsed_dummy_schema)
            if loaded_records:
                print("\nLoaded records:")
                for rec in loaded_records:
                    print(rec)
        finally:
            # Clean up dummy files
            if os.path.exists(dummy_schema_path):
                os.remove(dummy_schema_path)
            if os.path.exists(dummy_data_path):
                os.remove(dummy_data_path)
    else:
        print("Could not test Avro I/O due to schema loading failure.")