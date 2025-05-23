"""
EnviroSense Database Schema Setup

This script sets up the PostgreSQL database schema structure for the EnviroSense system.
It creates the following schemas:
- core: Core platform tables (users, permissions, configuration)
- simulation: Tables for simulation engine data
- sensor: Real and simulated sensor data
- guardian: Grid Guardian specific tables
- analysis: Analysis results and insights

Run this after creating the database with create_db.py
"""

import psycopg2
import json
import os
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def load_config():
    """Load database configuration from config file"""
    config_path = os.path.join('config', 'database.json')
    with open(config_path, 'r') as f:
        return json.load(f)

def create_schemas(cursor):
    """Create the database schemas"""
    schemas = ['core', 'simulation', 'sensor', 'guardian', 'analysis']
    
    for schema in schemas:
        try:
            cursor.execute(f'CREATE SCHEMA IF NOT EXISTS {schema}')
            print(f"Schema '{schema}' created or already exists")
        except Exception as e:
            print(f"Error creating schema '{schema}': {e}")

def create_core_schema_tables(cursor):
    """Create tables in the core schema"""
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS core.users (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        username VARCHAR(64) NOT NULL UNIQUE,
        email VARCHAR(255) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        first_name VARCHAR(64),
        last_name VARCHAR(64),
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        last_login TIMESTAMP WITH TIME ZONE
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS core.roles (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(64) NOT NULL UNIQUE,
        description TEXT,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS core.permissions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(64) NOT NULL UNIQUE,
        code VARCHAR(64) NOT NULL UNIQUE,
        description TEXT,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS core.role_permissions (
        role_id UUID NOT NULL REFERENCES core.roles(id) ON DELETE CASCADE,
        permission_id UUID NOT NULL REFERENCES core.permissions(id) ON DELETE CASCADE,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        PRIMARY KEY (role_id, permission_id)
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS core.user_roles (
        user_id UUID NOT NULL REFERENCES core.users(id) ON DELETE CASCADE,
        role_id UUID NOT NULL REFERENCES core.roles(id) ON DELETE CASCADE,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        PRIMARY KEY (user_id, role_id)
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS core.system_configuration (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        key VARCHAR(255) NOT NULL UNIQUE,
        value JSONB NOT NULL,
        description TEXT,
        is_editable BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS core.audit_logs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID REFERENCES core.users(id) ON DELETE SET NULL,
        action VARCHAR(64) NOT NULL,
        entity_type VARCHAR(64) NOT NULL,
        entity_id VARCHAR(64),
        details JSONB,
        ip_address VARCHAR(45),
        user_agent TEXT,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )
    """)
    
    print("Core schema tables created successfully")

def create_sensor_schema_tables(cursor):
    """Create tables in the sensor schema"""
    # Create extension for UUID support if it doesn't exist
    cursor.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sensor.devices (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        serial_number VARCHAR(64) NOT NULL UNIQUE,
        name VARCHAR(255),
        device_type VARCHAR(64) NOT NULL,
        firmware_version VARCHAR(32),
        location_name VARCHAR(255),
        latitude DOUBLE PRECISION,
        longitude DOUBLE PRECISION,
        elevation DOUBLE PRECISION,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        last_seen TIMESTAMP WITH TIME ZONE,
        metadata JSONB,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sensor.parameters (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(255) NOT NULL UNIQUE,
        code VARCHAR(64) NOT NULL UNIQUE,
        description TEXT,
        unit VARCHAR(32),
        min_valid_value DOUBLE PRECISION,
        max_valid_value DOUBLE PRECISION,
        precision DOUBLE PRECISION,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sensor.sensor_readings (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        device_id UUID NOT NULL REFERENCES sensor.devices(id) ON DELETE CASCADE,
        parameter_id UUID NOT NULL REFERENCES sensor.parameters(id),
        timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        value DOUBLE PRECISION NOT NULL,
        raw_value DOUBLE PRECISION,
        quality INTEGER,
        is_validated BOOLEAN NOT NULL DEFAULT FALSE,
        uncertainty DOUBLE PRECISION,
        batch_id VARCHAR(64),
        additional_data JSONB,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sensor.aggregated_readings (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        device_id UUID NOT NULL REFERENCES sensor.devices(id) ON DELETE CASCADE,
        parameter_id UUID NOT NULL REFERENCES sensor.parameters(id),
        start_time TIMESTAMP WITH TIME ZONE NOT NULL,
        end_time TIMESTAMP WITH TIME ZONE NOT NULL,
        interval_minutes INTEGER NOT NULL,
        min_value DOUBLE PRECISION,
        max_value DOUBLE PRECISION,
        avg_value DOUBLE PRECISION,
        median_value DOUBLE PRECISION,
        std_deviation DOUBLE PRECISION,
        count INTEGER NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sensor.data_quality_metrics (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        device_id UUID NOT NULL REFERENCES sensor.devices(id) ON DELETE CASCADE,
        parameter_id UUID REFERENCES sensor.parameters(id),
        metric_type VARCHAR(64) NOT NULL,
        start_time TIMESTAMP WITH TIME ZONE NOT NULL,
        end_time TIMESTAMP WITH TIME ZONE NOT NULL,
        score DOUBLE PRECISION NOT NULL,
        details JSONB,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )
    """)
    
    # Create indexes for sensor readings
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_readings_device_param_time 
    ON sensor.sensor_readings (device_id, parameter_id, timestamp)
    """)
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_readings_time_range 
    ON sensor.sensor_readings (timestamp)
    """)
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_devices_type_active 
    ON sensor.devices (device_type, is_active)
    """)
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_devices_location 
    ON sensor.devices (latitude, longitude)
    """)
    
    print("Sensor schema tables created successfully")

def create_simulation_schema_tables(cursor):
    """Create tables in the simulation schema"""
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS simulation.sensitivity_profiles (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(255) NOT NULL,
        profile_type VARCHAR(64) NOT NULL,
        description TEXT,
        demographic_factors JSONB,
        genetic_factors JSONB,
        health_status JSONB,
        sensitivity_data JSONB NOT NULL,
        version VARCHAR(32) NOT NULL,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS simulation.exposure_histories (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        profile_id UUID REFERENCES simulation.sensitivity_profiles(id) ON DELETE SET NULL,
        start_time TIMESTAMP WITH TIME ZONE NOT NULL,
        end_time TIMESTAMP WITH TIME ZONE NOT NULL,
        exposure_data JSONB NOT NULL,
        aggregated_metrics JSONB,
        scenario_id UUID,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS simulation.dose_response_models (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(255) NOT NULL,
        parameter_id UUID REFERENCES sensor.parameters(id),
        model_type VARCHAR(64) NOT NULL,
        description TEXT,
        model_parameters JSONB NOT NULL,
        reference_source TEXT,
        confidence_level DOUBLE PRECISION,
        valid_range JSONB,
        version VARCHAR(32) NOT NULL,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS simulation.physical_spaces (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(255) NOT NULL,
        description TEXT,
        dimensions JSONB NOT NULL,
        layout JSONB NOT NULL,
        barriers JSONB,
        hvac_configuration JSONB,
        environmental_conditions JSONB,
        version VARCHAR(32) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS simulation.chemical_sources (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(255) NOT NULL,
        description TEXT,
        parameter_id UUID REFERENCES sensor.parameters(id),
        emission_profile JSONB NOT NULL,
        spatial_configuration JSONB NOT NULL,
        temporal_pattern JSONB,
        version VARCHAR(32) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS simulation.biometric_signals (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        profile_id UUID REFERENCES simulation.sensitivity_profiles(id) ON DELETE CASCADE,
        signal_type VARCHAR(64) NOT NULL,
        start_time TIMESTAMP WITH TIME ZONE NOT NULL,
        end_time TIMESTAMP WITH TIME ZONE NOT NULL,
        sampling_rate INTEGER NOT NULL,
        signal_data JSONB NOT NULL,
        exposure_id UUID REFERENCES simulation.exposure_histories(id) ON DELETE SET NULL,
        scenario_id UUID,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS simulation.scenario_definitions (
        scenario_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        scenario_class_module TEXT,
        scenario_class_name TEXT,
        name TEXT NOT NULL,
        description TEXT,
        category TEXT,
        difficulty_level TEXT,
        expected_duration_seconds DOUBLE PRECISION,
        specific_params JSONB,
        tags TEXT[],
        version INTEGER DEFAULT 1,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_scenario_definitions_category
    ON simulation.scenario_definitions (category)
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_scenario_definitions_tags
    ON simulation.scenario_definitions USING GIN (tags)
    """)
    
    print("Simulation schema tables created successfully")

def create_analysis_schema_tables(cursor):
    """Create tables in the analysis schema"""
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS analysis.correlation_analyses (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(255) NOT NULL,
        description TEXT,
        source_type_a VARCHAR(64) NOT NULL,
        source_id_a UUID NOT NULL,
        parameter_id_a UUID REFERENCES sensor.parameters(id),
        source_type_b VARCHAR(64) NOT NULL,
        source_id_b UUID NOT NULL,
        parameter_id_b UUID REFERENCES sensor.parameters(id),
        start_time TIMESTAMP WITH TIME ZONE NOT NULL,
        end_time TIMESTAMP WITH TIME ZONE NOT NULL,
        correlation_method VARCHAR(64) NOT NULL,
        correlation_value DOUBLE PRECISION,
        significance_value DOUBLE PRECISION,
        result_details JSONB,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS analysis.time_series_alignments (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(255) NOT NULL,
        description TEXT,
        source_type_a VARCHAR(64) NOT NULL,
        source_id_a UUID NOT NULL,
        parameter_id_a UUID REFERENCES sensor.parameters(id),
        source_type_b VARCHAR(64) NOT NULL,
        source_id_b UUID NOT NULL,
        parameter_id_b UUID REFERENCES sensor.parameters(id),
        alignment_method VARCHAR(64) NOT NULL,
        alignment_parameters JSONB,
        alignment_result JSONB,
        quality_score DOUBLE PRECISION,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS analysis.delayed_response_profiles (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(255) NOT NULL,
        description TEXT,
        stimulus_parameter_id UUID REFERENCES sensor.parameters(id),
        response_type VARCHAR(64) NOT NULL,
        profile_id UUID REFERENCES simulation.sensitivity_profiles(id),
        delay_parameters JSONB NOT NULL,
        confidence_interval JSONB,
        validation_metrics JSONB,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS analysis.cumulative_effect_models (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(255) NOT NULL,
        description TEXT,
        parameter_id UUID REFERENCES sensor.parameters(id),
        profile_id UUID REFERENCES simulation.sensitivity_profiles(id),
        accumulation_function VARCHAR(64) NOT NULL,
        decay_function VARCHAR(64) NOT NULL,
        threshold_values JSONB,
        model_parameters JSONB NOT NULL,
        validation_metrics JSONB,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS analysis.thresholds (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(255) NOT NULL,
        description TEXT,
        parameter_id UUID REFERENCES sensor.parameters(id),
        threshold_type VARCHAR(64) NOT NULL,
        threshold_value DOUBLE PRECISION NOT NULL,
        confidence_interval JSONB,
        detection_method VARCHAR(64) NOT NULL,
        detection_parameters JSONB,
        validation_score DOUBLE PRECISION,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS analysis.reaction_signatures (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(255) NOT NULL,
        description TEXT,
        source_parameter_id UUID REFERENCES sensor.parameters(id),
        response_type VARCHAR(64) NOT NULL,
        signature_pattern JSONB NOT NULL,
        detection_parameters JSONB,
        confidence_score DOUBLE PRECISION,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS analysis.insights (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(255) NOT NULL,
        description TEXT NOT NULL,
        insight_type VARCHAR(64) NOT NULL,
        source_type VARCHAR(64) NOT NULL,
        source_id UUID NOT NULL,
        relevance_score DOUBLE PRECISION,
        confidence_score DOUBLE PRECISION,
        insight_data JSONB NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )
    """)
    
    print("Analysis schema tables created successfully")

def create_guardian_schema_tables(cursor):
    """Create tables in the guardian schema"""
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS guardian.device_models (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        model_number VARCHAR(64) NOT NULL UNIQUE,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        hardware_version VARCHAR(32) NOT NULL,
        specifications JSONB NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS guardian.device_calibrations (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        device_id UUID NOT NULL REFERENCES sensor.devices(id) ON DELETE CASCADE,
        parameter_id UUID REFERENCES sensor.parameters(id),
        calibration_date TIMESTAMP WITH TIME ZONE NOT NULL,
        calibration_type VARCHAR(64) NOT NULL,
        performed_by UUID REFERENCES core.users(id) ON DELETE SET NULL,
        calibration_values JSONB NOT NULL,
        reference_values JSONB,
        calibration_coefficients JSONB,
        is_valid BOOLEAN NOT NULL DEFAULT TRUE,
        notes TEXT,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS guardian.device_maintenance (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        device_id UUID NOT NULL REFERENCES sensor.devices(id) ON DELETE CASCADE,
        maintenance_date TIMESTAMP WITH TIME ZONE NOT NULL,
        maintenance_type VARCHAR(64) NOT NULL,
        performed_by UUID REFERENCES core.users(id) ON DELETE SET NULL,
        maintenance_details JSONB NOT NULL,
        is_successful BOOLEAN NOT NULL DEFAULT TRUE,
        next_maintenance_date TIMESTAMP WITH TIME ZONE,
        notes TEXT,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS guardian.device_firmware (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        model_id UUID NOT NULL REFERENCES guardian.device_models(id) ON DELETE CASCADE,
        version VARCHAR(32) NOT NULL,
        release_date TIMESTAMP WITH TIME ZONE NOT NULL,
        changelog TEXT,
        binary_url TEXT,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        UNIQUE (model_id, version)
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS guardian.device_deployments (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        device_id UUID NOT NULL REFERENCES sensor.devices(id) ON DELETE CASCADE,
        deployment_location VARCHAR(255) NOT NULL,
        deployment_date TIMESTAMP WITH TIME ZONE NOT NULL,
        deployed_by UUID REFERENCES core.users(id) ON DELETE SET NULL,
        configuration JSONB NOT NULL,
        status VARCHAR(64) NOT NULL,
        last_checked TIMESTAMP WITH TIME ZONE,
        notes TEXT,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS guardian.communication_logs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        device_id UUID NOT NULL REFERENCES sensor.devices(id) ON DELETE CASCADE,
        timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
        communication_type VARCHAR(64) NOT NULL,
        direction VARCHAR(16) NOT NULL,
        message_size INTEGER,
        status VARCHAR(64) NOT NULL,
        details JSONB,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )
    """)
    
    print("Guardian schema tables created successfully")

def main():
    """Main function to set up the database schema"""
    config = load_config()
    
    try:
        # Connect to the database
        conn = psycopg2.connect(
            host=config['writer_host'],
            port=config['port'],
            database=config['database'],
            user=config['username'],
            password=config['password']
        )
        
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Create schemas
        create_schemas(cursor)
        
        # Create tables in each schema
        create_core_schema_tables(cursor)
        create_sensor_schema_tables(cursor)
        create_simulation_schema_tables(cursor)
        create_analysis_schema_tables(cursor)
        create_guardian_schema_tables(cursor)
        
        print("Database schema setup completed successfully")
        
    except Exception as e:
        print(f"Error setting up database schema: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
