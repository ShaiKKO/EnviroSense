"""
Type definitions for dose-response models.

This module defines the common types, enums, and type aliases used
throughout the dose-response modeling system.
"""

from enum import Enum, auto
from typing import Union, Dict, Any, List, Optional, TypeVar
import numpy as np


class ResponseType(str, Enum):
    """Type of biological/health response being modeled."""
    
    # Binary/discrete responses
    BINARY = "binary"  # Binary yes/no response (e.g., affected vs unaffected)
    QUANTAL = "quantal"  # Proportion of population affected at a dose
    
    # Continuous responses
    CONTINUOUS = "continuous"  # Continuous measurement (e.g., enzyme activity)
    SEVERITY = "severity"  # Graded severity response
    
    # Special response types
    TEMPORAL = "temporal"  # Time-to-event response
    HORMETIC = "hormetic"  # Non-monotonic with beneficial effects at low doses
    
    # Default
    UNDEFINED = "undefined"
    
    def __str__(self) -> str:
        return self.value


class DoseUnit(str, Enum):
    """Units for dose measurement."""
    
    # Concentration-based
    PPM = "ppm"  # Parts per million
    PPB = "ppb"  # Parts per billion
    MG_PER_M3 = "mg/m³"  # Milligrams per cubic meter
    UG_PER_M3 = "μg/m³"  # Micrograms per cubic meter
    
    # Mass-based
    MG_PER_KG = "mg/kg"  # Milligrams per kilogram body weight (oral)
    UG_PER_KG = "μg/kg"  # Micrograms per kilogram body weight
    
    # Time-integrated
    MG_PER_KG_DAY = "mg/kg-day"  # Daily intake per body weight
    UG_PER_KG_DAY = "μg/kg-day"  # Daily intake per body weight (micro)
    
    # Default
    DIMENSIONLESS = "dimensionless"  # Relative or normalized dose
    ARBITRARY = "arbitrary"  # Arbitrary units
    
    def __str__(self) -> str:
        return self.value


class ResponseUnit(str, Enum):
    """Units for response measurement."""
    
    # Probability-based
    PROBABILITY = "probability"  # 0-1 probability
    PERCENT = "percent"  # Percentage (0-100%)
    FRACTION = "fraction"  # Fraction affected (0-1)
    LOGIT = "logit"  # Log-odds scale
    PROBIT = "probit"  # Probability units (normal quantile)
    
    # Relative units
    RELATIVE = "relative"  # Relative to control (fold-change)
    PERCENT_CONTROL = "percent_control"  # Percentage of control value
    
    # Physiological/clinical
    CONCENTRATION = "concentration"  # Biomarker concentration
    ACTIVITY = "activity"  # Enzyme activity
    CLINICAL_SCORE = "clinical_score"  # Clinical scoring system
    
    # Default
    DIMENSIONLESS = "dimensionless"  # Normalized or relative units
    ARBITRARY = "arbitrary"  # Arbitrary units
    
    def __str__(self) -> str:
        return self.value


class UncertaintyType(str, Enum):
    """Type of uncertainty representation."""
    
    STANDARD_ERROR = "standard_error"  # Standard error
    STANDARD_DEVIATION = "standard_deviation"  # Standard deviation
    VARIANCE = "variance"  # Variance
    CONFIDENCE_INTERVAL = "confidence_interval"  # Confidence interval
    CREDIBLE_INTERVAL = "credible_interval"  # Bayesian credible interval
    PERCENTILE = "percentile"  # Percentile-based range
    NONE = "none"  # No uncertainty information
    
    def __str__(self) -> str:
        return self.value


class ReliabilityRating(str, Enum):
    """Rating for reliability of dose-response data."""
    
    HIGH = "high"  # High reliability (e.g., from multiple well-designed studies)
    MEDIUM = "medium"  # Medium reliability
    LOW = "low"  # Low reliability (e.g., limited data, methodological issues)
    VERY_LOW = "very_low"  # Very low reliability (highly uncertain)
    UNKNOWN = "unknown"  # Unknown reliability
    
    def __str__(self) -> str:
        return self.value


class LiteratureReference:
    """Reference to literature or data source."""
    
    def __init__(
        self,
        title: str,
        authors: List[str],
        year: int,
        source: str,
        doi: Optional[str] = None,
        url: Optional[str] = None,
        pubmed_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> None:
        """
        Initialize a literature reference.
        
        Args:
            title: Title of the publication
            authors: List of author names
            year: Publication year
            source: Journal name or other source
            doi: Digital Object Identifier (optional)
            url: URL to the reference (optional)
            pubmed_id: PubMed ID (optional)
            notes: Additional notes about the reference (optional)
        """
        self.title = title
        self.authors = authors
        self.year = year
        self.source = source
        self.doi = doi
        self.url = url
        self.pubmed_id = pubmed_id
        self.notes = notes
    
    def __str__(self) -> str:
        """Format reference as a string."""
        author_text = ", ".join(self.authors)
        if len(self.authors) > 1:
            last_author = self.authors[-1]
            author_text = f"{', '.join(self.authors[:-1])} and {last_author}"
            
        reference = f"{author_text} ({self.year}). {self.title}. {self.source}."
        if self.doi:
            reference += f" DOI: {self.doi}"
        return reference
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'title': self.title,
            'authors': self.authors,
            'year': self.year,
            'source': self.source,
            'doi': self.doi,
            'url': self.url,
            'pubmed_id': self.pubmed_id,
            'notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LiteratureReference':
        """Create from dictionary representation."""
        return cls(
            title=data['title'],
            authors=data['authors'],
            year=data['year'],
            source=data['source'],
            doi=data.get('doi'),
            url=data.get('url'),
            pubmed_id=data.get('pubmed_id'),
            notes=data.get('notes')
        )


# Type aliases for improved type checking
DoseValue = Union[float, np.ndarray]
ResponseValue = Union[float, np.ndarray]
ParameterDict = Dict[str, float]
