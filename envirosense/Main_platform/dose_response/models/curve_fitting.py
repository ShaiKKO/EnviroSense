"""
Enhanced Dose-Response Curve Fitting module for EnviroSense.

This module provides a comprehensive set of curve fitting models for dose-response
relationships, enabling accurate prediction of physiological responses to various
exposure levels. It includes statistical model comparison, parameter estimation
with confidence intervals, and effective dose calculations.

Improvements include:
- Bootstrap confidence intervals
- Cross-validation for model selection
- Better optimization with multiple starting points
- Bayesian model averaging
- Integration with uncertainty propagation
- Enhanced visualization options
- Robust handling of edge cases
"""

import numpy as np
import scipy.stats as stats
from scipy import optimize
from sklearn.model_selection import KFold
from sklearn.metrics import mean_squared_error, r2_score
import warnings
from typing import Dict, List, Optional, Tuple, Union, Callable, Any
from dataclasses import dataclass, field
import matplotlib.pyplot as plt
import seaborn as sns
from enum import Enum, auto
import json
import pandas as pd
import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
import joblib
from abc import ABC, abstractmethod


class DoseResponseModelType(Enum):
    """Types of dose-response models available for fitting."""
    LINEAR = auto()
    QUADRATIC = auto()
    EXPONENTIAL = auto()
    LOGISTIC = auto()
    LOG_LOGISTIC = auto()
    PROBIT = auto()
    HILL = auto()
    PIECEWISE_LINEAR = auto()
    WEIBULL = auto()
    GOMPERTZ = auto()


