"""
Model fitting functions for dose-response models.

This module provides specialized functions for fitting dose-response models
to observed data with comprehensive statistical capabilities.
"""

import numpy as np
import scipy.stats as stats
from scipy import optimize
import warnings
from typing import Dict, List, Optional, Tuple, Union, Any


def fit_linear_model(
    doses: Union[List[float], np.ndarray],
    responses: Union[List[float], np.ndarray],
    method: str = 'ols',
    weights: Optional[Union[List[float], np.ndarray]] = None,
    robust_loss: str = 'soft_l1',
    priors: Optional[Dict[str, Dict[str, float]]] = None,
    mcmc_samples: int = 5000,
    store_diagnostics: bool = True,
    **kwargs
) -> Dict[str, Any]:
    """
    Fit a linear dose-response model to observed data.
    
    Args:
        doses: Array of dose values
        responses: Array of response values
        method: Estimation method:
            - 'ols': Ordinary least squares
            - 'wls': Weighted least squares
            - 'robust': Robust regression (less sensitive to outliers)
            - 'bayesian': Bayesian estimation with uncertainty quantification
        weights: Sample weights for weighted least squares
        robust_loss: Loss function for robust regression
        priors: Dictionary of prior distributions for Bayesian estimation
        mcmc_samples: Number of MCMC samples for Bayesian estimation
        store_diagnostics: Whether to include detailed diagnostics in results
        **kwargs: Additional method-specific parameters
        
    Returns:
        Dictionary of fitting results and diagnostics
    """
    # Validate input
    doses_array = np.array(doses, dtype=float)
    responses_array = np.array(responses, dtype=float)
    
    if len(doses_array) != len(responses_array):
        raise ValueError(f"Length mismatch: {len(doses_array)} doses vs {len(responses_array)} responses")
        
    if len(doses_array) < 2:
        raise ValueError("At least two data points are required for fitting")
    
    # Initialize results dictionary
    fit_results = {
        'success': False,
        'method': method,
        'n_observations': len(doses_array),
        'diagnostics': {}
    }
    
    # Perform fitting based on method
    if method == 'ols' or method == 'ordinary least squares':
        return _fit_ols(doses_array, responses_array, store_diagnostics)
        
    elif method == 'wls' or method == 'weighted least squares':
        if weights is None:
            raise ValueError("Weights must be provided for weighted least squares regression")
        weights_array = np.array(weights, dtype=float)
        return _fit_wls(doses_array, responses_array, weights_array, store_diagnostics)
        
    elif method == 'robust':
        return _fit_robust(doses_array, responses_array, robust_loss, store_diagnostics)
        
    elif method == 'bayesian':
        return _fit_bayesian(doses_array, responses_array, priors, mcmc_samples, store_diagnostics)
        
    else:
        raise ValueError(f"Unknown fitting method: {method}")


