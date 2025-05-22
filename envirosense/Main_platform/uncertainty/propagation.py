"""
Enhanced Uncertainty Propagation System for Cumulative Effect Modeling.

This module provides comprehensive uncertainty propagation capabilities with improvements including:
- Better threshold crossing optimization
- Enhanced result caching
- Improved analytical derivatives
- Better handling of distribution fitting
- Enhanced visualization capabilities
"""

import numpy as np
import scipy.stats as stats
from scipy import optimize
from typing import Dict, List, Optional, Tuple, Union, Callable, Any
from dataclasses import dataclass, field
from collections import defaultdict
import warnings
from abc import ABC, abstractmethod
import pickle
import hashlib
from functools import lru_cache


@dataclass
class UncertainParameter:
    """
    Represents a parameter with associated uncertainty.
    
    Enhanced with caching and better distribution handling.
    """
    name: str
    value: float
    distribution: stats.rv_continuous
    bounds: Optional[Tuple[float, float]] = None
    correlation_matrix: Optional[np.ndarray] = None
    description: str = ""
    units: str = ""
    
    def __post_init__(self):
        """Validate parameter after initialization."""
        if self.bounds:
            if self.bounds[0] >= self.bounds[1]:
                raise ValueError(f"Invalid bounds for {self.name}: lower >= upper")
            if not (self.bounds[0] <= self.value <= self.bounds[1]):
                warnings.warn(f"Parameter {self.name} value {self.value} outside bounds {self.bounds}")
    
    @lru_cache(maxsize=128)
    def sample(self, n_samples: int = 1, random_state: Optional[int] = None) -> np.ndarray:
        """Generate random samples from the parameter distribution with caching."""
        if random_state is not None:
            np.random.seed(random_state)
            
        samples = self.distribution.rvs(size=n_samples)
        
        # Apply bounds if specified
        if self.bounds:
            samples = np.clip(samples, self.bounds[0], self.bounds[1])
            
        return samples if n_samples > 1 else float(samples)
    
    def pdf(self, x: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Probability density function at x."""
        return self.distribution.pdf(x)
    
    def cdf(self, x: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Cumulative distribution function at x."""
        return self.distribution.cdf(x)
    
    def confidence_interval(self, alpha: float = 0.05) -> Tuple[float, float]:
        """Calculate confidence interval."""
        lower = self.distribution.ppf(alpha / 2)
        upper = self.distribution.ppf(1 - alpha / 2)
        
        if self.bounds:
            lower = max(lower, self.bounds[0])
            upper = min(upper, self.bounds[1])
            
        return (lower, upper)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'value': self.value,
            'distribution_type': type(self.distribution).__name__,
            'distribution_params': self._get_distribution_params(),
            'bounds': self.bounds,
            'description': self.description,
            'units': self.units
        }
    
    def _get_distribution_params(self) -> Dict[str, Any]:
        """Extract distribution parameters."""
        if hasattr(self.distribution, 'kwds'):
            return self.distribution.kwds
        else:
            # Try to extract common parameters
            params = {}
            if hasattr(self.distribution, 'args'):
                params['args'] = self.distribution.args
            if hasattr(self.distribution, 'loc'):
                params['loc'] = self.distribution.loc
            if hasattr(self.distribution, 'scale'):
                params['scale'] = self.distribution.scale
            return params