@dataclass
class ModelParameters:
    """
    Parameters for a fitted dose-response model.
    
    Includes bootstrap confidence intervals, cross-validation scores,
    and additional statistical metrics.
    """
    model_type: DoseResponseModelType
    parameter_values: Dict[str, float]
    parameter_names: List[str]
    confidence_intervals: Dict[str, Tuple[float, float]]
    bootstrap_confidence_intervals: Optional[Dict[str, Tuple[float, float]]] = None
    parameter_covariance: Optional[np.ndarray] = None
    aic: Optional[float] = None
    bic: Optional[float] = None
    aicc: Optional[float] = None  # Corrected AIC for small samples
    r_squared: Optional[float] = None
    adjusted_r_squared: Optional[float] = None
    rmse: Optional[float] = None
    mae: Optional[float] = None
    standard_errors: Optional[Dict[str, float]] = None
    p_values: Optional[Dict[str, float]] = None
    cv_scores: Optional[Dict[str, float]] = None
    residuals: Optional[np.ndarray] = None
    leverage: Optional[np.ndarray] = None
    cooks_distance: Optional[np.ndarray] = None
    dfbetas: Optional[np.ndarray] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model parameters to dictionary for serialization."""
        return {
            'model_type': self.model_type.name,
            'parameters': self.parameter_values,
            'confidence_intervals': {
                name: [float(ci[0]), float(ci[1])] 
                for name, ci in self.confidence_intervals.items()
            },
            'bootstrap_confidence_intervals': {
                name: [float(ci[0]), float(ci[1])] 
                for name, ci in self.bootstrap_confidence_intervals.items()
            } if self.bootstrap_confidence_intervals else None,
            'aic': float(self.aic) if self.aic is not None else None,
            'bic': float(self.bic) if self.bic is not None else None,
            'aicc': float(self.aicc) if self.aicc is not None else None,
            'r_squared': float(self.r_squared) if self.r_squared is not None else None,
            'adjusted_r_squared': float(self.adjusted_r_squared) if self.adjusted_r_squared is not None else None,
            'rmse': float(self.rmse) if self.rmse is not None else None,
            'mae': float(self.mae) if self.mae is not None else None,
            'cv_scores': self.cv_scores,
            'standard_errors': self.standard_errors,
            'p_values': self.p_values
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelParameters':
        """Create model parameters from dictionary."""
        model_type = DoseResponseModelType[data['model_type']]
        params = data['parameters']
        param_names = list(params.keys())
        
        # Convert confidence intervals back to tuples
        ci = {
            name: (float(ci_list[0]), float(ci_list[1]))
            for name, ci_list in data.get('confidence_intervals', {}).items()
        }
        
        # Convert bootstrap confidence intervals if available
        bootstrap_ci = None
        if data.get('bootstrap_confidence_intervals'):
            bootstrap_ci = {
                name: (float(ci_list[0]), float(ci_list[1]))
                for name, ci_list in data.get('bootstrap_confidence_intervals', {}).items()
            }
        
        return cls(
            model_type=model_type,
            parameter_values=params,
            parameter_names=param_names,
            confidence_intervals=ci,
            bootstrap_confidence_intervals=bootstrap_ci,
            aic=data.get('aic'),
            bic=data.get('bic'),
            aicc=data.get('aicc'),
            r_squared=data.get('r_squared'),
            adjusted_r_squared=data.get('adjusted_r_squared'),
            rmse=data.get('rmse'),
            mae=data.get('mae'),
            standard_errors=data.get('standard_errors'),
            p_values=data.get('p_values'),
            cv_scores=data.get('cv_scores')
        )


class BaseDoseResponseModel(ABC):
    """
    Base class for all dose-response models.
    
    Includes bootstrap confidence intervals, cross-validation,
    and improved optimization strategies.
    """
    
    def __init__(self, model_type: DoseResponseModelType):
        """Initialize the enhanced model."""
        self.model_type = model_type
        self.parameters = None
        self.function = None
        self.parameter_bounds = None
        self.jacobian = None
        self.initial_guess = None
        self.alternative_guesses = []  # Multiple starting points
        self.param_names = []
        self.constraints = None
        
    def generate_initial_guesses(self, doses: np.ndarray, responses: np.ndarray) -> List[np.ndarray]:
        """
        Generate multiple initial parameter guesses based on data.
        
        Args:
            doses: Array of dose values
            responses: Array of response values
            
        Returns:
            List of initial parameter guesses
        """
        guesses = [self.initial_guess]
        
        # Add data-driven guesses
        if hasattr(self, '_generate_data_driven_guesses'):
            data_guesses = self._generate_data_driven_guesses(doses, responses)
            guesses.extend(data_guesses)
        
        # Add random perturbations
        for _ in range(3):
            perturbed = self.initial_guess * (1 + 0.5 * np.random.randn(len(self.initial_guess)))
            guesses.append(perturbed)
            
        return guesses
    
    def fit(
        self, 
        doses: np.ndarray, 
        responses: np.ndarray,
        weights: Optional[np.ndarray] = None,
        alpha: float = 0.05,
        bootstrap_samples: int = 1000,
        cv_folds: int = 5,
        use_bootstrap: bool = True,
        use_cv: bool = True,
        n_jobs: int = 1
    ) -> ModelParameters:
        """
        Enhanced fit method with bootstrap CIs and cross-validation.
        
        Args:
            doses: Array of dose values
            responses: Array of response values
            weights: Optional array of weights for weighted fitting
            alpha: Significance level for confidence intervals
            bootstrap_samples: Number of bootstrap samples
            cv_folds: Number of cross-validation folds
            use_bootstrap: Whether to compute bootstrap confidence intervals
            use_cv: Whether to perform cross-validation
            n_jobs: Number of parallel jobs (-1 for all cores)
            
        Returns:
            ModelParameters with comprehensive statistics
        """
        if len(doses) != len(responses):
            raise ValueError("Doses and responses must have the same length")
        
        if weights is not None and len(weights) != len(doses):
            raise ValueError("Weights must have the same length as doses and responses")
        
        # Try multiple starting points for robust optimization
        best_result = None
        best_cost = float('inf')
        
        initial_guesses = self.generate_initial_guesses(doses, responses)
        
        for guess in initial_guesses:
            try:
                result = self._fit_with_guess(doses, responses, weights, guess)
                
                # Calculate cost (sum of squared residuals)
                predicted = self.predict(doses, result.x)
                residuals = responses - predicted
                if weights is not None:
                    residuals = residuals * np.sqrt(weights)
                cost = np.sum(residuals**2)
                
                if cost < best_cost:
                    best_cost = cost
                    best_result = result
                    
            except Exception as e:
                continue
        
        if best_result is None:
            raise ValueError("Model fitting failed with all initial guesses")
        
        # Calculate comprehensive statistics
        return self._calculate_enhanced_statistics(
            doses, responses, weights, best_result, alpha,
            bootstrap_samples, cv_folds, use_bootstrap, use_cv, n_jobs
        )
    
    def _fit_with_guess(self, doses, responses, weights, initial_guess):
        """Fit model with a specific initial guess."""
        def objective(params):
            try:
                predicted = self.predict(doses, params)
                residuals = responses - predicted
                if weights is not None:
                    residuals = residuals * np.sqrt(weights)
                return residuals
            except:
                return np.full_like(responses, 1e6)
        
        # Use multiple optimization methods for robustness
        methods = ['trf', 'lm', 'dogbox']
        
        for method in methods:
            try:
                result = optimize.least_squares(
                    objective, 
                    initial_guess,
                    bounds=self.parameter_bounds if self.parameter_bounds else (-np.inf, np.inf),
                    method=method,
                    jac=self.jacobian if self.jacobian else '2-point',
                    x_scale='jac',
                    max_nfev=1000
                )
                
                if result.success:
                    return result
                    
            except Exception:
                continue
        
        # Fallback to scipy.optimize.minimize
        def scalar_objective(params):
            residuals = objective(params)
            return np.sum(residuals**2)
        
        result = optimize.minimize(
            scalar_objective,
            initial_guess,
            method='Nelder-Mead',
            options={'maxiter': 1000}
        )
        
        # Convert to least_squares format
        class MinimizeResult:
            def __init__(self, x, fun_val, success):
                self.x = x
                self.fun = objective(x)
                self.success = success
                self.jac = self._compute_jacobian(x)
                
            def _compute_jacobian(self, x):
                epsilon = 1e-8
                jac = np.zeros((len(doses), len(x)))
                for i in range(len(x)):
                    x_plus = x.copy()
                    x_plus[i] += epsilon
                    x_minus = x.copy()
                    x_minus[i] -= epsilon
                    jac[:, i] = (objective(x_plus) - objective(x_minus)) / (2 * epsilon)
                return jac
        
        return MinimizeResult(result.x, result.fun, result.success)
    
    def _calculate_enhanced_statistics(
        self, doses, responses, weights, result, alpha,
        bootstrap_samples, cv_folds, use_bootstrap, use_cv, n_jobs
    ):
        """Calculate comprehensive model statistics."""
        param_values = {name: value for name, value in zip(self.param_names, result.x)}
        
        # Basic statistics
        predicted = self.predict(doses, result.x)
        residuals = responses - predicted
        n_points = len(doses)
        n_params = len(self.param_names)
        dof = n_points - n_params
        
        # Calculate various error metrics
        rmse = np.sqrt(np.mean(residuals**2))
        mae = np.mean(np.abs(residuals))
        
        # R-squared and adjusted R-squared
        ss_total = np.sum((responses - np.mean(responses))**2)
        ss_residual = np.sum(residuals**2)
        r_squared = 1 - (ss_residual / ss_total) if ss_total > 0 else 0
        adjusted_r_squared = 1 - (ss_residual / dof) / (ss_total / (n_points - 1)) if n_points > 1 else 0
        
        # Information criteria
        n = len(doses)
        log_likelihood = -0.5 * n * np.log(2 * np.pi * ss_residual / n) - 0.5 * n
        aic = 2 * n_params - 2 * log_likelihood
        bic = n_params * np.log(n) - 2 * log_likelihood
        aicc = aic + (2 * n_params * (n_params + 1)) / (n - n_params - 1) if n > n_params + 1 else aic
        
        # Parameter covariance and standard errors
        covariance = None
        std_errors = None
        confidence_intervals = {}
        p_values = {}
        
        try:
            if hasattr(result, 'jac') and result.jac is not None:
                jac = result.jac
                residual_variance = ss_residual / dof if dof > 0 else 1.0
                
                # Robust covariance calculation
                try:
                    covariance = residual_variance * np.linalg.pinv(jac.T @ jac)
                    std_errors_array = np.sqrt(np.diag(covariance))
                    std_errors = {name: se for name, se in zip(self.param_names, std_errors_array)}
                    
                    # Confidence intervals
                    t_value = stats.t.ppf(1 - alpha/2, dof) if dof > 0 else stats.norm.ppf(1 - alpha/2)
                    for i, name in enumerate(self.param_names):
                        ci_lower = result.x[i] - t_value * std_errors_array[i]
                        ci_upper = result.x[i] + t_value * std_errors_array[i]
                        confidence_intervals[name] = (ci_lower, ci_upper)
                    
                    # P-values
                    if dof > 0:
                        t_stats = np.abs(result.x / std_errors_array)
                        p_values = {
                            name: 2 * (1 - stats.t.cdf(t_stat, dof))
                            for name, t_stat in zip(self.param_names, t_stats)
                        }
                        
                except np.linalg.LinAlgError:
                    warnings.warn("Could not compute parameter covariance matrix")
                    
        except Exception as e:
            warnings.warn(f"Error computing parameter statistics: {e}")
        
        # Diagnostic statistics
        leverage = self._calculate_leverage(doses, result.x) if len(doses) > n_params else None
        cooks_distance = self._calculate_cooks_distance(residuals, leverage, rmse) if leverage is not None else None
        
        # Bootstrap confidence intervals
        bootstrap_cis = {}
        if use_bootstrap and bootstrap_samples > 0:
            try:
                bootstrap_cis = self._bootstrap_confidence_intervals(
                    doses, responses, weights, alpha, bootstrap_samples, n_jobs
                )
            except Exception as e:
                warnings.warn(f"Bootstrap confidence intervals failed: {e}")
        
        # Cross-validation
        cv_scores = {}
        if use_cv and cv_folds > 1:
            try:
                cv_scores = self._cross_validate(doses, responses, weights, cv_folds, n_jobs)
            except Exception as e:
                warnings.warn(f"Cross-validation failed: {e}")
        
        # Create parameters object
        self.parameters = ModelParameters(
            model_type=self.model_type,
            parameter_values=param_values,
            parameter_names=self.param_names,
            confidence_intervals=confidence_intervals,
            bootstrap_confidence_intervals=bootstrap_cis,
            parameter_covariance=covariance,
            aic=aic,
            bic=bic,
            aicc=aicc,
            r_squared=r_squared,
            adjusted_r_squared=adjusted_r_squared,
            rmse=rmse,
            mae=mae,
            standard_errors=std_errors,
            p_values=p_values,
            cv_scores=cv_scores,
            residuals=residuals,
            leverage=leverage,
            cooks_distance=cooks_distance
        )
        
        return self.parameters
    
    def _bootstrap_confidence_intervals(
        self, doses, responses, weights, alpha, n_bootstrap, n_jobs
    ):
        """Calculate bootstrap confidence intervals."""
        def bootstrap_fit(seed):
            np.random.seed(seed)
            n = len(doses)
            indices = np.random.choice(n, size=n, replace=True)
            
            boot_doses = doses[indices]
            boot_responses = responses[indices]
            boot_weights = weights[indices] if weights is not None else None
            
            try:
                # Fit model to bootstrap sample
                result = self._fit_with_guess(boot_doses, boot_responses, boot_weights, self.initial_guess)
                return result.x if result.success else None
            except:
                return None
        
        # Parallel bootstrap
        if n_jobs == 1:
            bootstrap_params = []
            for i in range(n_bootstrap):
                params = bootstrap_fit(i)
                if params is not None:
                    bootstrap_params.append(params)
        else:
            with ProcessPoolExecutor(max_workers=n_jobs if n_jobs > 0 else None) as executor:
                futures = [executor.submit(bootstrap_fit, i) for i in range(n_bootstrap)]
                bootstrap_params = []
                for future in as_completed(futures):
                    params = future.result()
                    if params is not None:
                        bootstrap_params.append(params)
        
        if not bootstrap_params:
            return {}
        
        bootstrap_params = np.array(bootstrap_params)
        
        # Calculate confidence intervals
        bootstrap_cis = {}
        for i, name in enumerate(self.param_names):
            param_values = bootstrap_params[:, i]
            ci_lower = np.percentile(param_values, 100 * alpha / 2)
            ci_upper = np.percentile(param_values, 100 * (1 - alpha / 2))
            bootstrap_cis[name] = (ci_lower, ci_upper)
        
        return bootstrap_cis
    
    def _cross_validate(self, doses, responses, weights, cv_folds, n_jobs):
        """Perform cross-validation."""
        kf = KFold(n_splits=cv_folds, shuffle=True, random_state=42)
        
        cv_scores = []
        cv_r2_scores = []
        
        for train_idx, test_idx in kf.split(doses):
            try:
                # Split data
                train_doses, test_doses = doses[train_idx], doses[test_idx]
                train_responses, test_responses = responses[train_idx], responses[test_idx]
                train_weights = weights[train_idx] if weights is not None else None
                
                # Fit on training set
                result = self._fit_with_guess(train_doses, train_responses, train_weights, self.initial_guess)
                
                # Predict on test set
                test_predicted = self.predict(test_doses, result.x)
                
                # Calculate scores
                mse = mean_squared_error(test_responses, test_predicted)
                r2 = r2_score(test_responses, test_predicted)
                
                cv_scores.append(mse)
                cv_r2_scores.append(r2)
                
            except Exception:
                continue
        
        if cv_scores:
            return {
                'cv_mse_mean': np.mean(cv_scores),
                'cv_mse_std': np.std(cv_scores),
                'cv_r2_mean': np.mean(cv_r2_scores),
                'cv_r2_std': np.std(cv_r2_scores)
            }
        else:
            return {}
    
    def _calculate_leverage(self, doses, params):
        """Calculate leverage values for diagnostic purposes."""
        try:
            # Calculate Jacobian matrix
            epsilon = 1e-8
            n = len(doses)
            p = len(params)
            jac = np.zeros((n, p))
            
            for i in range(p):
                params_plus = params.copy()
                params_plus[i] += epsilon
                params_minus = params.copy()
                params_minus[i] -= epsilon
                
                y_plus = self.predict(doses, params_plus)
                y_minus = self.predict(doses, params_minus)
                
                jac[:, i] = (y_plus - y_minus) / (2 * epsilon)
            
            # Calculate hat matrix diagonal
            try:
                hat_matrix = jac @ np.linalg.pinv(jac.T @ jac) @ jac.T
                leverage = np.diag(hat_matrix)
                return leverage
            except np.linalg.LinAlgError:
                return None
                
        except Exception:
            return None
    
    def _calculate_cooks_distance(self, residuals, leverage, rmse):
        """Calculate Cook's distance for outlier detection."""
        if leverage is None:
            return None
            
        try:
            p = len(self.param_names)
            standardized_residuals = residuals / rmse
            
            cooks_d = (standardized_residuals**2 / p) * (leverage / (1 - leverage)**2)
            return cooks_d
        except Exception:
            return None
    
    def predict(self, doses: np.ndarray, params: Optional[np.ndarray] = None) -> np.ndarray:
        """Predict responses for given doses."""
        if params is None:
            if self.parameters is None:
                raise ValueError("Model not fitted yet")
            params = np.array([self.parameters.parameter_values[name] 
                              for name in self.param_names])
        
        return self.function(doses, params)
    
    def plot_diagnostics(self, doses: np.ndarray, responses: np.ndarray, 
                        fig_size: Tuple[int, int] = (15, 10)) -> plt.Figure:
        """
        Create comprehensive diagnostic plots.
        
        Args:
            doses: Array of dose values
            responses: Array of response values
            fig_size: Figure size (width, height)
            
        Returns:
            Matplotlib figure with diagnostic plots
        """
        if self.parameters is None:
            raise ValueError("Model not fitted yet")
        
        fig, axes = plt.subplots(2, 3, figsize=fig_size)
        axes = axes.flatten()
        
        predicted = self.predict(doses)
        residuals = self.parameters.residuals
        
        # 1. Residuals vs Fitted
        axes[0].scatter(predicted, residuals, alpha=0.7)
        axes[0].axhline(y=0, color='red', linestyle='--')
        axes[0].set_xlabel('Fitted Values')
        axes[0].set_ylabel('Residuals')
        axes[0].set_title('Residuals vs Fitted')
        axes[0].grid(alpha=0.3)
        
        # 2. Q-Q Plot of Residuals
        from scipy import stats
        stats.probplot(residuals, dist="norm", plot=axes[1])
        axes[1].set_title('Q-Q Plot of Residuals')
        axes[1].grid(alpha=0.3)
        
        # 3. Scale-Location Plot
        sqrt_abs_residuals = np.sqrt(np.abs(residuals))
        axes[2].scatter(predicted, sqrt_abs_residuals, alpha=0.7)
        axes[2].set_xlabel('Fitted Values')
        axes[2].set_ylabel('√|Residuals|')
        axes[2].set_title('Scale-Location')
        axes[2].grid(alpha=0.3)
        
        # 4. Residuals vs Leverage
        if self.parameters.leverage is not None:
            axes[3].scatter(self.parameters.leverage, residuals, alpha=0.7)
            axes[3].axhline(y=0, color='red', linestyle='--')
            axes[3].set_xlabel('Leverage')
            axes[3].set_ylabel('Residuals')
            axes[3].set_title('Residuals vs Leverage')
            axes[3].grid(alpha=0.3)
        else:
            axes[3].text(0.5, 0.5, 'Leverage not available', ha='center', va='center', 
                        transform=axes[3].transAxes)
            axes[3].set_title('Residuals vs Leverage')
        
        # 5. Cook's Distance
        if self.parameters.cooks_distance is not None:
            axes[4].stem(range(len(self.parameters.cooks_distance)), 
                        self.parameters.cooks_distance, basefmt=" ")
            axes[4].set_xlabel('Observation')
            axes[4].set_ylabel("Cook's Distance")
            axes[4].set_title("Cook's Distance")
            axes[4].grid(alpha=0.3)
        else:
            axes[4].text(0.5, 0.5, "Cook's Distance not available", ha='center', va='center', 
                        transform=axes[4].transAxes)
            axes[4].set_title("Cook's Distance")
        
        # 6. Histogram of Residuals
        axes[5].hist(residuals, bins=20, density=True, alpha=0.7, edgecolor='black')
        axes[5].set_xlabel('Residuals')
        axes[5].set_ylabel('Density')
        axes[5].set_title('Distribution of Residuals')
        axes[5].grid(alpha=0.3)
        
        # Overlay normal distribution
        x = np.linspace(np.min(residuals), np.max(residuals), 100)
        normal_pdf = stats.norm.pdf(x, np.mean(residuals), np.std(residuals))
        axes[5].plot(x, normal_pdf, 'r-', linewidth=2, label='Normal')
        axes[5].legend()
        
        fig.tight_layout()
        return fig


