"""
EnviroSense Dose-Response Curve System

This module provides classes and functions for modeling dose-response relationships 
between chemical exposures and physiological responses. It implements various curve types
based on scientific literature and provides tools for curve fitting, interpolation,
and uncertainty modeling.

Classes:
    DoseResponseCurve: Base class for all dose-response curve types
    LinearDoseResponse: Linear response with or without threshold
    LogLogisticDoseResponse: Sigmoidal curve using log-logistic function (4PL model)
    LogProbitDoseResponse: Sigmoidal curve using log-probit function
    HormeticDoseResponse: Biphasic curve with low-dose stimulation and high-dose inhibition
    MultiExponentialDoseResponse: Multi-exponential model for gas sensor responses
    EnvironmentalCompensation: Decorator for temperature/humidity compensation
    MixtureDoseResponse: Model for chemical mixture effects
    LiteratureReference: Stores metadata about scientific literature sources

The module also provides functionality for fitting curves to empirical data
and estimating uncertainty in dose-response predictions.

References:
    - "The Four Parameter Logistic Model" - Journal of Biopharmaceutical Statistics (2020)
    - "Beyond the Hill Equation" - Environmental Health Perspectives (2021)
    - "Mathematical Model of Semiconductor Gas Sensors" - Sensors and Actuators B (2018)
    - "Temperature and Humidity Compensation Methods" - Sensors and Actuators B (2022)
"""

import uuid
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union, Any, Callable
from enum import Enum, auto
from abc import ABC, abstractmethod
from scipy import optimize, stats
import functools
import warnings


class ResponseType(Enum):
    """Types of physiological responses that can be modeled."""
    RESPIRATORY = auto()        # Respiratory system responses
    NEUROLOGICAL = auto()       # Neurological/nervous system responses
    CARDIOVASCULAR = auto()     # Heart and circulatory system responses
    DERMAL = auto()             # Skin responses
    OCULAR = auto()             # Eye responses
    GASTROINTESTINAL = auto()   # Digestive system responses
    IMMUNE = auto()             # Immune system responses
    HEMATOLOGIC = auto()        # Blood system responses
    HEPATIC = auto()            # Liver responses
    RENAL = auto()              # Kidney responses
    ENDOCRINE = auto()          # Hormone system responses
    REPRODUCTIVE = auto()       # Reproductive system responses
    DEVELOPMENTAL = auto()      # Developmental responses
    CARCINOGENIC = auto()       # Cancer-related responses
    GENOTOXIC = auto()          # DNA/genetic damage responses
    SYSTEMIC = auto()           # Whole-body/multi-system responses
    SENSOR_RESPONSE = auto()    # Physical sensor response (non-physiological)


class ReliabilityRating(Enum):
    """Reliability ratings for dose-response data."""
    HIGH = auto()           # Multiple high-quality studies with consistent results
    MEDIUM_HIGH = auto()    # Multiple good studies with mostly consistent results
    MEDIUM = auto()         # Limited studies or some inconsistency
    MEDIUM_LOW = auto()     # Few studies or significant inconsistency
    LOW = auto()            # Very limited data, poor study quality, or inconsistent findings
    PRELIMINARY = auto()    # Early or emerging research, not yet well-established
    MODEL_DERIVED = auto()  # Derived from computational models rather than empirical studies
    UNKNOWN = auto()        # Reliability cannot be determined