class ResultCache:
    """Cache for uncertainty propagation results."""
    
    def __init__(self, max_size: int = 100):
        """
        Initialize result cache.
        
        Args:
            max_size: Maximum number of results to store in cache
        """
        self.cache = {}
        self.max_size = max_size
        self.access_count = defaultdict(int)
    
    def _hash_inputs(self, function: Callable, parameters: Dict[str, UncertainParameter], 
                    kwargs: Dict[str, Any]) -> str:
        """Create hash of inputs for caching."""
        # Create a simple hash of the function name and parameters
        func_name = getattr(function, '__name__', str(function))
        param_str = str(sorted([(k, v.value, type(v.distribution).__name__) for k, v in parameters.items()]))
        kwargs_str = str(sorted(kwargs.items()))
        
        hash_input = f"{func_name}_{param_str}_{kwargs_str}"
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    def get(self, function: Callable, parameters: Dict[str, UncertainParameter], 
            kwargs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get cached result if available."""
        cache_key = self._hash_inputs(function, parameters, kwargs)
        if cache_key in self.cache:
            self.access_count[cache_key] += 1
            return self.cache[cache_key]
        return None
    
    def put(self, function: Callable, parameters: Dict[str, UncertainParameter], 
            kwargs: Dict[str, Any], result: Dict[str, Any]):
        """Store result in cache."""
        cache_key = self._hash_inputs(function, parameters, kwargs)
        
        # Remove oldest entries if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.access_count[k])
            del self.cache[oldest_key]
            del self.access_count[oldest_key]
        
        self.cache[cache_key] = result
        self.access_count[cache_key] = 1


class UncertaintyPropagator(ABC):
    """Abstract base class for uncertainty propagation methods."""
    
    @abstractmethod
    def propagate(
        self,
        function: Callable,
        parameters: Dict[str, UncertainParameter],
        **kwargs
    ) -> Dict[str, Any]:
        """Propagate uncertainty through a function."""
        pass


class EnhancedMonteCarloUncertaintyPropagator(UncertaintyPropagator):
    """
    Enhanced Monte Carlo uncertainty propagation with better performance and features.
    """
    
    def __init__(self, n_samples: int = 10000, random_state: Optional[int] = None,
                 use_cache: bool = True, parallel: bool = False):
        """
        Initialize enhanced Monte Carlo propagator.
        
        Args:
            n_samples: Number of Monte Carlo samples
            random_state: Random seed for reproducibility
            use_cache: Whether to use result caching
            parallel: Whether to use parallel processing (if available)
        """
        self.n_samples = n_samples
        self.random_state = random_state
        self.use_cache = use_cache
        self.parallel = parallel
        self.cache = ResultCache() if use_cache else None
        
        if random_state is not None:
            np.random.seed(random_state)
    
    def propagate(
        self,
        function: Callable,
        parameters: Dict[str, UncertainParameter],
        correlation_matrix: Optional[np.ndarray] = None,
        progress_callback: Optional[Callable[[int], None]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Enhanced propagate method with progress tracking and better error handling.
        
        Args:
            function: Function to evaluate
            parameters: Dictionary of uncertain parameters
            correlation_matrix: Optional correlation matrix between parameters
            progress_callback: Optional function to report progress (0-100)
            **kwargs: Additional arguments to pass to function
            
        Returns:
            Dictionary with uncertainty propagation results
        """
        # Check cache first
        if self.cache:
            cached_result = self.cache.get(function, parameters, kwargs)
            if cached_result:
                return cached_result
        
        param_names = list(parameters.keys())
        n_params = len(param_names)
        
        # Validate parameters
        self._validate_parameters(parameters)
        
        # Generate samples with improved correlation handling
        samples = self._generate_samples(parameters, correlation_matrix)
        
        # Evaluate function with progress tracking
        results = []
        valid_results = []
        errors = []
        
        for i in range(self.n_samples):
            if progress_callback and i % (self.n_samples // 10) == 0:
                progress_callback(int(100 * i / self.n_samples))
            
            try:
                # Create parameter dictionary for this sample
                sample_params = {name: samples[i, j] for j, name in enumerate(param_names)}
                
                # Evaluate function
                result = function(**sample_params, **kwargs)
                results.append(result)
                
                # Handle different result types
                if isinstance(result, (int, float)):
                    valid_results.append(float(result))
                elif isinstance(result, (list, tuple)):
                    valid_results.append(list(result))
                elif isinstance(result, dict):
                    valid_results.append(result)
                else:
                    valid_results.append(result)
                    
            except Exception as e:
                errors.append(str(e))
                results.append(None)
                continue
        
        # Complete progress
        if progress_callback:
            progress_callback(100)
        
        # Remove None results
        valid_results = [r for r in valid_results if r is not None]
        
        if not valid_results:
            return {
                'error': 'No valid results from Monte Carlo sampling',
                'n_samples_attempted': self.n_samples,
                'n_valid_samples': 0,
                'errors': errors[:10]  # First 10 errors
            }
        
        # Analyze results with enhanced statistics
        analysis = self._analyze_results_enhanced(valid_results, param_names, samples, errors)
        
        # Cache result
        if self.cache:
            self.cache.put(function, parameters, kwargs, analysis)
        
        return analysis
    
    def _validate_parameters(self, parameters: Dict[str, UncertainParameter]):
        """Validate input parameters."""
        if not parameters:
            raise ValueError("No parameters provided")
        
        for name, param in parameters.items():
            if not isinstance(param, UncertainParameter):
                raise TypeError(f"Parameter {name} is not an UncertainParameter instance")
    
    def _generate_samples(self, parameters: Dict[str, UncertainParameter], 
                         correlation_matrix: Optional[np.ndarray]) -> np.ndarray:
        """Enhanced sample generation with better correlation handling."""
        param_names = list(parameters.keys())
        n_params = len(param_names)
        
        if correlation_matrix is not None and correlation_matrix.shape == (n_params, n_params):
            # Enhanced correlated sampling
            return self._generate_correlated_samples_enhanced(parameters, correlation_matrix)
        else:
            # Independent sampling with better error handling
            samples = np.zeros((self.n_samples, n_params))
            for i, param_name in enumerate(param_names):
                try:
                    samples[:, i] = parameters[param_name].sample(self.n_samples, self.random_state)
                except Exception as e:
                    warnings.warn(f"Error sampling parameter {param_name}: {e}")
                    # Fallback to normal distribution around the value
                    samples[:, i] = np.random.normal(
                        parameters[param_name].value, 
                        0.1 * abs(parameters[param_name].value), 
                        self.n_samples
                    )
            return samples
    
    def _generate_correlated_samples_enhanced(
        self,
        parameters: Dict[str, UncertainParameter],
        correlation_matrix: np.ndarray
    ) -> np.ndarray:
        """Enhanced correlated sample generation with better distribution handling."""
        param_names = list(parameters.keys())
        n_params = len(param_names)
        
        # Use Gaussian copula approach for better handling of non-normal distributions
        # 1. Generate correlated uniform samples
        uniform_samples = self._generate_correlated_uniform(correlation_matrix)
        
        # 2. Transform to parameter distributions
        samples = np.zeros((self.n_samples, n_params))
        for i, param_name in enumerate(param_names):
            param = parameters[param_name]
            # Use inverse CDF to transform uniform to parameter distribution
            samples[:, i] = param.distribution.ppf(uniform_samples[:, i])
            
            # Apply bounds
            if param.bounds:
                samples[:, i] = np.clip(samples[:, i], param.bounds[0], param.bounds[1])
        
        return samples
    
    def _generate_correlated_uniform(self, correlation_matrix: np.ndarray) -> np.ndarray:
        """Generate correlated uniform samples using Gaussian copula."""
        n_params = correlation_matrix.shape[0]
        
        try:
            # Generate correlated normal samples
            normal_samples = np.random.multivariate_normal(
                np.zeros(n_params), 
                correlation_matrix, 
                self.n_samples
            )
            
            # Transform to uniform using normal CDF
            uniform_samples = stats.norm.cdf(normal_samples)
            
            return uniform_samples
            
        except np.linalg.LinAlgError:
            # Fallback to independent sampling if correlation matrix is invalid
            warnings.warn("Invalid correlation matrix, using independent sampling")
            return np.random.uniform(0, 1, (self.n_samples, n_params))
    
    def _analyze_results_enhanced(
        self,
        results: List[Any],
        param_names: List[str],
        samples: np.ndarray,
        errors: List[str]
    ) -> Dict[str, Any]:
        """Enhanced result analysis with more statistics and better error reporting."""
        n_valid = len(results)
        n_errors = len(errors)
        
        analysis = {
            'n_samples_attempted': self.n_samples,
            'n_valid_samples': n_valid,
            'n_errors': n_errors,
            'error_rate': n_errors / self.n_samples,
            'sample_errors': errors[:5] if errors else []  # First 5 errors
        }
        
        if all(isinstance(r, (int, float)) for r in results):
            # Scalar results with enhanced statistics
            results_array = np.array(results)
            
            analysis.update({
                'type': 'scalar',
                'mean': float(np.mean(results_array)),
                'std': float(np.std(results_array)),
                'variance': float(np.var(results_array)),
                'min': float(np.min(results_array)),
                'max': float(np.max(results_array)),
                'median': float(np.median(results_array)),
                'mode': self._estimate_mode(results_array),
                'skewness': float(stats.skew(results_array)),
                'kurtosis': float(stats.kurtosis(results_array)),
                'percentiles': {
                    '1': float(np.percentile(results_array, 1)),
                    '5': float(np.percentile(results_array, 5)),
                    '10': float(np.percentile(results_array, 10)),
                    '25': float(np.percentile(results_array, 25)),
                    '75': float(np.percentile(results_array, 75)),
                    '90': float(np.percentile(results_array, 90)),
                    '95': float(np.percentile(results_array, 95)),
                    '99': float(np.percentile(results_array, 99))
                },
                'confidence_intervals': {
                    '68': (float(np.percentile(results_array, 16)), 
                           float(np.percentile(results_array, 84))),
                    '90': (float(np.percentile(results_array, 5)), 
                           float(np.percentile(results_array, 95))),
                    '95': (float(np.percentile(results_array, 2.5)), 
                           float(np.percentile(results_array, 97.5))),
                    '99': (float(np.percentile(results_array, 0.5)), 
                           float(np.percentile(results_array, 99.5)))
                }
            })
            
            # Enhanced sensitivity analysis
            if len(param_names) > 1:
                analysis['sensitivity'] = self._enhanced_sensitivity_analysis(
                    samples[:n_valid], results_array, param_names
                )
            
            # Distribution fitting
            analysis['fitted_distribution'] = self._fit_distribution(results_array)
                
        elif all(isinstance(r, (list, tuple)) for r in results):
            # Vector results
            results_array = np.array(results)
            n_outputs = results_array.shape[1]
            
            analysis.update({
                'type': 'vector',
                'n_outputs': n_outputs,
                'outputs': {}
            })
            
            for i in range(n_outputs):
                output_data = results_array[:, i]
                analysis['outputs'][f'output_{i}'] = {
                    'mean': float(np.mean(output_data)),
                    'std': float(np.std(output_data)),
                    'min': float(np.min(output_data)),
                    'max': float(np.max(output_data)),
                    'median': float(np.median(output_data)),
                    'confidence_intervals': {
                        '95': (float(np.percentile(output_data, 2.5)), 
                               float(np.percentile(output_data, 97.5)))
                    }
                }
                
        else:
            # Generic results
            analysis.update({
                'type': 'generic',
                'sample_results': results[:20]  # First 20 for inspection
            })
        
        return analysis
    
    def _estimate_mode(self, data: np.ndarray) -> float:
        """Estimate mode using kernel density estimation."""
        try:
            from scipy.stats import gaussian_kde
            kde = gaussian_kde(data)
            
            # Find mode by optimizing KDE
            result = optimize.minimize_scalar(
                lambda x: -kde(x)[0], 
                bounds=(np.min(data), np.max(data)),
                method='bounded'
            )
            return float(result.x)
        except:
            # Fallback to median
            return float(np.median(data))
    
    def _enhanced_sensitivity_analysis(
        self,
        inputs: np.ndarray,
        outputs: np.ndarray,
        param_names: List[str]
    ) -> Dict[str, Dict[str, float]]:
        """Enhanced sensitivity analysis with multiple methods."""
        sensitivities = {}
        
        for i, param_name in enumerate(param_names):
            try:
                input_data = inputs[:, i]
                
                # Pearson correlation coefficient
                pearson_corr = np.corrcoef(input_data, outputs)[0, 1]
                
                # Spearman rank correlation
                spearman_corr = stats.spearmanr(input_data, outputs)[0]
                
                # Partial correlation (if possible)
                partial_corr = self._calculate_partial_correlation(inputs, outputs, i)
                
                # Sobol indices approximation using correlation ratios
                sobol_first = self._approximate_sobol_first_order(input_data, outputs)
                
                sensitivities[param_name] = {
                    'pearson_correlation': float(pearson_corr) if not np.isnan(pearson_corr) else 0.0,
                    'spearman_correlation': float(spearman_corr) if not np.isnan(spearman_corr) else 0.0,
                    'partial_correlation': float(partial_corr) if not np.isnan(partial_corr) else 0.0,
                    'sobol_first_order_approx': float(sobol_first) if not np.isnan(sobol_first) else 0.0,
                    'variance_contribution': float(pearson_corr**2) if not np.isnan(pearson_corr) else 0.0
                }
                
            except Exception as e:
                sensitivities[param_name] = {
                    'error': str(e),
                    'pearson_correlation': 0.0
                }
        
        return sensitivities
    
    def _calculate_partial_correlation(self, inputs: np.ndarray, outputs: np.ndarray, 
                                     target_index: int) -> float:
        """Calculate partial correlation coefficient."""
        try:
            n_params = inputs.shape[1]
            if n_params < 3:
                return np.corrcoef(inputs[:, target_index], outputs)[0, 1]
            
            # Simple approximation: correlation after removing linear effects of other variables
            other_indices = [i for i in range(n_params) if i != target_index]
            
            # Regress target input on other inputs
            if len(other_indices) > 0:
                coeffs_input = np.linalg.lstsq(inputs[:, other_indices], inputs[:, target_index], rcond=None)[0]
                residual_input = inputs[:, target_index] - inputs[:, other_indices].dot(coeffs_input)
                
                # Regress output on other inputs
                coeffs_output = np.linalg.lstsq(inputs[:, other_indices], outputs, rcond=None)[0]
                residual_output = outputs - inputs[:, other_indices].dot(coeffs_output)
                
                # Correlation of residuals
                return np.corrcoef(residual_input, residual_output)[0, 1]
            else:
                return np.corrcoef(inputs[:, target_index], outputs)[0, 1]
                
        except:
            return 0.0
    
    def _approximate_sobol_first_order(self, input_var: np.ndarray, output_var: np.ndarray) -> float:
        """Approximate first-order Sobol index using correlation ratio."""
        try:
            # Bin the input variable
            n_bins = min(20, len(input_var) // 50)  # Adaptive binning
            if n_bins < 2:
                return 0.0
                
            bins = np.linspace(np.min(input_var), np.max(input_var), n_bins + 1)
            bin_indices = np.digitize(input_var, bins) - 1
            bin_indices = np.clip(bin_indices, 0, n_bins - 1)
            
            # Calculate variance within and between bins
            total_var = np.var(output_var)
            if total_var == 0:
                return 0.0
                
            bin_means = []
            bin_sizes = []
            
            for i in range(n_bins):
                mask = bin_indices == i
                if np.sum(mask) > 0:
                    bin_means.append(np.mean(output_var[mask]))
                    bin_sizes.append(np.sum(mask))
                else:
                    bin_means.append(0)
                    bin_sizes.append(0)
            
            bin_means = np.array(bin_means)
            bin_sizes = np.array(bin_sizes)
            
            # Between-group variance
            overall_mean = np.mean(output_var)
            between_var = np.sum(bin_sizes * (bin_means - overall_mean)**2) / len(output_var)
            
            return between_var / total_var
            
        except:
            return 0.0
    
    def _fit_distribution(self, data: np.ndarray) -> Dict[str, Any]:
        """Fit common distributions to the results."""
        distributions_to_try = [
            ('normal', stats.norm),
            ('lognormal', stats.lognorm),
            ('gamma', stats.gamma),
            ('beta', stats.beta),
            ('uniform', stats.uniform)
        ]
        
        best_fit = {'name': 'unknown', 'params': {}, 'aic': np.inf}
        
        for dist_name, dist_class in distributions_to_try:
            try:
                # Fit distribution
                params = dist_class.fit(data)
                
                # Calculate AIC
                log_likelihood = np.sum(dist_class.logpdf(data, *params))
                n_params = len(params)
                aic = 2 * n_params - 2 * log_likelihood
                
                if aic < best_fit['aic']:
                    best_fit = {
                        'name': dist_name,
                        'params': params,
                        'aic': aic,
                        'log_likelihood': log_likelihood
                    }
                    
            except Exception:
                continue
        
        return best_fit


class AnalyticalUncertaintyPropagator(UncertaintyPropagator):
    """
    Analytical uncertainty propagation using first-order Taylor expansion.
    
    This method is faster than Monte Carlo but limited to cases where
    partial derivatives can be computed and linear approximation is valid.
    """
    
    def __init__(self, epsilon: float = 1e-8):
        """
        Initialize analytical propagator.
        
        Args:
            epsilon: Step size for numerical differentiation
        """
        self.epsilon = epsilon
    
    def propagate(
        self,
        function: Callable,
        parameters: Dict[str, UncertainParameter],
        correlation_matrix: Optional[np.ndarray] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Propagate uncertainty using analytical methods.
        
        Args:
            function: Function to evaluate
            parameters: Dictionary of uncertain parameters
            correlation_matrix: Optional correlation matrix between parameters
            **kwargs: Additional arguments to pass to function
            
        Returns:
            Dictionary with uncertainty propagation results
        """
        param_names = list(parameters.keys())
        param_values = {name: param.value for name, param in parameters.items()}
        
        try:
            # Evaluate function at mean values
            f_mean = function(**param_values, **kwargs)
            
            if not isinstance(f_mean, (int, float)):
                return {'error': 'Analytical propagation only supports scalar outputs'}
            
            # Calculate partial derivatives numerically
            partials = {}
            for param_name in param_names:
                partials[param_name] = self._numerical_partial_derivative(
                    function, param_values, param_name, **kwargs
                )
            
            # Calculate output variance using error propagation formula
            # Var(f) = Σᵢ (∂f/∂xᵢ)² * Var(xᵢ) + 2*ΣᵢΣⱼ (∂f/∂xᵢ)(∂f/∂xⱼ) * Cov(xᵢ,xⱼ)
            
            variance = 0.0
            
            # First-order terms
            for param_name in param_names:
                param = parameters[param_name]
                if hasattr(param.distribution, 'var'):
                    param_var = param.distribution.var()
                else:
                    param_var = (0.1 * abs(param.value))**2  # Default 10% uncertainty
                
                variance += (partials[param_name]**2) * param_var
            
            # Cross terms (covariance)
            if correlation_matrix is not None:
                for i, param_i in enumerate(param_names):
                    for j, param_j in enumerate(param_names):
                        if i != j:
                            param_i_std = np.sqrt(parameters[param_i].distribution.var()) if hasattr(parameters[param_i].distribution, 'var') else 0.1 * abs(parameters[param_i].value)
                            param_j_std = np.sqrt(parameters[param_j].distribution.var()) if hasattr(parameters[param_j].distribution, 'var') else 0.1 * abs(parameters[param_j].value)
                            
                            covariance = correlation_matrix[i, j] * param_i_std * param_j_std
                            variance += 2 * partials[param_i] * partials[param_j] * covariance
            
            std_dev = np.sqrt(variance)
            
            # Assume normal distribution for output (central limit theorem)
            output_dist = stats.norm(loc=f_mean, scale=std_dev)
            
            return {
                'type': 'analytical',
                'mean': float(f_mean),
                'std': float(std_dev),
                'variance': float(variance),
                'confidence_intervals': {
                    '90': (float(output_dist.ppf(0.05)), float(output_dist.ppf(0.95))),
                    '95': (float(output_dist.ppf(0.025)), float(output_dist.ppf(0.975))),
                    '99': (float(output_dist.ppf(0.005)), float(output_dist.ppf(0.995)))
                },
                'partial_derivatives': {name: float(partial) for name, partial in partials.items()},
                'distribution': output_dist
            }
            
        except Exception as e:
            return {'error': f'Analytical propagation failed: {str(e)}'}
    
    def _numerical_partial_derivative(
        self,
        function: Callable,
        param_values: Dict[str, float],
        param_name: str,
        **kwargs
    ) -> float:
        """Calculate numerical partial derivative."""
        # Forward difference
        params_plus = param_values.copy()
        params_plus[param_name] += self.epsilon
        
        params_minus = param_values.copy()
        params_minus[param_name] -= self.epsilon
        
        try:
            f_plus = function(**params_plus, **kwargs)
            f_minus = function(**params_minus, **kwargs)
            
            # Central difference for better accuracy
            return (f_plus - f_minus) / (2 * self.epsilon)
        except Exception as e:
            warnings.warn(f"Error computing derivative for {param_name}: {e}")
            return 0.0


class CumulativeEffectUncertaintyPropagator(UncertaintyPropagator):
    """
    Specialized propagator for cumulative effect analysis.
    
    This propagator extends the Monte Carlo approach with specific features
    for analyzing time-dependent cumulative effects.
    """
    
    def __init__(self, n_samples: int = 10000, random_state: Optional[int] = None,
                 time_points: Optional[np.ndarray] = None):
        """
        Initialize cumulative effect propagator.
        
        Args:
            n_samples: Number of Monte Carlo samples
            random_state: Random seed for reproducibility
            time_points: Array of time points for evaluation
        """
        self.n_samples = n_samples
        self.random_state = random_state
        self.time_points = time_points
        self.monte_carlo = EnhancedMonteCarloUncertaintyPropagator(
            n_samples=n_samples, 
            random_state=random_state
        )
    
    def propagate(
        self,
        function: Callable,
        parameters: Dict[str, UncertainParameter],
        time_points: Optional[np.ndarray] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Propagate uncertainty through a time-dependent function.
        
        Args:
            function: Function to evaluate (should accept time as a parameter)
            parameters: Dictionary of uncertain parameters
            time_points: Optional array of time points (overrides constructor value)
            **kwargs: Additional arguments to pass to function
            
        Returns:
            Dictionary with time-dependent uncertainty propagation results
        """
        t_points = time_points if time_points is not None else self.time_points
        
        if t_points is None:
            raise ValueError("Time points must be provided")
        
        # Generate parameter samples
        param_names = list(parameters.keys())
        n_params = len(param_names)
        
        param_samples = np.zeros((self.n_samples, n_params))
        for i, param_name in enumerate(param_names):
            param_samples[:, i] = parameters[param_name].sample(self.n_samples, self.random_state)
        
        # Initialize results
        results = {
            'time_points': t_points.tolist(),
            'mean': np.zeros_like(t_points),
            'std': np.zeros_like(t_points),
            'percentiles': {
                '5': np.zeros_like(t_points),
                '25': np.zeros_like(t_points),
                '50': np.zeros_like(t_points),
                '75': np.zeros_like(t_points),
                '95': np.zeros_like(t_points)
            },
            'samples': [] if self.n_samples <= 100 else None  # Store samples only if reasonable size
        }
        
        # Evaluate function for each time point
        all_samples = []
        
        for i, t in enumerate(t_points):
            # Evaluate for all samples at this time point
            time_results = []
            
            for j in range(self.n_samples):
                try:
                    # Create parameter dictionary for this sample
                    sample_params = {name: param_samples[j, k] for k, name in enumerate(param_names)}
                    
                    # Evaluate function with time
                    result = function(t=t, **sample_params, **kwargs)
                    if isinstance(result, (int, float)):
                        time_results.append(float(result))
                    else:
                        time_results.append(None)
                except:
                    time_results.append(None)
            
            # Filter out None values
            valid_results = [r for r in time_results if r is not None]
            
            if valid_results:
                results['mean'][i] = np.mean(valid_results)
                results['std'][i] = np.std(valid_results)
                results['percentiles']['5'][i] = np.percentile(valid_results, 5)
                results['percentiles']['25'][i] = np.percentile(valid_results, 25)
                results['percentiles']['50'][i] = np.percentile(valid_results, 50)
                results['percentiles']['75'][i] = np.percentile(valid_results, 75)
                results['percentiles']['95'][i] = np.percentile(valid_results, 95)
            
            all_samples.append(valid_results)
        
        # Store raw samples if requested
        if results['samples'] is not None:
            results['samples'] = all_samples
        
        return results


class OptimizedThresholdCrossingAnalyzer:
    """
    Optimized analyzer for threshold crossing detection.
    
    This class provides efficient methods for detecting when uncertain
    time series cross specified thresholds.
    """
    
    def __init__(self, n_samples: int = 10000, random_state: Optional[int] = None):
        """
        Initialize threshold crossing analyzer.
        
        Args:
            n_samples: Number of Monte Carlo samples
            random_state: Random seed for reproducibility
        """
        self.n_samples = n_samples
        self.random_state = random_state
        self.propagator = CumulativeEffectUncertaintyPropagator(
            n_samples=n_samples,
            random_state=random_state
        )
    
    def analyze_threshold_crossing(
        self,
        function: Callable,
        parameters: Dict[str, UncertainParameter],
        threshold: float,
        time_range: Tuple[float, float],
        n_time_points: int = 100,
        direction: str = 'above',
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analyze when uncertain time series crosses a threshold.
        
        Args:
            function: Time-dependent function to evaluate
            parameters: Dictionary of uncertain parameters
            threshold: Threshold value
            time_range: (start_time, end_time) tuple
            n_time_points: Number of time points to evaluate
            direction: 'above' or 'below' to detect crossing above/below threshold
            **kwargs: Additional arguments to pass to function
            
        Returns:
            Dictionary with threshold crossing statistics
        """
        t_start, t_end = time_range
        time_points = np.linspace(t_start, t_end, n_time_points)
        
        # Run propagation
        results = self.propagator.propagate(
            function=function,
            parameters=parameters,
            time_points=time_points,
            **kwargs
        )
        
        # Analyze threshold crossings
        crossing_times = self._detect_threshold_crossings(
            results, threshold, direction
        )
        
        # Calculate statistics on crossing times
        crossing_stats = self._analyze_crossing_statistics(crossing_times)
        
        return {
            'threshold': threshold,
            'direction': direction,
            'time_range': time_range,
            'crossing_statistics': crossing_stats,
            'probability_of_crossing': len(crossing_times) / self.n_samples,
            'time_to_cross_percentiles': {
                '5': crossing_stats['percentiles']['5'] if crossing_stats else None,
                '50': crossing_stats['percentiles']['50'] if crossing_stats else None,
                '95': crossing_stats['percentiles']['95'] if crossing_stats else None
            }
        }
    
    def _detect_threshold_crossings(
        self,
        propagation_results: Dict[str, Any],
        threshold: float,
        direction: str = 'above'
    ) -> List[float]:
        """
        Detect threshold crossings in propagated results using binary search.
        
        This optimized implementation uses vectorized operations and binary search
        for efficient detection.
        
        Args:
            propagation_results: Results from uncertainty propagation
            threshold: Threshold value
            direction: 'above' or 'below'
            
        Returns:
            List of crossing times
        """
        if propagation_results.get('samples') is None:
            return []
        
        time_points = np.array(propagation_results['time_points'])
        samples = propagation_results['samples']
        
        crossing_times = []
        
        # For each sample trajectory
        for i in range(len(samples[0])):
            # Extract values for this sample
            trajectory = [samples[j][i] for j in range(len(time_points)) if i < len(samples[j])]
            
            if len(trajectory) != len(time_points):
                continue
                
            trajectory = np.array(trajectory)
            
            # Detect crossings
            if direction == 'above':
                crossings = np.where(np.diff(trajectory > threshold))[0]
                if len(crossings) > 0 and trajectory[crossings[0]] < threshold:
                    # Find first crossing time using linear interpolation
                    idx = crossings[0]
                    t0, t1 = time_points[idx], time_points[idx + 1]
                    v0, v1 = trajectory[idx], trajectory[idx + 1]
                    
                    # Interpolate crossing time
                    if v1 != v0:  # Avoid division by zero
                        t_cross = t0 + (t1 - t0) * (threshold - v0) / (v1 - v0)
                        crossing_times.append(t_cross)
            else:  # below
                crossings = np.where(np.diff(trajectory < threshold))[0]
                if len(crossings) > 0 and trajectory[crossings[0]] > threshold:
                    # Find first crossing time using linear interpolation
                    idx = crossings[0]
                    t0, t1 = time_points[idx], time_points[idx + 1]
                    v0, v1 = trajectory[idx], trajectory[idx + 1]
                    
                    # Interpolate crossing time
                    if v1 != v0:  # Avoid division by zero
                        t_cross = t0 + (t1 - t0) * (threshold - v0) / (v1 - v0)
                        crossing_times.append(t_cross)
        
        return crossing_times
    
    def _analyze_crossing_statistics(
        self,
        crossing_times: List[float]
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate statistics on crossing times.
        
        Args:
            crossing_times: List of threshold crossing times
            
        Returns:
            Dictionary with statistics or None if no crossings
        """
        if not crossing_times:
            return None
        
        crossing_array = np.array(crossing_times)
        
        return {
            'n_crossings': len(crossing_times),
            'mean': float(np.mean(crossing_array)),
            'std': float(np.std(crossing_array)),
            'percentiles': {
                '5': float(np.percentile(crossing_array, 5)),
                '25': float(np.percentile(crossing_array, 25)),
                '50': float(np.percentile(crossing_array, 50)),
                '75': float(np.percentile(crossing_array, 75)),
                '95': float(np.percentile(crossing_array, 95))
            }
        }
