"""
EnviroSense Diffusion Model Validation

Utilities for validating diffusion models against test cases.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import json
import os
from typing import Dict, List, Tuple, Optional, Any, Callable, Union
from datetime import datetime

# Base path for test data
TEST_DATA_DIR = Path("envirosense/test_data/diffusion")
METADATA_PATH = TEST_DATA_DIR / "metadata.json"
VALIDATION_RESULTS_DIR = Path("envirosense/test_results/diffusion_validation")


class DiffusionValidator:
    """Validates diffusion model results against reference test data."""
    
    def __init__(self):
        """Initialize the validator."""
        self.load_metadata()
        self._ensure_directories_exist()
    
    def _ensure_directories_exist(self):
        """Create necessary directories if they don't exist."""
        os.makedirs(VALIDATION_RESULTS_DIR, exist_ok=True)
    
    def load_metadata(self):
        """Load test data metadata."""
        try:
            with open(METADATA_PATH, 'r') as f:
                self.metadata = json.load(f)
        except FileNotFoundError:
            print(f"Metadata file not found at {METADATA_PATH}")
            print("Please run test_data_setup.py first to download test data.")
            self.metadata = {"datasets": {}}
    
    def list_available_datasets(self) -> List[Dict]:
        """
        List all available datasets for validation.
        
        Returns:
            List[Dict]: List of available datasets with their details
        """
        available_datasets = []
        
        if "datasets" not in self.metadata:
            print("No metadata available. Please run test_data_setup.py first.")
            return available_datasets
            
        for dataset_id, dataset_info in self.metadata["datasets"].items():
            # Check if the dataset is available (downloaded or generated)
            if dataset_info.get("downloaded", False) or dataset_info.get("generated", False):
                available_datasets.append({
                    "id": dataset_id,
                    "description": dataset_info.get("description", ""),
                    "type": dataset_info.get("type", ""),
                    "generated": dataset_info.get("generated", False),
                    "path": dataset_info.get("path", "")
                })
        
        return available_datasets
    
    def validate_gaussian_plume(self, model_func: Callable, dataset_id: str,
                               parameter_mapping: Dict = None) -> Dict[str, Any]:
        """
        Validate a Gaussian plume model against reference data.
        
        Args:
            model_func: Function that takes test case parameters and returns model output
                Expected signature: model_func(x, y, z, params) -> concentration
            dataset_id: Identifier for the dataset to use for validation
            parameter_mapping: Optional mapping from dataset parameters to model parameters
            
        Returns:
            Dict containing validation statistics
        """
        # Check if dataset exists and is of correct type
        if not self._check_dataset(dataset_id, "gaussian_plume"):
            return {
                "dataset_id": dataset_id,
                "validated": False,
                "error": "Dataset not available or not of type 'gaussian_plume'"
            }
        
        dataset_info = self.metadata["datasets"][dataset_id]
        dataset_path = Path(dataset_info["path"])
        result_id = f"plume_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        results_path = VALIDATION_RESULTS_DIR / result_id
        os.makedirs(results_path, exist_ok=True)
        
        # Results structure
        results = {
            "dataset_id": dataset_id,
            "model_results": [],
            "aggregated_metrics": {},
            "validated": True,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # If it's a synthetic dataset, load from our generated files
            if dataset_info.get("generated", False):
                # Load metadata to get parameter sets
                with open(dataset_path / "metadata.json", 'r') as f:
                    synth_metadata = json.load(f)
                
                param_sets = synth_metadata.get("param_sets", 0)
                metrics_all = []
                
                # Process each parameter set
                for i in range(1, param_sets + 1):
                    param_set_id = f"set_{i}"
                    
                    # Get parameters for this set
                    if param_set_id in synth_metadata.get("parameters", {}):
                        params = synth_metadata["parameters"][param_set_id]
                        
                        # Map parameters if mapping provided
                        if parameter_mapping:
                            model_params = {}
                            for model_key, dataset_key in parameter_mapping.items():
                                if dataset_key in params:
                                    model_params[model_key] = params[dataset_key]
                        else:
                            model_params = params
                        
                        # Load reference data
                        csv_path = dataset_path / f"plume_set_{i}.csv"
                        if not os.path.exists(csv_path):
                            print(f"Warning: Data file not found for {param_set_id}")
                            continue
                            
                        ref_data = pd.read_csv(csv_path)
                        
                        # Run model with parameters
                        x_values = ref_data['distance'].values
                        y_values = np.zeros_like(x_values)  # Plume centerline
                        z_values = np.zeros_like(x_values)  # Ground level
                        
                        # Call the model function
                        model_concentrations = np.array([
                            model_func(x, y, z, model_params) 
                            for x, y, z in zip(x_values, y_values, z_values)
                        ])
                        
                        # Calculate metrics
                        ref_concentrations = ref_data['concentration'].values
                        metrics = self._calculate_metrics(ref_concentrations, model_concentrations)
                        metrics_all.append(metrics)
                        
                        # Store this set's results
                        set_result = {
                            "param_set_id": param_set_id,
                            "parameters": params,
                            "metrics": metrics
                        }
                        results["model_results"].append(set_result)
                        
                        # Generate comparison plot
                        self._plot_concentration_comparison(
                            x_values, ref_concentrations, model_concentrations,
                            param_set_id, params,
                            results_path / f"comparison_{param_set_id}.png"
                        )
                
                # Calculate aggregated metrics across all sets
                if metrics_all:
                    results["aggregated_metrics"] = self._aggregate_metrics(metrics_all)
                
                # Generate summary plot if we have multiple sets
                if len(results["model_results"]) > 1:
                    self._plot_metrics_summary(results, results_path / "summary_metrics.png")
            
            else:
                # Handle non-synthetic datasets (e.g., EPA AERMOD)
                # This would be implemented based on the specific format of those datasets
                pass
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            results["validated"] = False
            results["error"] = str(e)
        
        # Save validation results
        with open(results_path / "validation_results.json", 'w') as f:
            json.dump(results, f, indent=2)
        
        return results
    
    def validate_indoor_diffusion(self, model_func: Callable, dataset_id: str,
                                 parameter_mapping: Dict = None) -> Dict[str, Any]:
        """
        Validate an indoor diffusion model against reference data.
        
        Args:
            model_func: Function that takes test case parameters and returns model output
                Expected signature: model_func(time, room_config, params) -> Dict[room_id, concentrations]
            dataset_id: Identifier for the dataset to use for validation
            parameter_mapping: Optional mapping from dataset parameters to model parameters
            
        Returns:
            Dict containing validation statistics
        """
        # Check if dataset exists and is of correct type
        if not self._check_dataset(dataset_id, "indoor"):
            return {
                "dataset_id": dataset_id,
                "validated": False,
                "error": "Dataset not available or not of type 'indoor'"
            }
        
        dataset_info = self.metadata["datasets"][dataset_id]
        dataset_path = Path(dataset_info["path"])
        result_id = f"indoor_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        results_path = VALIDATION_RESULTS_DIR / result_id
        os.makedirs(results_path, exist_ok=True)
        
        # Results structure
        results = {
            "dataset_id": dataset_id,
            "model_results": [],
            "aggregated_metrics": {},
            "validated": True,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # If it's a synthetic dataset, load from our generated files
            if dataset_info.get("generated", False):
                # Load metadata to get configurations
                with open(dataset_path / "metadata.json", 'r') as f:
                    synth_metadata = json.load(f)
                
                room_configs = synth_metadata.get("room_configs", 0)
                metrics_all = []
                
                # Process each room configuration
                for i in range(1, room_configs + 1):
                    config_id = f"config_{i}"
                    
                    # Check if this configuration exists in metadata
                    if config_id in synth_metadata.get("configurations", {}):
                        # Get configuration
                        config = synth_metadata["configurations"][config_id]
                        
                        # Map parameters if mapping provided
                        if parameter_mapping:
                            model_params = {}
                            for model_key, dataset_key in parameter_mapping.items():
                                if dataset_key in config:
                                    model_params[model_key] = config[dataset_key]
                        else:
                            model_params = config
                        
                        # Load reference data
                        csv_path = dataset_path / f"indoor_config_{i}.csv"
                        if not os.path.exists(csv_path):
                            print(f"Warning: Data file not found for {config_id}")
                            continue
                            
                        ref_data = pd.read_csv(csv_path)
                        time_values = ref_data['time'].values
                        
                        # Get room IDs from the columns
                        room_ids = [col.split('_')[0] for col in ref_data.columns 
                                   if col.endswith('_concentration')]
                        
                        # Run model with parameters
                        model_result = model_func(time_values, config, model_params)
                        
                        # Calculate metrics for each room
                        config_metrics = {}
                        room_metrics = []
                        
                        for room_id in room_ids:
                            ref_column = f"{room_id}_concentration"
                            if ref_column in ref_data.columns and room_id in model_result:
                                ref_concentrations = ref_data[ref_column].values
                                model_concentrations = model_result[room_id]
                                
                                # Calculate metrics
                                metrics = self._calculate_metrics(ref_concentrations, model_concentrations)
                                metrics["room_id"] = room_id
                                room_metrics.append(metrics)
                                
                                # Generate room plot
                                self._plot_time_series_comparison(
                                    time_values, ref_concentrations, model_concentrations,
                                    f"{config_id}_{room_id}", {"room_id": room_id},
                                    results_path / f"comparison_{config_id}_{room_id}.png"
                                )
                        
                        # Aggregate metrics across rooms
                        if room_metrics:
                            config_metrics = self._aggregate_metrics(room_metrics)
                            metrics_all.append(config_metrics)
                        
                        # Store this configuration's results
                        config_result = {
                            "config_id": config_id,
                            "config": config,
                            "metrics": config_metrics,
                            "room_metrics": room_metrics
                        }
                        results["model_results"].append(config_result)
                        
                        # Generate multi-room plot
                        self._plot_multi_room_comparison(
                            ref_data, model_result, room_ids, config_id,
                            results_path / f"multi_room_{config_id}.png"
                        )
                
                # Calculate aggregated metrics across all configurations
                if metrics_all:
                    results["aggregated_metrics"] = self._aggregate_metrics(metrics_all)
                
                # Generate summary plot if we have multiple configurations
                if len(results["model_results"]) > 1:
                    self._plot_metrics_summary(results, results_path / "summary_metrics.png")
            
            else:
                # Handle non-synthetic datasets (e.g., NIST CONTAM)
                # This would be implemented based on the specific format of those datasets
                pass
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            results["validated"] = False
            results["error"] = str(e)
        
        # Save validation results
        with open(results_path / "validation_results.json", 'w') as f:
            json.dump(results, f, indent=2)
        
        return results
    
    def _check_dataset(self, dataset_id: str, expected_type: str) -> bool:
        """
        Check if a dataset exists and is of the expected type.
        
        Args:
            dataset_id: Identifier for the dataset
            expected_type: Expected dataset type
            
        Returns:
            bool: True if dataset exists and is of expected type, False otherwise
        """
        if "datasets" not in self.metadata:
            return False
            
        if dataset_id not in self.metadata["datasets"]:
            return False
            
        dataset_info = self.metadata["datasets"][dataset_id]
        
        # Check if dataset is available (downloaded or generated)
        if not (dataset_info.get("downloaded", False) or dataset_info.get("generated", False)):
            return False
            
        # Check if dataset is of expected type
        return dataset_info.get("type", "") == expected_type
    
    def _calculate_metrics(self, reference: np.ndarray, model: np.ndarray) -> Dict[str, float]:
        """
        Calculate validation metrics between reference and model data.
        
        Args:
            reference: Reference data values
            model: Model output values
            
        Returns:
            Dict containing validation metrics
        """
        # Ensure arrays are numpy arrays
        ref = np.asarray(reference)
        mod = np.asarray(model)
        
        # Calculate various metrics
        metrics = {}
        
        # Root Mean Square Error
        metrics["rmse"] = np.sqrt(np.mean((ref - mod) ** 2))
        
        # Normalized Root Mean Square Error (as percentage)
        if np.max(ref) > np.min(ref):
            metrics["nrmse"] = 100.0 * metrics["rmse"] / (np.max(ref) - np.min(ref))
        else:
            metrics["nrmse"] = np.nan
        
        # Mean Absolute Error
        metrics["mae"] = np.mean(np.abs(ref - mod))
        
        # Mean Absolute Percentage Error
        with np.errstate(divide='ignore', invalid='ignore'):
            mape = 100.0 * np.mean(np.abs((ref - mod) / ref))
        metrics["mape"] = np.nan if np.isnan(mape) or np.isinf(mape) else mape
        
        # Correlation Coefficient
        if np.std(ref) > 0 and np.std(mod) > 0:
            metrics["correlation"] = np.corrcoef(ref, mod)[0, 1]
        else:
            metrics["correlation"] = np.nan
        
        # R-squared (Coefficient of determination)
        ss_tot = np.sum((ref - np.mean(ref)) ** 2)
        ss_res = np.sum((ref - mod) ** 2)
        if ss_tot > 0:
            metrics["r_squared"] = 1 - (ss_res / ss_tot)
        else:
            metrics["r_squared"] = np.nan
        
        # Fractional Bias
        denom = 0.5 * (np.mean(ref) + np.mean(mod))
        if denom != 0:
            metrics["fractional_bias"] = (np.mean(ref) - np.mean(mod)) / denom
        else:
            metrics["fractional_bias"] = np.nan
        
        # Fractional Mean Squared Error
        if denom != 0:
            metrics["fractional_mse"] = np.mean(((ref - mod) / denom) ** 2)
        else:
            metrics["fractional_mse"] = np.nan
        
        # Index of Agreement
        denom = np.sum((np.abs(mod - np.mean(ref)) + np.abs(ref - np.mean(ref))) ** 2)
        if denom > 0:
            metrics["index_of_agreement"] = 1 - (np.sum((ref - mod) ** 2) / denom)
        else:
            metrics["index_of_agreement"] = np.nan
        
        return metrics
    
    def _aggregate_metrics(self, metrics_list: List[Dict[str, float]]) -> Dict[str, Dict[str, float]]:
        """
        Aggregate metrics from multiple validation runs.
        
        Args:
            metrics_list: List of metrics dictionaries
            
        Returns:
            Dict containing aggregate statistics for each metric
        """
        if not metrics_list:
            return {}
            
        # Extract metrics keys from first entry
        metric_keys = [k for k in metrics_list[0].keys() if k != "room_id"]
        agg_metrics = {}
        
        # Calculate statistics for each metric across all runs
        for key in metric_keys:
            # Extract values for this metric across all runs (ignoring NaNs)
            values = [m[key] for m in metrics_list if key in m and not np.isnan(m[key])]
            
            if values:
                agg_metrics[key] = {
                    "mean": np.mean(values),
                    "median": np.median(values),
                    "std": np.std(values),
                    "min": np.min(values),
                    "max": np.max(values),
                    "count": len(values)
                }
            else:
                agg_metrics[key] = {
                    "mean": np.nan,
                    "median": np.nan,
                    "std": np.nan,
                    "min": np.nan,
                    "max": np.nan,
                    "count": 0
                }
        
        return agg_metrics
    
    def _plot_concentration_comparison(self, x: np.ndarray, reference: np.ndarray, 
                                      model: np.ndarray, label: str, params: Dict,
                                      save_path: Optional[str] = None):
        """
        Plot comparison between reference and model concentration values.
        
        Args:
            x: Distance or position values
            reference: Reference concentration values
            model: Model concentration values
            label: Label for the plot
            params: Parameters used for the model
            save_path: Optional path to save the plot
        """
        plt.figure(figsize=(12, 8))
        
        # Plot concentrations
        plt.subplot(2, 1, 1)
        plt.plot(x, reference, 'b-', linewidth=2, label='Reference')
        plt.plot(x, model, 'r--', linewidth=2, label='Model')
        plt.xlabel('Distance (m)')
        plt.ylabel('Concentration')
        plt.title(f'Concentration Comparison - {label}')
        plt.legend()
        plt.grid(True)
        
        # Plot difference
        plt.subplot(2, 1, 2)
        plt.plot(x, model - reference, 'g-', linewidth=2)
        plt.xlabel('Distance (m)')
        plt.ylabel('Difference (Model - Reference)')
        plt.title('Difference')
        plt.grid(True)
        
        # Add parameters as text
        param_text = "\n".join([f"{k}: {v}" for k, v in params.items()])
        plt.figtext(0.02, 0.02, param_text, fontsize=10, 
                    bbox=dict(facecolor='white', alpha=0.5))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300)
            plt.close()
        else:
            plt.show()
    
    def _plot_time_series_comparison(self, time: np.ndarray, reference: np.ndarray,
                                    model: np.ndarray, label: str, params: Dict,
                                    save_path: Optional[str] = None):
        """
        Plot time series comparison between reference and model values.
        
        Args:
            time: Time values
            reference: Reference concentration values
            model: Model concentration values
            label: Label for the plot
            params: Parameters used for the model
            save_path: Optional path to save the plot
        """
        plt.figure(figsize=(12, 8))
        
        # Plot concentrations
        plt.subplot(2, 1, 1)
        plt.plot(time, reference, 'b-', linewidth=2, label='Reference')
        plt.plot(time, model, 'r--', linewidth=2, label='Model')
        plt.xlabel('Time (hours)')
        plt.ylabel('Concentration')
        plt.title(f'Time Series Comparison - {label}')
        plt.legend()
        plt.grid(True)
        
        # Plot difference
        plt.subplot(2, 1, 2)
        plt.plot(time, model - reference, 'g-', linewidth=2)
        plt.xlabel('Time (hours)')
        plt.ylabel('Difference (Model - Reference)')
        plt.title('Difference')
        plt.grid(True)
        
        # Add parameters as text
        param_text = "\n".join([f"{k}: {v}" for k, v in params.items()])
        plt.figtext(0.02, 0.02, param_text, fontsize=10, 
                    bbox=dict(facecolor='white', alpha=0.5))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300)
            plt.close()
        else:
            plt.show()
    
    def _plot_multi_room_comparison(self, ref_data: pd.DataFrame, 
                                   model_result: Dict[str, np.ndarray],
                                   room_ids: List[str], label: str,
                                   save_path: Optional[str] = None):
        """
        Plot multi-room comparison between reference and model values.
        
        Args:
            ref_data: DataFrame with reference data
            model_result: Dict mapping room_id to model concentrations
            room_ids: List of room IDs
            label: Label for the plot
            save_path: Optional path to save the plot
        """
        n_rooms = len(room_ids)
        fig, axes = plt.subplots(n_rooms, 1, figsize=(12, 4 * n_rooms), sharex=True)
        
        if n_rooms == 1:
            axes = [axes]  # Make it a list for consistent indexing
        
        time = ref_data['time'].values
        
        for i, room_id in enumerate(room_ids):
            ref_column = f"{room_id}_concentration"
            ax = axes[i]
            
            if ref_column in ref_data.columns and room_id in model_result:
                ref_conc = ref_data[ref_column].values
                model_conc = model_result[room_id]
                
                ax.plot(time, ref_conc, 'b-', linewidth=2, label='Reference')
                ax.plot(time, model_conc, 'r--', linewidth=2, label='Model')
                ax.set_ylabel('Concentration')
                ax.set_title(f'Room {room_id}')
                ax.legend()
                ax.grid(True)
                
                # Add metrics text
                metrics = self._calculate_metrics(ref_conc, model_conc)
                metrics_text = f"RMSE: {metrics['rmse']:.4f}, R²: {metrics['r_squared']:.4f}"
                ax.text(0.02, 0.90, metrics_text, transform=ax.transAxes, 
                        bbox=dict(facecolor='white', alpha=0.5))
        
        axes[-1].set_xlabel('Time (hours)')
        fig.suptitle(f'Multi-Room Comparison - {label}', fontsize=16)
        
        plt.tight_layout()
        plt.subplots_adjust(top=0.95)
        
        if save_path:
            plt.savefig(save_path, dpi=300)
            plt.close()
        else:
            plt.show()
    
    def _plot_metrics_summary(self, results: Dict[str, Any], 
                             save_path: Optional[str] = None):
        """
        Plot summary of metrics across multiple validation runs.
        
        Args:
            results: Dictionary of validation results
            save_path: Optional path to save the plot
        """
        # Extract metrics
        model_results = results.get("model_results", [])
        if not model_results:
            return
        
        # Extract important metrics to plot
        metrics_to_plot = ["rmse", "r_squared", "correlation", "fractional_bias"]
        
        # Create a unified dataset for plotting
        plot_data = {}
        for metric in metrics_to_plot:
            plot_data[metric] = []
        
        labels = []
        
        for result in model_results:
            if "param_set_id" in result:
                # Gaussian plume case
                labels.append(result["param_set_id"])
                for metric in metrics_to_plot:
                    if metric in result.get("metrics", {}):
                        plot_data[metric].append(result["metrics"][metric])
                    else:
                        plot_data[metric].append(np.nan)
            elif "config_id" in result:
                # Indoor diffusion case
                labels.append(result["config_id"])
                for metric in metrics_to_plot:
                    if metric in result.get("metrics", {}):
                        plot_data[metric].append(result["metrics"][metric])
                    else:
                        plot_data[metric].append(np.nan)
        
        # Create plot
        fig, axes = plt.subplots(len(metrics_to_plot), 1, figsize=(12, 3 * len(metrics_to_plot)))
        
        if len(metrics_to_plot) == 1:
            axes = [axes]  # Make it a list for consistent indexing
        
        metric_titles = {
            "rmse": "Root Mean Square Error",
            "r_squared": "R-squared",
            "correlation": "Correlation Coefficient",
            "fractional_bias": "Fractional Bias"
        }
        
        x = np.arange(len(labels))
        
        for i, metric in enumerate(metrics_to_plot):
            ax = axes[i]
            values = plot_data[metric]
            
            ax.bar(x, values)
            ax.set_ylabel(metric)
            ax.set_title(metric_titles.get(metric, metric))
            ax.set_xticks(x)
            ax.set_xticklabels(labels, rotation=45, ha='right')
            ax.grid(True, axis='y')
            
            # Add aggregated stats
            if metric in results.get("aggregated_metrics", {}):
                agg = results["aggregated_metrics"][metric]
                stats_text = f"Mean: {agg['mean']:.3f}, Median: {agg['median']:.3f}, Std: {agg['std']:.3f}"
                ax.text(0.02, 0.90, stats_text, transform=ax.transAxes, 
                        bbox=dict(facecolor='white', alpha=0.5))
        
        fig.suptitle('Validation Metrics Summary', fontsize=16)
        
        plt.tight_layout()
        plt.subplots_adjust(top=0.95)
        
        if save_path:
            plt.savefig(save_path, dpi=300)
            plt.close()
        else:
            plt.show()


# Convenience function for running validation
def validate_model(model_type: str, model_func: Callable, dataset_id: str, 
                  parameter_mapping: Dict = None) -> Dict[str, Any]:
    """
    Validate a diffusion model against a reference dataset.
    
    Args:
        model_type: Type of model ('gaussian_plume' or 'indoor')
        model_func: Function that implements the model
        dataset_id: Identifier for the dataset to use
        parameter_mapping: Optional mapping from dataset parameters to model parameters
        
    Returns:
        Dict containing validation results
    """
    validator = DiffusionValidator()
    
    if model_type.lower() == 'gaussian_plume':
        return validator.validate_gaussian_plume(model_func, dataset_id, parameter_mapping)
    elif model_type.lower() == 'indoor':
        return validator.validate_indoor_diffusion(model_func, dataset_id, parameter_mapping)
    else:
        raise ValueError(f"Unknown model type: {model_type}. "
                         f"Supported types are 'gaussian_plume' and 'indoor'.")


def list_available_datasets() -> List[Dict]:
    """
    List all available datasets for validation.
    
    Returns:
        List[Dict]: List of available datasets with their details
    """
    validator = DiffusionValidator()
    return validator.list_available_datasets()
