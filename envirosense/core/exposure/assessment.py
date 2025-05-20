"""
Exposure Assessment Module

This module evaluates chemical exposures against sensitivity profiles to provide
personalized health risk assessments. It integrates exposure records with
individual sensitivity profiles to calculate personalized exposure impacts
based on physiological factors like age, pre-existing conditions, and specific sensitivities.

Key features:
- Standard exposure assessment against regulatory thresholds
- Personalized assessment integrating sensitivity profiles
- Risk level calculation and symptom prediction
- Risk trend analysis and reporting
"""

import uuid
import math
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Union, Any
from enum import Enum, auto

from envirosense.core.chemical.chemical_properties import (
    ChemicalCategory,
    CHEMICAL_PROPERTIES
)
from envirosense.core.exposure.records import (
    ExposureRecord,
    ExposureHistory
)


class RiskLevel(Enum):
    """Standardized risk levels for exposure assessments."""
    NEGLIGIBLE = auto()
    LOW = auto()
    MODERATE = auto()
    HIGH = auto()
    VERY_HIGH = auto()
    SEVERE = auto()
    UNKNOWN = auto()


class ExposureAssessment:
    """
    Base class for assessing chemical exposures against regulatory thresholds.
    
    This class provides methods for evaluating chemical exposures against standard
    health thresholds and regulatory limits, independent of individual sensitivity.
    """
    
    def __init__(self, exposure_history: ExposureHistory):
        """
        Initialize an exposure assessment.
        
        Args:
            exposure_history: The exposure history to assess
        """
        self.exposure_history = exposure_history
        self.assessment_id = str(uuid.uuid4())
        self.created_at = datetime.now().isoformat()
    
    def assess_chemical(self, chemical_id: str) -> Dict[str, Any]:
        """
        Assess exposure to a specific chemical against standard thresholds.
        
        Args:
            chemical_id: The chemical to assess
            
        Returns:
            Dictionary with assessment results
        """
        # Check if chemical exists in database
        if chemical_id not in CHEMICAL_PROPERTIES:
            return {
                "chemical_id": chemical_id,
                "status": "unknown_chemical",
                "risk_level": RiskLevel.UNKNOWN.name,
                "message": f"Unknown chemical: {chemical_id}"
            }
        
        # Get chemical properties
        chemical_info = CHEMICAL_PROPERTIES[chemical_id]
        chemical_name = chemical_info.get("name", chemical_id)
        health_data = chemical_info.get("health_data", {})
        
        if not health_data:
            return {
                "chemical_id": chemical_id,
                "chemical_name": chemical_name,
                "status": "no_health_data",
                "risk_level": RiskLevel.UNKNOWN.name,
                "message": f"No health threshold data available for {chemical_name}"
            }
        
        # Get exposure metrics
        metrics = self.exposure_history.calculate_exposure_metrics(chemical_id)
        thresholds = self.exposure_history.evaluate_health_thresholds(chemical_id)
        
        # Determine the overall risk level based on thresholds
        risk_level = self._determine_risk_level(chemical_id, metrics, thresholds)
        
        # Build detailed assessment
        assessment = {
            "chemical_id": chemical_id,
            "chemical_name": chemical_name,
            "status": "assessed",
            "metrics": metrics,
            "threshold_evaluations": thresholds,
            "risk_level": risk_level.name,
            "assessment_time": datetime.now().isoformat()
        }
        
        # Add health guidance based on risk level
        assessment["guidance"] = self._get_health_guidance(chemical_id, risk_level)
        
        return assessment
    
    def assess_all_chemicals(self) -> Dict[str, Dict[str, Any]]:
        """
        Assess exposure to all chemicals in the exposure history.
        
        Returns:
            Dictionary mapping chemical_id to assessment results
        """
        # Get unique chemicals in the history
        summary = self.exposure_history.get_summary()
        chemicals = summary.get("chemicals", [])
        
        results = {}
        for chemical_id in chemicals:
            if chemical_id:  # Skip None or empty strings
                results[chemical_id] = self.assess_chemical(chemical_id)
        
        return results
    
    def _determine_risk_level(
        self, 
        chemical_id: str,
        metrics: Dict[str, float],
        threshold_evaluations: Dict[str, bool]
    ) -> RiskLevel:
        """
        Determine the risk level based on exposure metrics and threshold evaluations.
        
        Args:
            chemical_id: The chemical being evaluated
            metrics: Dictionary of exposure metrics
            threshold_evaluations: Dictionary of threshold exceeded flags
            
        Returns:
            Appropriate RiskLevel enum value
        """
        # If no health data is available
        if not CHEMICAL_PROPERTIES.get(chemical_id, {}).get("health_data", {}):
            return RiskLevel.UNKNOWN
        
        health_data = CHEMICAL_PROPERTIES[chemical_id]["health_data"]
        
        # Check if any thresholds are exceeded
        if not threshold_evaluations:
            # No thresholds to check against
            return RiskLevel.UNKNOWN
            
        # Check ceiling limits first (most acute)
        if threshold_evaluations.get("exceeds_NIOSH_CEILING", False):
            return RiskLevel.SEVERE
            
        # Check STELs next (short-term limits)
        if (threshold_evaluations.get("exceeds_OSHA_STEL", False) or 
            threshold_evaluations.get("exceeds_NIOSH_STEL", False)):
            return RiskLevel.VERY_HIGH
            
        # Check TWA limits
        twa_exceeded = (threshold_evaluations.get("exceeds_OSHA_PEL", False) or
                       threshold_evaluations.get("exceeds_NIOSH_REL", False) or
                       threshold_evaluations.get("exceeds_ACGIH_TLV", False))
                       
        if twa_exceeded:
            # Calculate how much the limit is exceeded
            # First, determine which limit to use (in order of priority)
            limit = None
            if "NIOSH_REL" in health_data and health_data["NIOSH_REL"] is not None:
                limit = health_data["NIOSH_REL"]
            elif "ACGIH_TLV" in health_data and health_data["ACGIH_TLV"] is not None:
                limit = health_data["ACGIH_TLV"]
            elif "OSHA_PEL" in health_data and health_data["OSHA_PEL"] is not None:
                limit = health_data["OSHA_PEL"]
                
            if limit and metrics["8hr_twa"] > limit:
                exceedance_factor = metrics["8hr_twa"] / limit
                
                if exceedance_factor > 5.0:
                    return RiskLevel.SEVERE
                elif exceedance_factor > 2.0:
                    return RiskLevel.VERY_HIGH
                else:
                    return RiskLevel.HIGH
        
        # If no regulatory limits are exceeded, further evaluate based on percentages
        if "NIOSH_REL" in health_data and health_data["NIOSH_REL"] is not None:
            rel_percentage = (metrics["8hr_twa"] / health_data["NIOSH_REL"]) * 100
            if rel_percentage > 75:
                return RiskLevel.MODERATE
            elif rel_percentage > 50:
                return RiskLevel.LOW
                
        # Check for odor threshold
        if "odor_threshold" in health_data and health_data["odor_threshold"] is not None:
            if metrics["peak_concentration"] > health_data["odor_threshold"]:
                return RiskLevel.LOW
        
        # If we've reached here, the exposure is below all significant thresholds
        return RiskLevel.NEGLIGIBLE
    
    def _get_health_guidance(self, chemical_id: str, risk_level: RiskLevel) -> str:
        """
        Get health guidance based on chemical and risk level.
        
        Args:
            chemical_id: The chemical being evaluated
            risk_level: The determined risk level
            
        Returns:
            String containing health guidance
        """
        if chemical_id not in CHEMICAL_PROPERTIES:
            return "No guidance available for unknown chemical."
            
        chemical_name = CHEMICAL_PROPERTIES[chemical_id].get("name", chemical_id)
        
        if risk_level == RiskLevel.UNKNOWN:
            return (f"Insufficient data to assess exposure risk for {chemical_name}. "
                   f"Consider monitoring exposure levels and comparing to relevant standards.")
                   
        elif risk_level == RiskLevel.NEGLIGIBLE:
            return (f"Current exposure to {chemical_name} appears to be within acceptable limits. "
                   f"Continued monitoring is recommended as a best practice.")
                   
        elif risk_level == RiskLevel.LOW:
            return (f"Exposure to {chemical_name} is detected but remains at low levels. "
                   f"Continue standard monitoring. Consider source identification for sensitive individuals.")
                   
        elif risk_level == RiskLevel.MODERATE:
            return (f"Moderate exposure to {chemical_name} detected. Exposure approaching regulatory limits. "
                   f"Consider improved ventilation or source control measures. "
                   f"Individuals with respiratory conditions may experience irritation.")
                   
        elif risk_level == RiskLevel.HIGH:
            return (f"High levels of {chemical_name} detected, exceeding recommended limits. "
                   f"Reduce exposure through ventilation, source removal, or use of protective equipment. "
                   f"Consider temporary relocation of sensitive individuals.")
                   
        elif risk_level == RiskLevel.VERY_HIGH:
            return (f"Very high levels of {chemical_name} detected, significantly above safe limits. "
                   f"Immediate action recommended to reduce exposure. Consider evacuation "
                   f"of the area until levels decrease. Consult with health professionals.")
                   
        elif risk_level == RiskLevel.SEVERE:
            return (f"SEVERE: {chemical_name} at potentially hazardous levels. "
                   f"Immediate evacuation recommended. Ventilate area thoroughly before "
                   f"re-entry. Seek medical attention if symptoms develop. "
                   f"Emergency services should be notified for severe exposure events.")
        
        # Default case
        return f"Assess exposure to {chemical_name} and take appropriate precautions."