class WeibullModel(BaseDoseResponseModel):
    """
    Weibull dose-response model: response = bottom + (top - bottom) * (1 - exp(-(dose/lambda)^k))
    """
    
    def __init__(self):
        super().__init__(DoseResponseModelType.WEIBULL)
        self.param_names = ['bottom', 'top', 'lambda', 'k']
        self.initial_guess = np.array([0.0, 1.0, 1.0, 1.0])
        self.parameter_bounds = ([0.0, 0.0, 0.0, 0.0], [np.inf, np.inf, np.inf, np.inf])
        
        def function(doses, params):
            bottom, top, lambda_param, k = params
            safe_doses = np.maximum(doses, 1e-10)
            return bottom + (top - bottom) * (1 - np.exp(-(safe_doses / lambda_param)**k))
        
        self.function = function
    
    def _generate_data_driven_guesses(self, doses, responses):
        """Generate data-driven initial guesses."""
        min_resp, max_resp = np.min(responses), np.max(responses)
        median_dose = np.median(doses)
        
        guesses = []
        for lambda_mult in [0.5, 1.0, 2.0]:
            for k_val in [0.5, 1.0, 2.0]:
                guess = np.array([min_resp, max_resp, median_dose * lambda_mult, k_val])
                guesses.append(guess)
        
        return guesses


