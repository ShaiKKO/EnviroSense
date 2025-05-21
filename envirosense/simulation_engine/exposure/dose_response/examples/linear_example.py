"""
Example demonstrating the use of LinearDoseResponse model.

This example shows how to create, fit, and use a linear dose-response model
with different fitting methods and uncertainty quantification.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from typing import Tuple
import os

from envirosense.core.exposure.dose_response import LinearDoseResponse
from envirosense.core.exposure.dose_response.types import (
    ResponseType, DoseUnit, ResponseUnit,
    UncertaintyType
)


def generate_sample_data(
    true_intercept: float = 0.05, 
    true_slope: float = 0.2, 
    noise_level: float = 0.02, 
    sample_size: int = 20,
    random_seed: int = 42
) -> Tuple[np.ndarray, np.ndarray]:
    """Generate synthetic dose-response data with noise."""
    np.random.seed(random_seed)
    
    # Generate dose values (concentrations)
    doses = np.random.uniform(0.0, 5.0, sample_size)
    doses.sort()  # Sort for clearer visualization
    
    # Generate responses with noise
    true_responses = true_intercept + true_slope * doses
    noise = np.random.normal(0, noise_level, sample_size)
    observed_responses = true_responses + noise
    
    # Ensure responses are within reasonable bounds (0-1 for probability)
    observed_responses = np.clip(observed_responses, 0.0, 1.0)
    
    return doses, observed_responses


def plot_model_fit(
    model: LinearDoseResponse, 
    doses: np.ndarray, 
    responses: np.ndarray, 
    title: str, 
    method: str,
    save_path: str = None
) -> plt.Figure:
    """Plot the model fit with uncertainty bands."""
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot observed data points
    ax.scatter(doses, responses, color='blue', alpha=0.7, label='Observed Data')
    
    # Generate smooth dose range for plotting the curve
    x_plot = np.linspace(0, max(doses) * 1.1, 100)
    
    # Predict with uncertainty
    y_pred, y_lower, y_upper = model.predict(
        x_plot,
        include_uncertainty=True,
        confidence_level=0.95,
        method=method
    )
    
    # Plot the fitted curve
    ax.plot(x_plot, y_pred, color='red', label=f'Fitted Curve (Slope={model.slope:.4f})')
    
    # Plot the confidence bands
    ax.fill_between(
        x_plot, y_lower, y_upper, 
        color='red', alpha=0.2,
        label='95% Confidence Interval'
    )
    
    # Add model information text
    info_text = (
        f"Model: Linear Dose Response\n"
        f"Fitting Method: {model.metadata.get('fit_diagnostics', {}).get('method', method)}\n"
        f"Intercept: {model.intercept:.4f} ± {model._uncertainty['intercept']:.4f}\n"
        f"Slope: {model.slope:.4f} ± {model._uncertainty['slope']:.4f}"
    )
    
    # Add R-squared if available
    r_squared = model.metadata.get('fit_diagnostics', {}).get('r_squared')
    if r_squared is not None:
        info_text += f"\nR²: {r_squared:.4f}"
    
    # Add text box
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
    ax.text(
        0.05, 0.95, info_text,
        transform=ax.transAxes, fontsize=10,
        verticalalignment='top', bbox=props
    )
    
    # Customize plot
    ax.set_xlabel('Dose')
    ax.set_ylabel('Response')
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    plt.tight_layout()
    
    # Save figure if path is provided
    if save_path:
        dirname = os.path.dirname(save_path)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname)
        plt.savefig(save_path, dpi=300)
        print(f"Figure saved to {save_path}")
    
    return fig


def compare_fitting_methods() -> None:
    """Compare different fitting methods for the same dataset."""
    # Generate sample data
    doses, responses = generate_sample_data(
        true_intercept=0.05, 
        true_slope=0.2, 
        noise_level=0.03,
        sample_size=30
    )
    
    # Add a few outliers
    outlier_indices = [5, 15, 25]
    responses[outlier_indices] = [0.8, 0.1, 0.9]
    
    # Add heteroscedastic noise (increasing variance with dose)
    additional_noise = np.random.normal(0, 0.01 * doses, len(doses))
    responses += additional_noise
    responses = np.clip(responses, 0.0, 1.0)  # Ensure within bounds
    
    # Create weights for weighted least squares
    # (inverse of variance, higher weight for more precise measurements)
    weights = 1.0 / (0.01 + 0.02 * doses)
    
    # Fitting methods to compare
    methods = ['ols', 'wls', 'robust', 'bayesian']
    
    # Initialize the models
    models = {}
    for method in methods:
        model = LinearDoseResponse(
            chemical_id='example_chemical',
            response_type=ResponseType.CONTINUOUS,
            dose_unit=DoseUnit.MG_PER_KG,
            response_unit=ResponseUnit.FRACTION,
            description=f'Example linear model using {method} fitting method'
        )
        
        # Fit with appropriate method
        if method == 'wls':
            model.fit(doses, responses, method=method, weights=weights)
        else:
            model.fit(doses, responses, method=method)
            
        models[method] = model
        
    # Output directory
    output_dir = 'envirosense/output/dose_response_examples/'
    
    # Plot the results
    method_names = {
        'ols': 'Ordinary Least Squares',
        'wls': 'Weighted Least Squares',
        'robust': 'Robust Regression',
        'bayesian': 'Bayesian Estimation'
    }
    
    for method, model in models.items():
        title = f"Linear Dose-Response -- {method_names[method]}"
        uncertainty_method = 'bayesian' if method == 'bayesian' else 'analytical'
        
        fig = plot_model_fit(
            model, doses, responses, title, uncertainty_method,
            save_path=f"{output_dir}{method}_linear_fit.png"
        )
        plt.close(fig)
        
    print("All plots saved to:", output_dir)
    
    # Print parameter comparison table
    print("\nParameter Estimates Comparison:\n")
    print(f"{'Method':<20} {'Intercept':<15} {'Slope':<15}")
    print("-" * 50)
    
    for method, model in models.items():
        intercept = f"{model.intercept:.4f} ± {model._uncertainty['intercept']:.4f}"
        slope = f"{model.slope:.4f} ± {model._uncertainty['slope']:.4f}"
        print(f"{method_names[method]:<20} {intercept:<15} {slope:<15}")


def demonstrate_prediction_uncertainty() -> None:
    """Demonstrate the different methods for prediction uncertainty."""
    # Generate sample data
    doses, responses = generate_sample_data(
        true_intercept=0.05, 
        true_slope=0.2, 
        noise_level=0.02,
        sample_size=25
    )
    
    # Create and fit model
    model = LinearDoseResponse(
        chemical_id='example_chemical',
        response_type=ResponseType.CONTINUOUS,
        dose_unit=DoseUnit.MG_PER_KG,
        response_unit=ResponseUnit.FRACTION,
        description='Example linear model for prediction uncertainty comparison'
    )
    
    # Fit model using OLS
    model.fit(doses, responses, method='ols')
    
    # Output directory
    output_dir = 'envirosense/output/dose_response_examples/'
    
    # Compare uncertainty methods
    uncertainty_methods = ['analytical', 'monte_carlo']
    
    for method in uncertainty_methods:
        title = f"Linear Dose-Response -- Prediction Uncertainty ({method})"
        
        fig = plot_model_fit(
            model, doses, responses, title, method,
            save_path=f"{output_dir}uncertainty_{method}_linear.png"
        )
        plt.close(fig)
        
    print("All uncertainty plots saved to:", output_dir)


def main() -> None:
    """Main function to run all examples."""
    # Ensure output directory exists
    output_dir = 'envirosense/output/dose_response_examples/'
    os.makedirs(output_dir, exist_ok=True)
    
    # Run examples
    compare_fitting_methods()
    demonstrate_prediction_uncertainty()


if __name__ == "__main__":
    main()