def _fit_ols(
    doses: np.ndarray,
    responses: np.ndarray,
    store_diagnostics: bool = True
) -> Dict[str, Any]:
    """Fit model using ordinary least squares."""
    # Perform OLS regression
    X = np.vstack([np.ones_like(doses), doses]).T
    
    # Use numpy's least squares solver
    beta, resid, rank, s = np.linalg.lstsq(X, responses, rcond=None)
    intercept, slope = beta
    
    # Calculate key regression statistics
    n = len(doses)
    k = 2  # number of parameters
    dof = n - k
    
    # Initialize results with success
    fit_results = {
        'success': True,
        'method': 'ordinary least squares',
        'parameters': {'intercept': float(intercept), 'slope': float(slope)},
    }
    
    if dof > 0:  # Ensure we can calculate standard errors
        # Residual sum of squares
        if len(resid) > 0:
            ssr = resid[0]  # np.linalg.lstsq returns RSS
        else:
            # Calculate RSS manually if not returned
            predicted = intercept + slope * doses
            residuals = responses - predicted
            ssr = np.sum(residuals**2)
        
        # Mean squared error
        mse = ssr / dof
        
        # Design matrix statistics needed for standard errors
        X_mean = np.mean(doses)
        X_var = np.sum((doses - X_mean)**2)
        
        # Standard errors of parameters
        intercept_se = np.sqrt(mse * (1/n + X_mean**2/X_var))
        slope_se = np.sqrt(mse / X_var)
        
        # Covariance matrix
        # Exact formula: cov(intercept, slope) = -X_mean/X_var * mse
        cov_b_m = -X_mean * mse / X_var
        cov_matrix = np.array([
            [intercept_se**2, cov_b_m],
            [cov_b_m, slope_se**2]
        ])
        
        # T-statistics and p-values
        t_intercept = intercept / intercept_se
        t_slope = slope / slope_se
        p_intercept = 2 * (1 - stats.t.cdf(abs(t_intercept), dof))
        p_slope = 2 * (1 - stats.t.cdf(abs(t_slope), dof))
        
        # R-squared and adjusted R-squared
        y_mean = np.mean(responses)
        tss = np.sum((responses - y_mean)**2)  # Total sum of squares
        r_squared = 1 - ssr / tss if tss > 0 else 0.0
        adj_r_squared = 1 - (1 - r_squared) * (n - 1) / dof if dof > 0 else 0.0
        
        # F-statistic and p-value
        f_stat = (tss - ssr) / mse if mse > 0 else 0.0
        f_pvalue = 1 - stats.f.cdf(f_stat, 1, dof)
        
        # Standard errors and covariance matrix
        fit_results.update({
            'standard_errors': {'intercept': float(intercept_se), 'slope': float(slope_se)},
            'covariance_matrix': cov_matrix.tolist()
        })
        
        # Store detailed diagnostics if requested
        if store_diagnostics:
            fit_diagnostics = {
                'degrees_of_freedom': dof,
                'residual_sum_squares': float(ssr),
                'mean_squared_error': float(mse),
                'r_squared': float(r_squared),
                'adj_r_squared': float(adj_r_squared),
                'f_statistic': float(f_stat),
                'f_pvalue': float(f_pvalue),
                'parameters': {
                    'intercept': {
                        'estimate': float(intercept),
                        'std_error': float(intercept_se),
                        't_statistic': float(t_intercept),
                        'p_value': float(p_intercept)
                    },
                    'slope': {
                        'estimate': float(slope),
                        'std_error': float(slope_se),
                        't_statistic': float(t_slope),
                        'p_value': float(p_slope)
                    }
                }
            }
            fit_results['diagnostics'] = fit_diagnostics
    else:
        # Not enough degrees of freedom for statistical inference
        fit_results['warning'] = "Not enough degrees of freedom for statistical inference"
        
    return fit_results


def _fit_wls(
    doses: np.ndarray,
    responses: np.ndarray,
    weights: np.ndarray,
    store_diagnostics: bool = True
) -> Dict[str, Any]:
    """Fit model using weighted least squares."""
    # Validate weights
    if len(weights) != len(doses):
        raise ValueError(f"Length mismatch: {len(weights)} weights vs {len(doses)} doses")
        
    # Apply square root of weights to observations
    sqrt_weights = np.sqrt(weights)
    doses_weighted = doses * sqrt_weights
    responses_weighted = responses * sqrt_weights
    ones_weighted = np.ones_like(doses) * sqrt_weights
    
    # Perform weighted regression
    X_weighted = np.vstack([ones_weighted, doses_weighted]).T
    beta, resid, rank, s = np.linalg.lstsq(X_weighted, responses_weighted, rcond=None)
    intercept, slope = beta
    
    # Initialize results with success
    fit_results = {
        'success': True,
        'method': 'weighted least squares',
        'parameters': {'intercept': float(intercept), 'slope': float(slope)},
    }
    
    # Calculate statistics
    n = len(doses)
    k = 2
    dof = n - k
    
    if dof > 0:
        # Calculate weighted residuals and diagnostics
        predicted = intercept + slope * doses
        residuals = responses - predicted
        weighted_residuals = residuals * sqrt_weights
        ssr = np.sum(weighted_residuals**2)
        mse = ssr / dof
        
        # Calculate covariance matrix using weighted design matrix
        X_weighted_T_X = X_weighted.T @ X_weighted
        try:
            cov_matrix = mse * np.linalg.inv(X_weighted_T_X)
        except np.linalg.LinAlgError:
            warnings.warn("Singular matrix in WLS, using pseudo-inverse for covariance")
            cov_matrix = mse * np.linalg.pinv(X_weighted_T_X)
        
        # Extract standard errors
        intercept_se = np.sqrt(cov_matrix[0, 0])
        slope_se = np.sqrt(cov_matrix[1, 1])
        
        # T-statistics and p-values
        t_intercept = intercept / intercept_se
        t_slope = slope / slope_se
        p_intercept = 2 * (1 - stats.t.cdf(abs(t_intercept), dof))
        p_slope = 2 * (1 - stats.t.cdf(abs(t_slope), dof))
        
        # Weighted R-squared
        weighted_mean = np.average(responses, weights=weights)
        weighted_tss = np.sum(weights * (responses - weighted_mean)**2)
        r_squared = 1 - ssr / weighted_tss if weighted_tss > 0 else 0.0
        adj_r_squared = 1 - (1 - r_squared) * (n - 1) / dof if dof > 0 else 0.0
        
        # Standard errors and covariance matrix
        fit_results.update({
            'standard_errors': {'intercept': float(intercept_se), 'slope': float(slope_se)},
            'covariance_matrix': cov_matrix.tolist()
        })
        
        # Store detailed diagnostics if requested
        if store_diagnostics:
            fit_diagnostics = {
                'degrees_of_freedom': dof,
                'residual_sum_squares': float(ssr),
                'mean_squared_error': float(mse),
                'r_squared': float(r_squared),
                'adj_r_squared': float(adj_r_squared),
                'parameters': {
                    'intercept': {
                        'estimate': float(intercept),
                        'std_error': float(intercept_se),
                        't_statistic': float(t_intercept),
                        'p_value': float(p_intercept)
                    },
                    'slope': {
                        'estimate': float(slope),
                        'std_error': float(slope_se),
                        't_statistic': float(t_slope),
                        'p_value': float(p_slope)
                    }
                }
            }
            fit_results['diagnostics'] = fit_diagnostics
    else:
        # Not enough degrees of freedom
        fit_results['warning'] = "Not enough degrees of freedom for statistical inference"
        
    return fit_results


