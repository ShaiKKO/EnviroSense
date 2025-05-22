# EnviroSense Uncertainty Propagation System

This module provides a comprehensive framework for uncertainty quantification and propagation in environmental simulations, dose-response modeling, and exposure assessment.

## Overview

The uncertainty propagation system enables:

- Representation of uncertain parameters with various probability distributions
- Monte Carlo propagation of uncertainty through arbitrary functions
- Analytical uncertainty propagation using first-order error propagation
- Sensitivity analysis to identify key parameters affecting uncertainty
- Confidence interval calculations for predictions
- Specialized tools for cumulative effect modeling

## Key Components

### `UncertainParameter`

A class representing a parameter with associated uncertainty:

```python
# Example: Create an uncertain parameter with log-normal distribution
from envirosense.core_platform.uncertainty import UncertainParameter
import scipy.stats as stats

half_life = UncertainParameter(
    name='half_life',
    value=3600.0,  # seconds
    distribution=stats.lognorm(s=0.2, scale=3600.0),
    bounds=(360.0, 36000.0)  # 10x bounds
)
```

### `MonteCarloUncertaintyPropagator`

Provides Monte Carlo uncertainty propagation for arbitrary functions:

```python
# Example: Propagate uncertainty using Monte Carlo
from envirosense.core_platform.uncertainty import MonteCarloUncertaintyPropagator

def my_model(param1, param2):
    return param1 * param2**2

uncertain_params = {
    'param1': UncertainParameter(...),
    'param2': UncertainParameter(...)
}

mc_propagator = MonteCarloUncertaintyPropagator(n_samples=10000)
result = mc_propagator.propagate(
    function=my_model,
    parameters=uncertain_params
)

# Access results
mean = result['mean']
std_dev = result['std']
ci_95 = result['confidence_intervals']['95']
```

### `AnalyticalUncertaintyPropagator`

Provides analytical uncertainty propagation using linearization:

```python
# Example: Propagate uncertainty using analytical methods
from envirosense.core_platform.uncertainty import AnalyticalUncertaintyPropagator

analytical_propagator = AnalyticalUncertaintyPropagator()
result = analytical_propagator.propagate(
    function=my_model,
    parameters=uncertain_params
)
```

### `CumulativeEffectUncertaintyPropagator`

Specialized propagator for cumulative effect modeling:

```python
# Example: Propagate uncertainty in cumulative effects
from envirosense.core_platform.uncertainty import CumulativeEffectUncertaintyPropagator

ce_propagator = CumulativeEffectUncertaintyPropagator(cumulative_model)
result = ce_propagator.propagate_threshold_crossing_uncertainty(
    substance_id='benzene',
    future_exposure_scenario=[...]
)
```

## Usage with Dose-Response Modeling

The uncertainty propagation system integrates with the dose-response modeling system:

```python
# Example: Combine uncertainty propagation with dose-response modeling
from envirosense.core.exposure.dose_response.models import DoseResponseModelType, DoseResponseModelSelector
from envirosense.core_platform.uncertainty import UncertainParameter, MonteCarloUncertaintyPropagator

# 1. Fit a dose-response model
model_selector = DoseResponseModelSelector()
log_logistic_model = model_selector.get_model(DoseResponseModelType.LOG_LOGISTIC)
params = log_logistic_model.fit(doses, responses)

# 2. Create uncertain parameters from fitted model
uncertain_params = {}
for name, value in params.parameter_values.items():
    ci = params.confidence_intervals[name]
    # Create appropriate distribution based on parameter characteristics
    # ...
    uncertain_params[name] = UncertainParameter(...)

# 3. Define dose-response function for uncertainty propagation
def dose_response_function(bottom, top, EC50, hill_slope, dose=5.0):
    return bottom + (top - bottom) / (1 + (dose / EC50) ** (-hill_slope))

# 4. Propagate uncertainty
mc_propagator = MonteCarloUncertaintyPropagator(n_samples=10000)
result = mc_propagator.propagate(
    function=dose_response_function,
    parameters=uncertain_params,
    dose=dose  # Additional argument to function
)
```

## Example Code

See the full example script at `envirosense/core/exposure/dose_response/examples/uncertainty_example.py` that demonstrates:

1. Fitting a dose-response curve model to data
2. Creating uncertain parameters from the fitted model
3. Propagating uncertainty through the dose-response function
4. Comparing Monte Carlo and analytical approaches
5. Calculating effective doses with uncertainty bounds
6. Visualizing uncertainty in dose-response relationships

Run the example:

```bash
cd path/to/envirosense
python -m envirosense.core.exposure.dose_response.examples.uncertainty_example
```

## Integration with Other Modules

The uncertainty propagation system is designed to work seamlessly with multiple EnviroSense modules:

- **Dose-Response Modeling**: Quantify uncertainty in parameter estimates and predictions
- **Physiological Response Modeling**: Propagate uncertainty through physiological response models
- **Exposure Assessment**: Provide confidence intervals for exposure estimates
- **Spatial Modeling**: Incorporate uncertainty in spatial interpolation and diffusion models
- **Time Series Analysis**: Account for uncertainty in temporal patterns and predictions