class GompertzModel(BaseDoseResponseModel):
    """
    Gompertz dose-response model: response = bottom + (top - bottom) * exp(-exp(-k * (dose - t0)))
    """
    
    def __init__(self):
        super().__init__(DoseResponseModelType.GOMPERTZ)
        self.param_names = ['bottom', 'top', 'k', 't0']
        self.initial_guess = np.array([0.0, 1.0, 1.0, 1.0])
        
        def function(doses, params):
            bottom, top, k, t0 = params
            return bottom + (top - bottom) * np.exp(-np.exp(-k * (doses - t0)))
        
        self.function = function
    
    def _generate_data_driven_guesses(self, doses, responses):
        """Generate data-driven initial guesses."""
        min_resp, max_resp = np.min(responses), np.max(responses)
        median_dose = np.median(doses)
        
        guesses = []
        for k_val in [0.1, 1.0, 10.0]:
            for t0_mult in [0.5, 1.0, 2.0]:
                guess = np.array([min_resp, max_resp, k_val, median_dose * t0_mult])
                guesses.append(guess)
        
        return guesses


class LinearModel(BaseDoseResponseModel):
    """Enhanced linear dose-response model with robust fitting."""
    
    def __init__(self):
        super().__init__(DoseResponseModelType.LINEAR)
        self.param_names = ['slope', 'intercept']
        self.initial_guess = np.array([1.0, 0.0])
        
        def function(doses, params):
            slope, intercept = params
            return slope * doses + intercept
        
        def jacobian(params, doses, responses):
            slope, intercept = params
            jac = np.zeros((len(doses), 2))
            jac[:, 0] = doses
            jac[:, 1] = 1.0
            return jac
        
        self.function = function
        self.jacobian = jacobian
    
    def _generate_data_driven_guesses(self, doses, responses):
        """Generate data-driven initial guesses using simple linear regression."""
        try:
            # Simple linear regression for initial guess
            slope, intercept = np.polyfit(doses, responses, 1)
            
            guesses = []
            # Original guess
            guesses.append(np.array([slope, intercept]))
            
            # Variations
            for mult in [0.5, 1.5, 2.0]:
                guesses.append(np.array([slope * mult, intercept]))
            
            return guesses
        except:
            return []