def _fit_robust(
    doses: np.ndarray,
    responses: np.ndarray,
    loss_function: str = 'soft_l1',
    store_diagnostics: bool = True
) -> Dict[str, Any]:
    """Fit model using robust regression."""
    try:
        # Define robust loss function
        def loss(params, x, y):
            intercept, slope = params
            residuals = y - (intercept + slope * x)
            return residuals
        
        # Initial guess from standard OLS
        X = np.vstack([np.ones_like(doses), doses]).T
        beta, _, _, _ = np.linalg.lstsq(X, responses, rcond=None)
        initial_guess = beta
        
        # Perform robust regression
        result = optimize.least_squares(
            loss, 
            initial_guess, 
            loss=loss_function,
            args=(doses, responses),
            method='trf'
        )
        
        # Extract parameters
        intercept, slope = result.x
        
        # Initialize results with success
        fit_results = {
            'success': True,
            'method': 'robust regression',
            'parameters': {'intercept': float(intercept), 'slope': float(slope)},
        }
        
        if result.success:
            # Estimate covariance matrix using robust approaches
            jac = result.jac
            residuals = result.fun
            s_sq = np.sum(residuals**2) / (len(residuals) - 2)
            try:
                cov_matrix = s_sq * np.linalg.inv(jac.T @ jac)
            except np.linalg.LinAlgError:
                warnings.warn("Singular matrix in robust regression, using pseudo-inverse")
                cov_matrix = s_sq * np.linalg.pinv(jac.T @ jac)
            
            # Extract standard errors
            intercept_se = np.sqrt(cov_matrix[0, 0])
            slope_se = np.sqrt(cov_matrix[1, 1])
            
            # Standard errors and covariance matrix
            fit_results.update({
                'standard_errors': {'intercept': float(intercept_se), 'slope': float(slope_se)},
                'covariance_matrix': cov_matrix.tolist()
            })
            
            # Store detailed diagnostics if requested
            if store_diagnostics:
                fit_diagnostics = {
                    'loss_function': loss_function,
                    'sample_size': len(doses),
                    'degrees_of_freedom': len(doses) - 2,
                    'cost': float(result.cost),
                    'parameters': {
                        'intercept': {
                            'estimate': float(intercept),
                            'std_error': float(intercept_se),
                        },
                        'slope': {
                            'estimate': float(slope),
                            'std_error': float(slope_se),
                        }
                    },
                    'optimization_details': {
                        'success': bool(result.success),
                        'status': int(result.status),
                        'message': str(result.message),
                        'iterations': int(result.nfev)
                    }
                }
                fit_results['diagnostics'] = fit_diagnostics
        else:
            fit_results.update({
                'success': False,
                'error': f"Robust regression optimization failed: {result.message}"
            })
    
    except Exception as e:
        # Fall back to more basic robust estimation
        warnings.warn(f"Advanced robust regression failed: {str(e)}. Falling back to basic method.")
        
        # Simple robust regression using median-based estimators
        # Theil-Sen estimator: median of all pairwise slopes
        slopes = []
        for i in range(len(doses)):
            for j in range(i + 1, len(doses)):
                if doses[i] != doses[j]:
                    slopes.append(
                        (responses[j] - responses[i]) / 
                        (doses[j] - doses[i])
                    )
        
        if not slopes:
            return {
                'success': False,
                'method': 'robust regression (simplified)',
                'error': "Could not compute robust slope estimates"
            }
        
        # Use median slope
        slope = np.median(slopes)
        
        # Calculate intercepts using each point and take median
        intercepts = responses - slope * doses
        intercept = np.median(intercepts)
        
        # Calculate MAD (Median Absolute Deviation) for uncertainty estimation
        predicted = intercept + slope * doses
        residuals = responses - predicted
        mad = np.median(np.abs(residuals - np.median(residuals)))
        
        # Scale MAD to approximate standard deviation
        # 1.4826 factor is for normal distribution
        sigma = 1.4826 * mad
        
        # Approximate standard errors
        slope_se = sigma / np.sqrt(np.sum((doses - np.median(doses))**2))
        intercept_se = sigma * np.sqrt(1/len(doses) + 
                                     np.mean(doses)**2 / 
                                     np.sum((doses - np.mean(doses))**2))
        
        # Approximate covariance (negative correlation between intercept and slope)
        cov = -np.mean(doses) * slope_se * intercept_se
        cov_matrix = np.array([[intercept_se**2, cov], 
                             [cov, slope_se**2]])
        
        # Results with simplified approach
        fit_results = {
            'success': True,
            'method': 'robust regression (simplified)',
            'parameters': {'intercept': float(intercept), 'slope': float(slope)},
            'standard_errors': {'intercept': float(intercept_se), 'slope': float(slope_se)},
            'covariance_matrix': cov_matrix.tolist(),
            'warning': "Used simplified robust regression due to error in advanced method"
        }
        
        # Store detailed diagnostics if requested
        if store_diagnostics:
            fit_diagnostics = {
                'sample_size': len(doses),
                'median_absolute_deviation': float(mad),
                'parameters': {
                    'intercept': {
                        'estimate': float(intercept),
                        'std_error': float(intercept_se),
                    },
                    'slope': {
                        'estimate': float(slope),
                        'std_error': float(slope_se),
                    }
                }
            }
            fit_results['diagnostics'] = fit_diagnostics
            
    return fit_results


