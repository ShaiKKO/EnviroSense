"""
Exposure Records Module

This module provides classes for tracking and managing exposure records for different
chemicals and environmental parameters. It supports:
- Recording timestamped exposure events
- Maintaining exposure histories
- Calculating time-weighted averages and other exposure metrics
- Evaluating exposure against regulatory thresholds
"""

import uuid
import math
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Union, Any
import os
import heapq
from collections import defaultdict
from dataclasses import dataclass, field, asdict

from envirosense.core.chemical.chemical_properties import (
    ChemicalCategory,
    CHEMICAL_PROPERTIES
)


@dataclass
class ExposureRecord:
    """
    Class representing a single chemical exposure event or measurement.
    
    This records a specific chemical concentration at a specific time and location,
    along with any contextual information about the exposure event.
    """
    
    # Basic identification
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Exposure details
    chemical_id: str = None
    concentration: float = 0.0  # In appropriate units (typically ppm)
    duration: float = 0.0  # Duration in seconds
    
    # Location
    location_id: Optional[str] = None  # Optional location identifier
    coordinates: Optional[Tuple[float, float, float]] = None  # (x, y, z) in meters
    
    # Context
    source_id: Optional[str] = None  # ID of source causing the exposure, if known
    sensor_id: Optional[str] = None  # ID of sensor recording the exposure, if applicable
    context: Dict[str, Any] = field(default_factory=dict)  # Additional context
    
    def __post_init__(self):
        """Validate and process after initialization."""
        # If timestamp is provided as datetime, convert to ISO format
        if isinstance(self.timestamp, datetime):
            self.timestamp = self.timestamp.isoformat()
    
    @property
    def datetime(self) -> datetime:
        """Get the timestamp as a datetime object."""
        if isinstance(self.timestamp, str):
            return datetime.fromisoformat(self.timestamp)
        return self.timestamp
    
    @property
    def dose(self) -> float:
        """Calculate the dose as concentration * duration."""
        return self.concentration * self.duration
    
    def get_health_context(self) -> Dict[str, Any]:
        """
        Retrieve health-related context for this exposure.
        
        Returns:
            Dictionary with health threshold information
        """
        if self.chemical_id not in CHEMICAL_PROPERTIES:
            return {}
            
        chemical_info = CHEMICAL_PROPERTIES[self.chemical_id]
        health_data = chemical_info.get("health_data", {})
        
        result = {
            "chemical_name": chemical_info.get("name", self.chemical_id),
            "health_data": health_data
        }
        
        # Evaluate exposure relative to thresholds
        if health_data:
            for threshold_name, threshold_value in health_data.items():
                if threshold_name.endswith("_PEL") or threshold_name.endswith("_TLV") or threshold_name.endswith("_REL"):
                    if threshold_value is not None and self.concentration > threshold_value:
                        result[f"exceeds_{threshold_name}"] = True
        
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExposureRecord':
        """Create an ExposureRecord from a dictionary."""
        return cls(**data)


