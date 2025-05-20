"""
Exposure Storage Module

This module provides functionality for persisting and retrieving exposure data,
including individual exposure records and exposure histories. It supports
various storage formats (JSON, CSV) and provides utilities for organizing
exposure data based on various criteria.
"""

import os
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Union, Any
import glob
import shutil

from envirosense.core.exposure.records import (
    ExposureRecord,
    ExposureHistory
)


class ExposureStorage:
    """
    Class for managing the storage and retrieval of exposure data.
    
    This class provides methods for saving and loading exposure records and histories
    to/from disk in various formats, as well as utilities for organizing and
    managing stored exposure data.
    """
    
    def __init__(self, base_dir: str = None):
        """
        Initialize an exposure storage manager.
        
        Args:
            base_dir: The base directory for storing exposure data.
                If None, defaults to 'envirosense/output/exposure_data'.
        """
        if base_dir is None:
            # Default to a subdirectory of the project output
            self.base_dir = os.path.join("envirosense", "output", "exposure_data")
        else:
            self.base_dir = base_dir
            
        # Create directory structure if it doesn't exist
        os.makedirs(os.path.join(self.base_dir, "records"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "histories"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "assessments"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "exports"), exist_ok=True)
    
    def save_record(self, record: ExposureRecord, format: str = "json") -> str:
        """
        Save an individual exposure record.
        
        Args:
            record: The exposure record to save
            format: The storage format ('json' or 'csv')
            
        Returns:
            Path to the saved file
        """
        # Create directory for records if it doesn't exist
        records_dir = os.path.join(self.base_dir, "records")
        os.makedirs(records_dir, exist_ok=True)
        
        # Generate filename based on record ID and timestamp
        timestamp = record.datetime.strftime("%Y%m%d_%H%M%S")
        record_id = record.record_id
        
        if format.lower() == "json":
            filename = f"record_{record_id}_{timestamp}.json"
            filepath = os.path.join(records_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(record.to_dict(), f, indent=2)
                
        elif format.lower() == "csv":
            filename = f"record_{record_id}_{timestamp}.csv"
            filepath = os.path.join(records_dir, filename)
            
            # Convert to dataframe with a single row
            df = pd.DataFrame([{
                "record_id": record.record_id,
                "timestamp": record.timestamp,
                "chemical_id": record.chemical_id,
                "concentration": record.concentration,
                "duration": record.duration,
                "location_id": record.location_id,
                "coordinates_x": record.coordinates[0] if record.coordinates else None,
                "coordinates_y": record.coordinates[1] if record.coordinates else None,
                "coordinates_z": record.coordinates[2] if record.coordinates else None,
                "source_id": record.source_id,
                "sensor_id": record.sensor_id
            }])
            
            df.to_csv(filepath, index=False)
        else:
            raise ValueError(f"Unsupported format: {format}. Use 'json' or 'csv'.")
            
        return filepath
    
    def save_records(self, records: List[ExposureRecord], format: str = "json") -> str:
        """
        Save multiple exposure records to a single file.
        
        Args:
            records: List of exposure records to save
            format: The storage format ('json' or 'csv')
            
        Returns:
            Path to the saved file
        """
        if not records:
            return None
            
        # Create directory for records if it doesn't exist
        records_dir = os.path.join(self.base_dir, "records")
        os.makedirs(records_dir, exist_ok=True)
        
        # Generate filename based on current timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format.lower() == "json":
            filename = f"records_batch_{timestamp}.json"
            filepath = os.path.join(records_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump([record.to_dict() for record in records], f, indent=2)
                
        elif format.lower() == "csv":
            filename = f"records_batch_{timestamp}.csv"
            filepath = os.path.join(records_dir, filename)
            
            # Create a list of dictionaries for DataFrame
            data = []
            for record in records:
                row = {
                    "record_id": record.record_id,
                    "timestamp": record.timestamp,
                    "chemical_id": record.chemical_id,
                    "concentration": record.concentration,
                    "duration": record.duration,
                    "location_id": record.location_id,
                    "source_id": record.source_id,
                    "sensor_id": record.sensor_id
                }
                
                # Add coordinates if available
                if record.coordinates:
                    row["coordinates_x"] = record.coordinates[0]
                    row["coordinates_y"] = record.coordinates[1]
                    row["coordinates_z"] = record.coordinates[2]
                
                data.append(row)
            
            df = pd.DataFrame(data)
            df.to_csv(filepath, index=False)
        else:
            raise ValueError(f"Unsupported format: {format}. Use 'json' or 'csv'.")
            
        return filepath
    
    def save_history(self, history: ExposureHistory, format: str = "json") -> str:
        """
        Save an exposure history.
        
        Args:
            history: The exposure history to save
            format: The storage format ('json' or 'csv')
            
        Returns:
            Path to the saved file
        """
        # Create directory for histories if it doesn't exist
        histories_dir = os.path.join(self.base_dir, "histories")
        os.makedirs(histories_dir, exist_ok=True)
        
        # Generate filename based on history ID
        history_id = history.history_id
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format.lower() == "json":
            filename = f"history_{history_id}_{timestamp}.json"
            filepath = os.path.join(histories_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(history.to_dict(), f, indent=2)
                
        elif format.lower() == "csv":
            # For CSV, we'll save the records as a table
            filename = f"history_{history_id}_{timestamp}.csv"
            filepath = os.path.join(histories_dir, filename)
            
            # Convert history to DataFrame
            df = history.to_dataframe()
            
            # Add history ID as a column
            df["history_id"] = history.history_id
            
            df.to_csv(filepath, index=False)
            
            # Also save metadata in a separate JSON file
            metadata_filename = f"history_{history_id}_{timestamp}_metadata.json"
            metadata_filepath = os.path.join(histories_dir, metadata_filename)
            
            metadata = {
                "history_id": history.history_id,
                "created_at": history.created_at,
                "updated_at": history.updated_at,
                "metadata": history.metadata,
                "record_count": len(history.records)
            }
            
            with open(metadata_filepath, 'w') as f:
                json.dump(metadata, f, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}. Use 'json' or 'csv'.")
            
        return filepath
    
    def load_record(self, filepath: str) -> ExposureRecord:
        """
        Load an exposure record from a file.
        
        Args:
            filepath: Path to the file containing the record
            
        Returns:
            The loaded ExposureRecord
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
            
        if filepath.endswith(".json"):
            with open(filepath, 'r') as f:
                data = json.load(f)
                return ExposureRecord.from_dict(data)
                
        elif filepath.endswith(".csv"):
            df = pd.read_csv(filepath)
            
            if len(df) != 1:
                raise ValueError(f"Expected a single record in CSV, found {len(df)}")
                
            row = df.iloc[0].to_dict()
            
            # Convert row data to ExposureRecord format
            record_data = {
                "record_id": row.get("record_id"),
                "timestamp": row.get("timestamp"),
                "chemical_id": row.get("chemical_id"),
                "concentration": row.get("concentration"),
                "duration": row.get("duration"),
                "location_id": row.get("location_id"),
                "source_id": row.get("source_id"),
                "sensor_id": row.get("sensor_id")
            }
            
            # Add coordinates if available
            if all(k in row for k in ["coordinates_x", "coordinates_y", "coordinates_z"]):
                record_data["coordinates"] = (
                    row.get("coordinates_x"),
                    row.get("coordinates_y"),
                    row.get("coordinates_z")
                )
            
            return ExposureRecord.from_dict(record_data)
        else:
            raise ValueError(f"Unsupported file format: {filepath}")
    
    def load_records(self, filepath: str) -> List[ExposureRecord]:
        """
        Load multiple exposure records from a file.
        
        Args:
            filepath: Path to the file containing the records
            
        Returns:
            List of loaded ExposureRecord objects
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
            
        if filepath.endswith(".json"):
            with open(filepath, 'r') as f:
                data = json.load(f)
                return [ExposureRecord.from_dict(record_data) for record_data in data]
                
        elif filepath.endswith(".csv"):
            df = pd.read_csv(filepath)
            
            records = []
            for _, row in df.iterrows():
                row_dict = row.to_dict()
                
                # Convert row data to ExposureRecord format
                record_data = {
                    "record_id": row_dict.get("record_id"),
                    "timestamp": row_dict.get("timestamp"),
                    "chemical_id": row_dict.get("chemical_id"),
                    "concentration": row_dict.get("concentration"),
                    "duration": row_dict.get("duration"),
                    "location_id": row_dict.get("location_id"),
                    "source_id": row_dict.get("source_id"),
                    "sensor_id": row_dict.get("sensor_id")
                }
                
                # Add coordinates if available
                if all(k in row_dict for k in ["coordinates_x", "coordinates_y", "coordinates_z"]):
                    record_data["coordinates"] = (
                        row_dict.get("coordinates_x"),
                        row_dict.get("coordinates_y"),
                        row_dict.get("coordinates_z")
                    )
                
                records.append(ExposureRecord.from_dict(record_data))
            
            return records
        else:
            raise ValueError(f"Unsupported file format: {filepath}")
    
    def load_history(self, filepath: str) -> ExposureHistory:
        """
        Load an exposure history from a file.
        
        Args:
            filepath: Path to the file containing the history
            
        Returns:
            The loaded ExposureHistory
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
            
        if filepath.endswith(".json"):
            with open(filepath, 'r') as f:
                data = json.load(f)
                return ExposureHistory.from_dict(data)
                
        elif filepath.endswith(".csv"):
            df = pd.read_csv(filepath)
            
            # Check if we have a corresponding metadata file
            metadata_filepath = filepath.replace(".csv", "_metadata.json")
            
            if os.path.exists(metadata_filepath):
                with open(metadata_filepath, 'r') as f:
                    metadata = json.load(f)
                    history_id = metadata.get("history_id")
            else:
                # Try to extract history ID from the CSV
                if "history_id" in df.columns:
                    # All rows should have the same history_id
                    history_ids = df["history_id"].unique()
                    if len(history_ids) == 1:
                        history_id = history_ids[0]
                    else:
                        raise ValueError(f"Multiple history IDs found in CSV: {history_ids}")
                else:
                    history_id = None
            
            # Create history object
            history = ExposureHistory(history_id)
            
            # Add records from DataFrame
            for _, row in df.iterrows():
                row_dict = row.to_dict()
                
                # Convert row data to ExposureRecord format
                record_data = {
                    "record_id": row_dict.get("record_id"),
                    "timestamp": row_dict.get("timestamp"),
                    "chemical_id": row_dict.get("chemical_id"),
                    "concentration": row_dict.get("concentration"),
                    "duration": row_dict.get("duration"),
                    "location_id": row_dict.get("location_id"),
                    "source_id": row_dict.get("source_id"),
                    "sensor_id": row_dict.get("sensor_id")
                }
                
                # Add coordinates if available
                if all(k in row_dict for k in ["coordinates_x", "coordinates_y", "coordinates_z"]):
                    record_data["coordinates"] = (
                        row_dict.get("coordinates_x"),
                        row_dict.get("coordinates_y"),
                        row_dict.get("coordinates_z")
                    )
                
                record = ExposureRecord.from_dict(record_data)
                history.add_record(record)
            
            # Set metadata if available
            if os.path.exists(metadata_filepath):
                with open(metadata_filepath, 'r') as f:
                    metadata = json.load(f)
                    if "created_at" in metadata:
                        history.created_at = metadata["created_at"]
                    if "updated_at" in metadata:
                        history.updated_at = metadata["updated_at"]
                    if "metadata" in metadata:
                        history.metadata = metadata["metadata"]
            
            return history
        else:
            raise ValueError(f"Unsupported file format: {filepath}")
    
    def save_history_visualization(
        self,
        history: ExposureHistory,
        chemicals: Optional[List[str]] = None,
        include_thresholds: bool = True
    ) -> str:
        """
        Create and save a visualization of an exposure history.
        
        Args:
            history: The exposure history to visualize
            chemicals: Optional list of specific chemicals to include
            include_thresholds: Whether to include threshold lines
            
        Returns:
            Path to the saved visualization file
        """
        # Create directory for exports if it doesn't exist
        exports_dir = os.path.join(self.base_dir, "exports")
        os.makedirs(exports_dir, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        history_id = history.history_id
        filename = f"exposure_viz_{history_id}_{timestamp}.png"
        filepath = os.path.join(exports_dir, filename)
        
        # Create the visualization
        fig = history.plot_exposures(
            chemical_ids=chemicals,
            include_thresholds=include_thresholds,
            save_path=filepath
        )
        
        return filepath
    
    def export_history_to_csv(self, history: ExposureHistory) -> str:
        """
        Export an exposure history to CSV format.
        
        Args:
            history: The exposure history to export
            
        Returns:
            Path to the exported CSV file
        """
        # Create directory for exports if it doesn't exist
        exports_dir = os.path.join(self.base_dir, "exports")
        os.makedirs(exports_dir, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        history_id = history.history_id
        filename = f"exposure_export_{history_id}_{timestamp}.csv"
        filepath = os.path.join(exports_dir, filename)
        
        # Convert to DataFrame and export
        df = history.to_dataframe()
        df.to_csv(filepath, index=False)
        
        return filepath
    
    def list_histories(self) -> List[Dict[str, Any]]:
        """
        List all saved exposure histories.
        
        Returns:
            List of dictionaries with history metadata
        """
        histories_dir = os.path.join(self.base_dir, "histories")
        
        if not os.path.exists(histories_dir):
            return []
            
        # Find all JSON history files
        json_files = glob.glob(os.path.join(histories_dir, "history_*.json"))
        
        histories = []
        for filepath in json_files:
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    
                history_info = {
                    "filepath": filepath,
                    "filename": os.path.basename(filepath),
                    "history_id": data.get("history_id", "unknown"),
                    "created_at": data.get("created_at", "unknown"),
                    "updated_at": data.get("updated_at", "unknown"),
                    "record_count": len(data.get("records", [])),
                    "chemicals": list(set(r.get("chemical_id") for r in data.get("records", []) if r.get("chemical_id")))
                }
                
                histories.append(history_info)
            except Exception as e:
                print(f"Error reading history file {filepath}: {e}")
        
        # Add CSV histories that have metadata files
        metadata_files = glob.glob(os.path.join(histories_dir, "history_*_metadata.json"))
        
        for filepath in metadata_files:
            try:
                with open(filepath, 'r') as f:
                    metadata = json.load(f)
                    
                csv_path = filepath.replace("_metadata.json", ".csv")
                if os.path.exists(csv_path):
                    record_count = metadata.get("record_count", 0)
                    if record_count == 0:
                        # Count rows in CSV
                        df = pd.read_csv(csv_path)
                        record_count = len(df)
                    
                    history_info = {
                        "filepath": csv_path,
                        "filename": os.path.basename(csv_path),
                        "history_id": metadata.get("history_id", "unknown"),
                        "created_at": metadata.get("created_at", "unknown"),
                        "updated_at": metadata.get("updated_at", "unknown"),
                        "record_count": record_count,
                        "format": "csv"
                    }
                    
                    # Try to get chemicals from CSV
                    try:
                        df = pd.read_csv(csv_path)
                        if "chemical_id" in df.columns:
                            chemicals = df["chemical_id"].unique().tolist()
                            history_info["chemicals"] = chemicals
                    except:
                        pass
                    
                    histories.append(history_info)
            except Exception as e:
                print(f"Error reading metadata file {filepath}: {e}")
        
        return histories
    
    def delete_history(self, history_id: str) -> bool:
        """
        Delete all files associated with a specific history ID.
        
        Args:
            history_id: The ID of the history to delete
            
        Returns:
            True if successful, False otherwise
        """
        histories_dir = os.path.join(self.base_dir, "histories")
        
        if not os.path.exists(histories_dir):
            return False
            
        # Find all files containing this history ID
        pattern = os.path.join(histories_dir, f"*{history_id}*")
        matching_files = glob.glob(pattern)
        
        if not matching_files:
            return False
            
        # Delete all matching files
        for filepath in matching_files:
            try:
                os.remove(filepath)
            except Exception as e:
                print(f"Error deleting file {filepath}: {e}")
                return False
                
        return True
    
    def create_backup(self, backup_dir: Optional[str] = None) -> str:
        """
        Create a backup of all exposure data.
        
        Args:
            backup_dir: Directory to store the backup. If None, uses base_dir/backups
            
        Returns:
            Path to the backup directory
        """
        if backup_dir is None:
            backup_dir = os.path.join(self.base_dir, "backups")
            
        os.makedirs(backup_dir, exist_ok=True)
        
        # Create timestamped backup directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_subdir = os.path.join(backup_dir, f"exposure_backup_{timestamp}")
        os.makedirs(backup_subdir, exist_ok=True)
        
        # Copy all files from records, histories, and exports
        for subdir in ["records", "histories", "assessments", "exports"]:
            src_dir = os.path.join(self.base_dir, subdir)
            dst_dir = os.path.join(backup_subdir, subdir)
            
            if os.path.exists(src_dir):
                os.makedirs(dst_dir, exist_ok=True)
                
                # Copy all files
                for filename in os.listdir(src_dir):
                    src_file = os.path.join(src_dir, filename)
                    dst_file = os.path.join(dst_dir, filename)
                    
                    if os.path.isfile(src_file):
                        shutil.copy2(src_file, dst_file)
        
        return backup_subdir
