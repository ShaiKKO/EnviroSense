# EnviroSense Dose-Response Curve Fitting System

This module provides comprehensive tools for dose-response modeling, curve fitting, and statistical analysis of exposure-response relationships.

## Overview

The dose-response curve fitting system enables:

- Fitting various curve types to dose-response data
- Statistical model comparison and selection
- Parameter estimation with confidence intervals
- Effective dose calculations
- Visual representation of fitted curves with uncertainty
- Integration with uncertainty propagation

## Key Components

### Dose-Response Model Types

The system supports multiple model types for different dose-response relationships:

- Linear models
- Quadratic models
- Exponential models
- Logistic models
- Log-logistic models
- Probit models
- Hill equation models
- Piecewise linear models with thresholds

### `BaseDoseResponseModel`

Base class for all dose-response models, providing common functionality:

```python
# Example: Fit a log-logistic model to data
from envirosense.core.exposure.dose_response.models import LogLogisticModel

model = LogLogisticModel()
parameters = model.fit(doses, responses)

# Access fitted parameters
bottom = parameters.parameter_values['bottom']
top = parameters.parameter_values['top']
ec50 = parameters.parameter_values['EC50']
hill_slope = parameters.parameter_values['hill_slope']

# Predict responses for new doses
predicted = model.predict(new_doses)
```

### `DoseResponseModelSelector`

Enables automatic selection of the best-fitting model:

```python
# Example: Fit multiple models and select the best
from envirosense.core.exposure.dose_response.models import DoseResponseModelSelector

selector = DoseResponseModelSelector()
selector.fit_all_models(doses, responses)
best_model_type, best_params = selector.select_best_model(criterion='aic')

# Compare models visually
fig = selector.compare_models(doses, responses)
```

### `DoseResponseManager`

High-level manager for working with multiple substances and models:

```python
# Example: Manage multiple dose-response models
from envirosense.core.exposure.dose_response.models import DoseResponseManager

manager = DoseResponseManager()

# Fit a model for a substance
model_id, fitted_model = manager.fit_model(
    substance_id='benzene',
    doses=doses,
    responses=responses,
    auto_select=True
)

# Use the fitted model
predictions = manager.predict_response(model_id, new_doses)
ed50 = manager.calculate_effective_dose(model_id, target_response=0.5)
fig = manager.plot_model(model_id)

# Export/import models
model_data = manager.export_model(model_id)
# ...later
imported_id = manager.import_model(model_data)
```

## Statistical Features

The system provides rich statistical information about fitted models:

- Parameter estimates with confidence intervals
- Standard errors and p-values for parameters
- Covariance matrix for parameter uncertainty
- Goodness-of-fit metrics (AIC, BIC, R-squared)
- Effective dose calculations with confidence intervals

## Integration with Uncertainty Propagation

The dose-response models integrate with the uncertainty propagation system:

```python
# Example: Combine with uncertainty propagation
from envirosense.core.exposure.dose_response.models import DoseResponseModelType, DoseResponseModelSelector
from envirosense.core_platform.uncertainty import UncertainParameter, MonteCarloUncertaintyPropagator
import scipy.stats as stats

# Fit model and get parameters
model_selector = DoseResponseModelSelector()
model = model_selector.get_model(DoseResponseModelType.LOG_LOGISTIC)
parameters = model.fit(doses, responses)

# Create uncertain parameters based on fitted parameters
uncertain_params = {}
for name, value in parameters.parameter_values.items():
    ci = parameters.confidence_intervals[name]
    std_dev = (ci[1] - ci[0]) / 3.92  # approximation
    
    # Create appropriate distribution
    if name in ['bottom', 'top']:
        # Beta or truncated normal for [0,1] bounded parameters
        dist = stats.truncnorm((0 - value) / std_dev, (1 - value) / std_dev, loc=value, scale=std_dev)
    elif name in ['EC50']:
        # Log-normal for positive parameters
        sigma = np.sqrt(np.log(1 + (std_dev/value)**2))
        mu = np.log(value) - sigma**2/2
        dist = stats.lognorm(s=sigma, scale=np.exp(mu))
    else:
        # Normal for unconstrained parameters
        dist = stats.norm(loc=value, scale=std_dev)
        
    uncertain_params[name] = UncertainParameter(
        name=name,
        value=value,
        distribution=dist,
        bounds=(ci[0], ci[1])
    )

# Propagate uncertainty
mc_propagator = MonteCarloUncertaintyPropagator(n_samples=10000)
result = mc_propagator.propagate(
    function=lambda **params: model.predict(test_dose, list(params.values())),
    parameters=uncertain_params
)

# Access results
mean_response = result['mean']
ci_95 = result['confidence_intervals']['95']
```

## Example Code

See the full examples:

1. `envirosense/core/exposure/dose_response/examples/linear_example.py`: Simple linear model fitting
2. `envirosense/core/exposure/dose_response/examples/uncertainty_example.py`: Advanced example with uncertainty propagation

## Applications

The dose-response curve fitting system can be used for:

- Chemical toxicity assessment
- Pharmaceutical drug efficacy modeling
- Environmental pollutant impact analysis
- Radiation exposure response modeling
- Hormesis effect characterization (non-monotonic responses)
- Benchmark dose calculation for regulatory purposes
- Species sensitivity distribution analysis
- Combined exposure effects modeling
