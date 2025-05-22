"""
Database setup script for EnviroSense PostgreSQL integration.

This script:
1. Connects to PostgreSQL
2. Creates the envirosense database if it doesn't exist
3. Creates the sensor schema
4. Creates all required tables
"""

import psycopg2
import json
import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load database configuration
def load_config():
    config_path = os.path.join('config', 'database.json')
    with open(config_path, 'r') as f:
        return json.load(f)

def connect_postgres(config, database="postgres"):
    """Connect to PostgreSQL server"""
    return psycopg2.connect(
        host=config['writer_host'],
        port=config['port'],
        database=database,
        user=config['username'],
        password=config['password']
    )

def create_database(config):
    """Create the envirosense database if it doesn't exist"""
    db_name = config['database']
    
    # Connect to default postgres database to check if our database exists
    conn = connect_postgres(config)
    conn.autocommit = True
    cursor = conn.cursor()
    
    try:
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        exists = cursor.fetchone()
        
        if not exists:
            logger.info(f"Creating database '{db_name}'...")
            # Need to escape database name for SQL
            cursor.execute(f'CREATE DATABASE "{db_name}"')
            logger.info(f"Database '{db_name}' created successfully")
        else:
            logger.info(f"Database '{db_name}' already exists")
            
    except Exception as e:
        logger.error(f"Error creating database: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

def setup_schema(config):
    """Create the sensor schema and tables"""
    conn = connect_postgres(config, config['database'])
    conn.autocommit = True
    cursor = conn.cursor()
    
    try:
        # Create schema if it doesn't exist
        cursor.execute("CREATE SCHEMA IF NOT EXISTS sensor;")
        logger.info("Sensor schema created or already exists")
        
        # Create devices table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sensor.devices (
            id UUID PRIMARY KEY,
            serial_number VARCHAR(100) NOT NULL UNIQUE,
            name VARCHAR(200) NOT NULL,
            device_type VARCHAR(100) NOT NULL,
            firmware_version VARCHAR(50),
            latitude DOUBLE PRECISION,
            longitude DOUBLE PRECISION,
            installation_date TIMESTAMP WITH TIME ZONE,
            is_active BOOLEAN DEFAULT TRUE,
            last_seen TIMESTAMP WITH TIME ZONE,
            metadata JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """)
        logger.info("Devices table created or already exists")
        
        # Create parameters table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sensor.parameters (
            id UUID PRIMARY KEY,
            code VARCHAR(50) NOT NULL UNIQUE,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            unit VARCHAR(50),
            min_valid_value DOUBLE PRECISION,
            max_valid_value DOUBLE PRECISION,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """)
        logger.info("Parameters table created or already exists")
        
        # Create sensor_readings table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sensor.sensor_readings (
            id UUID PRIMARY KEY,
            device_id UUID NOT NULL REFERENCES sensor.devices(id),
            parameter_id UUID NOT NULL REFERENCES sensor.parameters(id),
            value DOUBLE PRECISION NOT NULL,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            batch_id VARCHAR(100),
            quality INTEGER,
            is_validated BOOLEAN DEFAULT FALSE,
            uncertainty DOUBLE PRECISION,
            raw_value DOUBLE PRECISION,
            additional_data JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """)
        logger.info("Sensor readings table created or already exists")
        
        # Create index on timestamp for time-series queries
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS sensor_readings_timestamp_idx 
        ON sensor.sensor_readings (device_id, parameter_id, timestamp DESC);
        """)
        
        # Create aggregated_readings table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sensor.aggregated_readings (
            id UUID PRIMARY KEY,
            device_id UUID NOT NULL REFERENCES sensor.devices(id),
            parameter_id UUID NOT NULL REFERENCES sensor.parameters(id),
            start_time TIMESTAMP WITH TIME ZONE NOT NULL,
            end_time TIMESTAMP WITH TIME ZONE NOT NULL,
            interval_minutes INTEGER NOT NULL,
            min_value DOUBLE PRECISION NOT NULL,
            max_value DOUBLE PRECISION NOT NULL,
            avg_value DOUBLE PRECISION NOT NULL,
            median_value DOUBLE PRECISION,
            std_deviation DOUBLE PRECISION,
            count INTEGER NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """)
        logger.info("Aggregated readings table created or already exists")
        
        # Create index on time range for aggregated data
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS aggregated_readings_timerange_idx 
        ON sensor.aggregated_readings (device_id, parameter_id, start_time, end_time);
        """)
        
        logger.info("All tables and indexes created successfully")
        
    except Exception as e:
        logger.error(f"Error setting up schema: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

def main():
    """Main entry point for database setup"""
    logger.info("Starting database setup...")
    
    config = load_config()
    create_database(config)
    setup_schema(config)
    
    logger.info("Database setup completed successfully")

if __name__ == "__main__":
    main()
