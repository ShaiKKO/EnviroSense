"""
Threshold framework for physiological responses.

This module provides a framework for defining, managing, and evaluating
physiological response thresholds with confidence intervals.

References:
- EPA Guidelines (2023): "Uncertainty Analysis in Risk Assessment"
- WHO (2022): "Threshold Determination for Health Effects"
"""

from typing import Dict, List, Optional, Union, Any, Tuple
import numpy as np
from dataclasses import dataclass
import uuid
import datetime

from envirosense.core.exposure.physiological_response.base import ResponseSeverityLevel


@dataclass
class ResponseThreshold:
    """
    Defines a threshold for physiological response onset.
    
    This class defines a specific threshold level, including its
    uncertainty and confidence interval.
    """
    # Core properties
    response_type: str
    threshold_value: float
    severity_level: ResponseSeverityLevel
    uncertainty: float = 0.2  # Default 20% uncertainty
    
    # Metadata
    name: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = None
    threshold_id: str = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize default values for optional fields."""
        if self.threshold_id is None:
            self.threshold_id = str(uuid.uuid4())
            
        if self.metadata is None:
            self.metadata = {}
            
        if self.name is None:
            self.name = f"{self.response_type} {self.severity_level.name} Threshold"
    
    def get_confidence_interval(self, confidence: float = 0.95) -> Tuple[float, float]:
        """
        Calculate confidence interval for this threshold.
        
        Args:
            confidence: Confidence level (default 95%)
            
        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        # Calculate z-score for the given confidence level
        if confidence == 0.95:
            z_score = 1.96
        elif confidence == 0.99:
            z_score = 2.58
        elif confidence == 0.90:
            z_score = 1.64
        else:
            # For other values, use the normal distribution
            z_score = np.abs(np.percentile(np.random.normal(0, 1, 10000), 
                                         (1 - confidence) * 100 / 2))
        
        # Calculate the margin of error
        margin = self.threshold_value * self.uncertainty * z_score
        
        # Return the confidence interval
        return (max(0, self.threshold_value - margin), 
                self.threshold_value + margin)
    
    def calculate_exceedance_probability(self, response_value: float) -> float:
        """
        Calculate the probability that the true threshold has been exceeded.
        
        Args:
            response_value: The measured or calculated response value
            
        Returns:
            Probability (0-1) that the threshold has been exceeded
        """
        # If the response is exactly at the threshold, probability is 0.5
        if response_value == self.threshold_value:
            return 0.5
            
        # If clearly above or below, return 0 or 1
        if response_value < self.threshold_value * 0.5:
            return 0.0
        if response_value > self.threshold_value * 1.5:
            return 1.0
            
        # Otherwise, calculate based on normal distribution
        # Standardize the response value
        z = (response_value - self.threshold_value) / (self.threshold_value * self.uncertainty)
        
        # Calculate probability from the standard normal CDF
        # Use simplified approximation for CDF
        probability = 0.5 * (1 + np.tanh(np.sqrt(np.pi / 8) * z))
        
        return min(1.0, max(0.0, probability))
    
    def calculate_confidence(self, response_value: float) -> float:
        """
        Calculate confidence that the threshold has been crossed.
        
        Args:
            response_value: The measured or calculated response value
            
        Returns:
            Confidence (0-1) that the threshold has been crossed
        """
        # Simply use the exceedance probability
        return self.calculate_exceedance_probability(response_value)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert threshold to dictionary representation.
        
        Returns:
            Dictionary with threshold properties
        """
        return {
            "threshold_id": self.threshold_id,
            "name": self.name,
            "description": self.description,
            "response_type": self.response_type,
            "threshold_value": self.threshold_value,
            "severity_level": self.severity_level.name,
            "uncertainty": self.uncertainty,
            "source": self.source,
            "metadata": self.metadata
        }


class ThresholdSet:
    """
    A collection of thresholds for a specific response type.
    
    This class manages multiple thresholds for different severity
    levels of the same response type.
    """
    
    def __init__(
        self,
        response_type: str,
        thresholds: Optional[List[ResponseThreshold]] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize a threshold set.
        
        Args:
            response_type: Type of response these thresholds apply to
            thresholds: List of ResponseThreshold objects
            name: Name of the threshold set
            description: Description of the threshold set
            metadata: Additional metadata
        """
        self.response_type = response_type
        self.thresholds = thresholds or []
        self.name = name or f"{response_type} Threshold Set"
        self.description = description or f"Thresholds for {response_type} responses"
        self.metadata = metadata or {}
        
        # Create a map of severity levels to thresholds
        self.threshold_map = {
            threshold.severity_level: threshold for threshold in self.thresholds
        }
    
    def add_threshold(self, threshold: ResponseThreshold) -> None:
        """
        Add a threshold to the set.
        
        Args:
            threshold: ResponseThreshold to add
        """
        # Ensure the threshold is for the correct response type
        if threshold.response_type != self.response_type:
            raise ValueError(
                f"Threshold response type '{threshold.response_type}' does not "
                f"match set response type '{self.response_type}'"
            )
        
        self.thresholds.append(threshold)
        self.threshold_map[threshold.severity_level] = threshold
    
    def get_threshold(
        self, 
        severity_level: ResponseSeverityLevel
    ) -> Optional[ResponseThreshold]:
        """
        Get a threshold by severity level.
        
        Args:
            severity_level: ResponseSeverityLevel to get threshold for
            
        Returns:
            ResponseThreshold for the specified level, or None if not found
        """
        return self.threshold_map.get(severity_level)
    
    def classify_severity(
        self, 
        response_value: float,
        with_confidence: bool = False
    ) -> Union[ResponseSeverityLevel, Tuple[ResponseSeverityLevel, float]]:
        """
        Classify the severity of a response value.
        
        Args:
            response_value: Response value to classify
            with_confidence: If True, also return the confidence level
            
        Returns:
            ResponseSeverityLevel if with_confidence is False,
            Tuple of (ResponseSeverityLevel, confidence) otherwise
        """
        # Default to no response
        result = ResponseSeverityLevel.NONE
        confidence = 0.0
        
        # Sort thresholds by value (ascending)
        sorted_thresholds = sorted(
            self.thresholds,
            key=lambda t: t.threshold_value
        )
        
        # Find the highest threshold that the response exceeds
        # and calculate the confidence for that classification
        for threshold in sorted_thresholds:
            if response_value >= threshold.threshold_value:
                threshold_confidence = threshold.calculate_confidence(response_value)
                
                # Only update if we have higher confidence in this classification
                if threshold_confidence > confidence:
                    result = threshold.severity_level
                    confidence = threshold_confidence
        
        if with_confidence:
            return result, confidence
        return result
    
    def get_classification_details(
        self,
        response_value: float
    ) -> Dict[str, Any]:
        """
        Get detailed classification information for a response value.
        
        Args:
            response_value: Response value to classify
            
        Returns:
            Dictionary with classification details
        """
        # Get basic severity classification and confidence
        severity, confidence = self.classify_severity(response_value, with_confidence=True)
        
        # Get all thresholds and their exceedance probabilities
        threshold_details = []
        for threshold in self.thresholds:
            threshold_details.append({
                "severity_level": threshold.severity_level.name,
                "threshold_value": threshold.threshold_value,
                "exceedance_probability": threshold.calculate_exceedance_probability(response_value),
                "confidence_interval": threshold.get_confidence_interval()
            })
        
        return {
            "response_type": self.response_type,
            "response_value": response_value,
            "classification": severity.name,
            "confidence": confidence,
            "threshold_details": threshold_details
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert threshold set to dictionary representation.
        
        Returns:
            Dictionary with threshold set properties
        """
        return {
            "name": self.name,
            "description": self.description,
            "response_type": self.response_type,
            "thresholds": [threshold.to_dict() for threshold in self.thresholds],
            "metadata": self.metadata
        }


def create_standard_threshold_set(
    response_type: str,
    subclinical_value: float,
    mild_value: float,
    moderate_value: float,
    severe_value: float,
    critical_value: float,
    uncertainty: float = 0.2,
    name: Optional[str] = None,
    description: Optional[str] = None,
    source: Optional[str] = None
) -> ThresholdSet:
    """
    Create a standard set of thresholds with all severity levels.
    
    Args:
        response_type: Type of response for these thresholds
        subclinical_value: Value for subclinical threshold
        mild_value: Value for mild threshold
        moderate_value: Value for moderate threshold
        severe_value: Value for severe threshold
        critical_value: Value for critical threshold
        uncertainty: Uncertainty factor for thresholds
        name: Name for the threshold set
        description: Description for the threshold set
        source: Source/reference for threshold values
        
    Returns:
        ThresholdSet with all standard severity levels
    """
    # Create individual thresholds
    thresholds = [
        ResponseThreshold(
            response_type=response_type,
            threshold_value=subclinical_value,
            severity_level=ResponseSeverityLevel.SUBCLINICAL,
            uncertainty=uncertainty,
            source=source
        ),
        ResponseThreshold(
            response_type=response_type,
            threshold_value=mild_value,
            severity_level=ResponseSeverityLevel.MILD,
            uncertainty=uncertainty,
            source=source
        ),
        ResponseThreshold(
            response_type=response_type,
            threshold_value=moderate_value,
            severity_level=ResponseSeverityLevel.MODERATE,
            uncertainty=uncertainty,
            source=source
        ),
        ResponseThreshold(
            response_type=response_type,
            threshold_value=severe_value,
            severity_level=ResponseSeverityLevel.SEVERE,
            uncertainty=uncertainty,
            source=source
        ),
        ResponseThreshold(
            response_type=response_type,
            threshold_value=critical_value,
            severity_level=ResponseSeverityLevel.CRITICAL,
            uncertainty=uncertainty,
            source=source
        )
    ]
    
    # Create and return the threshold set
    return ThresholdSet(
        response_type=response_type,
        thresholds=thresholds,
        name=name,
        description=description
    )
