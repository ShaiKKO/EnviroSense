"""
Physiological sensitivity profile generators for EnviroSense testing.

This module provides data generators for realistic physiological sensitivity profiles,
representing how individuals with different characteristics respond to environmental
stimuli. These profiles model various sensitivity types (respiratory, dermal, ocular, etc.)
across different demographic parameters.
"""

import datetime
import math
import numpy as np
import json
import uuid
import os
from typing import Any, Dict, List, Optional, Tuple, Union, Set

from envirosense.testing.framework import DataGenerator, TestScenario


class SensitivityProfile:
    """
    Class representing an individual's physiological sensitivity profile.
    
    This class encapsulates all aspects of how an individual responds to environmental
    stimuli, including base sensitivities, demographic factors, pre-existing conditions,
    and response patterns. It can be used to simulate personalized responses to 
    environmental exposures.
    """
    
    def __init__(self, profile_id: Optional[str] = None):
        """
        Initialize a new sensitivity profile.
        
        Args:
            profile_id: Optional unique identifier for this profile. If None, a new UUID will be generated.
        """
        # Basic profile information
        self.profile_id = profile_id if profile_id else str(uuid.uuid4())
        self.created_at = datetime.datetime.now().isoformat()
        self.updated_at = self.created_at
        self.version = "1.0.0"
        self.metadata = {}
        
        # Demographic information
        self.demographics = {
            "age": None,
            "age_group": None,
            "sex": None,
            "height": None,
            "weight": None,
            "bmi": None,
            "ethnicity": None,
            "geographic_region": None
        }
        
        # Pre-existing conditions
        self.conditions = []
        
        # Sensitivity scores for different types (0.0-2.0 scale, 1.0 is average)
        self.sensitivity_scores = {}
        
        # Subtype modifiers (relative to the base sensitivity score)
        self.subtype_modifiers = {}
        
        # Parameter-specific sensitivity modifiers
        self.parameter_modifiers = {}
        
        # Response curves for different sensitivity types
        self.response_curves = {}
        
        # Symptom thresholds for typical symptoms
        self.symptom_thresholds = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the profile to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the profile
        """
        return {
            "profile_id": self.profile_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
            "metadata": self.metadata,
            "demographics": self.demographics,
            "conditions": self.conditions,
            "sensitivity_scores": self.sensitivity_scores,
            "subtype_modifiers": self.subtype_modifiers,
            "parameter_modifiers": self.parameter_modifiers,
            "response_curves": self.response_curves,
            "symptom_thresholds": self.symptom_thresholds
        }
    
    def from_dict(self, data: Dict[str, Any]) -> None:
        """
        Load profile data from a dictionary.
        
        Args:
            data: Dictionary containing profile data
        """
        self.profile_id = data.get("profile_id", self.profile_id)
        self.created_at = data.get("created_at", self.created_at)
        self.updated_at = data.get("updated_at", self.updated_at)
        self.version = data.get("version", self.version)
        self.metadata = data.get("metadata", {})
        self.demographics = data.get("demographics", {})
        self.conditions = data.get("conditions", [])
        self.sensitivity_scores = data.get("sensitivity_scores", {})
        self.subtype_modifiers = data.get("subtype_modifiers", {})
        self.parameter_modifiers = data.get("parameter_modifiers", {})
        self.response_curves = data.get("response_curves", {})
        self.symptom_thresholds = data.get("symptom_thresholds", {})
    
    def set_demographics(self, **kwargs) -> None:
        """
        Set demographic information for this profile.
        
        Args:
            **kwargs: Demographic key-value pairs (age, sex, height, weight, etc.)
        """
        # Update demographic fields
        for key, value in kwargs.items():
            self.demographics[key] = value
        
        # If both height and weight are provided, calculate BMI
        if "height" in kwargs and "weight" in kwargs and self.demographics["height"] > 0:
            height_m = self.demographics["height"] / 100  # Convert cm to m
            self.demographics["bmi"] = round(self.demographics["weight"] / (height_m * height_m), 1)
        
        # Determine age group if age is provided
        if "age" in kwargs and self.demographics["age"] is not None:
            age = self.demographics["age"]
            if 0 <= age <= 12:
                self.demographics["age_group"] = "child"
            elif 13 <= age <= 19:
                self.demographics["age_group"] = "adolescent"
            elif 20 <= age <= 39:
                self.demographics["age_group"] = "young_adult"
            elif 40 <= age <= 59:
                self.demographics["age_group"] = "middle_aged"
            elif 60 <= age <= 79:
                self.demographics["age_group"] = "older_adult"
            elif 80 <= age <= 120:
                self.demographics["age_group"] = "elderly"
        
        # Update the profile's updated_at timestamp
        self.updated_at = datetime.datetime.now().isoformat()
    
    def add_condition(self, condition: str) -> None:
        """
        Add a pre-existing condition to this profile.
        
        Args:
            condition: Name of the condition to add
        """
        if condition not in self.conditions:
            self.conditions.append(condition)
            
            # Update sensitivities based on condition
            if condition in CONDITION_SENSITIVITY_MODIFIERS:
                for sens_type, modifier in CONDITION_SENSITIVITY_MODIFIERS[condition].items():
                    current = self.sensitivity_scores.get(sens_type, 1.0)
                    # Apply condition modifier (capped at 2.0 maximum)
                    self.sensitivity_scores[sens_type] = min(2.0, current * modifier)
            
            # Update the profile's updated_at timestamp
            self.updated_at = datetime.datetime.now().isoformat()
    
    def set_sensitivity(self, sensitivity_type: str, score: float) -> None:
        """
        Set the sensitivity score for a specific sensitivity type.
        
        Args:
            sensitivity_type: Type of sensitivity (respiratory, dermal, etc.)
            score: Sensitivity score (0.0-2.0, with 1.0 being average)
        """
        # Ensure score is in valid range
        score = max(0.2, min(2.0, score))
        
        # Set the sensitivity score
        self.sensitivity_scores[sensitivity_type] = score
        
        # Update the profile's updated_at timestamp
        self.updated_at = datetime.datetime.now().isoformat()


class SensitivityProfileGenerator(DataGenerator):
    """
    Generator for physiological sensitivity profiles.
    
    This generator creates realistic sensitivity profiles for individuals or populations,
    accounting for demographic factors, pre-existing conditions, and natural variation
    in sensitivity to different environmental parameters.
    """
    
    def __init__(self):
        """Initialize the sensitivity profile generator with default parameters."""
        super().__init__()
        
        # Set default parameters
        self.parameters.update({
            'profile_count': 1,             # Number of profiles to generate
            'age_distribution': 'global',   # Which age distribution to use
            'include_conditions': True,     # Whether to include pre-existing conditions
            'condition_prevalence': {       # Prevalence rates for conditions
                'asthma': 0.08,             # 8% prevalence
                'allergic_rhinitis': 0.15,  # 15% prevalence
                'copd': 0.06,               # 6% prevalence
                'eczema': 0.1,              # 10% prevalence
                'migraine': 0.12,           # 12% prevalence
                'hypertension': 0.3,        # 30% prevalence
                'diabetes': 0.1,            # 10% prevalence
                'autoimmune_disorders': 0.03 # 3% prevalence
            },
            'sensitivity_variation': 0.3,   # Standard deviation for sensitivity (0-1)
            'include_metadata': True,       # Whether to include metadata in profiles
            'random_seed': None,            # Seed for reproducibility
        })
    
    def generate(self, scenario: TestScenario, **kwargs) -> Dict[str, Any]:
        """
        Generate sensitivity profiles based on scenario parameters.
        
        Args:
            scenario: Test scenario to generate data for
            **kwargs: Additional parameters
            
        Returns:
            Dictionary containing generated sensitivity profiles
        """
        # Update parameters from scenario
        for key, value in scenario.parameters.items():
            if key in self.parameters:
                self.parameters[key] = value
        
        # Override with any explicit kwargs
        for key, value in kwargs.items():
            if key in self.parameters:
                self.parameters[key] = value
        
        # Initialize random number generator if needed
        if self.parameters['random_seed'] is not None:
            self.rng = np.random.RandomState(self.parameters['random_seed'])
        else:
            self.rng = np.random.RandomState()
        
        # Generate profiles
        profiles = []
        for i in range(self.parameters['profile_count']):
            profile = self._create_profile(i)
            profiles.append(profile.to_dict())
        
        # Create response data
        result = {
            "profiles": profiles,
            "metadata": {
                "generator_parameters": self.parameters,
                "timestamp": datetime.datetime.now().isoformat(),
                "scenario_id": getattr(scenario, 'id', None)
            }
        }
        
        return result
    
    def _create_profile(self, index: int) -> SensitivityProfile:
        """
        Create a single sensitivity profile.
        
        Args:
            index: Index of the profile being created
            
        Returns:
            A SensitivityProfile instance
        """
        profile = SensitivityProfile()
        
        # Set demographics
        age = self._generate_random_age()
        sex = self.rng.choice(["male", "female"])
        
        # Generate height and weight appropriate for age/sex
        if sex == "male":
            if age < 18:
                # Growing child/adolescent
                height = 100 + (age * 4.5) + self.rng.normal(0, 5)
                weight = 15 + (age * 3) + self.rng.normal(0, 3)
            else:
                # Adult
                height = 170 + self.rng.normal(0, 7)
                weight = 70 + self.rng.normal(0, 10)
        else:  # female
            if age < 18:
                height = 100 + (age * 4.3) + self.rng.normal(0, 5)
                weight = 15 + (age * 2.7) + self.rng.normal(0, 3)
            else:
                height = 160 + self.rng.normal(0, 6)
                weight = 60 + self.rng.normal(0, 8)
        
        # Keep values in reasonable ranges
        height = max(50, min(220, height))
        weight = max(10, min(150, weight))
        
        # Set demographics
        profile.set_demographics(
            age=int(age),
            sex=sex,
            height=round(height, 1),
            weight=round(weight, 1)
        )
        
        # Add conditions based on prevalence rates
        if self.parameters['include_conditions']:
            for condition, prevalence in self.parameters['condition_prevalence'].items():
                if self.rng.random() < prevalence:
                    profile.add_condition(condition)
        
        # Set random sensitivity scores
        variation = self.parameters['sensitivity_variation']
        for sens_type in ["respiratory", "dermal", "ocular", "neurological", "cardiovascular", "immunological"]:
            # Generate base sensitivity with normal distribution around 1.0
            score = 1.0 + self.rng.normal(0, variation)
            score = max(0.2, min(2.0, score))  # Keep in reasonable range
            profile.set_sensitivity(sens_type, score)
        
        # Add metadata if requested
        if self.parameters['include_metadata']:
            profile.metadata = {
                "profile_index": index,
                "generation_parameters": dict(self.parameters),
                "generation_timestamp": datetime.datetime.now().isoformat()
            }
        
        return profile
    
    def _generate_random_age(self) -> int:
        """
        Generate a random age based on the specified age distribution.
        
        Returns:
            Age in years
        """
        dist_name = self.parameters['age_distribution']
        if dist_name not in AGE_DISTRIBUTIONS:
            dist_name = "global"  # Fallback to global distribution
        
        age_dist = AGE_DISTRIBUTIONS[dist_name]
        
        # Choose an age group based on population percentages
        groups = list(age_dist.keys())
        probs = [age_dist[g][2] for g in groups]
        chosen_group = self.rng.choice(groups, p=probs)
        
        # Get age range for this group
        min_age, max_age, _ = age_dist[chosen_group]
        
        # Choose a random age within this range
        age = min_age + self.rng.random() * (max_age - min_age)
        
        return int(age)


# Define baseline physiological sensitivity profiles for major categories
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
            },
            "combined_respiratory": {
                "description": "Sensitivity across the entire respiratory system",
                "typical_symptoms": ["coughing", "sneezing", "congestion", "shortness_of_breath"]
            }
        },
        "relevant_conditions": [
            "asthma", "copd", "allergic_rhinitis", "chronic_bronchitis", "emphysema"
        ],
        "demographic_factors": [
            "age", "smoking_history", "occupational_exposure", "genetic_factors"
        ]
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
            },
            "photosensitivity": {
                "description": "Increased sensitivity to ultraviolet light",
                "typical_symptoms": ["redness", "burning", "blistering", "rash_in_sun_exposed_areas"]
            }
        },
        "relevant_conditions": [
            "eczema", "contact_dermatitis", "psoriasis", "urticaria", "photodermatosis"
        ],
        "demographic_factors": [
            "age", "genetic_factors", "previous_sensitization", "existing_skin_conditions"
        ]
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
            },
            "corneal": {
                "description": "Sensitivity of the cornea (front surface of eye)",
                "typical_symptoms": ["pain", "light_sensitivity", "blurred_vision", "sensation_of_foreign_body"]
            },
            "general_ocular": {
                "description": "General eye sensitivity to environmental factors",
                "typical_symptoms": ["dryness", "irritation", "discomfort", "fatigue"]
            }
        },
        "relevant_conditions": [
            "dry_eye_syndrome", "allergic_conjunctivitis", "keratitis", "blepharitis"
        ],
        "demographic_factors": [
            "age", "contact_lens_use", "previous_eye_surgery", "screen_time"
        ]
    },
    "neurological": {
        "description": "Sensitivity manifesting through neurological symptoms",
        "affected_parameters": [
            "co", "co2", "formaldehyde", "tvoc", "pesticides", "solvents", "noise_level"
        ],
        "subtypes": {
            "headache_inducing": {
                "description": "Triggers for headaches and migraines",
                "typical_symptoms": ["headache", "migraine", "pressure_sensation", "throbbing_pain"]
            },
            "cognitive": {
                "description": "Impacts on cognitive function and clarity",
                "typical_symptoms": ["difficulty_concentrating", "memory_issues", "brain_fog", "confusion"]
            },
            "neurosensory": {
                "description": "Effects on sensory perception and sensitivity",
                "typical_symptoms": ["dizziness", "tingling", "sensory_hypersensitivity", "disorientation"]
            }
        },
        "relevant_conditions": [
            "migraine", "multiple_chemical_sensitivity", "traumatic_brain_injury", "fibromyalgia"
        ],
        "demographic_factors": [
            "age", "sex", "previous_head_injury", "stress_levels"
        ]
    },
    "cardiovascular": {
        "description": "Sensitivity affecting the cardiovascular system",
        "affected_parameters": [
            "co", "pm2_5", "pm10", "temperature", "humidity", "no2"
        ],
        "subtypes": {
            "cardiac_rhythm": {
                "description": "Effects on heart rate and rhythm",
                "typical_symptoms": ["palpitations", "irregular_heartbeat", "racing_heart", "fluttering_sensation"]
            },
            "vascular_response": {
                "description": "Effects on blood vessels and circulation",
                "typical_symptoms": ["hypertension", "flushing", "circulatory_changes", "chest_pressure"]
            },
            "cardiac_function": {
                "description": "Effects on overall heart function",
                "typical_symptoms": ["shortness_of_breath", "fatigue", "reduced_exercise_tolerance", "chest_pain"]
            }
        },
        "relevant_conditions": [
            "hypertension", "coronary_artery_disease", "arrhythmia", "heart_failure"
        ],
        "demographic_factors": [
            "age", "sex", "weight", "underlying_heart_conditions", "fitness_level"
        ]
    },
    "immunological": {
        "description": "Sensitivity involving immune system responses",
        "affected_parameters": [
            "pollen", "mold", "dust_mites", "tvoc", "formaldehyde", "pm2_5", "pm10"
        ],
        "subtypes": {
            "allergic_reaction": {
                "description": "Type I hypersensitivity (immediate allergic reactions)",
                "typical_symptoms": ["sneezing", "itching", "hives", "swelling"]
            },
            "inflammatory_response": {
                "description": "General inflammatory responses to irritants",
                "typical_symptoms": ["redness", "pain", "swelling", "heat"]
            },
            "systemic_immune": {
                "description": "Systemic immune activation and responses",
                "typical_symptoms": ["fatigue", "malaise", "mild_fever", "lymph_node_swelling"]
            }
        },
        "relevant_conditions": [
            "allergies", "asthma", "eczema", "autoimmune_disorders", "immunodeficiency"
        ],
        "demographic_factors": [
            "age", "genetic_factors", "previous_exposures", "immune_system_status"
        ]
    }
}


# Define population demographic distributions
AGE_DISTRIBUTIONS = {
    "global": {
        "child": (0, 12, 0.20),       # Age range and population percentage
        "adolescent": (13, 19, 0.10),
        "young_adult": (20, 39, 0.30),
        "middle_aged": (40, 59, 0.25),
        "older_adult": (60, 79, 0.12),
        "elderly": (80, 100, 0.03)
    },
    # Regional variations could be added here
}


# Sensitivity modifiers based on demographic factors
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
    },
    "immunological": {
        "child": 1.2,             # Developing immune system
        "adolescent": 1.1,
        "young_adult": 1.0,       # Baseline
        "middle_aged": 1.0,
        "older_adult": 1.2,
        "elderly": 1.4            # Immunosenescence in elderly
    }
}


# Sensitivity modifiers based on pre-existing conditions
CONDITION_SENSITIVITY_MODIFIERS = {
    "asthma": {
        "respiratory": 2.0,
        "ocular": 1.2,
        "immunological": 1.3
    },
    "copd": {
        "respiratory": 2.5,
        "cardiovascular": 1.3
    },
    "eczema": {
        "dermal": 2.0,
        "immunological": 1.3
    },
    "allergic_rhinitis": {
        "respiratory": 1.7,
        "ocular": 1.5,
        "immunological": 1.7
    },
    "migraine": {
        "neurological": 2.0,
        "ocular": 1.3
    },
    "hypertension": {
        "cardiovascular": 1.7,
        "neurological": 1.2
    },
    "diabetes": {
        "cardiovascular": 1.5,
        "dermal": 1.3,
        "neurological": 1.2
    },
    "autoimmune_disorders": {
        "immunological": 2.0,
        "dermal": 1.4,
        "neurological": 1.3
    }
    # Additional conditions can be added
}


# Response curve parameters for different sensitivity types
# These define how quickly symptoms develop as exposure increases
RESPONSE_CURVE_PARAMETERS = {
    "respiratory": {
        "default": {
            "threshold": 0.3,     # Exposure level where symptoms begin (0-1 scale)
            "slope": 1.5,         # Steepness of response curve
            "max_response": 1.0   # Maximum response level
        },
        "asthma": {              # Example of condition-specific curve
            "threshold": 0.1,
            "slope": 2.5,
            "max_response": 1.0
        }
    },
    "dermal": {
        "default": {
            "threshold": 0.4,
            "slope": 1.2,
            "max_response": 1.0
        },
        "eczema": {
            "threshold": 0.2,
            "slope": 2.0,
            "max_response": 1.0
        }
    },
    # Additional sensitivity types follow the same pattern
    "ocular": {
        "default": {
            "threshold": 0.3,
            "slope": 1.3,
            "max_response": 1.0
        }
    },
    "neurological": {
        "default": {
            "threshold": 0.5,
            "slope": 1.1,
            "max_response": 1.0
        },
        "migraine": {
            "threshold": 0.2,
            "slope": 1.8,
            "max_response": 1.0
        }
    },
    "cardiovascular": {
        "default": {
            "threshold": 0.6,
            "slope": 1.0,
            "max_response": 1.0
        }
    },
    "immunological": {
        "default": {
            "threshold": 0.4,
            "slope": 1.3,
            "max_response": 1.0
        }
    }
}
