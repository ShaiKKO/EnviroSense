"""
Example demonstrating uncertainty propagation in dose-response modeling.

This example shows how to combine the uncertainty propagation system with
dose-response curve fitting to generate predictions with confidence intervals.
"""

import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import sys
import os

# Add parent directory to path for imports to work when running directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from envirosense.core.exposure.dose_response.models import (
    DoseResponseModelType, 
    LogLogisticModel, 
    DoseResponseModelSelector
)
from envirosense.core_platform.uncertainty import (
    UncertainParameter,
    MonteCarloUncertaintyPropagator,
    AnalyticalUncertaintyPropagator
)
import scipy.stats as stats


def demonstrate_uncertainty_in_dose_response():
    """Demonstrate uncertainty propagation in dose-response modeling."""
    # 1. Generate synthetic dose-response data with noise
    true_bottom = 0.05
    true_top = 0.95
    true_ec50 = 10.0
    true_hill_slope = 2.0
    
    np.random.seed(42)  # For reproducibility
    
    # Generate doses on a log scale
    doses = np.logspace(-1, 2, 20)
    
    # Generate true responses from log-logistic model
    true_responses = true_bottom + (true_top - true_bottom) / (
        1 + (doses / true_ec50) ** (-true_hill_slope)
    )
    
    # Add noise to create observed data
    noise_level = 0.05
    observed_responses = true_responses + np.random.normal(0, noise_level, len(doses))
    observed_responses = np.clip(observed_responses, 0, 1)  # Ensure responses are between 0 and 1
    
    # 2. Fit dose-response model
    print("Fitting dose-response model...")
    model_selector = DoseResponseModelSelector()
    log_logistic_model = model_selector.get_model(DoseResponseModelType.LOG_LOGISTIC)
    parameters = log_logistic_model.fit(doses, observed_responses)
    
    # Print fitted parameters
    print("\nFitted Model Parameters:")
    for name, value in parameters.parameter_values.items():
        ci = parameters.confidence_intervals[name]
        print(f"  {name}: {value:.4f} (95% CI: {ci[0]:.4f} - {ci[1]:.4f})")
    
    # 3. Define uncertain parameters based on fitted model
    print("\nCreating uncertain parameters...")
    uncertain_params = {}
    for name, value in parameters.parameter_values.items():
        ci = parameters.confidence_intervals[name]
        # Estimate standard deviation from confidence interval
        std_dev = (ci[1] - ci[0]) / 3.92  # 3.92 is approximately 2*1.96 (95% CI)
        
        # Create distribution based on parameter characteristics
        if name in ['bottom', 'top']:
            # Beta distribution for parameters bounded between 0 and 1
            # Convert mean and std to alpha, beta parameters
            mean = value
            var = std_dev**2
            if var >= mean * (1 - mean):  # Check for valid parameters
                # Fall back to normal if beta doesn't fit well
                dist = stats.truncnorm(
                    (0 - mean) / std_dev, 
                    (1 - mean) / std_dev, 
                    loc=mean, 
                    scale=std_dev
                )
            else:
                alpha = mean * (mean * (1 - mean) / var - 1)
                beta = (1 - mean) * (mean * (1 - mean) / var - 1)
                dist = stats.beta(alpha, beta)
        elif name in ['EC50']:
            # Log-normal for strictly positive parameters
            # Convert mean and std to log-normal parameters
            if value > 0:
                sigma = np.sqrt(np.log(1 + (std_dev/value)**2))
                mu = np.log(value) - sigma**2/2
                dist = stats.lognorm(s=sigma, scale=np.exp(mu))
            else:
                # Fallback for non-positive values
                dist = stats.norm(loc=value, scale=std_dev)
        else:
            # Normal distribution for unconstrained parameters
            dist = stats.norm(loc=value, scale=std_dev)
            
        uncertain_params[name] = UncertainParameter(
            name=name,
            value=value,
            distribution=dist,
            bounds=(ci[0], ci[1])
        )
        
        print(f"  Created uncertain parameter for {name}")
    
    # 4. Define dose-response function for uncertainty propagation
    def dose_response_function(bottom, top, EC50, hill_slope, dose=5.0):
        """Log-logistic dose-response function."""
        return bottom + (top - bottom) / (1 + (dose / EC50) ** (-hill_slope))
    
    # 5. Propagate uncertainty using Monte Carlo
    print("\nPropagating uncertainty using Monte Carlo...")
    mc_propagator = MonteCarloUncertaintyPropagator(n_samples=10000)
    
    # Create correlation matrix (we'll assume parameters are uncorrelated for simplicity)
    n_params = len(uncertain_params)
    correlation_matrix = np.eye(n_params)
    
    # For a range of doses, calculate response with uncertainty
    test_doses = np.logspace(-1, 2, 100)
    results = []
    
    for dose in test_doses:
        result = mc_propagator.propagate(
            function=dose_response_function,
            parameters=uncertain_params,
            correlation_matrix=correlation_matrix,
            dose=dose  # Pass the current dose as a keyword argument
        )
        results.append(result)
    
    # 6. Try analytical propagation for comparison
    print("Propagating uncertainty using analytical method...")
    analytical_propagator = AnalyticalUncertaintyPropagator()
    analytical_results = []
    
    for dose in test_doses:
        try:
            result = analytical_propagator.propagate(
                function=dose_response_function,
                parameters=uncertain_params,
                correlation_matrix=correlation_matrix,
                dose=dose
            )
            analytical_results.append(result)
        except Exception as e:
            print(f"  Analytical propagation failed for dose {dose}: {str(e)}")
            # If analytical fails, use MC result
            analytical_results.append(results[len(analytical_results)])
    
    # 7. Extract results for plotting
    mean_responses = [result['mean'] for result in results]
    lower_bounds = [result['confidence_intervals']['95'][0] for result in results]
    upper_bounds = [result['confidence_intervals']['95'][1] for result in results]
    
    analytical_means = []
    analytical_lower = []
    analytical_upper = []
    
    for result in analytical_results:
        if 'mean' in result:
            analytical_means.append(result['mean'])
            analytical_lower.append(result['confidence_intervals']['95'][0])
            analytical_upper.append(result['confidence_intervals']['95'][1])
        else:
            analytical_means.append(np.nan)
            analytical_lower.append(np.nan)
            analytical_upper.append(np.nan)
    
    # 8. Plot results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    plt.figure(figsize=(12, 8))
    
    # Plot the original data points
    plt.scatter(doses, observed_responses, color='blue', label='Observed Data', alpha=0.6, s=30)
    
    # Plot the true curve
    plt.plot(test_doses, true_bottom + (true_top - true_bottom) / (1 + (test_doses/true_ec50)**(-true_hill_slope)), 
             'k--', label='True Curve', alpha=0.7)
    
    # Plot the fitted curve with Monte Carlo confidence bands
    plt.plot(test_doses, mean_responses, 'r-', label='Fitted Model (MC)')
    plt.fill_between(test_doses, lower_bounds, upper_bounds, color='red', alpha=0.2, label='95% CI (MC)')
    
    # Plot analytical results if available
    if len(analytical_means) > 0 and not all(np.isnan(analytical_means)):
        plt.plot(test_doses, analytical_means, 'g--', label='Analytical Approximation')
        plt.fill_between(test_doses, analytical_lower, analytical_upper, color='green', alpha=0.1, label='95% CI (Analytical)')
    
    plt.xscale('log')
    plt.xlabel('Dose (log scale)')
    plt.ylabel('Response')
    plt.title('Dose-Response Curve with Uncertainty Propagation')
    plt.grid(alpha=0.3)
    plt.legend()
    
    # Add parameter information as text
    param_text = "Fitted Parameters:\n"
    for name, value in parameters.parameter_values.items():
        ci = parameters.confidence_intervals[name]
        param_text += f"{name}: {value:.4f} ({ci[0]:.4f}, {ci[1]:.4f})\n"
    
    plt.figtext(0.02, 0.02, param_text, fontsize=9,
                bbox={'facecolor': 'white', 'alpha': 0.8, 'pad': 5})
    
    # Save figure
    os.makedirs('output/uncertainty_examples', exist_ok=True)
    plt.savefig(f'output/uncertainty_examples/dose_response_uncertainty_{timestamp}.png', dpi=300, bbox_inches='tight')
    print(f"\nPlot saved to output/uncertainty_examples/dose_response_uncertainty_{timestamp}.png")
    
    plt.tight_layout()
    plt.show()
    
    # 9. Calculate effective dose with uncertainty
    target_response = 0.5  # EC50 by definition
    print("\nCalculating effective dose for 50% response...")
    
    # Calculate effective dose from fitted model
    ed50_result = log_logistic_model.calculate_effective_dose(target_response)
    
    if 'effective_dose' in ed50_result:
        ed50 = ed50_result['effective_dose']
        ed50_lower = ed50_result.get('lower_bound')
        ed50_upper = ed50_result.get('upper_bound')
        
        print(f"  EC50: {ed50:.4f}")
        if ed50_lower is not None and ed50_upper is not None:
            print(f"  95% CI: ({ed50_lower:.4f}, {ed50_upper:.4f})")
            
        # Verify using uncertainty propagation
        print("\nVerifying using uncertainty propagation...")
        
        # Define inverse function (find dose for given response)
        def inverse_dose_response(bottom, top, EC50, hill_slope, target_response=0.5):
            """Calculate the dose that produces a given response."""
            if bottom >= target_response >= top or top <= target_response <= bottom:
                return np.nan  # Response not achievable
            
            # Rearrange the log-logistic equation to solve for dose
            term = (top - bottom) / (target_response - bottom) - 1
            if term <= 0:
                return np.nan  # Invalid term
            
            return EC50 * term ** (1/hill_slope)
        
        # Propagate uncertainty for inverse function
        inverse_result = mc_propagator.propagate(
            function=inverse_dose_response,
            parameters=uncertain_params,
            correlation_matrix=correlation_matrix,
            target_response=target_response
        )
        
        if 'mean' in inverse_result:
            print(f"  Monte Carlo EC50: {inverse_result['mean']:.4f}")
            print(f"  Monte Carlo 95% CI: ({inverse_result['confidence_intervals']['95'][0]:.4f}, "
                  f"{inverse_result['confidence_intervals']['95'][1]:.4f})")
            
            # Print most sensitive parameters
            if 'sensitivity' in inverse_result:
                print("\nSensitivity analysis:")
                sensitivities = sorted(
                    [(name, sensitivity['correlation']**2) 
                     for name, sensitivity in inverse_result['sensitivity'].items()],
                    key=lambda x: abs(x[1]),
                    reverse=True
                )
                
                for name, r2 in sensitivities:
                    print(f"  {name}: {r2:.4f} (R² contribution)")
    else:
        print("  Effective dose calculation failed")
    
    print("\nUncertainty propagation example completed.")


if __name__ == "__main__":
    demonstrate_uncertainty_in_dose_response()