class PersonalizedExposureAssessment(ExposureAssessment):
    """
    Class for personalized exposure assessment based on sensitivity profiles.
    
    This class extends the standard exposure assessment by incorporating 
    individual sensitivity profiles to provide personalized risk evaluations.
    """
    
    def __init__(
        self,
        exposure_history: ExposureHistory,
        sensitivity_profile: Dict[str, Any]
    ):
        """
        Initialize a personalized exposure assessment.
        
        Args:
            exposure_history: The exposure history to assess
            sensitivity_profile: The sensitivity profile to use for personalization
        """
        super().__init__(exposure_history)
        self.sensitivity_profile = sensitivity_profile
        self.profile_id = sensitivity_profile.get("profile_id")
        
    def get_sensitivity_factor(self, chemical_id: str, sensitivity_type: str = None) -> float:
        """
        Calculate a sensitivity factor for a specific chemical and sensitivity type.
        
        Args:
            chemical_id: The chemical to calculate sensitivity for
            sensitivity_type: Optional specific sensitivity type to use
                (if None, the most relevant type will be determined)
                
        Returns:
            Sensitivity factor (1.0 = baseline/average, >1.0 = more sensitive)
        """
        if chemical_id not in CHEMICAL_PROPERTIES:
            return 1.0  # Default to baseline if chemical unknown
            
        # Determine the primary sensitivity type for this chemical
        if sensitivity_type is None:
            chem_properties = CHEMICAL_PROPERTIES[chemical_id]
            
            # Check affected parameters in each sensitivity type
            for sens_type, type_info in SENSITIVITY_TYPES.items():
                affected_params = type_info.get("affected_parameters", [])
                if chemical_id in affected_params:
                    sensitivity_type = sens_type
                    break
            
            # If still not determined, use a default
            if sensitivity_type is None:
                # Fallback mappings based on chemical category
                category = chem_properties.get("category")
                if category == ChemicalCategory.VOC or category == ChemicalCategory.INORGANIC_GAS:
                    sensitivity_type = "respiratory"
                elif category == ChemicalCategory.PARTICULATE:
                    sensitivity_type = "respiratory"
                else:
                    # Default to respiratory as most common for air contaminants
                    sensitivity_type = "respiratory"
        
        # Get the baseline sensitivity score for this type
        sensitivity_score = self.sensitivity_profile.get("sensitivity_scores", {}).get(sensitivity_type, 1.0)
        
        # Apply any chemical-specific modifiers from the profile
        chemical_modifier = self.sensitivity_profile.get("parameter_modifiers", {}).get(chemical_id, 1.0)
        
        # Apply demographic factors if available
        demographic_factor = 1.0
        age_group = self.sensitivity_profile.get("demographics", {}).get("age_group")
        
        if age_group and sensitivity_type:
            # Get age modifiers for this sensitivity type if available
            age_modifiers = AGE_SENSITIVITY_MODIFIERS.get(sensitivity_type, {})
            if age_group in age_modifiers:
                demographic_factor = age_modifiers[age_group]
        
        # Apply condition modifiers
        condition_factor = 1.0
        conditions = self.sensitivity_profile.get("conditions", [])
        
        for condition in conditions:
            if condition in CONDITION_SENSITIVITY_MODIFIERS:
                # Get condition modifier for this sensitivity type if available
                condition_modifier = CONDITION_SENSITIVITY_MODIFIERS[condition].get(sensitivity_type, 1.0)
                condition_factor = max(condition_factor, condition_modifier)
        
        # Combine all factors
        final_sensitivity = sensitivity_score * chemical_modifier * demographic_factor * condition_factor
        
        # Cap at maximum sensitivity (prevents unrealistic values)
        return min(2.5, final_sensitivity)
    
    def assess_chemical(self, chemical_id: str) -> Dict[str, Any]:
        """
        Assess exposure to a specific chemical with personalized sensitivity.
        
        Args:
            chemical_id: The chemical to assess
            
        Returns:
            Dictionary with assessment results including personalized factors
        """
        # Get standard assessment first
        standard_assessment = super().assess_chemical(chemical_id)
        
        if standard_assessment.get("status") not in ["assessed"]:
            # If standard assessment couldn't be completed, return as is
            standard_assessment["personalized"] = False
            return standard_assessment
        
        # Get personalization factors
        sensitivity_factor = self.get_sensitivity_factor(chemical_id)
        
        # Create personalized assessment
        personalized = dict(standard_assessment)
        personalized["personalized"] = True
        personalized["sensitivity_factor"] = sensitivity_factor
        
        # Adjust metrics based on sensitivity
        adjusted_metrics = {}
        for metric_name, metric_value in standard_assessment.get("metrics", {}).items():
            adjusted_metrics[metric_name] = metric_value
            adjusted_metrics[f"adjusted_{metric_name}"] = metric_value * sensitivity_factor
        
        personalized["metrics"] = adjusted_metrics
        
        # Re-evaluate thresholds using adjusted metrics
        adjusted_thresholds = {}
        
        if chemical_id in CHEMICAL_PROPERTIES:
            health_data = CHEMICAL_PROPERTIES[chemical_id].get("health_data", {})
            
            # Adjust for personalized TWA limits
            if "NIOSH_REL" in health_data and health_data["NIOSH_REL"] is not None:
                adjusted_thresholds["exceeds_adjusted_NIOSH_REL"] = (
                    adjusted_metrics["adjusted_8hr_twa"] > health_data["NIOSH_REL"]
                )
                
            if "OSHA_PEL" in health_data and health_data["OSHA_PEL"] is not None:
                adjusted_thresholds["exceeds_adjusted_OSHA_PEL"] = (
                    adjusted_metrics["adjusted_8hr_twa"] > health_data["OSHA_PEL"]
                )
                
            if "ACGIH_TLV" in health_data and health_data["ACGIH_TLV"] is not None:
                adjusted_thresholds["exceeds_adjusted_ACGIH_TLV"] = (
                    adjusted_metrics["adjusted_8hr_twa"] > health_data["ACGIH_TLV"]
                )
            
            # Adjust for personalized STEL limits
            if "OSHA_STEL" in health_data and health_data["OSHA_STEL"] is not None:
                adjusted_thresholds["exceeds_adjusted_OSHA_STEL"] = (
                    adjusted_metrics["adjusted_peak_15min"] > health_data["OSHA_STEL"]
                )
                
            if "NIOSH_STEL" in health_data and health_data["NIOSH_STEL"] is not None:
                adjusted_thresholds["exceeds_adjusted_NIOSH_STEL"] = (
                    adjusted_metrics["adjusted_peak_15min"] > health_data["NIOSH_STEL"]
                )
            
            # Adjust for personalized ceiling values
            if "NIOSH_CEILING" in health_data and health_data["NIOSH_CEILING"] is not None:
                adjusted_thresholds["exceeds_adjusted_NIOSH_CEILING"] = (
                    adjusted_metrics["adjusted_peak_concentration"] > health_data["NIOSH_CEILING"]
                )
        
        personalized["adjusted_threshold_evaluations"] = adjusted_thresholds
        
        # Determine personalized risk level
        personalized_risk_level = self._determine_personalized_risk_level(
            chemical_id, adjusted_metrics, adjusted_thresholds, sensitivity_factor
        )
        
        # Update risk level and guidance
        personalized["standard_risk_level"] = standard_assessment["risk_level"]
        personalized["risk_level"] = personalized_risk_level.name
        personalized["standard_guidance"] = standard_assessment.get("guidance", "")
        personalized["guidance"] = self._get_personalized_guidance(
            chemical_id, personalized_risk_level, sensitivity_factor
        )
        
        # Add predicted symptoms
        personalized["predicted_symptoms"] = self._predict_symptoms(
            chemical_id, personalized_risk_level, sensitivity_factor
        )
        
        return personalized
    
    def _determine_personalized_risk_level(
        self, 
        chemical_id: str,
        adjusted_metrics: Dict[str, float],
        adjusted_thresholds: Dict[str, bool],
        sensitivity_factor: float
    ) -> RiskLevel:
        """
        Determine personalized risk level based on sensitivity-adjusted metrics.
        
        Args:
            chemical_id: The chemical being evaluated
            adjusted_metrics: Dictionary of sensitivity-adjusted exposure metrics
            adjusted_thresholds: Dictionary of adjusted threshold evaluations
            sensitivity_factor: The calculated sensitivity factor
            
        Returns:
            Personalized RiskLevel enum value
        """
        # If no health data is available
        if not CHEMICAL_PROPERTIES.get(chemical_id, {}).get("health_data", {}):
            return RiskLevel.UNKNOWN
        
        # Start with standard risk level determination logic
        if not adjusted_thresholds:
            base_risk = RiskLevel.UNKNOWN
        elif adjusted_thresholds.get("exceeds_adjusted_NIOSH_CEILING", False):
            base_risk = RiskLevel.SEVERE
        elif (adjusted_thresholds.get("exceeds_adjusted_OSHA_STEL", False) or 
              adjusted_thresholds.get("exceeds_adjusted_NIOSH_STEL", False)):
            base_risk = RiskLevel.VERY_HIGH
        elif (adjusted_thresholds.get("exceeds_adjusted_OSHA_PEL", False) or
              adjusted_thresholds.get("exceeds_adjusted_NIOSH_REL", False) or
              adjusted_thresholds.get("exceeds_adjusted_ACGIH_TLV", False)):
            base_risk = RiskLevel.HIGH
        else:
            # No adjusted thresholds exceeded, evaluate based on sensitivity factor
            health_data = CHEMICAL_PROPERTIES[chemical_id]["health_data"]
            limit = None
            
            # Find the most appropriate limit to use
            if "NIOSH_REL" in health_data and health_data["NIOSH_REL"] is not None:
                limit = health_data["NIOSH_REL"]
            elif "ACGIH_TLV" in health_data and health_data["ACGIH_TLV"] is not None:
                limit = health_data["ACGIH_TLV"]
            elif "OSHA_PEL" in health_data and health_data["OSHA_PEL"] is not None:
                limit = health_data["OSHA_PEL"]
                
            if limit:
                adjusted_twa = adjusted_metrics.get("adjusted_8hr_twa", 0)
                rel_percentage = (adjusted_twa / limit) * 100
                
                if rel_percentage > 90:
                    base_risk = RiskLevel.HIGH
                elif rel_percentage > 75:
                    base_risk = RiskLevel.MODERATE
                elif rel_percentage > 50:
                    base_risk = RiskLevel.LOW
                else:
                    base_risk = RiskLevel.NEGLIGIBLE
            else:
                base_risk = RiskLevel.NEGLIGIBLE
        
        # Apply sensitivity factor to potentially escalate the risk level
        risk_levels = list(RiskLevel)
        risk_levels.remove(RiskLevel.UNKNOWN)  # Don't include UNKNOWN in the escalation
        base_index = risk_levels.index(base_risk) if base_risk in risk_levels else 0
        
        # Calculate how many levels to escalate based on sensitivity
        # Sensitivity factor > 1.5 adds one level, > 2.0 adds two levels
        escalation = 0
        if sensitivity_factor >= 2.0:
            escalation = 2
        elif sensitivity_factor >= 1.5:
            escalation = 1
            
        # Apply escalation, capped at max risk level
        final_index = min(len(risk_levels) - 1, base_index + escalation)
        final_risk = risk_levels[final_index]
        
        return final_risk
    
    def _get_personalized_guidance(
        self,
        chemical_id: str,
        risk_level: RiskLevel,
        sensitivity_factor: float
    ) -> str:
        """
        Get personalized health guidance based on sensitivity profile.
        
        Args:
            chemical_id: The chemical being evaluated
            risk_level: The personalized risk level
            sensitivity_factor: The calculated sensitivity factor
            
        Returns:
            Personalized guidance string
        """
        if chemical_id not in CHEMICAL_PROPERTIES:
            return "No guidance available for unknown chemical."
            
        chemical_name = CHEMICAL_PROPERTIES[chemical_id].get("name", chemical_id)
        
        # Get basic guidance first
        guidance = super()._get_health_guidance(chemical_id, risk_level)
        
        # Add personalized components
        personalizations = []
        
        # Add sensitivity context
        if sensitivity_factor > 1.8:
            personalizations.append(
                f"You show significantly higher sensitivity to {chemical_name} based on your profile. "
                f"Consider taking more conservative precautions than typically recommended."
            )
        elif sensitivity_factor > 1.4:
            personalizations.append(
                f"Your sensitivity profile indicates moderately elevated sensitivity to {chemical_name}. "
                f"You may experience effects at lower concentrations than the general population."
            )
        elif sensitivity_factor > 1.1:
            personalizations.append(
                f"Your sensitivity profile shows slightly elevated sensitivity to {chemical_name}."
            )
        
        # Add condition-specific advice
        conditions = self.sensitivity_profile.get("conditions", [])
        for condition in conditions:
            if condition == "asthma" and (risk_level in [RiskLevel.MODERATE, RiskLevel.HIGH, RiskLevel.VERY_HIGH, RiskLevel.SEVERE]):
                personalizations.append(
                    f"Due to your asthma, consider keeping rescue medication accessible when exposed to {chemical_name}. "
                    f"Watch for early signs of asthma exacerbation."
                )
            elif condition == "copd" and (risk_level in [RiskLevel.MODERATE, RiskLevel.HIGH, RiskLevel.VERY_HIGH, RiskLevel.SEVERE]):
                personalizations.append(
                    f"With COPD, you may experience increased respiratory symptoms from {chemical_name} exposure. "
                    f"Consider wearing a protective mask or relocating if levels remain elevated."
                )
            elif condition == "allergic_rhinitis" and (risk_level in [RiskLevel.LOW, RiskLevel.MODERATE, RiskLevel.HIGH]):
                personalizations.append(
                    f"Your allergic rhinitis may be triggered by {chemical_name}. "
                    f"Consider using air purifiers and keeping antihistamines available."
                )
        
        # Add age-specific advice
        age_group = self.sensitivity_profile.get("demographics", {}).get("age_group")
        if age_group == "child" and risk_level not in [RiskLevel.NEGLIGIBLE, RiskLevel.UNKNOWN]:
            personalizations.append(
                f"Children may be more susceptible to {chemical_name}. Consider increased ventilation "
                f"or temporary relocation if exposure continues."
            )
        elif age_group == "elderly" and risk_level not in [RiskLevel.NEGLIGIBLE, RiskLevel.UNKNOWN]:
            personalizations.append(
                f"Elderly individuals may experience more pronounced effects from {chemical_name}. "
                f"Monitor for symptoms closely and consider seeking medical advice if symptoms develop."
            )
        
        if personalizations:
            guidance += "\n\nPersonalized recommendations:\n- " + "\n- ".join(personalizations)
            
        return guidance
    
    def _predict_symptoms(
        self,
        chemical_id: str,
        risk_level: RiskLevel,
        sensitivity_factor: float
    ) -> Dict[str, float]:
        """
        Predict likely symptoms based on exposure and sensitivity profile.
        
        Args:
            chemical_id: The chemical being evaluated
            risk_level: The personalized risk level
            sensitivity_factor: The calculated sensitivity factor
            
        Returns:
            Dictionary mapping symptom names to probability (0-1)
        """
        if chemical_id not in CHEMICAL_PROPERTIES:
            return {}
            
        # Get chemical sensitivity type
        chem_properties = CHEMICAL_PROPERTIES[chemical_id]
        primary_sensitivity_type = None
        
        # Find the most relevant sensitivity type for this chemical
        for sens_type, type_info in SENSITIVITY_TYPES.items():
            affected_params = type_info.get("affected_parameters", [])
            if chemical_id in affected_params:
                primary_sensitivity_type = sens_type
                break
                
        if primary_sensitivity_type is None:
            # Fallback based on chemical category
            category = chem_properties.get("category")
            if category == ChemicalCategory.VOC or category == ChemicalCategory.INORGANIC_GAS:
                primary_sensitivity_type = "respiratory"
            elif category == ChemicalCategory.PARTICULATE:
                primary_sensitivity_type = "respiratory"
            else:
                return {}  # Can't determine relevant symptoms
        
        # Get symptoms for this sensitivity type
        symptoms = {}
        sensitivity_info = SENSITIVITY_TYPES.get(primary_sensitivity_type, {})
        
        # Basic probability based on risk level
        base_probability = {
            RiskLevel.NEGLIGIBLE: 0.05,
            RiskLevel.LOW: 0.2,
            RiskLevel.MODERATE: 0.4,
            RiskLevel.HIGH: 0.7,
            RiskLevel.VERY_HIGH: 0.85,
            RiskLevel.SEVERE: 0.95,
            RiskLevel.UNKNOWN: 0.0
        }.get(risk_level, 0.0)
        
        # Get typical symptoms for all subtypes of this sensitivity
        all_symptoms = []
        for subtype, subtype_info in sensitivity_info.get("subtypes", {}).items():
            all_symptoms.extend(subtype_info.get("typical_symptoms", []))
        
        # Calculate probability for each symptom
        for symptom in set(all_symptoms):
            # Base probability adjusted by sensitivity factor
            symptom_prob = base_probability * min(2.0, sensitivity_factor)
            
            # Cap probability at 0.98
            symptom_prob = min(0.98, symptom_prob)
            
            # Add to results if significant
            if symptom_prob > 0.1:
                symptoms[symptom] = round(symptom_prob, 2)
        
        return symptoms