class HillModel(BaseDoseResponseModel):
    """
    Hill dose-response model: response = bottom + (top - bottom) * (dose^n / (EC50^n + dose^n))
    """
    
    def __init__(self):
        super().__init__(DoseResponseModelType.HILL)
        self.param_names = ['bottom', 'top', 'EC50', 'n']
        self.initial_guess = np.array([0.0, 1.0, 1.0, 1.0])
        self.parameter_bounds = ([0.0, 0.0, 0.0, 0.0], [np.inf, np.inf, np.inf, np.inf])
        
        def function(doses, params):
            bottom, top, ec50, n = params
            safe_doses = np.maximum(doses, 1e-10)
            return bottom + (top - bottom) * (safe_doses**n / (ec50**n + safe_doses**n))
        
        self.function = function
    
    def _generate_data_driven_guesses(self, doses, responses):
        """Generate data-driven initial guesses."""
        min_resp, max_resp = np.min(responses), np.max(responses)
        median_dose = np.median(doses)
        
        guesses = []
        for ec50_mult in [0.5, 1.0, 2.0]:
            for n_val in [0.5, 1.0, 2.0, 4.0]:
                guess = np.array([min_resp, max_resp, median_dose * ec50_mult, n_val])
                guesses.append(guess)
        
        return guesses


