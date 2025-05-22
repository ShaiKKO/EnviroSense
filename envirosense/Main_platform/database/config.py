"""
Database configuration for EnviroSense Aurora PostgreSQL integration.

This module handles configuration for connecting to an Aurora PostgreSQL cluster,
supporting both environment variables and configuration files for secure credential management.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Default configuration paths
CONFIG_FILE_PATH = os.environ.get(
    "ENVIROSENSE_DB_CONFIG", 
    str(Path(__file__).parent.parent.parent.parent / "config" / "database.json")
)

# Environment variable prefix for database configuration
ENV_PREFIX = "ENVIROSENSE_DB_"


def get_aurora_config() -> Dict[str, Any]:
    """
    Get Aurora PostgreSQL configuration from environment variables or configuration file.
    
    Returns:
        Dict[str, Any]: A dictionary containing all configuration parameters needed
                        for connecting to the Aurora PostgreSQL cluster.
                        
    Priority:
    1. Environment variables
    2. Configuration file
    3. Default development settings (non-production only)
    """
    # Start with defaults that work for development
    config = {
        "writer_host": "localhost",  # Will be overridden in production
        "reader_host": "",           # Optional, falls back to writer_host if empty
        "port": 5432,
        "database": "envirosense",
        "username": "postgres",
        "password": "",              # Empty password for development only
        "pool_size": 5,
        "max_overflow": 10,
        "pool_recycle": 1800,        # Recycle connections after 30 minutes
        "connect_timeout": 10,
        "use_ssl": True,
        "application_name": "envirosense"
    }
    
    # Load from config file if exists
    config_file = Path(CONFIG_FILE_PATH)
    if config_file.exists():
        try:
            with open(config_file, "r") as f:
                file_config = json.load(f)
                config.update(file_config)
                logger.info(f"Loaded database configuration from {config_file}")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load database config file: {e}")
    
    # Override with environment variables if set
    for key in config:
        env_var = f"{ENV_PREFIX}{key.upper()}"
        if env_var in os.environ:
            # Convert types appropriately
            if isinstance(config[key], int):
                config[key] = int(os.environ[env_var])
            elif isinstance(config[key], bool):
                config[key] = os.environ[env_var].lower() in ('true', 'yes', '1')
            else:
                config[key] = os.environ[env_var]
    
    # Ensure critical config is present
    if not config["password"] and "password" not in os.environ:
        logger.warning("No database password configured. This is only acceptable for development.")
    
    return config


def get_connection_string(for_write=True) -> str:
    """
    Build a PostgreSQL connection string based on the configuration.
    
    Args:
        for_write (bool): If True, use writer endpoint, otherwise use reader endpoint

    Returns:
        str: A SQLAlchemy compatible connection string
    """
    config = get_aurora_config()
    
    # Use writer endpoint for writes, reader endpoint for reads if available
    host = config["writer_host"]
    if not for_write and config["reader_host"]:
        host = config["reader_host"]
    
    # Build connection string
    conn_str = (
        f"postgresql://{config['username']}:{config['password']}@"
        f"{host}:{config['port']}/{config['database']}"
    )
    
    logger.info(f"Generated connection string: {'postgresql://<USERNAME>:<PASSWORD>@' + host + ':' + str(config['port']) + '/' + config['database'] if config['username'] else conn_str}") # Mask credentials for logging
    return conn_str


def get_engine_kwargs() -> Dict[str, Any]:
    """
    Get SQLAlchemy engine keyword arguments optimized for Aurora PostgreSQL.
    
    Returns:
        Dict[str, Any]: Engine configuration parameters
    """
    config = get_aurora_config()
    
    connect_args = {}
    if config["use_ssl"]:
        connect_args["sslmode"] = "require"
    
    connect_args["connect_timeout"] = config["connect_timeout"]
    connect_args["application_name"] = config["application_name"]
    
    return {
        "pool_size": config["pool_size"],
        "max_overflow": config["max_overflow"],
        "pool_recycle": config["pool_recycle"],
        "connect_args": connect_args,
        "pool_pre_ping": True,  # Verifies connections before use (important for Aurora)
        "echo": False,  # Set to True for SQL query logging (development only)
    }