# Define baseline physiological sensitivity profiles for major categories
# This is a simplified version of the data from sensitivity_profiles.py
SENSITIVITY_TYPES = {
    "respiratory": {
        "description": "Sensitivity of the respiratory system to airborne contaminants",
        "affected_parameters": [
            "pm2_5", "pm10", "ozone", "no2", "co2", "co", "so2", "formaldehyde", "tvoc"
        ],
        "subtypes": {
            "upper_respiratory": {
                "description": "Sensitivity of nasal passages, sinuses, and throat",
                "typical_symptoms": ["nasal_irritation", "sneezing", "congestion", "sore_throat"]
            },
            "lower_respiratory": {
                "description": "Sensitivity of bronchial tubes and lungs",
                "typical_symptoms": ["coughing", "wheezing", "shortness_of_breath", "chest_tightness"]
            }
        }
    },
    "dermal": {
        "description": "Sensitivity of the skin to contact irritants and allergens",
        "affected_parameters": [
            "tvoc", "formaldehyde", "pesticides", "solvents", "humidity", "uv_index"
        ],
        "subtypes": {
            "irritant_contact": {
                "description": "Sensitivity to irritating substances causing direct skin damage",
                "typical_symptoms": ["redness", "burning", "itching", "dryness"]
            },
            "allergic_contact": {
                "description": "Sensitivity to allergens triggering immune response",
                "typical_symptoms": ["redness", "swelling", "blistering", "intense_itching"]
            }
        }
    },
    "ocular": {
        "description": "Sensitivity of the eyes to irritants and environmental factors",
        "affected_parameters": [
            "tvoc", "formaldehyde", "ozone", "pm2_5", "pm10", "humidity", "light_level"
        ],
        "subtypes": {
            "conjunctival": {
                "description": "Sensitivity of the conjunctiva (eye surface membrane)",
                "typical_symptoms": ["redness", "itching", "burning", "watering"]
            }
        }
    },
    "neurological": {
        "description": "Sensitivity manifesting through neurological symptoms",
        "affected_parameters": [
            "co", "co2", "formaldehyde", "tvoc", "pesticides", "solvents"
        ],
        "subtypes": {
            "headache_inducing": {
                "description": "Triggers for headaches and migraines",
                "typical_symptoms": ["headache", "migraine", "pressure_sensation", "throbbing_pain"]
            },
            "cognitive": {
                "description": "Impacts on cognitive function and clarity",
                "typical_symptoms": ["difficulty_concentrating", "memory_issues", "brain_fog", "confusion"]
            }
        }
    },
    "cardiovascular": {
        "description": "Sensitivity affecting the cardiovascular system",
        "affected_parameters": [
            "co", "pm2_5", "pm10", "temperature"
        ],
        "subtypes": {
            "cardiac_rhythm": {
                "description": "Effects on heart rate and rhythm",
                "typical_symptoms": ["palpitations", "irregular_heartbeat", "racing_heart"]
            },
            "vascular_response": {
                "description": "Effects on blood vessels and circulation",
                "typical_symptoms": ["hypertension", "flushing", "chest_pressure"]
            }
        }
    }
}