class LogisticModel(BaseDoseResponseModel):
    """
    Logistic dose-response model: response = bottom + (top - bottom) / (1 + exp(-k * (dose - EC50)))
    """
    
    def __init__(self):
        super().__init__(DoseResponseModelType.LOGISTIC)
        self.param_names = ['bottom', 'top', 'EC50', 'k']
        self.initial_guess = np.array([0.0, 1.0, 1.0, 1.0])
        
        def function(doses, params):
            bottom, top, ec50, k = params
            return bottom + (top - bottom) / (1 + np.exp(-k * (doses - ec50)))
        
        self.function = function
    
    def _generate_data_driven_guesses(self, doses, responses):
        """Generate data-driven initial guesses."""
        min_resp, max_resp = np.min(responses), np.max(responses)
        median_dose = np.median(doses)
        
        guesses = []
        for ec50_mult in [0.5, 1.0, 2.0]:
            for k_val in [0.5, 1.0, 2.0, 5.0]:
                guess = np.array([min_resp, max_resp, median_dose * ec50_mult, k_val])
                guesses.append(guess)
        
        return guesses


class BayesianModelAveraging:
    """
    Bayesian Model Averaging for dose-response models.
    
    Combines predictions from multiple models weighted by their posterior probabilities.
    """
    
    def __init__(self, models: Dict[DoseResponseModelType, ModelParameters]):
        """
        Initialize Bayesian Model Averaging.
        
        Args:
            models: Dictionary of fitted models with their parameters
        """
        self.models = models
        self.model_weights = self._calculate_model_weights()
    
    def _calculate_model_weights(self) -> Dict[DoseResponseModelType, float]:
        """Calculate model weights based on AIC values."""
        if not self.models:
            return {}
        
        # Calculate AIC weights
        aic_values = {}
        for model_type, params in self.models.items():
            if params.aic is not None:
                aic_values[model_type] = params.aic
        
        if not aic_values:
            # Equal weights if no AIC values
            weight = 1.0 / len(self.models)
            return {model_type: weight for model_type in self.models.keys()}
        
        # Calculate Akaike weights
        min_aic = min(aic_values.values())
        delta_aic = {model_type: aic - min_aic for model_type, aic in aic_values.items()}
        
        # Calculate relative likelihoods
        rel_likelihood = {model_type: np.exp(-0.5 * delta) for model_type, delta in delta_aic.items()}
        
        # Normalize to get weights
        total_likelihood = sum(rel_likelihood.values())
        weights = {model_type: rel_like / total_likelihood 
                  for model_type, rel_like in rel_likelihood.items()}
        
        return weights
    
    def predict(self, doses: np.ndarray, model_selector) -> Tuple[np.ndarray, np.ndarray]:
        """
        Make predictions using Bayesian Model Averaging.
        
        Args:
            doses: Array of dose values
            model_selector: Instance with fitted models
            
        Returns:
            Tuple of (weighted predictions, prediction variance)
        """
        if not self.models:
            raise ValueError("No models available for averaging")
        
        predictions = {}
        for model_type, weight in self.model_weights.items():
            if weight > 0:
                model = model_selector.get_model(model_type)
                model.parameters = self.models[model_type]
                pred = model.predict(doses)
                predictions[model_type] = pred
        
        # Calculate weighted average
        weighted_pred = np.zeros_like(doses, dtype=float)
        for model_type, pred in predictions.items():
            weight = self.model_weights[model_type]
            weighted_pred += weight * pred
        
        # Calculate prediction variance (model uncertainty)
        pred_variance = np.zeros_like(doses, dtype=float)
        for model_type, pred in predictions.items():
            weight = self.model_weights[model_type]
            pred_variance += weight * (pred - weighted_pred)**2
        
        return weighted_pred, pred_variance