class ExposureHistory:
    """
    Class for managing and analyzing a history of exposure records.
    
    This class maintains a collection of exposure records for one or more chemicals,
    providing methods to analyze exposure patterns, calculate statistics, and 
    assess potential health impacts.
    """
    
    def __init__(self, history_id: Optional[str] = None):
        """
        Initialize an exposure history.
        
        Args:
            history_id: Unique identifier for this history. If None, a UUID is generated.
        """
        self.history_id = history_id if history_id else str(uuid.uuid4())
        self.records: List[ExposureRecord] = []
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.metadata: Dict[str, Any] = {}
        
        # Cache for computed values
        self._cache = {}
    
    def add_record(self, record: ExposureRecord) -> None:
        """
        Add an exposure record to the history.
        
        Args:
            record: The exposure record to add
        """
        self.records.append(record)
        self.updated_at = datetime.now().isoformat()
        
        # Clear cache since data has changed
        self._cache = {}
    
    def add_records(self, records: List[ExposureRecord]) -> None:
        """
        Add multiple exposure records to the history.
        
        Args:
            records: List of exposure records to add
        """
        self.records.extend(records)
        self.updated_at = datetime.now().isoformat()
        
        # Clear cache since data has changed
        self._cache = {}
    
    def get_records_by_chemical(self, chemical_id: str) -> List[ExposureRecord]:
        """
        Get all records for a specific chemical.
        
        Args:
            chemical_id: The chemical ID to filter by
            
        Returns:
            List of matching exposure records
        """
        return [record for record in self.records if record.chemical_id == chemical_id]
    
    def get_records_by_timerange(
        self, 
        start_time: Union[str, datetime], 
        end_time: Union[str, datetime]
    ) -> List[ExposureRecord]:
        """
        Get records within a specific time range.
        
        Args:
            start_time: Start of the time range
            end_time: End of the time range
            
        Returns:
            List of matching exposure records
        """
        # Convert string timestamps to datetime objects
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time)
        if isinstance(end_time, str):
            end_time = datetime.fromisoformat(end_time)
            
        return [
            record for record in self.records
            if start_time <= record.datetime <= end_time
        ]
    
    def calculate_twa(
        self, 
        chemical_id: str, 
        time_period: float, 
        end_time: Optional[Union[str, datetime]] = None
    ) -> float:
        """
        Calculate the time-weighted average (TWA) for a specific chemical.
        
        Args:
            chemical_id: The chemical to calculate TWA for
            time_period: Period in seconds for the TWA calculation
            end_time: The end time for the calculation window, defaults to now
            
        Returns:
            Time-weighted average concentration
        """
        # Get the end time
        if end_time is None:
            end_time = datetime.now()
        elif isinstance(end_time, str):
            end_time = datetime.fromisoformat(end_time)
            
        # Calculate the start time
        start_time = end_time - timedelta(seconds=time_period)
        
        # Get records in the time range for this chemical
        relevant_records = [
            record for record in self.records
            if (record.chemical_id == chemical_id and 
                start_time <= record.datetime <= end_time)
        ]
        
        if not relevant_records:
            return 0.0
            
        # Sort records by time
        relevant_records.sort(key=lambda r: r.datetime)
        
        # Calculate TWA using the trapezoid rule
        total_area = 0.0
        prev_time = start_time
        prev_conc = 0.0  # Assume zero concentration at boundary
        
        for record in relevant_records:
            # Calculate time difference in seconds
            time_diff = (record.datetime - prev_time).total_seconds()
            
            # Calculate area of this trapezoid segment
            segment_area = (prev_conc + record.concentration) * time_diff / 2
            total_area += segment_area
            
            # Update for next iteration
            prev_time = record.datetime
            prev_conc = record.concentration
            
        # Handle the final segment to the end time
        final_diff = (end_time - prev_time).total_seconds()
        if final_diff > 0:
            # Use the last known concentration
            final_area = prev_conc * final_diff
            total_area += final_area
            
        # Calculate TWA
        twa = total_area / time_period
        return twa
    
    def calculate_peak(
        self, 
        chemical_id: str,
        time_period: Optional[float] = None,
        end_time: Optional[Union[str, datetime]] = None
    ) -> float:
        """
        Calculate the peak concentration for a specific chemical.
        
        Args:
            chemical_id: The chemical to find peak concentration for
            time_period: Optional period in seconds to look back from end_time
            end_time: The end time for the calculation window, defaults to now
            
        Returns:
            Peak concentration value
        """
        # Get the records to consider
        if time_period is None:
            # All records for this chemical
            relevant_records = [r for r in self.records if r.chemical_id == chemical_id]
        else:
            # Get the end time
            if end_time is None:
                end_time = datetime.now()
            elif isinstance(end_time, str):
                end_time = datetime.fromisoformat(end_time)
                
            # Calculate the start time
            start_time = end_time - timedelta(seconds=time_period)
            
            # Get records in the time range for this chemical
            relevant_records = [
                record for record in self.records
                if (record.chemical_id == chemical_id and 
                    start_time <= record.datetime <= end_time)
            ]
        
        if not relevant_records:
            return 0.0
        
        # Find the maximum concentration
        peak = max(record.concentration for record in relevant_records)
        return peak
    
    def calculate_exposure_metrics(
        self, 
        chemical_id: str
    ) -> Dict[str, float]:
        """
        Calculate key exposure metrics for a specific chemical.
        
        Args:
            chemical_id: The chemical to calculate metrics for
            
        Returns:
            Dictionary of exposure metrics including:
            - 8hr_twa: 8-hour time-weighted average
            - 24hr_twa: 24-hour time-weighted average  
            - peak_15min: Peak 15-minute average
            - peak_concentration: Absolute peak concentration
            - cumulative_dose: Total cumulative dose
        """
        # Check cache first
        cache_key = f"metrics_{chemical_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        metrics = {}
        
        # Calculate TWAs
        metrics["8hr_twa"] = self.calculate_twa(chemical_id, 8 * 3600)  # 8 hours in seconds
        metrics["24hr_twa"] = self.calculate_twa(chemical_id, 24 * 3600)  # 24 hours in seconds
        
        # Calculate peak 15-minute TWA
        # This requires a different approach - finding the highest 15-min window
        records = self.get_records_by_chemical(chemical_id)
        if records:
            records.sort(key=lambda r: r.datetime)
            max_15min_avg = 0.0
            
            for i in range(len(records)):
                end_idx = i
                start_time = records[i].datetime
                window_records = [records[i]]
                
                # Build a 15-minute window
                for j in range(i + 1, len(records)):
                    if (records[j].datetime - start_time).total_seconds() <= 15 * 60:
                        window_records.append(records[j])
                        end_idx = j
                    else:
                        break
                
                if window_records:
                    # Calculate average for this window
                    avg = sum(r.concentration for r in window_records) / len(window_records)
                    max_15min_avg = max(max_15min_avg, avg)
            
            metrics["peak_15min"] = max_15min_avg
        else:
            metrics["peak_15min"] = 0.0
        
        # Calculate absolute peak
        metrics["peak_concentration"] = self.calculate_peak(chemical_id)
        
        # Calculate cumulative dose
        cumulative_dose = sum(r.concentration * r.duration for r in records if r.duration > 0)
        if cumulative_dose == 0 and records:
            # If durations aren't set, make a rough estimate
            sorted_records = sorted(records, key=lambda r: r.datetime)
            total_dose = 0.0
            for i in range(len(sorted_records) - 1):
                duration = (sorted_records[i+1].datetime - sorted_records[i].datetime).total_seconds()
                avg_conc = (sorted_records[i].concentration + sorted_records[i+1].concentration) / 2
                total_dose += avg_conc * duration
            cumulative_dose = total_dose
        
        metrics["cumulative_dose"] = cumulative_dose
        
        # Cache results
        self._cache[cache_key] = metrics
        return metrics
    
    def evaluate_health_thresholds(
        self, 
        chemical_id: str
    ) -> Dict[str, bool]:
        """
        Evaluate exposure against health thresholds for a specific chemical.
        
        Args:
            chemical_id: The chemical to evaluate
            
        Returns:
            Dictionary mapping threshold names to boolean exceeded status
        """
        if chemical_id not in CHEMICAL_PROPERTIES:
            return {}
            
        health_data = CHEMICAL_PROPERTIES[chemical_id].get("health_data", {})
        if not health_data:
            return {}
            
        # Calculate relevant metrics
        metrics = self.calculate_exposure_metrics(chemical_id)
        
        results = {}
        
        # Check TWA values against relevant thresholds
        if "NIOSH_REL" in health_data and health_data["NIOSH_REL"] is not None:
            results["exceeds_NIOSH_REL"] = metrics["8hr_twa"] > health_data["NIOSH_REL"]
            
        if "OSHA_PEL" in health_data and health_data["OSHA_PEL"] is not None:
            results["exceeds_OSHA_PEL"] = metrics["8hr_twa"] > health_data["OSHA_PEL"]
            
        if "ACGIH_TLV" in health_data and health_data["ACGIH_TLV"] is not None:
            results["exceeds_ACGIH_TLV"] = metrics["8hr_twa"] > health_data["ACGIH_TLV"]
        
        # Check STEL (Short-Term Exposure Limit) - usually 15-minute average
        if "OSHA_STEL" in health_data and health_data["OSHA_STEL"] is not None:
            results["exceeds_OSHA_STEL"] = metrics["peak_15min"] > health_data["OSHA_STEL"]
            
        if "NIOSH_STEL" in health_data and health_data["NIOSH_STEL"] is not None:
            results["exceeds_NIOSH_STEL"] = metrics["peak_15min"] > health_data["NIOSH_STEL"]
        
        # Check ceiling values against peak
        if "NIOSH_CEILING" in health_data and health_data["NIOSH_CEILING"] is not None:
            results["exceeds_NIOSH_CEILING"] = metrics["peak_concentration"] > health_data["NIOSH_CEILING"]
        
        return results
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the exposure history.
        
        Returns:
            Dictionary with exposure summary information
        """
        summary = {
            "history_id": self.history_id,
            "record_count": len(self.records),
            "chemicals": set(record.chemical_id for record in self.records if record.chemical_id),
            "start_time": min([record.datetime for record in self.records], default=None) if self.records else None,
            "end_time": max([record.datetime for record in self.records], default=None) if self.records else None,
            "chemical_summaries": {}
        }
        
        # Convert set to list for JSON serialization
        summary["chemicals"] = list(summary["chemicals"])
        
        # Calculate summary statistics for each chemical
        for chemical_id in summary["chemicals"]:
            if not chemical_id:
                continue  # Skip None or empty strings
                
            chemical_records = self.get_records_by_chemical(chemical_id)
            
            # Get chemical name
            chemical_name = CHEMICAL_PROPERTIES.get(chemical_id, {}).get("name", chemical_id)
            
            chemical_summary = {
                "name": chemical_name,
                "record_count": len(chemical_records),
                "metrics": self.calculate_exposure_metrics(chemical_id),
                "health_evaluation": self.evaluate_health_thresholds(chemical_id)
            }
            
            summary["chemical_summaries"][chemical_id] = chemical_summary
        
        return summary
    
    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert exposure records to a pandas DataFrame.
        
        Returns:
            DataFrame with exposure record data
        """
        data = []
        
        for record in self.records:
            row = {
                "record_id": record.record_id,
                "timestamp": record.datetime,
                "chemical_id": record.chemical_id,
                "concentration": record.concentration,
                "duration": record.duration,
                "location_id": record.location_id,
                "source_id": record.source_id,
                "sensor_id": record.sensor_id
            }
            
            # Add coordinates if available
            if record.coordinates:
                row["x"] = record.coordinates[0]
                row["y"] = record.coordinates[1]
                row["z"] = record.coordinates[2]
            
            # Add chemical name if available
            if record.chemical_id in CHEMICAL_PROPERTIES:
                row["chemical_name"] = CHEMICAL_PROPERTIES[record.chemical_id].get("name", record.chemical_id)
            
            data.append(row)
        
        if not data:
            # Create empty DataFrame with expected columns
            return pd.DataFrame(columns=[
                "record_id", "timestamp", "chemical_id", "chemical_name",
                "concentration", "duration", "location_id", "source_id", "sensor_id",
                "x", "y", "z"
            ])
        
        return pd.DataFrame(data)
    
    def plot_exposures(
        self, 
        chemical_ids: Optional[List[str]] = None, 
        timeframe: Optional[Tuple[datetime, datetime]] = None,
        figsize: Tuple[int, int] = (12, 8),
        include_thresholds: bool = True,
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """
        Plot exposure concentrations over time.
        
        Args:
            chemical_ids: List of chemical IDs to plot (defaults to all)
            timeframe: Optional (start_time, end_time) tuple to limit plot range
            figsize: Figure size as (width, height) in inches
            include_thresholds: Whether to include health threshold lines
            save_path: Optional file path to save the plot
            
        Returns:
            Matplotlib figure object
        """
        # Convert to DataFrame for easier plotting
        df = self.to_dataframe()
        
        if df.empty:
            fig, ax = plt.subplots(figsize=figsize)
            ax.text(0.5, 0.5, "No exposure data available", 
                   ha='center', va='center', fontsize=12)
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
            return fig
        
        # Filter by chemical IDs if specified
        if chemical_ids:
            df = df[df["chemical_id"].isin(chemical_ids)]
        
        # Filter by timeframe if specified
        if timeframe:
            start_time, end_time = timeframe
            df = df[(df["timestamp"] >= start_time) & (df["timestamp"] <= end_time)]
        
        # Sort by timestamp
        df = df.sort_values("timestamp")
        
        # Create figure
        fig, ax = plt.subplots(figsize=figsize)
        
        # Get unique chemicals
        unique_chemicals = df["chemical_id"].unique()
        
        # Plot each chemical
        for chemical_id in unique_chemicals:
            chem_df = df[df["chemical_id"] == chemical_id]
            
            # Get chemical name if available
            if chemical_id in CHEMICAL_PROPERTIES:
                chemical_name = CHEMICAL_PROPERTIES[chemical_id].get("name", chemical_id)
            else:
                chemical_name = chemical_id
            
            ax.plot(chem_df["timestamp"], chem_df["concentration"], 
                   marker='o', linestyle='-', markersize=4, label=chemical_name)
            
            # Add health threshold lines if requested
            if include_thresholds and chemical_id in CHEMICAL_PROPERTIES:
                health_data = CHEMICAL_PROPERTIES[chemical_id].get("health_data", {})
                
                # Add OSHA PEL threshold line
                if "OSHA_PEL" in health_data and health_data["OSHA_PEL"] is not None:
                    ax.axhline(y=health_data["OSHA_PEL"], color='r', linestyle='--', alpha=0.7,
                              label=f"{chemical_name} OSHA PEL ({health_data['OSHA_PEL']} ppm)")
                
                # Add NIOSH REL threshold line
                if "NIOSH_REL" in health_data and health_data["NIOSH_REL"] is not None:
                    ax.axhline(y=health_data["NIOSH_REL"], color='orange', linestyle='--', alpha=0.7,
                              label=f"{chemical_name} NIOSH REL ({health_data['NIOSH_REL']} ppm)")
        
        # Set labels and title
        ax.set_xlabel("Time")
        ax.set_ylabel("Concentration (ppm)")
        ax.set_title("Chemical Exposure Concentrations Over Time")
        
        # Format x-axis for timestamps
        plt.gcf().autofmt_xdate()
        
        # Add legend
        ax.legend(loc='upper right')
        
        # Add grid for readability
        ax.grid(True, alpha=0.3)
        
        # Save if requested
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "history_id": self.history_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
            "records": [record.to_dict() for record in self.records]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExposureHistory':
        """Create an ExposureHistory from a dictionary."""
        history = cls(data.get("history_id"))
        history.created_at = data.get("created_at", history.created_at)
        history.updated_at = data.get("updated_at", history.updated_at)
        history.metadata = data.get("metadata", {})
        
        # Add records
        for record_data in data.get("records", []):
            history.add_record(ExposureRecord.from_dict(record_data))
        
        return history
