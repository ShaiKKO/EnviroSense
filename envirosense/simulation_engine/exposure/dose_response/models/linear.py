"""
Linear dose-response model implementation with advanced statistical capabilities.

This module provides a sophisticated linear dose-response model with
parameter uncertainty quantification and covariance propagation.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Union, Any

from envirosense.core.exposure.dose_response.base import DoseResponseCurve
from envirosense.core.exposure.dose_response.types import (
    ResponseType, DoseUnit, ResponseUnit,
    DoseValue, ResponseValue, UncertaintyType
)
from envirosense.core.exposure.dose_response.references import (
    LiteratureReference, ReliabilityRating
)
from envirosense.core.exposure.dose_response.models.fit import fit_linear_model
from envirosense.core.exposure.dose_response.models.prediction import predict_linear_response


class LinearDoseResponse(DoseResponseCurve):
    """
    Advanced linear dose-response curve model.
    
    This model implements a linear relationship between dose and response,
    with the form:
    
        response = intercept + slope * dose
    
    The implementation includes:
    - Parameter uncertainty quantification
    - Complete parameter covariance matrix
    - Multiple estimation methods
    
    Attributes:
        slope (float): The slope coefficient of the linear relationship
        intercept (float): The intercept (response at zero dose)
        cov_matrix (np.ndarray): Covariance matrix of parameters [intercept, slope]
    """
    
    def __init__(
        self,
        chemical_id: str,
        response_type: Union[ResponseType, str],
        dose_unit: DoseUnit,
        response_unit: ResponseUnit,
        slope: float = 1.0,
        intercept: float = 0.0,
        cov_matrix: Optional[np.ndarray] = None,
        uncertainty_type: UncertaintyType = UncertaintyType.STANDARD_ERROR,
        reliability: Optional[ReliabilityRating] = None,
        references: Optional[List[LiteratureReference]] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize the linear dose-response curve.
        
        Args:
            chemical_id: Identifier for the chemical substance
            response_type: Type of biological response this curve models
            dose_unit: Unit of measurement for the dose (e.g., 'mg/kg', 'ppm')
            response_unit: Unit of measurement for the response (e.g., '%', 'probability')
            slope: Slope coefficient of the linear relationship
            intercept: Intercept (response at zero dose)
            cov_matrix: 2x2 covariance matrix for [intercept, slope]
            uncertainty_type: Type of uncertainty representation
            reliability: Rating of the data reliability
            references: Scientific references supporting this model
            description: Human-readable description of this curve
            metadata: Additional metadata about this curve
        """
        # Initialize base class
        super().__init__(
            chemical_id=chemical_id,
            response_type=response_type,
            dose_unit=dose_unit,
            response_unit=response_unit,
            reliability=reliability,
            references=references,
            description=description,
            metadata=metadata or {}
        )
        
        # Define parameter information
        self._parameter_info = {
            'intercept': {
                'description': 'Intercept (response at zero dose)',
                'units': f'{response_unit}',
                'typical_range': [0.0, 1.0],  # Often between 0-1 for normalized responses
                'constraints': 'Represents background response rate',
            },
            'slope': {
                'description': 'Slope coefficient of the linear relationship',
                'units': f'{response_unit}/{dose_unit}',
                'typical_range': [0.0, float('inf')],  # Typically positive for most toxicants
                'constraints': 'Typically positive for harmful responses',
            }
        }
        
        # Set initial parameter values
        self._parameters = {
            'intercept': float(intercept),
            'slope': float(slope)
        }
        
        # Set covariance matrix if provided, or use default
        if cov_matrix is not None:
            if not isinstance(cov_matrix, np.ndarray) or cov_matrix.shape != (2, 2):
                raise ValueError("Covariance matrix must be a 2x2 numpy array")
            self._cov_matrix = cov_matrix.copy() 
        else:
            # Default to zero covariance
            self._cov_matrix = np.array([[0.0, 0.0], [0.0, 0.0]])
        
        # Set uncertainty type
        self._uncertainty_type = uncertainty_type
        
        # Initialize uncertainty values from covariance matrix
        self._update_uncertainty_values()
        
        # Store MCMC samples if Bayesian estimation is used
        self._mcmc_samples = None
        
        # Add model-specific metadata
        self.metadata['model_type'] = 'linear'
        self.metadata['model_equation'] = 'response = intercept + slope * dose'
        self.metadata['model_complexity'] = 'low'  # Linear is simplest form
        
    def _update_uncertainty_values(self):
        """Update uncertainty values based on the covariance matrix."""
        self._uncertainty = {
            'intercept': np.sqrt(self._cov_matrix[0, 0]) if self._cov_matrix[0, 0] > 0 else 0.0,
            'slope': np.sqrt(self._cov_matrix[1, 1]) if self._cov_matrix[1, 1] > 0 else 0.0,
            'covariance': self._cov_matrix[0, 1],
            'correlation': (
                self._cov_matrix[0, 1] / 
                np.sqrt(self._cov_matrix[0, 0] * self._cov_matrix[1, 1])
                if self._cov_matrix[0, 0] > 0 and self._cov_matrix[1, 1] > 0
                else 0.0
            ),
            'type': self._uncertainty_type.value
        }
        
    @property
    def cov_matrix(self) -> np.ndarray:
        """Get the parameter covariance matrix."""
        return self._cov_matrix.copy()
        
    @cov_matrix.setter
    def cov_matrix(self, matrix: np.ndarray) -> None:
        """
        Set the parameter covariance matrix.
        
        Args:
            matrix: 2x2 covariance matrix for [intercept, slope]
            
        Raises:
            ValueError: If matrix is not 2x2 or not positive semidefinite
        """
        if not isinstance(matrix, np.ndarray) or matrix.shape != (2, 2):
            raise ValueError("Covariance matrix must be a 2x2 numpy array")
            
        # Ensure matrix is symmetric
        if not np.allclose(matrix, matrix.T):
            raise ValueError("Covariance matrix must be symmetric")
            
        # Check for positive semi-definiteness (eigenvalues >= 0)
        eigvals = np.linalg.eigvals(matrix)
        if not np.all(eigvals >= -1e-10):  # Allow for small numerical errors
            raise ValueError("Covariance matrix must be positive semidefinite")
            
        self._cov_matrix = matrix.copy()
        
        # Update uncertainty values
        self._update_uncertainty_values()
    
    @property
    def slope(self) -> float:
        """Get the slope parameter."""
        return self._parameters['slope']
    
    @slope.setter
    def slope(self, value: float) -> None:
        """Set the slope parameter."""
        self._parameters['slope'] = float(value)
    
    @property
    def intercept(self) -> float:
        """Get the intercept parameter."""
        return self._parameters['intercept']
    
    @intercept.setter
    def intercept(self, value: float) -> None:
        """Set the intercept parameter."""
        self._parameters['intercept'] = float(value)
    
    def predict(self, 
               doses: Union[DoseValue, List[DoseValue], np.ndarray], 
               include_uncertainty: bool = False,
               confidence_level: float = 0.95,
               method: str = 'analytical'
              ) -> Union[ResponseValue, List[ResponseValue], np.ndarray, Tuple]:
        """
        Predict response values for given dose values with uncertainty quantification.
        
        Args:
            doses: Single dose value or array of dose values
            include_uncertainty: Whether to include uncertainty estimates
            confidence_level: Confidence level for uncertainty bounds (0-1)
            method: Method for uncertainty calculation:
                - 'analytical': Use analytical formula for confidence intervals
                - 'monte_carlo': Use Monte Carlo simulation for uncertainty bounds
                - 'bayesian': Use Bayesian credible intervals from posterior samples
                
        Returns:
            If include_uncertainty is False:
                - Single response value or array of response values
            If include_uncertainty is True:
                - Tuple of (responses, lower_bound, upper_bound)
        """
        return predict_linear_response(
            self._parameters['intercept'], 
            self._parameters['slope'],
            self._cov_matrix,
            doses,
            include_uncertainty=include_uncertainty,
            confidence_level=confidence_level,
            method=method,
            mcmc_samples=self._mcmc_samples
        )
    
    def fit(self, 
           doses: Union[List[DoseValue], np.ndarray], 
           responses: Union[List[ResponseValue], np.ndarray],
           **kwargs
          ) -> Dict[str, Any]:
        """
        Fit the model parameters to observed dose-response data.
        
        Args:
            doses: Array of dose values
            responses: Array of response values
            **kwargs: Additional fitting options
                - method: Estimation method ('ols', 'wls', 'robust', 'bayesian')
                - weights: Sample weights for weighted least squares
                - robust_loss: Loss function for robust regression ('huber', 'soft_l1', etc.)
                - priors: Dictionary of prior distributions for Bayesian estimation
                - mcmc_samples: Number of MCMC samples for Bayesian estimation
                - store_diagnostics: Whether to store fit diagnostics in metadata
                
        Returns:
            Dictionary of fitting results and diagnostics
        """
        # Call the fit module function
        fit_result = fit_linear_model(
            doses, responses, 
            store_diagnostics=kwargs.get('store_diagnostics', True),
            **kwargs
        )
        
        # Update model parameters from fit results
        if fit_result['success']:
            self.intercept = fit_result['parameters']['intercept']
            self.slope = fit_result['parameters']['slope']
            
            if 'covariance_matrix' in fit_result:
                self.cov_matrix = np.array(fit_result['covariance_matrix'])
            
            # Store diagnostics in metadata if requested
            if kwargs.get('store_diagnostics', True) and 'diagnostics' in fit_result:
                self.metadata['fit_diagnostics'] = fit_result['diagnostics']
                
            # Store MCMC samples if Bayesian method was used
            if fit_result.get('method') == 'bayesian' and 'mcmc_samples' in fit_result:
                self._mcmc_samples = fit_result['mcmc_samples']
        
        return fit_result
