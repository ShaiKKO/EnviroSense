"""
EnviroSense Test Data Setup

This script downloads and sets up standardized test cases for diffusion model validation.
It includes datasets for Gaussian plume modeling, atmospheric diffusion experiments, 
indoor air quality tests, and computational benchmarks.
"""

import os
import sys
import requests
import numpy as np
import pandas as pd
import zipfile
import json
import urllib.request
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Base paths
TEST_DATA_DIR = Path("envirosense/test_data/diffusion")
METADATA_PATH = TEST_DATA_DIR / "metadata.json"


class TestDataManager:
    """Manages the acquisition and processing of test data for diffusion modeling."""
    
    def __init__(self):
        """Initialize the test data manager."""
        self.ensure_directories_exist()
        self.datasets = self.get_dataset_registry()
    
    def ensure_directories_exist(self):
        """Create necessary directories if they don't exist."""
        os.makedirs(TEST_DATA_DIR, exist_ok=True)
        for subdir in ["gaussian_plume", "atmospheric", "indoor", "cfd", "multi_source"]:
            os.makedirs(TEST_DATA_DIR / subdir, exist_ok=True)
    
    def get_dataset_registry(self) -> Dict:
        """
        Define the registry of available datasets.
        
        These URLs point to established scientific datasets for diffusion modeling validation.
        Some are from EPA, NOAA, NIST, and other research organizations.
        """
        return {
            # Gaussian plume test cases
            "epa_aermod_1": {
                "url": "https://gaftp.epa.gov/Air/aqmg/SCRAM/models/preferred/aermod/aermet_test_data.zip",
                "description": "EPA AERMOD meteorological input test data",
                "type": "gaussian_plume",
                "format": "zip"
            },
            "epa_aermod_2": {
                "url": "https://gaftp.epa.gov/Air/aqmg/SCRAM/models/preferred/aermod/aermod_test_cases.zip",
                "description": "EPA AERMOD test cases with point sources and multiple terrain types",
                "type": "gaussian_plume",
                "format": "zip"
            },
            
            # Atmospheric diffusion experiments
            "prairiegrass": {
                "url": "https://www.jstor.org/stable/26238160",
                "description": "Project Prairie Grass field experiment data, classic dispersion dataset",
                "type": "atmospheric",
                "format": "pdf",
                "manual_download": True
            },
            "kincaid": {
                "url": "https://www.atmos-chem-phys.net/7/6061/2007/acp-7-6061-2007-supplement.zip",
                "description": "Kincaid power plant SF6 tracer study data",
                "type": "atmospheric",
                "format": "zip"
            },
            
            # Indoor air quality test cases
            "nist_multizone": {
                "url": "https://www.nist.gov/services-resources/software/contam",
                "description": "NIST CONTAM multizone indoor air quality modelling data",
                "type": "indoor",
                "format": "zip",
                "manual_download": True
            },
            "ashrae_62_1": {
                "url": "https://www.ashrae.org/technical-resources/standards-and-guidelines/read-only-versions-of-ashrae-standards",
                "description": "ASHRAE 62.1 ventilation test cases (reference document)",
                "type": "indoor",
                "format": "pdf",
                "manual_download": True
            },
            
            # Synthetic data for our own test cases
            "envirosense_synthetic_basic": {
                "generate": True,
                "description": "Basic synthetic test cases for Gaussian plume validation",
                "type": "gaussian_plume",
                "param_sets": 10,
                "points_per_set": 100,
            },
            "envirosense_synthetic_multiroom": {
                "generate": True,
                "description": "Multi-room synthetic indoor model test cases",
                "type": "indoor",
                "room_configs": 5,
                "time_steps": 200,
            }
        }
    
    def download_dataset(self, dataset_id: str) -> bool:
        """
        Download a specific dataset.
        
        Args:
            dataset_id: Identifier for the dataset to download
            
        Returns:
            bool: True if successful, False otherwise
        """
        if dataset_id not in self.datasets:
            print(f"Error: Dataset {dataset_id} not found in registry")
            return False
        
        dataset = self.datasets[dataset_id]
        
        # Handle synthetic data generation
        if dataset.get("generate", False):
            return self.generate_synthetic_dataset(dataset_id, dataset)
            
        # Handle manual download datasets
        if dataset.get("manual_download", False):
            print(f"\nDataset '{dataset_id}' requires manual download:")
            print(f"Description: {dataset['description']}")
            print(f"URL: {dataset['url']}")
            print(f"Please download the file manually and place it in: {TEST_DATA_DIR / dataset['type']}")
            return False
            
        target_dir = TEST_DATA_DIR / dataset["type"]
        filename = os.path.basename(dataset["url"])
        target_path = target_dir / filename
        
        print(f"Downloading {dataset_id}: {dataset['description']}")
        try:
            # Download the file with progress indicator
            self._download_with_progress(dataset["url"], target_path)
            
            # Process based on format
            if dataset["format"] == "zip":
                print(f"Extracting {filename}...")
                with zipfile.ZipFile(target_path, 'r') as zip_ref:
                    extract_dir = target_dir / dataset_id
                    os.makedirs(extract_dir, exist_ok=True)
                    zip_ref.extractall(extract_dir)
            
            print(f"Successfully downloaded and processed {dataset_id}")
            return True
            
        except Exception as e:
            print(f"Error downloading {dataset_id}: {str(e)}")
            return False
    
    def _download_with_progress(self, url: str, target_path: Path):
        """Download a file with progress indicator."""
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            block_size = 8192
            transferred = 0
            
            with open(target_path, 'wb') as f:
                start_time = time.time()
                for chunk in response.iter_content(chunk_size=block_size):
                    if chunk:
                        f.write(chunk)
                        transferred += len(chunk)
                        
                        # Progress indicator
                        if total_size > 0:
                            progress = min(transferred / total_size * 100, 100)
                            elapsed = time.time() - start_time
                            if elapsed > 0:
                                speed = transferred / 1024 / elapsed
                                print(f"\rDownloading... {progress:.1f}% ({transferred/1024/1024:.1f}MB of {total_size/1024/1024:.1f}MB) [{speed:.1f} KB/s]", end="")
                
                print()  # New line after progress indicator
                
        except requests.exceptions.RequestException as e:
            print(f"\nError during download: {e}")
            if os.path.exists(target_path):
                os.remove(target_path)
            raise
    
    def generate_synthetic_dataset(self, dataset_id: str, dataset_info: Dict) -> bool:
        """
        Generate synthetic test data when actual dataset is not available.
        
        Args:
            dataset_id: Identifier for the dataset to generate
            dataset_info: Dataset information from the registry
        
        Returns:
            bool: True if successful, False otherwise
        """
        print(f"Generating synthetic dataset: {dataset_id}")
        try:
            target_dir = TEST_DATA_DIR / dataset_info["type"] / dataset_id
            os.makedirs(target_dir, exist_ok=True)
            
            if dataset_id == "envirosense_synthetic_basic":
                self._generate_gaussian_plume_synthetic(target_dir, dataset_info)
            elif dataset_id == "envirosense_synthetic_multiroom":
                self._generate_indoor_synthetic(target_dir, dataset_info)
            
            print(f"Successfully generated synthetic dataset: {dataset_id}")
            return True
            
        except Exception as e:
            print(f"Error generating synthetic dataset {dataset_id}: {str(e)}")
            return False
    
    def _generate_gaussian_plume_synthetic(self, target_dir: Path, dataset_info: Dict):
        """
        Generate synthetic Gaussian plume test data.
        
        Args:
            target_dir: Directory to save the generated data
            dataset_info: Dataset information from the registry
        """
        param_sets = dataset_info.get("param_sets", 5)
        points_per_set = dataset_info.get("points_per_set", 100)
        
        # Generate metadata
        metadata = {
            "description": dataset_info["description"],
            "generated": pd.Timestamp.now().isoformat(),
            "param_sets": param_sets,
            "points_per_set": points_per_set,
            "parameters": {}
        }
        
        # Generate parameter sets and corresponding data
        for i in range(param_sets):
            # Generate random parameters for this set
            source_strength = np.random.uniform(1, 100)  # g/s
            wind_speed = np.random.uniform(1, 10)  # m/s
            wind_direction = np.random.uniform(0, 360)  # degrees
            stability_class = np.random.choice(['A', 'B', 'C', 'D', 'E', 'F'])
            
            # Map stability class to dispersion parameters
            if stability_class == 'A':
                a_y, b_y, a_z, b_z = 0.22, 0.92, 0.20, 1.1
            elif stability_class == 'B':
                a_y, b_y, a_z, b_z = 0.16, 0.92, 0.12, 1.0
            elif stability_class == 'C':
                a_y, b_y, a_z, b_z = 0.11, 0.92, 0.08, 0.93
            elif stability_class == 'D':
                a_y, b_y, a_z, b_z = 0.08, 0.92, 0.06, 0.85
            elif stability_class == 'E':
                a_y, b_y, a_z, b_z = 0.06, 0.92, 0.03, 0.8
            else:  # F
                a_y, b_y, a_z, b_z = 0.04, 0.91, 0.016, 0.7
            
            # Store parameters in metadata
            metadata["parameters"][f"set_{i+1}"] = {
                "source_strength": source_strength,
                "wind_speed": wind_speed,
                "wind_direction": wind_direction,
                "stability_class": stability_class
            }
            
            # Generate synthetic data points for this parameter set
            x = np.linspace(100, 5000, points_per_set)
            y = np.zeros_like(x)  # Assuming plume centerline
            z = np.zeros_like(x)  # Ground level
            
            sigma_y = a_y * x ** b_y
            sigma_z = a_z * x ** b_z
            
            # Calculate concentration using Gaussian plume equation
            concentration = (source_strength / (2 * np.pi * wind_speed * sigma_y * sigma_z)) * \
                            np.exp(-0.5 * (y / sigma_y) ** 2) * \
                            (np.exp(-0.5 * (z / sigma_z) ** 2) + np.exp(-0.5 * ((2 * 10 - z) / sigma_z) ** 2))
            
            # Create dataframe and save to CSV
            df = pd.DataFrame({
                'distance': x,
                'concentration': concentration,
                'sigma_y': sigma_y,
                'sigma_z': sigma_z
            })
            
            df.to_csv(target_dir / f"plume_set_{i+1}.csv", index=False)
        
        # Save metadata
        with open(target_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def _generate_indoor_synthetic(self, target_dir: Path, dataset_info: Dict):
        """
        Generate synthetic indoor air quality test data.
        
        Args:
            target_dir: Directory to save the generated data
            dataset_info: Dataset information from the registry
        """
        room_configs = dataset_info.get("room_configs", 3)
        time_steps = dataset_info.get("time_steps", 100)
        
        # Generate metadata
        metadata = {
            "description": dataset_info["description"],
            "generated": pd.Timestamp.now().isoformat(),
            "room_configs": room_configs,
            "time_steps": time_steps,
            "configurations": {}
        }
        
        # Room dimensions and properties for each configuration
        for i in range(room_configs):
            num_rooms = np.random.randint(2, 5)
            rooms = []
            
            for r in range(num_rooms):
                room = {
                    "id": f"room_{r+1}",
                    "volume": np.random.uniform(30, 150),  # cubic meters
                    "air_exchange_rate": np.random.uniform(0.5, 3),  # air changes per hour
                    "has_source": r == 0,  # Only first room has source by default
                }
                rooms.append(room)
            
            # Define connections between rooms
            connections = []
            for r1 in range(num_rooms):
                for r2 in range(r1 + 1, num_rooms):
                    if np.random.random() < 0.7:  # 70% chance of connection
                        connections.append({
                            "from": f"room_{r1+1}",
                            "to": f"room_{r2+1}",
                            "flow_rate": np.random.uniform(10, 50)  # m³/h
                        })
            
            # Store configuration in metadata
            metadata["configurations"][f"config_{i+1}"] = {
                "rooms": rooms,
                "connections": connections,
                "source_strength": np.random.uniform(1, 10),  # g/h
                "source_duration": np.random.uniform(1, 4)  # hours
            }
            
            # Generate time series data for each room
            time = np.linspace(0, 8, time_steps)  # 8 hours simulation
            df = pd.DataFrame({"time": time})
            
            # Get configuration parameters
            config = metadata["configurations"][f"config_{i+1}"]
            source_strength = config["source_strength"]
            source_duration = config["source_duration"]
            
            # Simple box model for each room
            for room in rooms:
                room_id = room["id"]
                volume = room["volume"]
                air_exchange = room["air_exchange_rate"]
                
                # Calculate concentration time series
                concentration = np.zeros(time_steps)
                
                # Initial conditions
                if room["has_source"]:
                    # First room with source
                    for t in range(1, time_steps):
                        dt = time[t] - time[t-1]
                        source_term = source_strength if time[t] < source_duration else 0
                        decay_term = air_exchange * concentration[t-1]
                        
                        concentration[t] = concentration[t-1] + (source_term - decay_term) * dt / volume
                else:
                    # Other rooms get inflow from connected rooms
                    # This is a simplified model that doesn't account for all dynamics
                    inflow_rooms = [c for c in connections if c["to"] == room_id]
                    
                    for t in range(1, time_steps):
                        if not inflow_rooms:
                            continue
                            
                        # Simplified transport from previous room with time delay
                        source_room = inflow_rooms[0]["from"]
                        source_idx = next(i for i, r in enumerate(rooms) if r["id"] == source_room)
                        
                        # Calculate delay based on rooms
                        delay_steps = int(time_steps / 8)  # Simple delay of 1/8 the total time
                        
                        if t >= delay_steps:
                            # Get concentration from source room with delay
                            source_conc = concentration[t-delay_steps] if room_id != source_room else 0
                            
                            dt = time[t] - time[t-1]
                            inflow_term = source_conc * 0.2  # Simplified transfer coefficient
                            decay_term = air_exchange * concentration[t-1]
                            
                            concentration[t] = concentration[t-1] + (inflow_term - decay_term) * dt
                
                # Add to dataframe
                df[f"{room_id}_concentration"] = concentration
            
            # Save to CSV
            df.to_csv(target_dir / f"indoor_config_{i+1}.csv", index=False)
        
        # Save metadata
        with open(target_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def download_all_datasets(self) -> Dict[str, bool]:
        """
        Download all datasets in the registry.
        
        Returns:
            Dict[str, bool]: Dictionary of dataset IDs and success status
        """
        results = {}
        for dataset_id in self.datasets:
            results[dataset_id] = self.download_dataset(dataset_id)
        return results
    
    def generate_metadata(self):
        """Generate metadata file with information about all downloaded datasets."""
        metadata = {
            "datasets": {},
            "download_timestamp": pd.Timestamp.now().isoformat(),
            "version": "1.0.0"
        }
        
        for dataset_id, dataset_info in self.datasets.items():
            # Check if dataset was downloaded/generated
            if dataset_info.get("generate", False):
                # Check for generated dataset
                specific_dir = TEST_DATA_DIR / dataset_info["type"] / dataset_id
                
                if os.path.exists(specific_dir) and os.path.isdir(specific_dir):
                    # Dataset was generated
                    files = os.listdir(specific_dir)
                    metadata["datasets"][dataset_id] = {
                        "description": dataset_info["description"],
                        "type": dataset_info["type"],
                        "files": files,
                        "path": str(specific_dir),
                        "generated": True
                    }
                else:
                    metadata["datasets"][dataset_id] = {
                        "description": dataset_info["description"],
                        "type": dataset_info["type"],
                        "generated": False
                    }
            elif dataset_info.get("manual_download", False):
                # Manual download dataset
                type_dir = TEST_DATA_DIR / dataset_info["type"]
                
                # Check if any files related to this dataset exist
                potential_files = [f for f in os.listdir(type_dir) if dataset_id in f.lower()]
                
                if potential_files:
                    metadata["datasets"][dataset_id] = {
                        "description": dataset_info["description"],
                        "type": dataset_info["type"],
                        "files": potential_files,
                        "path": str(type_dir),
                        "downloaded": True,
                        "manual_download": True
                    }
                else:
                    metadata["datasets"][dataset_id] = {
                        "description": dataset_info["description"],
                        "type": dataset_info["type"],
                        "downloaded": False,
                        "manual_download": True
                    }
            else:
                # Check for downloaded dataset
                type_dir = TEST_DATA_DIR / dataset_info["type"]
                specific_dir = type_dir / dataset_id
                
                if os.path.exists(specific_dir) and os.path.isdir(specific_dir):
                    # Dataset was downloaded and extracted
                    files = os.listdir(specific_dir)
                    metadata["datasets"][dataset_id] = {
                        "description": dataset_info["description"],
                        "type": dataset_info["type"],
                        "files": files,
                        "path": str(specific_dir),
                        "downloaded": True
                    }
                else:
                    # Check for single file download
                    filename = os.path.basename(dataset_info["url"])
                    file_path = type_dir / filename
                    
                    if os.path.exists(file_path):
                        metadata["datasets"][dataset_id] = {
                            "description": dataset_info["description"],
                            "type": dataset_info["type"],
                            "files": [filename],
                            "path": str(file_path),
                            "downloaded": True
                        }
                    else:
                        metadata["datasets"][dataset_id] = {
                            "description": dataset_info["description"],
                            "type": dataset_info["type"],
                            "downloaded": False
                        }
        
        # Write metadata to file
        with open(METADATA_PATH, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Metadata written to {METADATA_PATH}")


def main():
    """Main function to run the test data setup."""
    print("EnviroSense Diffusion Test Data Setup")
    print("-" * 40)
    
    manager = TestDataManager()
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "all":
            results = manager.download_all_datasets()
            success = sum(1 for result in results.values() if result)
            print(f"Downloaded/generated {success} of {len(results)} datasets")
        else:
            for dataset_id in sys.argv[1:]:
                manager.download_dataset(dataset_id)
    else:
        # Interactive mode
        print("\nAvailable datasets:")
        for idx, (dataset_id, info) in enumerate(manager.datasets.items(), 1):
            source_type = "Generate" if info.get("generate", False) else "Download"
            if info.get("manual_download", False):
                source_type = "Manual download required"
                
            print(f"{idx}. {dataset_id}: {info['description']} [{source_type}]")
        
        selection = input("\nEnter dataset numbers to download/generate (comma-separated) or 'all': ")
        if selection.lower() == 'all':
            results = manager.download_all_datasets()
            success = sum(1 for result in results.values() if result)
            print(f"Downloaded/generated {success} of {len(results)} datasets")
        else:
            try:
                indices = [int(x.strip()) - 1 for x in selection.split(',')]
                dataset_ids = list(manager.datasets.keys())
                for idx in indices:
                    if 0 <= idx < len(dataset_ids):
                        manager.download_dataset(dataset_ids[idx])
            except ValueError:
                print("Invalid input. Please enter numbers separated by commas.")
    
    # Generate metadata
    manager.generate_metadata()
    
    print("\nTest data setup complete!")


if __name__ == "__main__":
    main()
