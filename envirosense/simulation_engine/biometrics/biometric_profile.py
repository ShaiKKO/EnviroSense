"""
Integrated Biometric Profile Model

This module provides a comprehensive biometric profile that combines multiple biometric signals
(heart rate, skin conductance, respiratory, etc.) into a coordinated physiological response system.
"""

import uuid
import json
import numpy as np
from typing import Dict, List, Optional, Tuple, Union, Any

from envirosense.core.biometrics.base import BiometricSignalModel
from envirosense.core.biometrics.heart_rate import HeartRateModel
from envirosense.core.biometrics.skin_conductance import SkinConductanceModel
from envirosense.core.biometrics.respiratory import RespiratoryModel


class BiometricProfile:
    """Integrated biometric profile model.
    
    This class combines multiple biometric signals into a cohesive physiological response system,
    ensuring coordinated and realistic responses to environmental conditions, stress,
    chemical exposures, and other factors.
    
    Attributes:
        heart_rate (HeartRateModel): Heart rate biometric signal model
        skin_conductance (SkinConductanceModel): Skin conductance biometric signal model
        respiratory (RespiratoryModel): Respiratory biometric signal model
        name (str): Name identifier for this biometric profile
        description (str): Description of the profile
        uuid (str): Unique identifier for this profile instance
        sensitivity_factors (Dict[str, float]): Person-specific sensitivity factors for different stimuli
    """
    
    def __init__(self, 
                name: str = "Default Profile",
                description: str = "Default biometric profile with standard physiological parameters",
                heart_rate: Optional[HeartRateModel] = None,
                skin_conductance: Optional[SkinConductanceModel] = None,
                respiratory: Optional[RespiratoryModel] = None,
                sensitivity_factors: Optional[Dict[str, float]] = None):
        """Initialize the biometric profile.
        
        Args:
            name: Name identifier for this profile
            description: Description of the profile
            heart_rate: Optional pre-configured heart rate model
            skin_conductance: Optional pre-configured skin conductance model
            respiratory: Optional pre-configured respiratory model
            sensitivity_factors: Optional dictionary of person-specific sensitivity factors
        """
        self.name = name
        self.description = description
        self.uuid = str(uuid.uuid4())
        
        # Initialize biometric signal models with defaults if not provided
        self.heart_rate = heart_rate or HeartRateModel()
        self.skin_conductance = skin_conductance or SkinConductanceModel()
        self.respiratory = respiratory or RespiratoryModel()
        
        # Person-specific sensitivity factors (1.0 = standard response)
        self.sensitivity_factors = sensitivity_factors or {
            "stress": 1.0,               # General stress sensitivity
            "chemical": 1.0,             # Chemical exposure sensitivity
            "environmental": 1.0,        # Environmental conditions sensitivity
            "cardio_stress": 1.0,        # Heart-specific stress sensitivity
            "respiratory_stress": 1.0,   # Respiratory-specific stress sensitivity
            "dermal_stress": 1.0,        # Skin-specific stress sensitivity
            "exercise": 1.0              # Exercise response sensitivity
        }
        
        # History of coordinated biometric readings
        self.history: List[Tuple[float, Dict[str, Dict]]] = []
        self.max_history_size = 1000
    
    def generate_signals(self, 
                        time_point: float, 
                        exposures: Optional[Dict[str, float]] = None, 
                        environmental_conditions: Optional[Dict[str, float]] = None,
                        exercise_level: float = 0.0,
                        stress_level: float = 0.0,
                        distress_level: Optional[float] = None) -> Dict[str, Dict]:
        """Generate all biometric signals for a given time point.
        
        Args:
            time_point: The time point to generate signals for
            exposures: Optional dictionary of chemical exposures and their concentrations
            environmental_conditions: Optional dictionary of environmental conditions
            exercise_level: Optional exercise intensity (0.0 to 1.0)
            stress_level: Optional general stress level (0.0 to 1.0)
            distress_level: Optional respiratory distress level (0.0 to 1.0)
            
        Returns:
            Dictionary containing all biometric signals
        """
        exposures = exposures or {}
        environmental_conditions = environmental_conditions or {}
        
        # Apply person-specific sensitivity factors
        adjusted_exposures = {
            agent: concentration * self.sensitivity_factors.get("chemical", 1.0)
            for agent, concentration in exposures.items()
        }
        
        adjusted_env_conditions = {
            condition: value * self.sensitivity_factors.get("environmental", 1.0)
            for condition, value in environmental_conditions.items()
        }
        
        adjusted_exercise = exercise_level * self.sensitivity_factors.get("exercise", 1.0)
        adjusted_stress = stress_level * self.sensitivity_factors.get("stress", 1.0)
        
        # Generate respiratory signal first as it may influence other signals
        respiratory_stress = adjusted_stress * self.sensitivity_factors.get("respiratory_stress", 1.0)
        respiratory_values = self.respiratory.generate_signal(
            time_point, 
            exposures=adjusted_exposures,
            environmental_conditions=adjusted_env_conditions,
            exercise_level=adjusted_exercise,
            distress_level=distress_level
        )
        
        # Extract respiratory info that may affect other systems
        respiratory_distress = respiratory_values["distress"]
        respiratory_rate = respiratory_values["rate"]
        respiratory_pattern = respiratory_values["pattern"]
        
        # Determine derived cardiovascular stress based on respiratory response
        # Respiratory distress typically elevates heart rate
        cardio_stress_from_resp = 0.0
        if respiratory_pattern == "labored":
            cardio_stress_from_resp = 0.7
        elif respiratory_pattern == "rapid-shallow":
            cardio_stress_from_resp = 0.5
        elif respiratory_pattern == "rapid":
            cardio_stress_from_resp = 0.3
        
        # Generate heart rate signal
        cardio_stress = max(
            adjusted_stress * self.sensitivity_factors.get("cardio_stress", 1.0),
            cardio_stress_from_resp,
            respiratory_distress * 0.8  # Respiratory distress drives heart rate
        )
        heart_rate_values = self.heart_rate.generate_signal(
            time_point,
            exposures=adjusted_exposures,
            environmental_conditions=adjusted_env_conditions,
            exercise_level=adjusted_exercise,
            stress_level=cardio_stress
        )
        
        # Determine skin conductance stress level
        # Both heart rate and respiratory responses contribute to skin conductance
        heart_rate_normalized = (heart_rate_values["heart_rate"] - self.heart_rate.baseline_heart_rate) / 50.0
        heart_rate_stress = max(0.0, min(1.0, heart_rate_normalized))
        
        dermal_stress = max(
            adjusted_stress * self.sensitivity_factors.get("dermal_stress", 1.0),
            heart_rate_stress * 0.7,
            respiratory_distress * 0.6
        )
        
        # Generate skin conductance signal
        skin_conductance_values = self.skin_conductance.generate_signal(
            time_point,
            exposures=adjusted_exposures,
            environmental_conditions=adjusted_env_conditions,
            stress_level=dermal_stress
        )
        
        # Combine all results
        result = {
            "heart_rate": heart_rate_values,
            "skin_conductance": skin_conductance_values,
            "respiratory": respiratory_values
        }
        
        # Add to history
        self.add_to_history(time_point, result)
        
        return result
    
    def add_to_history(self, time_point: float, values: Dict[str, Dict]) -> None:
        """Add a data point to the profile history.
        
        Args:
            time_point: Time point for the data
            values: Dictionary of biometric values
        """
        self.history.append((time_point, values))
        
        # Keep history size manageable
        if len(self.history) > self.max_history_size:
            self.history = self.history[-self.max_history_size:]
    
    def reset(self) -> None:
        """Reset all biometric models to initial state."""
        self.heart_rate.reset()
        self.skin_conductance.reset()
        self.respiratory.reset()
        self.history = []
    
    def calculate_stress_index(self) -> float:
        """Calculate an overall physiological stress index based on current biometric values.
        
        Returns:
            Stress index from 0.0 (no stress) to 1.0 (extreme stress)
        """
        if not self.history:
            return 0.0
        
        # Get most recent values
        _, latest_values = self.history[-1]
        
        # Extract key metrics
        hr = latest_values["heart_rate"]["heart_rate"]
        hr_baseline = self.heart_rate.baseline_heart_rate
        hr_max = self.heart_rate.max_heart_rate
        
        sc = latest_values["skin_conductance"]
        sc_baseline = self.skin_conductance.baseline_conductance
        
        resp_rate = latest_values["respiratory"]["rate"]
        resp_baseline = self.respiratory.baseline_rate
        resp_distress = latest_values["respiratory"]["distress"]
        
        # Normalize each component (0.0 to 1.0 scale)
        hr_component = min(1.0, max(0.0, (hr - hr_baseline) / (hr_max - hr_baseline)))
        sc_component = min(1.0, max(0.0, (sc - sc_baseline) / (self.skin_conductance.max_conductance - sc_baseline)))
        resp_component = min(1.0, max(0.0, (resp_rate - resp_baseline) / (self.respiratory.max_rate - resp_baseline)))
        
        # Weighted combination with respiratory distress having direct influence
        stress_index = (
            (hr_component * 0.4) + 
            (sc_component * 0.3) + 
            (resp_component * 0.2) + 
            (resp_distress * 0.1)
        )
        
        return min(1.0, max(0.0, stress_index))
    
    def calculate_energy_expenditure(self) -> float:
        """Calculate approximate energy expenditure in METs (Metabolic Equivalent of Task).
        
        Returns:
            Energy expenditure in METs (1.0 = resting)
        """
        if not self.history:
            return 1.0  # Resting MET
        
        # Get most recent values
        _, latest_values = self.history[-1]
        
        # Extract key metrics
        hr = latest_values["heart_rate"]["heart_rate"]
        hr_baseline = self.heart_rate.baseline_heart_rate
        hr_reserve = self.heart_rate.max_heart_rate - hr_baseline
        
        resp_minute_volume = latest_values["respiratory"]["minute_volume"]
        resp_baseline_minute_volume = self.respiratory.baseline_rate * self.respiratory.baseline_volume
        
        # Calculate approximate MET based on heart rate (heart rate reserve method)
        hr_percent_reserve = min(1.0, max(0.0, (hr - hr_baseline) / hr_reserve))
        hr_mets = 1.0 + (hr_percent_reserve * 11.0)  # Max around 12 METs
        
        # Calculate approximate MET based on minute ventilation
        vent_ratio = min(10.0, max(1.0, resp_minute_volume / resp_baseline_minute_volume))
        vent_mets = 1.0 + (vent_ratio - 1.0) * 1.5  # Scaled factor
        
        # Combine estimates
        combined_mets = (hr_mets * 0.7) + (vent_mets * 0.3)
        
        return combined_mets
    
    def detect_biometric_pattern(self) -> Dict[str, Any]:
        """Detect notable patterns in biometric signals.
        
        Returns:
            Dictionary of detected patterns and their confidence levels
        """
        # Requires at least some history
        if len(self.history) < 5:
            return {"insufficient_data": True}
        
        results = {
            "physical_exertion": False,
            "acute_stress": False,
            "chemical_exposure": False,
            "respiratory_distress": False,
            "recovery_phase": False,
            "confidence": 0.0,
            "primary_factor": None
        }
        
        # Get recent history
        recent_history = self.history[-min(len(self.history), 30):]
        time_points = [t for t, _ in recent_history]
        hr_values = [v["heart_rate"]["heart_rate"] for _, v in recent_history]
        sc_values = [v["skin_conductance"] for _, v in recent_history]
        resp_rate = [v["respiratory"]["rate"] for _, v in recent_history]
        resp_volume = [v["respiratory"]["volume"] for _, v in recent_history]
        resp_pattern = [v["respiratory"]["pattern"] for _, v in recent_history]
        
        # Calculate trends and variability
        hr_trend = hr_values[-1] - hr_values[0] if len(hr_values) > 1 else 0
        hr_variability = np.std(hr_values) if len(hr_values) > 1 else 0
        sc_trend = sc_values[-1] - sc_values[0] if len(sc_values) > 1 else 0
        resp_trend = resp_rate[-1] - resp_rate[0] if len(resp_rate) > 1 else 0
        
        # Pattern: Physical Exertion
        # Characterized by elevated HR, increased respiratory rate and volume, moderate SC
        exertion_score = 0.0
        if hr_values[-1] > self.heart_rate.baseline_heart_rate * 1.3:
            exertion_score += 0.4
        if resp_rate[-1] > self.respiratory.baseline_rate * 1.4:
            exertion_score += 0.3
        if resp_volume[-1] > self.respiratory.baseline_volume * 1.3:
            exertion_score += 0.3
            
        results["physical_exertion"] = exertion_score > 0.6
        
        # Pattern: Acute Stress
        # Characterized by elevated HR, high SC, increased respiratory rate but normal/reduced volume
        stress_score = 0.0
        if hr_values[-1] > self.heart_rate.baseline_heart_rate * 1.2:
            stress_score += 0.3
        if sc_values[-1] > self.skin_conductance.baseline_conductance * 1.5:
            stress_score += 0.4
        if resp_rate[-1] > self.respiratory.baseline_rate * 1.2 and resp_volume[-1] <= self.respiratory.baseline_volume:
            stress_score += 0.3
            
        results["acute_stress"] = stress_score > 0.6
        
        # Pattern: Chemical Exposure
        # Might vary by chemical, but often shows respiratory changes first
        chem_score = 0.0
        if "rapid-shallow" in resp_pattern or "labored" in resp_pattern:
            chem_score += 0.5
        if hr_variability > self.heart_rate.baseline_heart_rate * 0.15:
            chem_score += 0.3
        if sc_trend > 0:
            chem_score += 0.2
            
        results["chemical_exposure"] = chem_score > 0.6
        
        # Pattern: Respiratory Distress
        # Primary respiratory indicators with secondary cardiovascular effects
        distress_score = 0.0
        if "labored" in resp_pattern:
            distress_score += 0.6
        if "rapid-shallow" in resp_pattern:
            distress_score += 0.4
        if hr_trend > 0:
            distress_score += 0.2
            
        results["respiratory_distress"] = distress_score > 0.5
        
        # Pattern: Recovery Phase
        # Gradual return to baseline after elevated values
        recovery_score = 0.0
        if len(hr_values) > 5 and hr_trend < 0 and hr_values[-1] > self.heart_rate.baseline_heart_rate:
            recovery_score += 0.4
        if len(resp_rate) > 5 and resp_trend < 0 and resp_rate[-1] > self.respiratory.baseline_rate:
            recovery_score += 0.4
        if len(sc_values) > 5 and sc_trend < 0 and sc_values[-1] > self.skin_conductance.baseline_conductance:
            recovery_score += 0.2
            
        results["recovery_phase"] = recovery_score > 0.5
        
        # Determine primary factor and confidence
        scores = {
            "physical_exertion": exertion_score,
            "acute_stress": stress_score,
            "chemical_exposure": chem_score,
            "respiratory_distress": distress_score,
            "recovery_phase": recovery_score
        }
        
        primary_factor = max(scores.items(), key=lambda x: x[1])
        results["primary_factor"] = primary_factor[0]
        results["confidence"] = primary_factor[1]
        
        return results
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the biometric profile to a dictionary.
        
        Returns:
            Dictionary representation of the profile
        """
        return {
            "name": self.name,
            "description": self.description,
            "uuid": self.uuid,
            "sensitivity_factors": self.sensitivity_factors,
            "heart_rate": self.heart_rate.to_dict(),
            "skin_conductance": self.skin_conductance.to_dict(),
            "respiratory": self.respiratory.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BiometricProfile':
        """Create a biometric profile from a dictionary.
        
        Args:
            data: Dictionary containing profile data
            
        Returns:
            An instance of BiometricProfile
        """
        # Create component models
        heart_rate = HeartRateModel.from_dict(data.get("heart_rate", {}))
        skin_conductance = SkinConductanceModel.from_dict(data.get("skin_conductance", {}))
        respiratory = RespiratoryModel.from_dict(data.get("respiratory", {}))
        
        # Create the profile
        profile = cls(
            name=data.get("name", "Default Profile"),
            description=data.get("description", "Default biometric profile"),
            heart_rate=heart_rate,
            skin_conductance=skin_conductance,
            respiratory=respiratory,
            sensitivity_factors=data.get("sensitivity_factors", {})
        )
        
        # Restore UUID if provided
        if "uuid" in data:
            profile.uuid = data["uuid"]
            
        return profile
    
    def to_json(self) -> str:
        """Convert the biometric profile to a JSON string.
        
        Returns:
            JSON string representation of the profile
        """
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'BiometricProfile':
        """Create a biometric profile from a JSON string.
        
        Args:
            json_str: JSON string containing profile data
            
        Returns:
            An instance of BiometricProfile
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def create_demographic_variant(self, 
                                  age: int = 35, 
                                  fitness_level: float = 0.5,
                                  stress_sensitivity: float = 1.0,
                                  chemical_sensitivity: float = 1.0,
                                  name: Optional[str] = None) -> 'BiometricProfile':
        """Create a demographic variant of this profile.
        
        Args:
            age: Age in years
            fitness_level: Fitness level from 0.0 (very unfit) to 1.0 (elite athlete)
            stress_sensitivity: Sensitivity to stress (multiplier)
            chemical_sensitivity: Sensitivity to chemical exposures (multiplier)
            name: Optional name for the new profile
            
        Returns:
            A new BiometricProfile instance with adjusted parameters
        """
        # Age affects heart rate
        if age < 30:
            max_hr = 220 - age  # Typical formula
            resting_hr = 70 - fitness_level * 15
        elif age < 50:
            max_hr = 220 - age
            resting_hr = 72 - fitness_level * 12
        else:
            max_hr = 208 - (0.7 * age)  # Better formula for older adults
            resting_hr = 75 - fitness_level * 10
        
        # Fitness affects recovery rate and respiratory parameters
        recovery_rate = 0.08 + (fitness_level * 0.07)
        respiratory_baseline = 16.0 - (fitness_level * 4.0)  # More fit people breathe slower at rest
        respiratory_volume = 0.5 + (fitness_level * 0.2)     # More fit people have higher tidal volume
        
        # Create adjusted heart rate model
        heart_rate = HeartRateModel(
            baseline_heart_rate=resting_hr,
            max_heart_rate=max_hr,
            recovery_rate=recovery_rate
        )
        
        # Create adjusted respiratory model
        respiratory = RespiratoryModel(
            baseline_rate=respiratory_baseline,
            baseline_volume=respiratory_volume,
            recovery_rate=recovery_rate,
            chemical_sensitivity=chemical_sensitivity
        )
        
        # Create adjusted skin conductance model
        skin_conductance = SkinConductanceModel(
            stress_sensitivity=stress_sensitivity,
            recovery_rate=recovery_rate
        )
        
        # Create sensitivity factors
        sensitivity_factors = {
            "stress": stress_sensitivity,
            "chemical": chemical_sensitivity,
            "environmental": 1.0,
            "cardio_stress": stress_sensitivity,
            "respiratory_stress": stress_sensitivity,
            "dermal_stress": stress_sensitivity,
            "exercise": 1.0 / max(0.1, fitness_level)  # Less fit people have stronger exercise response
        }
        
        # Generate profile name if not provided
        if name is None:
            fitness_desc = "Highly Fit" if fitness_level > 0.8 else "Fit" if fitness_level > 0.6 else "Average" if fitness_level > 0.4 else "Sedentary"
            name = f"{fitness_desc} {age}y Profile"
        
        # Create profile with adjusted parameters
        return BiometricProfile(
            name=name,
            description=f"Demographic variant with age={age}, fitness={fitness_level:.1f}, stress sensitivity={stress_sensitivity:.1f}",
            heart_rate=heart_rate,
            respiratory=respiratory,
            skin_conductance=skin_conductance,
            sensitivity_factors=sensitivity_factors
        )