# Sensitivity modifiers based on demographic factors (age groups)
# Simplified from the full sensitivity_profiles.py implementation
AGE_SENSITIVITY_MODIFIERS = {
    "respiratory": {
        "child": 1.3,             # Children have increased respiratory sensitivity
        "adolescent": 1.1,
        "young_adult": 1.0,       # Baseline
        "middle_aged": 1.1,
        "older_adult": 1.3,
        "elderly": 1.5
    },
    "dermal": {
        "child": 1.4,             # Children have more sensitive skin
        "adolescent": 1.2,
        "young_adult": 1.0,       # Baseline
        "middle_aged": 1.1,
        "older_adult": 1.3,
        "elderly": 1.5            # Elderly have thinner, more fragile skin
    },
    "ocular": {
        "child": 1.1,
        "adolescent": 1.0,
        "young_adult": 1.0,       # Baseline
        "middle_aged": 1.2,
        "older_adult": 1.4,
        "elderly": 1.6            # Dry eye increases with age
    },
    "neurological": {
        "child": 1.3,             # Developing nervous system more vulnerable
        "adolescent": 1.2,
        "young_adult": 1.0,       # Baseline
        "middle_aged": 1.1,
        "older_adult": 1.2,
        "elderly": 1.4
    },
    "cardiovascular": {
        "child": 0.8,             # Children generally have robust cardiovascular systems
        "adolescent": 0.9,
        "young_adult": 1.0,       # Baseline
        "middle_aged": 1.2,
        "older_adult": 1.5,
        "elderly": 1.8            # Elderly have highest cardiovascular sensitivity
    }
}


# Sensitivity modifiers based on pre-existing conditions
# Simplified from the full sensitivity_profiles.py implementation
CONDITION_SENSITIVITY_MODIFIERS = {
    "asthma": {
        "respiratory": 2.0,
        "ocular": 1.2
    },
    "copd": {
        "respiratory": 2.5,
        "cardiovascular": 1.3
    },
    "eczema": {
        "dermal": 2.0
    },
    "allergic_rhinitis": {
        "respiratory": 1.7,
        "ocular": 1.5
    },
    "migraine": {
        "neurological": 2.0,
        "ocular": 1.3
    },
    "hypertension": {
        "cardiovascular": 1.7,
        "neurological": 1.2
    }
}