class DoseResponseModelSelector:
    """
    Class for selecting and comparing multiple dose-response models.
    
    Facilitates model comparison, selection, and Bayesian model averaging.
    """
    
    def __init__(self):
        """Initialize with available dose-response models."""
        self.models = {
            DoseResponseModelType.LINEAR: LinearModel(),
            DoseResponseModelType.LOGISTIC: LogisticModel(),
            DoseResponseModelType.HILL: HillModel(),
            DoseResponseModelType.WEIBULL: WeibullModel(),
            DoseResponseModelType.GOMPERTZ: GompertzModel()
        }
        
        self.fitted_models = {}
        self.bayesian_avg = None
    
    def get_model(self, model_type: DoseResponseModelType) -> BaseDoseResponseModel:
        """Get a specific model by type."""
        if model_type not in self.models:
            raise ValueError(f"Model type {model_type} not available")
        return self.models[model_type]
    
    def fit_all(
        self, 
        doses: np.ndarray, 
        responses: np.ndarray,
        weights: Optional[np.ndarray] = None,
        bootstrap_samples: int = 500,
        cv_folds: int = 5,
        use_bootstrap: bool = True,
        use_cv: bool = True,
        n_jobs: int = 1
    ) -> Dict[DoseResponseModelType, ModelParameters]:
        """
        Fit all available models to the data.
        
        Args:
            doses: Array of dose values
            responses: Array of response values
            weights: Optional array of weights for weighted fitting
            bootstrap_samples: Number of bootstrap samples
            cv_folds: Number of cross-validation folds
            use_bootstrap: Whether to compute bootstrap confidence intervals
            use_cv: Whether to perform cross-validation
            n_jobs: Number of parallel jobs (-1 for all cores)
            
        Returns:
            Dictionary of fitted model parameters
        """
        self.fitted_models = {}
        
        for model_type, model in self.models.items():
            try:
                params = model.fit(
                    doses, responses, weights, 
                    bootstrap_samples=bootstrap_samples,
                    cv_folds=cv_folds,
                    use_bootstrap=use_bootstrap,
                    use_cv=use_cv,
                    n_jobs=n_jobs
                )
                self.fitted_models[model_type] = params
            except Exception as e:
                warnings.warn(f"Model {model_type.name} fitting failed: {e}")
        
        # Create Bayesian model averaging after fitting
        if self.fitted_models:
            self.bayesian_avg = BayesianModelAveraging(self.fitted_models)
        
        return self.fitted_models
    
    def select_best_model(self, criterion: str = 'aic') -> Tuple[DoseResponseModelType, ModelParameters]:
        """
        Select the best model based on the specified criterion.
        
        Args:
            criterion: Criterion for model selection ('aic', 'bic', 'aicc', 'r_squared', 'cv')
            
        Returns:
            Tuple of (best model type, best model parameters)
        """
        if not self.fitted_models:
            raise ValueError("No fitted models available")
        
        if criterion == 'aic':
            scores = {model_type: params.aic for model_type, params in self.fitted_models.items() 
                     if params.aic is not None}
            best_model = min(scores.items(), key=lambda x: x[1])[0]
        elif criterion == 'bic':
            scores = {model_type: params.bic for model_type, params in self.fitted_models.items() 
                     if params.bic is not None}
            best_model = min(scores.items(), key=lambda x: x[1])[0]
        elif criterion == 'aicc':
            scores = {model_type: params.aicc for model_type, params in self.fitted_models.items() 
                     if params.aicc is not None}
            best_model = min(scores.items(), key=lambda x: x[1])[0]
        elif criterion == 'r_squared':
            scores = {model_type: params.r_squared for model_type, params in self.fitted_models.items() 
                     if params.r_squared is not None}
            best_model = max(scores.items(), key=lambda x: x[1])[0]
        elif criterion == 'cv':
            scores = {model_type: params.cv_scores['cv_r2_mean'] 
                     for model_type, params in self.fitted_models.items() 
                     if params.cv_scores and 'cv_r2_mean' in params.cv_scores}
            if not scores:
                raise ValueError("No cross-validation scores available")
            best_model = max(scores.items(), key=lambda x: x[1])[0]
        else:
            raise ValueError(f"Unknown criterion: {criterion}")
        
        return best_model, self.fitted_models[best_model]
    
    def predict_with_uncertainty(
        self, 
        doses: np.ndarray, 
        model_type: Optional[DoseResponseModelType] = None,
        use_bayesian_avg: bool = False
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Make predictions with uncertainty estimates.
        
        Args:
            doses: Array of dose values
            model_type: Specific model type to use for prediction
            use_bayesian_avg: Whether to use Bayesian model averaging
            
        Returns:
            Tuple of (predictions, prediction uncertainty)
        """
        if use_bayesian_avg:
            if self.bayesian_avg is None:
                raise ValueError("Bayesian model averaging not available")
            return self.bayesian_avg.predict(doses, self)
        
        if model_type is None:
            # Use best model by AIC
            model_type, _ = self.select_best_model(criterion='aic')
        
        if model_type not in self.fitted_models:
            raise ValueError(f"Model {model_type.name} not fitted")
        
        model = self.get_model(model_type)
        model.parameters = self.fitted_models[model_type]
        
        # Predict mean
        predictions = model.predict(doses)
        
        # Estimate uncertainty from parameter covariance
        uncertainty = np.zeros_like(doses)
        
        params = self.fitted_models[model_type]
        if params.parameter_covariance is not None:
            try:
                # Calculate Jacobian
                epsilon = 1e-6
                jac = np.zeros((len(doses), len(params.parameter_names)))
                
                for i, param_name in enumerate(params.parameter_names):
                    param_values = np.array([params.parameter_values[name] for name in params.parameter_names])
                    
                    param_values_plus = param_values.copy()
                    param_values_plus[i] += epsilon
                    
                    param_values_minus = param_values.copy()
                    param_values_minus[i] -= epsilon
                    
                    pred_plus = model.predict(doses, param_values_plus)
                    pred_minus = model.predict(doses, param_values_minus)
                    
                    jac[:, i] = (pred_plus - pred_minus) / (2 * epsilon)
                
                # Calculate prediction variance
                for i in range(len(doses)):
                    uncertainty[i] = jac[i] @ params.parameter_covariance @ jac[i]
                
                # Take square root to get standard deviation
                uncertainty = np.sqrt(np.abs(uncertainty))
                
            except Exception as e:
                warnings.warn(f"Error computing prediction uncertainty: {e}")
        
        return predictions, uncertainty
    
    def plot_model_comparison(
        self, 
        doses: np.ndarray, 
        responses: np.ndarray,
        x_scale: str = 'linear',
        fig_size: Tuple[int, int] = (12, 8)
    ) -> plt.Figure:
        """
        Plot model comparison with data and fitted curves.
        
        Args:
            doses: Array of dose values
            responses: Array of response values
            x_scale: Scale for x-axis ('linear' or 'log')
            fig_size: Figure size (width, height)
            
        Returns:
            Matplotlib figure with model comparison
        """
        if not self.fitted_models:
            raise ValueError("No fitted models available")
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=fig_size)
        
        # Plot data
        ax1.scatter(doses, responses, alpha=0.7, color='black', label='Data')
        
        # Plot dose-response curves
        x_plot = np.logspace(np.log10(max(1e-10, np.min(doses))), np.log10(np.max(doses)), 200)
        
        colors = plt.cm.tab10.colors
        for i, (model_type, params) in enumerate(self.fitted_models.items()):
            model = self.get_model(model_type)
            model.parameters = params
            
            # Predict
            y_pred = model.predict(x_plot)
            
            # Plot curve
            color = colors[i % len(colors)]
            ax1.plot(x_plot, y_pred, label=f"{model_type.name} (AIC: {params.aic:.1f})", color=color)
        
        # If Bayesian averaging is available, plot it
        if self.bayesian_avg is not None:
            avg_pred, avg_var = self.bayesian_avg.predict(x_plot, self)
            ax1.plot(x_plot, avg_pred, 'k--', linewidth=2, label='Bayesian Average')
            
            # Plot confidence bands (1 standard deviation)
            ax1.fill_between(x_plot, avg_pred - np.sqrt(avg_var), avg_pred + np.sqrt(avg_var), 
                            alpha=0.2, color='gray')
        
        # Setup plot
        ax1.set_xlabel('Dose')
        ax1.set_ylabel('Response')
        ax1.set_title('Model Comparison')
        if x_scale == 'log':
            ax1.set_xscale('log')
        ax1.legend(loc='best')
        ax1.grid(alpha=0.3)
        
        # Plot AIC comparison
        model_names = [model_type.name for model_type in self.fitted_models.keys()]
        aic_values = [params.aic for params in self.fitted_models.values()]
        
        # Sort by AIC
        sorted_indices = np.argsort(aic_values)
        sorted_names = [model_names[i] for i in sorted_indices]
        sorted_aic = [aic_values[i] for i in sorted_indices]
        
        ax2.barh(sorted_names, sorted_aic)
        ax2.set_xlabel('AIC (lower is better)')
        ax2.set_title('Model Comparison by AIC')
        ax2.grid(alpha=0.3, axis='x')
        
        fig.tight_layout()
        return fig