class LiteratureReference:
    """
    Container for scientific literature reference data.
    
    This class stores metadata about scientific publications that provide
    dose-response data, allowing for proper citation and assessment of
    data quality.
    """
    
    def __init__(
        self,
        title: str,
        authors: List[str],
        year: int,
        journal: Optional[str] = None,
        doi: Optional[str] = None,
        pubmed_id: Optional[str] = None,
        url: Optional[str] = None,
        reliability_rating: Optional[ReliabilityRating] = ReliabilityRating.MEDIUM,
        notes: Optional[str] = None
    ):
        """
        Initialize a literature reference.
        
        Args:
            title: Publication title
            authors: List of author names
            year: Publication year
            journal: Journal name (optional)
            doi: Digital Object Identifier (optional)
            pubmed_id: PubMed identifier (optional)
            url: Web link to the reference (optional)
            reliability_rating: Assessment of reliability (optional)
            notes: Additional information about the reference (optional)
        """
        self.reference_id = str(uuid.uuid4())
        self.title = title
        self.authors = authors
        self.year = year
        self.journal = journal
        self.doi = doi
        self.pubmed_id = pubmed_id
        self.url = url
        self.reliability_rating = reliability_rating
        self.notes = notes
    
    @property
    def citation(self) -> str:
        """
        Get formatted citation string.
        
        Returns:
            Properly formatted citation string for this reference
        """
        author_part = ", ".join(self.authors)
        if len(self.authors) > 2:
            author_part = f"{self.authors[0]} et al."
        
        if self.journal:
            return f"{author_part} ({self.year}). {self.title}. {self.journal}."
        else:
            return f"{author_part} ({self.year}). {self.title}."
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert reference to dictionary.
        
        Returns:
            Dictionary representation of this reference
        """
        return {
            "reference_id": self.reference_id,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "journal": self.journal,
            "doi": self.doi,
            "pubmed_id": self.pubmed_id,
            "url": self.url,
            "reliability_rating": self.reliability_rating.name if self.reliability_rating else None,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LiteratureReference':
        """
        Create reference from dictionary.
        
        Args:
            data: Dictionary containing reference data
            
        Returns:
            New LiteratureReference object
        """
        # Extract the basic required parameters
        ref = cls(
            title=data["title"],
            authors=data["authors"],
            year=data["year"]
        )
        
        # Process optional parameters
        ref.reference_id = data.get("reference_id", ref.reference_id)
        ref.journal = data.get("journal")
        ref.doi = data.get("doi")
        ref.pubmed_id = data.get("pubmed_id")
        ref.url = data.get("url")
        ref.notes = data.get("notes")
        
        # Process reliability rating
        if "reliability_rating" in data and data["reliability_rating"]:
            try:
                ref.reliability_rating = ReliabilityRating[data["reliability_rating"]]
            except KeyError:
                ref.reliability_rating = ReliabilityRating.UNKNOWN
        
        return ref


class DoseResponseCurve(ABC):
    """
    Abstract base class for all dose-response curve types.
    
    This class defines the interface for all dose-response models
    and provides common functionality for confidence bounds, visualization,
    and metadata management.
    """
    
    def __init__(
        self,
        chemical_id: str,
        response_type: ResponseType,
        response_name: str,
        curve_name: Optional[str] = None,
        dose_unit: str = "ppm",
        response_unit: Optional[str] = None,
        references: Optional[List[LiteratureReference]] = None,
        notes: Optional[str] = None
    ):
        """
        Initialize a dose-response curve.
        
        Args:
            chemical_id: ID of the chemical this curve applies to
            response_type: Category of physiological response
            response_name: Specific name of the response (e.g., "bronchoconstriction")
            curve_name: Optional name for this curve
            dose_unit: Unit of measure for dose (e.g., "ppm", "mg/m³")
            response_unit: Unit of measure for response (if applicable)
            references: List of literature references supporting this curve
            notes: Additional information about this curve
        """
        self.curve_id = str(uuid.uuid4())
        self.chemical_id = chemical_id
        self.response_type = response_type
        self.response_name = response_name
        self.curve_name = curve_name or f"{chemical_id}_{response_name}_response"
        self.dose_unit = dose_unit
        self.response_unit = response_unit
        self.references = references or []
        self.notes = notes
        
        # Set creation timestamp
        self.created_at = datetime.now().isoformat()
        
        # Confidence interval settings
        self._confidence_level = 0.95  # 95% confidence by default
        
        # Dose range data
        self.min_validated_dose = None  # Minimum dose with validated data
        self.max_validated_dose = None  # Maximum dose with validated data
    
    @property
    def confidence_level(self) -> float:
        """Get the confidence level for bounds (0.0-1.0)."""
        return self._confidence_level
    
    @confidence_level.setter
    def confidence_level(self, level: float):
        """Set the confidence level for bounds (0.0-1.0)."""
        if not 0 < level < 1:
            raise ValueError("Confidence level must be between 0 and 1")
        self._confidence_level = level
         @abstractmethod
    def calculate_response(
        self, 
        dose: float,
        include_confidence_bounds: bool = False
    ) -> Union[float, Tuple[float, float, float]]:
        """
        Calculate the response for a given dose.
        
        Args:
            dose: The exposure dose in dose_unit
            include_confidence_bounds: If True, returns (response, lower_bound, upper_bound)
                                      If False, returns just the response
            
        Returns:
            If include_confidence_bounds is False: response value
            If include_confidence_bounds is True: (response, lower_bound, upper_bound)
        """
        pass
    
    def calculate_responses(
        self,
        doses: List[float],
        include_confidence_bounds: bool = False
    ) -> Union[List[float], Tuple[List[float], List[float], List[float]]]:
        """
        Calculate responses for multiple doses.
        
        Args:
            doses: List of exposure doses in dose_unit
            include_confidence_bounds: If True, returns tuple of lists with bounds
                                      If False, returns just the response list
            
        Returns:
            If include_confidence_bounds is False: list of response values
            If include_confidence_bounds is True: (responses, lower_bounds, upper_bounds)
        """
        if include_confidence_bounds:
            responses, lower_bounds, upper_bounds = [], [], []
            for dose in doses:
                response, lower, upper = self.calculate_response(dose, True)
                responses.append(response)
                lower_bounds.append(lower)
                upper_bounds.append(upper)
            return responses, lower_bounds, upper_bounds
        else:
            return [self.calculate_response(dose) for dose in doses]
    
    @abstractmethod
    def fit_to_data(
        self,
        doses: List[float],
        responses: List[float],
        weights: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Fit the curve parameters to empirical dose-response data.
        
        Args:
            doses: List of dose values
            responses: List of corresponding response values
            weights: Optional weights for each data point (e.g., 1/variance)
            
        Returns:
            Dictionary containing fit results including parameters and quality metrics
        """
        pass
    
    def calculate_ec_value(self, response_level: float) -> Optional[float]:
        """
        Calculate the dose that produces the specified response level.
        
        Args:
            response_level: The target response level
            
        Returns:
            Dose producing the specified response level, or None if not found
        """
        # Default implementation uses binary search
        # Subclasses may override with analytical solutions
        
        # First check if the response level is achievable
        min_resp = self.calculate_response(0.0)
        max_resp = self.calculate_response(1e6)  # Use a very large dose as an approximation of infinity
        
        # Check if response level is within achievable range
        if not (min(min_resp, max_resp) <= response_level <= max(min_resp, max_resp)):
            return None
        
        # Binary search for dose producing the target response
        low_dose = 0.0
        high_dose = 1e6
        tolerance = 1e-6
        max_iterations = 100
        
        for _ in range(max_iterations):
            mid_dose = (low_dose + high_dose) / 2
            mid_response = self.calculate_response(mid_dose)
            
            if abs(mid_response - response_level) < tolerance:
                return mid_dose
            
            if (mid_response < response_level) == (max_resp > min_resp):
                low_dose = mid_dose
            else:
                high_dose = mid_dose
                
        # Return the best approximation after max iterations
        return (low_dose + high_dose) / 2
    
    def calculate_ec50(self) -> Optional[float]:
        """
        Calculate the EC50 value (dose producing 50% of maximum response).
        
        Returns:
            EC50 value, or None if not applicable/findable
        """
        # Default implementation - subclasses may override with direct parameter access
        min_resp = self.calculate_response(0.0)
        max_resp = self.calculate_response(1e6)  # Very large dose
        
        # Calculate the 50% response level
        target_response = min_resp + (max_resp - min_resp) * 0.5
        
        return self.calculate_ec_value(target_response)
    
    def plot_curve(
        self,
        dose_range: Optional[Tuple[float, float]] = None,
        num_points: int = 100,
        show_confidence: bool = True,
        show_data: bool = True,
        data_doses: Optional[List[float]] = None,
        data_responses: Optional[List[float]] = None,
        title: Optional[str] = None,
        save_path: Optional[str] = None,
        log_scale: bool = False
    ):
        """
        Plot the dose-response curve.
        
        Args:
            dose_range: Optional (min_dose, max_dose) to plot
            num_points: Number of points to plot on the curve
            show_confidence: Whether to show confidence bounds
            show_data: Whether to show empirical data points (if provided)
            data_doses: List of empirical dose values
            data_responses: List of empirical response values
            title: Custom plot title
            save_path: If provided, save plot to this file path
            log_scale: Whether to use logarithmic scale for dose axis
        """
        # Determine dose range if not specified
        if dose_range is None:
            if self.min_validated_dose is not None and self.max_validated_dose is not None:
                min_dose = self.min_validated_dose * 0.1  # Go lower to show threshold effects
                max_dose = self.max_validated_dose * 1.5  # Go higher to show plateau effects
            elif data_doses:
                min_dose = min(data_doses) * 0.1
                max_dose = max(data_doses) * 1.5
            else:
                # Fallback to arbitrary range if no guidance available
                min_dose = 0.01
                max_dose = 10.0
        else:
            min_dose, max_dose = dose_range
        
        # Generate curve
        if log_scale and min_dose <= 0:
            # Adjust minimum dose for log scale
            min_dose = max(min_dose, 0.001)
            
        if log_scale:
            # For log scale, use logarithmically spaced points
            doses = np.logspace(np.log10(min_dose), np.log10(max_dose), num_points)
        else:
            doses = np.linspace(min_dose, max_dose, num_points)
        
        # Calculate responses with confidence bounds
        if show_confidence:
            responses, lower_bounds, upper_bounds = self.calculate_responses(doses.tolist(), True)
        else:
            responses = self.calculate_responses(doses.tolist(), False)
        
        # Create plot
        plt.figure(figsize=(10, 6))
        
        # Plot the curve
        plt.plot(doses, responses, 'b-', linewidth=2, label='Dose-Response Curve')
        
        # Plot confidence bounds if requested
        if show_confidence:
            plt.fill_between(doses, lower_bounds, upper_bounds, color='b', alpha=0.2,
                            label=f'{int(self.confidence_level*100)}% Confidence Interval')
        
        # Plot data points if provided
        if show_data and data_doses and data_responses:
            plt.scatter(data_doses, data_responses, color='red', s=30, label='Empirical Data')
        
        # Set title and labels
        if title:
            plt.title(title, fontsize=14)
        else:
            plt.title(f'Dose-Response Curve: {self.response_name}', fontsize=14)
            
        plt.xlabel(f'Dose ({self.dose_unit})', fontsize=12)
        ylabel = f'Response' if not self.response_unit else f'Response ({self.response_unit})'
        plt.ylabel(ylabel, fontsize=12)
        
        # Set log scale if requested
        if log_scale:
            plt.xscale('log')
        
        # Show grid and legend
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # Save if path provided
        if save_path:
            plt.tight_layout()
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    def add_reference(self, reference: LiteratureReference):
        """
        Add a literature reference to this curve.
        
        Args:
            reference: The LiteratureReference to add
        """
        self.references.append(reference)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert curve to dictionary representation.
        
        Returns:
            Dictionary containing all curve data
        """
        return {
            "curve_id": self.curve_id,
            "curve_type": self.__class__.__name__,
            "chemical_id": self.chemical_id,
            "response_type": self.response_type.name,
            "response_name": self.response_name,
            "curve_name": self.curve_name,
            "dose_unit": self.dose_unit,
            "response_unit": self.response_unit,
            "min_validated_dose": self.min_validated_dose,
            "max_validated_dose": self.max_validated_dose,
            "confidence_level": self.confidence_level,
            "references": [ref.to_dict() for ref in self.references],
            "notes": self.notes,
            "created_at": self.created_at,
            "parameters": self._get_parameters_dict()
        }
    
    @abstractmethod
    def _get_parameters_dict(self) -> Dict[str, Any]:
        """
        Get dictionary of model-specific parameters.
        
        Returns:
            Dictionary of parameter names and values
        """
        pass
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DoseResponseCurve':
        """
        Create a curve object from dictionary data.
        
        Args:
            data: Dictionary containing curve data
            
        Returns:
            Appropriate DoseResponseCurve subclass instance
        """
        # This needs to be implemented in subclasses but we provide
        # a basic implementation to handle common parameters
        curve_type = data.get("curve_type", "")
        
        # Map curve type to class (must be updated when adding new curve types)
        curve_classes = {
            "LinearDoseResponse": LinearDoseResponse,
            "LogLogisticDoseResponse": LogLogisticDoseResponse,
            "LogProbitDoseResponse": LogProbitDoseResponse,
            "HormeticDoseResponse": HormeticDoseResponse,
            "MultiExponentialDoseResponse": MultiExponentialDoseResponse,
            "MixtureDoseResponse": MixtureDoseResponse
        }
        
        if curve_type not in curve_classes:
            raise ValueError(f"Unknown dose-response curve type: {curve_type}")
            
        # Delegate to the appropriate subclass
        return curve_classes[curve_type].from_dict(data)
    class LinearDoseResponse(DoseResponseCurve):
    """
    Linear dose-response model with optional threshold.
    
    This model represents a simple linear relationship between dose and response,
    with an optional threshold below which no response occurs.
    
    Formula: response = max(0, slope * (dose - threshold))
    """
    
    def __init__(
        self,
        chemical_id: str,
        response_type: ResponseType,
        response_name: str,
        slope: float,
        threshold: float = 0.0,
        variance: Optional[float] = None,
        **kwargs
    ):
        """
        Initialize a linear dose-response curve.
        
        Args:
            chemical_id: ID of the chemical this curve applies to
            response_type: Category of physiological response
            response_name: Specific name of the response
            slope: Steepness of the linear relationship
            threshold: Dose below which no response occurs (default: 0.0)
            variance: Variance of the response for uncertainty calculation
            **kwargs: Additional arguments to pass to DoseResponseCurve constructor
        """
        super().__init__(chemical_id, response_type, response_name, **kwargs)
        self.slope = slope
        self.threshold = threshold
        self.variance = variance or (slope * 0.1) ** 2  # Default to 10% of slope if not provided
    
    def calculate_response(
        self, 
        dose: float,
        include_confidence_bounds: bool = False
    ) -> Union[float, Tuple[float, float, float]]:
        """
        Calculate the response for a given dose.
        
        Args:
            dose: The exposure dose
            include_confidence_bounds: If True, returns (response, lower_bound, upper_bound)
            
        Returns:
            If include_confidence_bounds is False: response value
            If include_confidence_bounds is True: (response, lower_bound, upper_bound)
        """
        # Calculate the response
        response = max(0, self.slope * (dose - self.threshold))
        
        if not include_confidence_bounds:
            return response
        
        # Calculate confidence bounds
        # For simple linear model, we use standard error based on variance
        std_dev = np.sqrt(self.variance)
        z_score = stats.norm.ppf((1 + self.confidence_level) / 2)
        margin = z_score * std_dev
        
        lower_bound = max(0, response - margin)
        upper_bound = response + margin
        
        return response, lower_bound, upper_bound
    
    def fit_to_data(
        self,
        doses: List[float],
        responses: List[float],
        weights: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Fit the linear model to empirical dose-response data.
        
        Args:
            doses: List of dose values
            responses: List of corresponding response values
            weights: Optional weights for each data point
            
        Returns:
            Dictionary containing fit results and parameters
        """
        # Convert to numpy arrays
        x = np.array(doses)
        y = np.array(responses)
        w = np.array(weights) if weights else np.ones_like(x)
        
        # Define fitting function for linear model with threshold
        def linear_model(x, slope, threshold):
            return np.maximum(0, slope * (x - threshold))
        
        # Initial parameter guesses
        # Estimate threshold as minimum dose with non-zero response
        positive_responses = [doses[i] for i, r in enumerate(responses) if r > 0]
        initial_threshold = min(positive_responses) if positive_responses else 0
        
        # Estimate slope from data points above threshold
        above_threshold = [i for i, d in enumerate(doses) if d > initial_threshold]
        if above_threshold:
            # Use highest dose and response to estimate slope
            max_index = above_threshold[-1]
            initial_slope = responses[max_index] / (doses[max_index] - initial_threshold)
        else:
            initial_slope = 1.0
        
        # Initial parameter guesses
        initial_params = [initial_slope, initial_threshold]
        
        try:
            # Perform curve fitting
            params, pcov = optimize.curve_fit(
                linear_model, x, y, p0=initial_params, sigma=1/np.sqrt(w),
                bounds=([0, 0], [np.inf, np.inf])  # Enforce positive slope and threshold
            )
            
            # Extract parameters
            slope, threshold = params
            
            # Calculate variance
            residuals = y - linear_model(x, slope, threshold)
            variance = np.sum(residuals**2) / (len(x) - len(params))
            
            # Update model parameters
            self.slope = slope
            self.threshold = threshold
            self.variance = variance
            
            # Set validated dose range
            self.min_validated_dose = min(doses)
            self.max_validated_dose = max(doses)
            
            # Calculate goodness of fit
            r_squared = 1 - np.sum(residuals**2) / np.sum((y - np.mean(y))**2)
            rmse = np.sqrt(np.mean(residuals**2))
            
            return {
                "success": True,
                "slope": slope,
                "threshold": threshold,
                "variance": variance,
                "r_squared": r_squared,
                "rmse": rmse,
                "params_covariance": pcov.tolist()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_parameters_dict(self) -> Dict[str, Any]:
        """Get dictionary of model-specific parameters."""
        return {
            "slope": self.slope,
            "threshold": self.threshold,
            "variance": self.variance
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LinearDoseResponse':
        """Create a LinearDoseResponse from a dictionary."""
        # Extract parameters specific to this model
        params = data.get("parameters", {})
        slope = params.get("slope")
        threshold = params.get("threshold", 0.0)
        variance = params.get("variance")
        
        # Create object with required parameters
        response_type = ResponseType[data["response_type"]]
        curve = cls(
            chemical_id=data["chemical_id"],
            response_type=response_type,
            response_name=data["response_name"],
            slope=slope,
            threshold=threshold,
            variance=variance,
            curve_name=data.get("curve_name"),
            dose_unit=data.get("dose_unit", "ppm"),
            response_unit=data.get("response_unit")
        )
        
        # Add other attributes from the dictionary
        curve.curve_id = data.get("curve_id", curve.curve_id)
        curve.min_validated_dose = data.get("min_validated_dose")
        curve.max_validated_dose = data.get("max_validated_dose")
        curve.notes = data.get("notes")
        curve.created_at = data.get("created_at", curve.created_at)
        
        if "confidence_level" in data:
            curve.confidence_level = data["confidence_level"]
        
        # Add references
        if "references" in data:
            for ref_data in data["references"]:
                curve.references.append(LiteratureReference.from_dict(ref_data))
                
        return curve


class LogLogisticDoseResponse(DoseResponseCurve):
    """
    Log-logistic dose-response model (4PL model).
    
    This model follows a sigmoidal curve with a logistic function and is widely used
    for many toxicological and pharmacological responses. It's also known as the 
    4-parameter logistic (4PL) model in the literature.
    
    Formula: response = bottom + (top - bottom) / (1 + (dose/ec50)^hill_slope)
    
    Where:
    - bottom: Minimum response level
    - top: Maximum response level
    - ec50: Dose that produces 50% of the maximum response
    - hill_slope: Steepness parameter (Hill coefficient)
    
    References:
    - "The Four Parameter Logistic Model" (Journal of Biopharmaceutical Statistics, 2020)
    """
    
    def __init__(
        self,
        chemical_id: str,
        response_type: ResponseType,
        response_name: str,
        ec50: float,
        hill_slope: float,
        bottom: float = 0.0,
        top: float = 1.0,
        variance: Optional[float] = None,
        **kwargs
    ):
        """
        Initialize a log-logistic dose-response curve.
        
        Args:
            chemical_id: ID of the chemical this curve applies to
            response_type: Category of physiological response
            response_name: Specific name of the response
            ec50: Dose producing 50% of maximum response
            hill_slope: Steepness parameter (positive for increasing, negative for decreasing)
            bottom: bottom: Minimum response level (default: 0.0)
            top: Maximum response level (default: 1.0)
            variance: Variance of the response for uncertainty calculation
            **kwargs: Additional arguments to pass to DoseResponseCurve constructor
        """
        super().__init__(chemical_id, response_type, response_name, **kwargs)
        self.ec50 = ec50
        self.hill_slope = hill_slope
        self.bottom = bottom
        self.top = top
        self.variance = variance or ((top - bottom) * 0.1) ** 2  # Default to 10% of range
    
    def calculate_response(
        self, 
        dose: float,
        include_confidence_bounds: bool = False
    ) -> Union[float, Tuple[float, float, float]]:
        """
        Calculate the response for a given dose using the log-logistic model.
        
        Args:
            dose: The exposure dose
            include_confidence_bounds: If True, returns confidence bounds
            
        Returns:
            Response value or (response, lower_bound, upper_bound)
        """
        # Handle very small doses to avoid numerical issues
        if dose < 1e-10:
            dose = 1e-10
            
        # Calculate the response using the 4PL equation
        term = (dose / self.ec50) ** self.hill_slope
        response = self.bottom + (self.top - self.bottom) / (1 + term)
        
        if not include_confidence_bounds:
            return response
        
        # Calculate confidence bounds
        # For 4PL model, uncertainty is higher near EC50 and lower at extremes
        # We use a heuristic based on distance from EC50 in log space
        log_distance = abs(np.log10(dose) - np.log10(self.ec50))
        scale_factor = max(0.1, 1.0 / (1 + log_distance))  # Higher uncertainty near EC50
        
        std_dev = np.sqrt(self.variance) * scale_factor
        z_score = stats.norm.ppf((1 + self.confidence_level) / 2)
        margin = z_score * std_dev
        
        lower_bound = max(self.bottom, response - margin)
        upper_bound = min(self.top, response + margin)
        
        return response, lower_bound, upper_bound
    
    def calculate_ec50(self) -> float:
        """
        Return the EC50 value directly from the model parameters.
        
        Returns:
            EC50 value
        """
        # For the 4PL model, EC50 is a direct parameter
        return self.ec50
    
    def fit_to_data(
        self,
        doses: List[float],
        responses: List[float],
        weights: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Fit the log-logistic model to empirical dose-response data.
        
        Args:
            doses: List of dose values
            responses: List of corresponding response values
            weights: Optional weights for each data point
            
        Returns:
            Dictionary containing fit results and parameters
        """
        # Convert to numpy arrays
        x = np.array(doses)
        y = np.array(responses)
        w = np.array(weights) if weights else np.ones_like(x)
        
        # Define fitting function for 4PL model
        def loglogistic_model(x, ec50, hill_slope, bottom, top):
            x_safe = np.maximum(x, 1e-10)  # Avoid numerical issues
            term = (x_safe / ec50) ** hill_slope
            return bottom + (top - bottom) / (1 + term)
        
        # Initial parameter guesses
        min_response = min(responses)
        max_response = max(responses)
        # Estimate EC50 from data (where response is halfway between min and max)
        target = (min_response + max_response) / 2
        closest_idx = np.argmin(np.abs(np.array(responses) - target))
        initial_ec50 = doses[closest_idx]
        
        # Use default hill_slope direction based on response direction
        if responses[-1] > responses[0]:
            initial_hill_slope = -1.0  # Increasing response
        else:
            initial_hill_slope = 1.0  # Decreasing response
        
        # Initial parameter guesses
        initial_params = [initial_ec50, initial_hill_slope, min_response, max_response]
        
        try:
            # Perform curve fitting
            params, pcov = optimize.curve_fit(
                loglogistic_model, x, y, p0=initial_params, sigma=1/np.sqrt(w),
                bounds=([1e-10, -100, -np.inf, -np.inf], [np.inf, 100, np.inf, np.inf])
            )
            
            # Extract parameters
            ec50, hill_slope, bottom, top = params
            
            # Calculate variance
            residuals = y - loglogistic_model(x, ec50, hill_slope, bottom, top)
            variance = np.sum(residuals**2) / (len(x) - len(params))
            
            # Update model parameters
            self.ec50 = ec50
            self.hill_slope = hill_slope
            self.bottom = bottom
            self.top = top
            self.variance = variance
            
            # Set validated dose range
            self.min_validated_dose = min(doses)
            self.max_validated_dose = max(doses)
            
            # Calculate goodness of fit
            r_squared = 1 - np.sum(residuals**2) / np.sum((y - np.mean(y))**2)
            rmse = np.sqrt(np.mean(residuals**2))
            
            return {
                "success": True,
                "ec50": ec50,
                "hill_slope": hill_slope,
                "bottom": bottom,
                "top": top,
                "variance": variance,
                "r_squared": r_squared,
                "rmse": rmse,
                "params_covariance": pcov.tolist()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_parameters_dict(self) -> Dict[str, Any]:
        """Get dictionary of model-specific parameters."""
        return {
            "ec50": self.ec50,
            "hill_slope": self.hill_slope,
            "bottom": self.bottom,
            "top": self.top,
            "variance": self.variance
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LogLogisticDoseResponse':
        """Create a LogLogisticDoseResponse from a dictionary."""
        # Extract parameters specific to this model
        params = data.get("parameters", {})
        ec50 = params.get("ec50")
        hill_slope = params.get("hill_slope")
        bottom = params.get("bottom", 0.0)
        top = params.get("top", 1.0)
        variance = params.get("variance")
        
        # Create object with required parameters
        response_type = ResponseType[data["response_type"]]
        curve = cls(
            chemical_id=data["chemical_id"],
            response_type=response_type,
            response_name=data["response_name"],
            ec50=ec50,
            hill_slope=hill_slope,
            bottom=bottom,
            top=top,
            variance=variance,
            curve_name=data.get("curve_name"),
            dose_unit=data.get("dose_unit", "ppm"),
            response_unit=data.get("response_unit")
        )
        
        # Add other attributes from the dictionary
        curve.curve_id = data.get("curve_id", curve.curve_id)
        curve.min_validated_dose = data.get("min_validated_dose")
        curve.max_validated_dose = data.get("max_validated_dose")
        curve.notes = data.get("notes")
        curve.created_at = data.get("created_at", curve.created_at)
        
        if "confidence_level" in data:
            curve.confidence_level = data["confidence_level"]
        
        # Add references
        if "references" in data:
            for ref_data in data["references"]:
                curve.references.append(LiteratureReference.from_dict(ref_data))
                
        return curve


class LogProbitDoseResponse(DoseResponseCurve):
    """
    Log-probit dose-response model.
    
    This model follows a sigmoidal curve based on the cumulative distribution function
    of the normal distribution. It's widely used in toxicology and risk assessment.
    
    Formula: response = bottom + (top - bottom) * Φ((log(dose) - location) / scale)
    
    Where:
    - bottom: Minimum response level
    - top: Maximum response level
    - location: Log of dose that produces 50% of maximum response (like log(EC50))
    - scale: Steepness parameter (inverse of Hill slope in logistic model)
    - Φ: Cumulative distribution function of the standard normal distribution
    
    References:
    - "Probit Analysis" (Toxicology Research, 2018)
    """
    
    def __init__(
        self,
        chemical_id: str,
        response_type: ResponseType,
        response_name: str,
        location: float,  # log of EC50
        scale: float,     # inverse of Hill slope
        bottom: float = 0.0,
        top: float = 1.0,
        variance: Optional[float] = None,
        **kwargs
    ):
        """
        Initialize a log-probit dose-response curve.
        
        Args:
            chemical_id: ID of the chemical this curve applies to
            response_type: Category of physiological response
            response_name: Specific name of the response
            location: Log of dose producing 50% of maximum response
            scale: Steepness parameter (smaller values = steeper curves)
            bottom: Minimum response level (default: 0.0)
            top: Maximum response level (default: 1.0)
            variance: Variance of the response for uncertainty calculation
            **kwargs: Additional arguments to pass to DoseResponseCurve constructor
        """
        super().__init__(chemical_id, response_type, response_name, **kwargs)
        self.location = location
        self.scale = scale
        self.bottom = bottom
        self.top = top
        self.variance = variance or ((top - bottom) * 0.1) ** 2
    
    def calculate_response(
        self, 
        dose: float,
        include_confidence_bounds: bool = False
    ) -> Union[float, Tuple[float, float, float]]:
        """
        Calculate the response for a given dose using the log-probit model.
        
        Args:
            dose: The exposure dose
            include_confidence_bounds: If True, returns confidence bounds
            
        Returns:
            Response value or (response, lower_bound, upper_bound)
        """
        # Handle very small doses to avoid numerical issues with log
        if dose < 1e-10:
            dose = 1e-10
        
        # Calculate using probit model with the normal CDF
        z = (np.log(dose) - self.location) / self.scale
        response = self.bottom + (self.top - self.bottom) * stats.norm.cdf(z)
        
        if not include_confidence_bounds:
            return response
        
        # Calculate confidence bounds
        # Similar heuristic as LogLogistic - higher uncertainty near inflection point
        z_distance = abs(z)
        scale_factor = max(0.1, 1.0 / (1 + z_distance))
        
        std_dev = np.sqrt(self.variance) * scale_factor
        z_score = stats.norm.ppf((1 + self.confidence_level) / 2)
        margin = z_score * std_dev
        
        lower_bound = max(self.bottom, response - margin)
        upper_bound = min(self.top, response + margin)
        
        return response, lower_bound, upper_bound
    
    def calculate_ec50(self) -> float:
        """
        Calculate the EC50 value from the location parameter.
        
        Returns:
            EC50 value
        """
        # EC50 is exp(location) in the log-probit model
        return np.exp(self.location)
    
    def fit_to_data(
        self,
        doses: List[float],
        responses: List[float],
        weights: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Fit the log-probit model to empirical dose-response data.
        """
        # Initial parameter guesses
        initial_params = {
            "location": np.log(np.median(doses)),
            "scale": 1.0,
            "bottom": 0.0,
            "top": 1.0
        }
        
        # Define the objective function for fitting
        def objective_function(params: Dict[str, float]) -> float:
            self.location = params["location"]
            self.scale = params["scale"]
            self.bottom = params["bottom"]
            self.top = params["top"]
            # Calculate the predicted responses
            predicted = [self.calculate_response(dose) for dose in doses]
            # Compute the weighted residuals
            residuals = [(resp - pred) ** 2 for resp, pred in zip(responses, predicted)]
            if weights is not None:
                residuals = [w * r for w, r in zip(weights, residuals)]
            return np.sum(residuals)

        # Optimize the parameters
        result = minimize(objective_function, initial_params, method="L-BFGS-B")
        if not result.success:
            raise RuntimeError("Parameter fitting failed")

        # Update the model parameters with the optimized values
        self.location = result.x["location"]
        self.scale = result.x["scale"]
        self.bottom = result.x["bottom"]
        self.top = result.x["top"]

        return {
            "location": self.location,
            "scale": self.scale,
            "bottom": self.bottom,
            "top": self.top
        }
    Args:
            doses: List of dose values
            responses: List of corresponding response values
            weights: Optional weights for each data point
            
        Returns:
            Dictionary containing fit results and parameters
        """
        # Convert to numpy arrays
        x = np.array(doses)
        y = np.array(responses)
        w = np.array(weights) if weights else np.ones_like(x)
        
        # Define fitting function for log-probit model
        def logprobit_model(x, location, scale, bottom, top):
            x_safe = np.maximum(x, 1e-10)  # Avoid numerical issues
            z = (np.log(x_safe) - location) / scale
            return bottom + (top - bottom) * stats.norm.cdf(z)
        
        # Initial parameter guesses
        min_response = min(responses)
        max_response = max(responses)
        
        # Estimate EC50 similar to LogLogisticDoseResponse
        target = (min_response + max_response) / 2
        closest_idx = np.argmin(np.abs(np.array(responses) - target))
        initial_ec50 = doses[closest_idx]
        initial_location = np.log(initial_ec50)
        
        # Default scale parameter
        initial_scale = 1.0
        
        # Initial parameter guesses
        initial_params = [initial_location, initial_scale, min_response, max_response]
        
        try:
            # Perform curve fitting
            params, pcov = optimize.curve_fit(
                logprobit_model, x, y, p0=initial_params, sigma=1/np.sqrt(w),
                bounds=([-np.inf, 0.01, -np.inf, -np.inf], [np.inf, 100, np.inf, np.inf])
            )
            
            # Extract parameters
            location, scale, bottom, top = params
            
            # Calculate variance
            residuals = y - logprobit_model(x, location, scale, bottom, top)
            variance = np.sum(residuals**2) / (len(x) - len(params))
            
            # Update model parameters
            self.location = location
            self.scale = scale
            self.bottom = bottom
            self.top = top
            self.variance = variance
            
            # Set validated dose range
            self.min_validated_dose = min(doses)
            self.max_validated_dose = max(doses)
            
            # Calculate goodness of fit
            r_squared = 1 - np.sum(residuals**2) / np.sum((y - np.mean(y))**2)
            rmse = np.sqrt(np.mean(residuals**2))
            
            return {
                "success": True,
                "location": location,
                "scale": scale,
                "bottom": bottom,
                "top": top,
                "variance": variance,
                "r_squared": r_squared,
                "rmse": rmse,
                "params_covariance": pcov.tolist()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_parameters_dict(self) -> Dict[str, Any]:
        """Get dictionary of model-specific parameters."""
        return {
            "location": self.location,
            "scale": self.scale,
            "bottom": self.bottom,
            "top": self.top,
            "variance": self.variance
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LogProbitDoseResponse':
        """Create a LogProbitDoseResponse from a dictionary."""
        # Extract parameters specific to this model
        params = data.get("parameters", {})
        location = params.get("location")
        scale = params.get("scale")
        bottom = params.get("bottom", 0.0)
        top = params.get("top", 1.0)
        variance = params.get("variance")
        
        # Create object with required parameters
        response_type = ResponseType[data["response_type"]]
        curve = cls(
            chemical_id=data["chemical_id"],
            response_type=response_type,
            response_name=data["response_name"],
            location=location,
            scale=scale,
            bottom=bottom,
            top=top,
            variance=variance,
            curve_name=data.get("curve_name"),
            dose_unit=data.get("dose_unit", "ppm"),
            response_unit=data.get("response_unit")
        )
        
        # Add other attributes from the dictionary
        curve.curve_id = data.get("curve_id", curve.curve_id)
        curve.min_validated_dose = data.get("min_validated_dose")
        curve.max_validated_dose = data.get("max_validated_dose")
        curve.notes = data.get("notes")
        curve.created_at = data.get("created_at", curve.created_at)
        
        if "confidence_level" in data:
            curve.confidence_level = data["confidence_level"]
        
        # Add references
        if "references" in data:
            for ref_data in data["references"]:
                curve.references.append(LiteratureReference.from_dict(ref_data))
                
        return curve


class HormeticDoseResponse(DoseResponseCurve):
    """
    Hormetic dose-response model showing biphasic behavior.
    
    This model captures the hormesis phenomenon, where low doses stimulate and
    high doses inhibit (or vice versa). The model uses a modified form of the
    Brain-Cousens equation for hormesis in dose-response relationships.
    
    Formula: response = c + (d-c+f*x)/[1 + exp(b*(log(x)-log(e)))]
    
    Where:
    - c: Lower asymptote (response at zero dose)
    - d: Upper asymptote (response at infinite dose)
    - b: Hill slope (steepness)
    - e: EC50 parameter (inflection point)
    - f: Hormesis parameter (controls magnitude of hormetic effect)
    
    References:
    - "Beyond the Hill Equation" (Environmental Health Perspectives, 2021)
    - "Brain-Cousens Model for Hormesis" (Toxicological Sciences, 2017)
    """
    
    def __init__(
        self,
        chemical_id: str,
        response_type: ResponseType,
        response_name: str,
        ec50: float,         # e parameter
        hill_slope: float,   # b parameter
        bottom: float,       # c parameter
        top: float,          # d parameter
        hormesis: float,     # f parameter
        variance: Optional[float] = None,
        **kwargs
    ):
        """
        Initialize a hormetic dose-response curve.
        
        Args:
            chemical_id: ID of the chemical this curve applies to
            response_type: Category of physiological response
            response_name: Specific name of the response
            ec50: Dose at the inflection point (e parameter)
            hill_slope: Steepness parameter (b parameter)
            bottom: Lower asymptote (c parameter, response at zero dose)
            top: Upper asymptote (d parameter, response at infinite dose)
            hormesis: Parameter controlling hormetic effect (f parameter)
            variance: Variance of the response for uncertainty calculation
            **kwargs: Additional arguments to pass to DoseResponseCurve constructor
        """
        super().__init__(chemical_id, response_type, response_name, **kwargs)
        self.ec50 = ec50
        self.hill_slope = hill_slope
        self.bottom = bottom
        self.top = top
        self.hormesis = hormesis
        self.variance = variance or ((top - bottom) * 0.1) ** 2