def _fit_bayesian(
    doses: np.ndarray,
    responses: np.ndarray,
    priors: Optional[Dict[str, Dict[str, float]]] = None,
    n_samples: int = 5000,
    store_diagnostics: bool = True
) -> Dict[str, Any]:
    """Fit model using Bayesian estimation."""
    # Default priors if not provided
    if priors is None:
        priors = {
            'intercept': {'mean': 0.0, 'std': 1.0},
            'slope': {'mean': 0.0, 'std': 1.0}
        }
    
    try:
        # This is a simplified implementation. In a production system,
        # one would use PyMC, Stan, or another Bayesian framework.
        
        # First, get OLS estimates as starting point
        X = np.vstack([np.ones_like(doses), doses]).T
        beta, resid, rank, s = np.linalg.lstsq(X, responses, rcond=None)
        ols_intercept, ols_slope = beta
        
        # Estimate error variance (sigma^2) from residuals
        if len(resid) > 0:
            sigma_squared = resid[0] / (len(doses) - 2)
        else:
            predicted = ols_intercept + ols_slope * doses
            residuals = responses - predicted
            sigma_squared = np.sum(residuals**2) / (len(doses) - 2)
        
        sigma = np.sqrt(sigma_squared)
        
        # Simple Metropolis-Hastings sampler
        def log_likelihood(params, x, y, sigma):
            intercept, slope = params
            y_pred = intercept + slope * x
            return -0.5 * np.sum(((y - y_pred) / sigma)**2)
        
        def log_prior(params):
            intercept, slope = params
            
            # Prior for intercept: normal
            lp_intercept = -0.5 * ((intercept - priors['intercept']['mean']) / 
                                 priors['intercept']['std'])**2
            
            # Prior for slope: normal
            lp_slope = -0.5 * ((slope - priors['slope']['mean']) / 
                             priors['slope']['std'])**2
            
            return lp_intercept + lp_slope
        
        def log_posterior(params, x, y, sigma):
            return log_prior(params) + log_likelihood(params, x, y, sigma)
        
        # Simplified Metropolis-Hastings sampling
        burnin = int(n_samples * 0.2)  # 20% burn-in
        samples = np.zeros((n_samples, 2))
        accepted = 0
        
        # Start from OLS estimates
        current_params = np.array([ols_intercept, ols_slope])
        current_log_post = log_posterior(current_params, doses, responses, sigma)
        
        # Estimate reasonable step size from OLS standard errors
        # (This is a heuristic - in practice, adapt this based on acceptance rate)
        X_mean = np.mean(doses)
        X_var = np.sum((doses - X_mean)**2)
        intercept_se = sigma * np.sqrt(1/len(doses) + X_mean**2/X_var)
        slope_se = sigma / np.sqrt(X_var)
        step_size = np.array([intercept_se, slope_se]) * 0.5
        
        # Run MCMC
        for i in range(n_samples + burnin):
            # Propose new parameters
            proposal = current_params + np.random.normal(0, 1, 2) * step_size
            
            # Calculate posterior
            proposed_log_post = log_posterior(proposal, doses, responses, sigma)
            
            # Accept or reject (Metropolis criterion)
            if np.log(np.random.rand()) < proposed_log_post - current_log_post:
                current_params = proposal
                current_log_post = proposed_log_post
                accepted += 1
            
            # Store samples after burn-in
            if i >= burnin:
                samples[i - burnin] = current_params
        
        # Calculate acceptance rate
        acceptance_rate = accepted / (n_samples + burnin)
        
        # Calculate posterior means and credible intervals
        intercept_samples = samples[:, 0]
        slope_samples = samples[:, 1]
        
        # Posterior means as parameter estimates
        intercept = np.mean(intercept_samples)
        slope = np.mean(slope_samples)
        
        # Calculate covariance matrix from samples
        cov_matrix = np.cov(samples, rowvar=False)
        
        # Standard errors (posterior standard deviations)
        intercept_se = np.std(intercept_samples)
        slope_se = np.std(slope_samples)
        
        # Credible intervals (95% by default)
        alpha = 0.05
        intercept_ci = np.percentile(intercept_samples, [100 * alpha/2, 100 * (1 - alpha/2)])
        slope_ci = np.percentile(slope_samples, [100 * alpha/2, 100 * (1 - alpha/2)])
        
        # Results with MCMC approach
        fit_results = {
            'success': True,
            'method': 'bayesian',
            'parameters': {'intercept': float(intercept), 'slope': float(slope)},
            'standard_errors': {'intercept': float(intercept_se), 'slope': float(slope_se)},
            'covariance_matrix': cov_matrix.tolist(),
            'mcmc_samples': {
                'intercept': intercept_samples.tolist(),
                'slope': slope_samples.tolist()
            }
        }
        
        # Store detailed diagnostics if requested
        if store_diagnostics:
            fit_diagnostics = {
                'sample_size': len(doses),
                'mcmc_samples': n_samples,
                'acceptance_rate': float(acceptance_rate),
                'credible_intervals': {
                    'intercept': intercept_ci.tolist(),
                    'slope': slope_ci.tolist()
                },
                'parameters': {
                    'intercept': {
                        'estimate': float(intercept),
                        'std_error': float(intercept_se),
                        'lower_ci': float(intercept_ci[0]),
                        'upper_ci': float(intercept_ci[1])
                    },
                    'slope': {
                        'estimate': float(slope),
                        'std_error': float(slope_se),
                        'lower_ci': float(slope_ci[0]),
                        'upper_ci': float(slope_ci[1])
                    }
                },
                'priors': {
                    'intercept': priors['intercept'],
                    'slope': priors['slope']
                }
            }
            fit_results['diagnostics'] = fit_diagnostics
            
    except Exception as e:
        # Fall back to OLS if Bayesian method fails
        warnings.warn(f"Bayesian estimation failed: {str(e)}. Falling back to OLS.")
        
        fit_results = _fit_ols(doses, responses, store_diagnostics)
        fit_results['warning'] = f"Bayesian estimation failed with error: {str(e)}. Used OLS instead."
        
    return fit_results
