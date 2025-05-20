"""
EnviroSense Chemical Properties Database

This module provides a database of chemical and particulate matter properties
relevant to environmental monitoring. Properties include physical characteristics,
diffusion behaviors, and health-related thresholds.

The database is structured as a dictionary of chemicals, each with standardized
property fields. This serves as a reference for simulation and analysis components
across the EnviroSense system.

References:
- NIOSH Pocket Guide to Chemical Hazards
- EPA Air Quality Standards
- WHO Air Quality Guidelines
- Scientific literature on diffusion coefficients and physical properties
"""

from enum import Enum, auto
from typing import Dict, Any, List, Optional, Union, Tuple


class ChemicalCategory(Enum):
    """Categories of chemicals for classification purposes."""
    VOC = auto()              # Volatile Organic Compounds
    INORGANIC_GAS = auto()    # Inorganic gases (CO, CO2, NOx, etc.)
    PARTICULATE = auto()      # Particulate matter (PM2.5, PM10, etc.)
    BIOAEROSOL = auto()       # Biological aerosols (pollen, mold, etc.)
    RADIATION = auto()        # Radiation (radon, etc.)
    SEMI_VOLATILE = auto()    # Semi-volatile organic compounds
    PYROLYSIS_PRODUCT = auto()# Products from thermal decomposition without oxygen
    COMBUSTION_PRODUCT = auto()# Products from burning with oxygen
    INDUSTRIAL_GAS = auto()   # Industrial process gases
    ELECTRICAL_SIGNATURE = auto()  # Chemicals associated with electrical issues
    EMF_SIGNATURE = auto()    # Electromagnetic field signatures
    ACOUSTIC_SIGNATURE = auto()# Acoustic signatures
    TERPENE = auto()          # Plant-derived hydrocarbons (often associated with wildfires)
    ALCOHOL = auto()          # Alcohols (isopropyl, ethanol, etc.)
    ESTER = auto()            # Organic compounds formed from acids and alcohols
    ORGANOCHLORINE = auto()   # Chlorinated organic compounds (PCBs, vinyl chloride, etc.)
    HYDROCARBON = auto()      # Aliphatic and aromatic hydrocarbon compounds
    OTHER = auto()            # Other chemicals


def get_chemical_property(chemical_id: str, property_name: str, default: Any = None) -> Any:
    """
    Get a specific property for a chemical.
    
    Args:
        chemical_id: The ID of the chemical
        property_name: The name of the property to get
        default: Default value to return if property doesn't exist
        
    Returns:
        The property value, or default if not found
    """
    if chemical_id not in CHEMICAL_PROPERTIES:
        return default
        
    # Handle nested properties with dot notation (e.g., "health_data.OSHA_PEL")
    if "." in property_name:
        parts = property_name.split(".")
        value = CHEMICAL_PROPERTIES[chemical_id]
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        return value
        
    return CHEMICAL_PROPERTIES[chemical_id].get(property_name, default)


def get_chemicals_by_category(category: ChemicalCategory) -> List[str]:
    """
    Get all chemicals belonging to a specific category.
    
    Args:
        category: The ChemicalCategory to filter by
        
    Returns:
        List of chemical IDs in the specified category
    """
    return [
        chem_id for chem_id, properties in CHEMICAL_PROPERTIES.items()
        if properties.get("category") == category
    ]


def get_diffusion_coefficient(
    chemical_id: str, 
    temperature: float = 25.0,
    pressure: float = 101.325
) -> float:
    """
    Get the diffusion coefficient for a chemical, with optional temperature adjustment.
    
    Args:
        chemical_id: The ID of the chemical
        temperature: Temperature in C (default 25C)
        pressure: Pressure in kPa (default 101.325 kPa = 1 atm)
        
    Returns:
        Diffusion coefficient in m²/s, or 0.0 if not found
    """
    base_coefficient = get_chemical_property(chemical_id, "diffusion_coefficient", 0.0)
    
    if base_coefficient == 0.0:
        return 0.0
        
    # Apply temperature correction using Fuller-Schettler-Giddings equation
    # D_T2 = D_T1 * (T2/T1)^1.75 * (P1/P2)
    if temperature != 25.0 or pressure != 101.325:
        T1 = 25.0 + 273.15  # Reference temp in K
        T2 = temperature + 273.15  # Target temp in K
        P1 = 101.325  # Reference pressure in kPa
        P2 = pressure  # Target pressure in kPa
        
        correction_factor = ((T2/T1) ** 1.75) * (P1/P2)
        return base_coefficient * correction_factor
        
    return base_coefficient


# Chemical properties database
# All properties use SI units where applicable
CHEMICAL_PROPERTIES = {
    # VOCs and aldehydes
    "formaldehyde": {
        "name": "Formaldehyde", 
        "formula": "CH2O",
        "category": ChemicalCategory.VOC,
        "molecular_weight": 30.031,  # g/mol
        "diffusion_coefficient": 0.16e-4,  # m²/s in air at 25°C
        "density": 1.067,  # kg/m³ (gas)
        "air_density_ratio": 1.037,  # ratio to air density
        "volatility": 0.9,  # 0-1 scale
        "reactivity": 0.4,  # 0-1 scale
        "settling_velocity": 0.0,  # m/s (gas doesn't settle)
        "deposition_rate": 0.001,  # fraction deposited per second
        "temperature_scaling": {
            "type": "arrhenius",
            "activation_energy": 88.0,  # kJ/mol
            "reference_temp": 298.15,  # K (25°C)
            "scaling_factor": 2.0,  # approximate doubling per 10°C
        },
        "humidity_effect": 0.2,  # 0-1 scale, higher means more affected by humidity
        "health_data": {
            "odor_threshold": 0.05,  # ppm
            "irritation_threshold": 0.1,  # ppm
            "OSHA_PEL": 0.75,  # ppm (8-hour TWA)
            "OSHA_STEL": 2.0,  # ppm (15-min)
            "NIOSH_REL": 0.016,  # ppm (8-hour TWA)
            "NIOSH_CEILING": 0.1,  # ppm (15-min)
            "ACGIH_TLV": 0.1,  # ppm (8-hour TWA)
            "IDLH": 20,  # ppm
            "carcinogen_class": "1",  # IARC classification 
        },
        "typical_sources": ["building materials", "furniture", "carpets", "cleaning products"],
        "typical_concentrations": {
            "outdoor": 0.001,  # ppm average
            "indoor_residential": 0.02,  # ppm average
            "indoor_office": 0.02,  # ppm average
            "industrial": 0.1,  # ppm average
        },
    },
    
    "benzene": {
        "name": "Benzene",
        "formula": "C6H6",
        "category": ChemicalCategory.VOC,
        "molecular_weight": 78.11,  # g/mol
        "diffusion_coefficient": 0.088e-4,  # m²/s in air at 25°C
        "density": 3.19,  # kg/m³ (gas)
        "air_density_ratio": 2.7,  # ratio to air density
        "volatility": 0.7,  # 0-1 scale
        "reactivity": 0.3,  # 0-1 scale
        "settling_velocity": 0.0,  # m/s (gas doesn't settle)
        "deposition_rate": 0.0005,  # fraction deposited per second
        "temperature_scaling": {
            "type": "linear",
            "slope": 0.03,  # fractional increase per °C
            "reference_temp": 25.0,  # °C
        },
        "humidity_effect": 0.1,  # 0-1 scale
        "health_data": {
            "odor_threshold": 1.5,  # ppm
            "OSHA_PEL": 1.0,  # ppm (8-hour TWA)
            "OSHA_STEL": 5.0,  # ppm (15-min)
            "NIOSH_REL": 0.1,  # ppm (8-hour TWA)
            "ACGIH_TLV": 0.5,  # ppm (8-hour TWA)
            "IDLH": 500,  # ppm
            "carcinogen_class": "1",  # IARC classification
        },
        "typical_sources": ["gasoline", "vehicle exhaust", "cigarette smoke", "industrial emissions"],
        "typical_concentrations": {
            "outdoor_urban": 0.002,  # ppm average
            "outdoor_industrial": 0.01,  # ppm average
            "indoor_residential": 0.001,  # ppm average
            "indoor_garage": 0.05,  # ppm average
        },
    },

    # Inorganic Gases
    "carbon_monoxide": {
        "name": "Carbon Monoxide",
        "formula": "CO",
        "category": ChemicalCategory.INORGANIC_GAS,
        "molecular_weight": 28.01,  # g/mol
        "diffusion_coefficient": 0.2e-4,  # m²/s in air at 25°C
        "density": 1.14,  # kg/m³ (gas)
        "air_density_ratio": 0.968,  # ratio to air density
        "volatility": 1.0,  # 0-1 scale
        "reactivity": 0.2,  # 0-1 scale 
        "settling_velocity": 0.0,  # m/s (gas doesn't settle)
        "deposition_rate": 0.0001,  # fraction deposited per second
        "temperature_scaling": {
            "type": "linear",
            "slope": 0.01,  # fractional increase per °C
            "reference_temp": 25.0,  # °C
        },
        "humidity_effect": 0.05,  # 0-1 scale
        "health_data": {
            "odor_threshold": None,  # odorless
            "OSHA_PEL": 50,  # ppm (8-hour TWA)
            "NIOSH_REL": 35,  # ppm (8-hour TWA)
            "NIOSH_CEILING": 200,  # ppm
            "ACGIH_TLV": 25,  # ppm (8-hour TWA)
            "IDLH": 1200,  # ppm
        },
        "typical_sources": ["combustion appliances", "vehicle exhaust", "tobacco smoke"],
        "typical_concentrations": {
            "outdoor_urban": 2.0,  # ppm average
            "outdoor_high_traffic": 10.0,  # ppm average
            "indoor_residential": 0.5,  # ppm average
            "indoor_with_gas_stove": 5.0,  # ppm average
            "indoor_garage": 35.0,  # ppm average
        },
    },

    "carbon_dioxide": {
        "name": "Carbon Dioxide",
        "formula": "CO2",
        "category": ChemicalCategory.INORGANIC_GAS,
        "molecular_weight": 44.01,  # g/mol
        "diffusion_coefficient": 0.155e-4,  # m²/s in air at 25°C
        "density": 1.98,  # kg/m³ (gas)
        "air_density_ratio": 1.65,  # ratio to air density
        "volatility": 1.0,  # 0-1 scale
        "reactivity": 0.1,  # 0-1 scale (relatively inert)
        "settling_velocity": 0.0,  # m/s (slight tendency to sink)
        "deposition_rate": 0.0,  # fraction deposited per second
        "temperature_scaling": {
            "type": "linear",
            "description": "Production increases during combustion",
            "reference_curve": [(0, 0.9), (25, 1.0), (50, 1.1)],  # temp in °C, scaling factor
        },
        "humidity_effect": 0.0,  # 0-1 scale
        "health_data": {
            "odor_threshold": None,  # odorless
            "OSHA_PEL": 5000,  # ppm (8-hour TWA)
            "NIOSH_CEILING": 30000,  # ppm (10-min)
            "ACGIH_TLV": 5000,  # ppm (8-hour TWA)
            "IDLH": 40000,  # ppm
        },
        "typical_sources": ["combustion", "respiration", "fermentation", "electrical arcing"],
        "typical_concentrations": {
            "outdoor_ambient": 420,  # ppm average (rising yearly)
            "indoor_residential": 800,  # ppm average
            "poorly_ventilated_room": 2000,  # ppm
            "early_fire_stage": 1000,  # ppm above ambient
            "electrical_fault": 600,  # ppm above ambient
        },
    },

    # Particulate Matter
    "pm2.5": {
        "name": "PM2.5",
        "formula": None,  # Not applicable for particulate mix
        "category": ChemicalCategory.PARTICULATE,
        "molecular_weight": None,  # N/A for particulate
        "diffusion_coefficient": 0.4e-6,  # m²/s - much lower than gases
        "density": 1500,  # kg/m³ (typical value for fine particles)
        "air_density_ratio": None,  # Not applicable for particulate
        "volatility": 0.0,  # 0-1 scale (non-volatile)
        "reactivity": 0.2,  # 0-1 scale (varies by composition)
        "settling_velocity": 0.0003,  # m/s (slow settling)
        "deposition_rate": 0.002,  # fraction deposited per second
        "temperature_scaling": {
            "type": "minimal",
            "factor": 0.003,  # fractional change per °C
        },
        "humidity_effect": 0.7,  # 0-1 scale (hygroscopic growth significant)
        "health_data": {
            "WHO_guideline": 25,  # μg/m³ (24-hour mean)
            "EPA_NAAQS": 35,  # μg/m³ (24-hour)
            "EPA_NAAQS_annual": 12,  # μg/m³ (annual mean)
        },
        "typical_sources": ["combustion", "vehicle exhaust", "industrial emissions", "cooking"],
        "typical_concentrations": {
            "outdoor_rural": 5,  # μg/m³ average
            "outdoor_urban": 15,  # μg/m³ average
            "outdoor_industrial": 25,  # μg/m³ average
            "indoor_residential": 10,  # μg/m³ average
            "indoor_with_cooking": 30,  # μg/m³ average
        },
    },

    "pm10": {
        "name": "PM10",
        "formula": None,  # Not applicable for particulate mix
        "category": ChemicalCategory.PARTICULATE,
        "molecular_weight": None,  # N/A for particulate
        "diffusion_coefficient": 0.1e-6,  # m²/s - very low for larger particles
        "density": 1200,  # kg/m³ (typical value)
        "air_density_ratio": None,  # Not applicable for particulate
        "volatility": 0.0,  # 0-1 scale (non-volatile)
        "reactivity": 0.1,  # 0-1 scale
        "settling_velocity": 0.003,  # m/s (faster than PM2.5)
        "deposition_rate": 0.005,  # fraction deposited per second
        "temperature_scaling": {
            "type": "minimal",
            "factor": 0.002,  # fractional change per °C
        },
        "humidity_effect": 0.5,  # 0-1 scale
        "health_data": {
            "WHO_guideline": 50,  # μg/m³ (24-hour mean)
            "EPA_NAAQS": 150,  # μg/m³ (24-hour)
        },
        "typical_sources": ["dust", "pollen", "mold", "combustion", "road dust"],
        "typical_concentrations": {
            "outdoor_rural": 15,  # μg/m³ average
            "outdoor_urban": 30,  # μg/m³ average
            "outdoor_industrial": 50,  # μg/m³ average
            "indoor_residential": 20,  # μg/m³ average
            "indoor_dusty": 60,  # μg/m³ average
        },
    },

    # Grid Guardian Specific Chemicals - Fire Precursors and Electrical Signatures
    "ozone": {
        "name": "Ozone",
        "formula": "O3",
        "category": ChemicalCategory.INORGANIC_GAS,
        "molecular_weight": 48.0,  # g/mol
        "diffusion_coefficient": 0.14e-4,  # m²/s in air at 25°C
        "density": 2.14,  # kg/m³ (gas)
        "air_density_ratio": 1.66,  # ratio to air density
        "volatility": 1.0,  # 0-1 scale
        "reactivity": 0.9,  # 0-1 scale (highly reactive)
        "settling_velocity": 0.0,  # m/s (gas doesn't settle)
        "deposition_rate": 0.001,  # fraction deposited per second
        "temperature_scaling": {
            "type": "linear",
            "slope": 0.02,  # fractional increase per °C
            "reference_temp": 25.0,  # °C
        },
        "humidity_effect": 0.3,  # 0-1 scale
        "health_data": {
            "odor_threshold": 0.01,  # ppm
            "OSHA_PEL": 0.1,  # ppm (8-hour TWA)
            "ACGIH_TLV": 0.05,  # ppm (8-hour TWA)
            "NIOSH_CEILING": 0.1,  # ppm (15-min)
            "EPA_NAAQS": 0.07,  # ppm (8-hour)
        },
        "typical_sources": ["electrical arcing", "corona discharge", "photochemical reactions", "lightning"],
        "typical_concentrations": {
            "outdoor_clean": 0.03,  # ppm average
            "outdoor_urban": 0.05,  # ppm average
            "outdoor_smog": 0.15,  # ppm average
            "electrical_fault": 0.5,  # ppm near arcing events
            "near_operating_equipment": 0.1,  # ppm
        },
        "electrical_signature": {
            "arcing_indicator": True,
            "corona_indicator": True,
            "detection_threshold": 0.03,  # ppm (for electrical issues)
            "false_positive_risk": "Medium",  # can be produced by other sources
            "rise_time_electrical_fault": "Fast",  # seconds to minutes
        },
    },

    "nitrogen_dioxide": {
        "name": "Nitrogen Dioxide",
        "formula": "NO2",
        "category": ChemicalCategory.INORGANIC_GAS,
        "molecular_weight": 46.01,  # g/mol
        "diffusion_coefficient": 0.14e-4,  # m²/s in air at 25°C
        "density": 1.88,  # kg/m³ (gas)
        "air_density_ratio": 1.58,  # ratio to air density
        "volatility": 1.0,  # 0-1 scale
        "reactivity": 0.7,  # 0-1 scale
        "settling_velocity": 0.0,  # m/s (gas doesn't settle)
        "deposition_rate": 0.0005,  # fraction deposited per second
        "temperature_scaling": {
            "type": "linear",
            "slope": 0.015,  # fractional increase per °C
            "reference_temp": 25.0,  # °C
        },
        "humidity_effect": 0.3,  # 0-1 scale
        "health_data": {
            "odor_threshold": 0.1,  # ppm
            "OSHA_PEL": 5,  # ppm (8-hour TWA)
            "ACGIH_TLV": 3,  # ppm (8-hour TWA)
            "NIOSH_STEL": 1,  # ppm (15-min)
            "EPA_NAAQS": 0.053,  # ppm (annual mean)
            "EPA_NAAQS_1hour": 0.100,  # ppm (1-hour)
        },
        "typical_sources": ["combustion", "vehicle exhaust", "electrical arcing", "industrial processes"],
        "typical_concentrations": {
            "outdoor_rural": 0.005,  # ppm average
            "outdoor_urban": 0.020,  # ppm average
            "indoor_with_gas_stove": 0.025,  # ppm average
            "near_electrical_fault": 0.2,  # ppm average
        },
        "electrical_signature": {
            "arcing_indicator": True,
            "corona_indicator": False,
            "detection_threshold": 0.05,  # ppm (for electrical issues)
            "false_positive_risk": "High",  # commonly from other sources
            "rise_time_electrical_fault": "Medium",  # minutes
        },
    },

    "sulfur_hexafluoride": {
        "name": "Sulfur Hexafluoride",
        "formula": "SF6",
        "category": ChemicalCategory.INDUSTRIAL_GAS,
        "molecular_weight": 146.05,  # g/mol
        "diffusion_coefficient": 0.034e-4,  # m²/s in air at 25°C
        "density": 6.17,  # kg/m³ (gas)
        "air_density_ratio": 5.11,  # ratio to air density (much heavier than air)
        "volatility": 1.0,  # 0-1 scale
        "reactivity": 0.05,  # 0-1 scale (very inert)
        "settling_velocity": 0.002,  # m/s (tends to sink being much heavier than air)
        "deposition_rate": 0.0001,  # fraction deposited per second
        "temperature_scaling": {
            "type": "minimal",
            "factor": 0.001,  # fractional change per °C
        },
        "humidity_effect": 0.01,  # 0-1 scale (minimally affected)
        "health_data": {
            "odor_threshold": None,  # Odorless
            "OSHA_PEL": 1000,  # ppm (8-hour TWA)
            "ACGIH_TLV": 1000,  # ppm (8-hour TWA)
        },
        "typical_sources": ["electrical insulation", "switchgear", "transformers", "circuit breakers"],
        "typical_concentrations": {
            "background": 0.00001,  # ppm (trace)
            "electrical_equipment_room": 0.01,  # ppm
            "near_leak": 5.0,  # ppm
            "major_leak": 50.0,  # ppm
        },
        "electrical_signature": {
            "arcing_indicator": False,
            "leak_indicator": True,
            "detection_threshold": 0.001,  # ppm (for electrical equipment leak)
            "false_positive_risk": "Very Low",  # almost exclusively from electrical equipment
            "rise_time_electrical_fault": "Slow",  # gradual accumulation
        },
    },

    # Fire Precursor Chemicals
    "acetaldehyde": {
        "name": "Acetaldehyde",
        "formula": "C2H4O",
        "category": ChemicalCategory.PYROLYSIS_PRODUCT,
        "molecular_weight": 44.05,  # g/mol
        "diffusion_coefficient": 0.124e-4,  # m²/s in air at 25°C
        "density": 1.83,  # kg/m³ (gas)
        "air_density_ratio": 1.52,  # ratio to air density
        "volatility": 0.9,  # 0-1 scale
        "reactivity": 0.6,  # 0-1 scale
        "settling_velocity": 0.0,  # m/s (gas doesn't settle)
        "deposition_rate": 0.0004,  # fraction deposited per second
        "temperature_scaling": {
            "type": "exponential",
            "base_factor": 1.08,  # per °C above reference
            "reference_temp": 25.0,  # °C
        },
        "humidity_effect": 0.2,  # 0-1 scale
        "health_data": {
            "odor_threshold": 0.05,  # ppm
            "OSHA_PEL": 200,  # ppm (8-hour TWA)
            "ACGIH_TLV": 25,  # ppm (8-hour TWA)
            "NIOSH_CEILING": 2000,  # ppm (15-min)
            "IDLH": 2000,  # ppm
        },
        "typical_sources": ["thermal degradation", "smoldering", "wood combustion"],
        "typical_concentrations": {
            "ambient": 0.003,  # ppm average
            "indoor_normal": 0.01,  # ppm average
            "pre_fire_thermal_degradation": 1.0,  # ppm
            "active_fire": 50.0,  # ppm
        },
        "fire_precursor": {
            "indicator_reliability": "High",
            "detection_threshold": 0.2,  # ppm (for fire warning)
            "false_positive_sources": ["industrial emissions", "alcohol fermentation"],
            "rise_time_pre_fire": "Medium",  # minutes to hours
            "correlation_with_temperature": 0.7,  # 0-1 scale
        },
    },

    "acrolein": {
        "name": "Acrolein",
        "formula": "C3H4O",
        "category": ChemicalCategory.PYROLYSIS_PRODUCT,
        "molecular_weight": 56.06,  # g/mol
        "diffusion_coefficient": 0.11e-4,  # m²/s in air at 25°C
        "density": 2.33,  # kg/m³ (gas)
        "air_density_ratio": 1.94,  # ratio to air density
        "volatility": 0.85,  # 0-1 scale
        "reactivity": 0.8,  # 0-1 scale (highly reactive)
        "settling_velocity": 0.0,  # m/s (gas doesn't settle)
        "deposition_rate": 0.0006,  # fraction deposited per second
        "temperature_scaling": {
            "type": "exponential",
            "base_factor": 1.12,  # per °C above reference
            "reference_temp": 25.0,  # °C
        },
        "humidity_effect": 0.3,  # 0-1 scale
        "health_data": {
            "odor_threshold": 0.16,  # ppm
            "OSHA_PEL": 0.1,  # ppm (8-hour TWA)
            "ACGIH_TLV": 0.1,  # ppm (8-hour TWA)
            "NIOSH_REL": 0.1,  # ppm (10-hour TWA)
            "IDLH": 2,  # ppm
        },
        "typical_sources": ["overheated cooking oil", "plastic combustion", "wood combustion", "electrical overheating"],
        "typical_concentrations": {
            "ambient": 0.001,  # ppm average
            "indoor_normal": 0.003,  # ppm average
            "pre_fire_overheating": 0.08,  # ppm
            "active_fire": 2.0,  # ppm
            "electrical_overheating": 0.05,  # ppm
        },
        "fire_precursor": {
            "indicator_reliability": "Very High",
            "detection_threshold": 0.03,  # ppm (for fire warning)
            "false_positive_sources": ["cooking", "tobacco smoke"],
            "rise_time_pre_fire": "Fast",  # minutes
            "correlation_with_temperature": 0.9,  # 0-1 scale
        },
    },
    
    # Radiation related
    "radon": {
        "name": "Radon",
        "formula": "Rn",
        "category": ChemicalCategory.RADIATION,
        "molecular_weight": 222.0,  # g/mol
        "diffusion_coefficient": 0.12e-4,  # m²/s in air at 25°C
        "density": 9.73,  # kg/m³ (gas)
        "air_density_ratio": 7.5,  # ratio to air density
        "volatility": 1.0,  # 0-1 scale
        "reactivity": 0.0,  # 0-1 scale (noble gas, inert)
        "settling_velocity": 0.0005,  # m/s (tends to settle in lower areas due to high density)
        "deposition_rate": 0.00001,  # fraction deposited per second
        "temperature_scaling": {
            "type": "linear",
            "slope": 0.005,  # fractional increase per °C
            "reference_temp": 25.0,  # °C
        },
        "humidity_effect": 0.1,  # 0-1 scale
        "health_data": {
            "odor_threshold": None,  # Odorless
            "EPA_action_level": 4.0,  # pCi/L (picocuries per liter)
            "WHO_reference_level": 2.7,  # pCi/L
        },
        "typical_sources": ["soil", "rock", "groundwater", "building materials"],
        "typical_concentrations": {
            "outdoor_average": 0.4,  # pCi/L
            "indoor_average": 1.3,  # pCi/L
            "indoor_basement": 3.0,  # pCi/L
            "high_risk_area": 10.0,  # pCi/L
        },
        "radiation_properties": {
            "half_life": 3.8235,  # days
            "decay_mode": "alpha",
            "progeny": ["Po-218", "Pb-214", "Bi-214", "Po-214", "Pb-210"],
            "energy_alpha": 5.49,  # MeV
            "detection_methods": ["alpha track", "electret ion chamber", "continuous monitors"],
        },
    },
    
    # EMF Signatures for Grid Guardian
    "emf_signature": {
        "name": "Electromagnetic Field Signature",
        "category": ChemicalCategory.EMF_SIGNATURE,
        "fields": {
            "electric_field": {
                "units": "V/m",
                "typical_background": 1.0,  # V/m
                "warning_level": 5000,  # V/m
                "frequency_bands": {
                    "power_line": "50-60 Hz",
                    "radio": "10 kHz - 300 MHz",
                    "microwave": "300 MHz - 300 GHz"
                }
            },
            "magnetic_field": {
                "units": "μT",
                "typical_background": 0.1,  # μT (microtesla)
                "warning_level": 100,  # μT
                "frequency_response": "Primarily 50-60 Hz for power equipment"
            }
        },
        "electrical_signature": {
            "arcing_indicator": True,
            "corona_indicator": True,
            "detection_threshold": {
                "arcing": 10,  # μT for magnetic transients
                "corona": 2000,  # V/m for electric field
                "fault_current": 50,  # % above baseline
            },
            "false_positive_risk": "Low",  # highly specific to electrical issues
            "rise_time_electrical_fault": "Very Fast",  # milliseconds
        },
        "typical_sources": ["power lines", "transformers", "switchgear", "motors", "arcing faults"],
        "typical_readings": {
            "normal_operation_power_line": 2.0,  # μT at 1m distance
            "normal_operation_transformer": 5.0,  # μT at 1m distance
            "arcing_fault": 50.0,  # μT transient spike
            "pre_failure_electrical_equipment": 20.0,  # % increase over baseline
        },
    },
    
    # Acoustic Signatures for Grid Guardian Arcing Detection
    "acoustic_signature": {
        "name": "Acoustic Signature",
        "category": ChemicalCategory.ACOUSTIC_SIGNATURE,
        "sound_properties": {
            "frequency_bands": {
                "low": "20 Hz - 500 Hz",
                "mid": "500 Hz - 2 kHz",
                "high": "2 kHz - 20 kHz",
                "ultrasonic": "20 kHz - 100 kHz"
            },
            "units": "dB SPL",  # Sound Pressure Level
            "typical_background": {
                "indoor_quiet": 30,  # dB
                "indoor_equipment_room": 60,  # dB
                "outdoor_substation": 65,  # dB
                "industrial_area": 75,  # dB
            }
        },
        "electrical_signature": {
            "arcing_indicator": True,
            "corona_indicator": True,
            "transformer_degradation_indicator": True,
            "detection_threshold": {
                "arcing": 65,  # dB in ultrasonic range
                "corona": 45,  # dB in high frequency range
                "transformer_vibration": 70,  # dB in low frequency range
            },
            "characteristic_frequencies": {
                "arcing": "2 kHz - 40 kHz",
                "corona": "4 kHz - 12 kHz",
                "transformer_hum": "100 Hz - 300 Hz",
                "contact_degradation": "300 Hz - 3 kHz"
            },
            "false_positive_risk": "Medium",  # various mechanical sounds can mimic
            "rise_time_electrical_fault": "Instantaneous",  # milliseconds or less
        },
        "typical_sources": ["electrical arcing", "corona discharge", "transformer vibration", "loose connections"],
        "typical_readings": {
            "normal_operation_transformer": {
                "level": 55,  # dB
                "spectrum": "Primarily fundamental frequency (50/60 Hz) and harmonics"
            },
            "arcing_fault": {
                "level": 75,  # dB
                "spectrum": "Broadband with high ultrasonic component"
            },
            "corona_discharge": {
                "level": 60,  # dB
                "spectrum": "Broadband hissing in 4-12 kHz range"
            },
            "loose_connection": {
                "level": 65,  # dB
                "spectrum": "Intermittent crackling with thermal cycling"
            }
        },
        "pattern_recognition": {
            "temporal_pattern": {
                "arcing": "Irregular, sporadic bursts",
                "corona": "Continuous with amplitude modulation in wet conditions",
                "transformer_aging": "Progressive increase in harmonics over time"
            },
            "correlation_with_load": {
                "arcing": "Often correlated with circuit switching or load changes",
                "corona": "Worse in high humidity, rain, or contamination",
                "transformer": "Directly proportional to load"
            }
        },
    },

    # Wildfire and Electrical Fault Detection Compounds
    "alpha_pinene": {
        "name": "Alpha-Pinene",
        "formula": "C10H16",
        "category": ChemicalCategory.TERPENE,
        "molecular_weight": 136.24,  # g/mol
        "diffusion_coefficient": 0.067e-4,  # m²/s in air at 25°C
        "density": 5.65,  # kg/m³ (gas)
        "air_density_ratio": 4.69,  # ratio to air density
        "volatility": 0.8,  # 0-1 scale
        "reactivity": 0.6,  # 0-1 scale
        "settling_velocity": 0.0002,  # m/s
        "deposition_rate": 0.002,  # fraction deposited per second
        "temperature_scaling": {
            "type": "exponential",
            "description": "Emission increases with temperature, especially when vegetation is heated",
            "reference_curve": [(10, 0.5), (20, 1.0), (30, 2.0), (40, 4.0), (50, 8.0), (60, 15.0)],  # temp in °C, scaling factor
        },
        "humidity_effect": 0.2,  # 0-1 scale
        "health_data": {
            "odor_threshold": 0.01,  # ppm (pine odor)
            "OSHA_PEL": None,
            "NIOSH_CEILING": None,
            "ACGIH_TLV": None,
            "IDLH": None,
        },
        "typical_sources": ["coniferous trees", "heated vegetation", "forest fire precursor", "essential oils"],
        "typical_concentrations": {
            "outdoor_forest": 0.002,  # ppm average
            "heated_vegetation": 0.02,  # ppm
            "early_stage_wildfire": 0.05,  # ppm
            "indoor_with_pine_products": 0.005,  # ppm
        },
    },

    "limonene": {
        "name": "Limonene",
        "formula": "C10H16",
        "category": ChemicalCategory.TERPENE,
        "molecular_weight": 136.24,  # g/mol
        "diffusion_coefficient": 0.066e-4,  # m²/s in air at 25°C
        "density": 5.6,  # kg/m³ (gas)
        "air_density_ratio": 4.65,  # ratio to air density
        "volatility": 0.85,  # 0-1 scale
        "reactivity": 0.65,  # 0-1 scale
        "settling_velocity": 0.0002,  # m/s
        "deposition_rate": 0.002,  # fraction deposited per second
        "temperature_scaling": {
            "type": "exponential",
            "description": "Emission increases with temperature, especially when vegetation is heated",
            "reference_curve": [(10, 0.5), (20, 1.0), (30, 2.0), (40, 4.0), (50, 8.0), (60, 15.0)],  # temp in °C, scaling factor
        },
        "humidity_effect": 0.2,  # 0-1 scale
        "health_data": {
            "odor_threshold": 0.01,  # ppm (citrus odor)
            "OSHA_PEL": None,
            "NIOSH_CEILING": None,
            "ACGIH_TLV": None,
            "IDLH": None,
        },
        "typical_sources": ["citrus trees", "heated vegetation", "cleaning products", "consumer products"],
        "typical_concentrations": {
            "outdoor_citrus_grove": 0.004,  # ppm average
            "heated_vegetation": 0.02,  # ppm
            "early_stage_wildfire": 0.04,  # ppm
            "indoor_with_cleaning_products": 0.1,  # ppm
        },
    },

    "isopropyl_alcohol": {
        "name": "Isopropyl Alcohol",
        "formula": "C3H8O",
        "category": ChemicalCategory.ALCOHOL,
        "molecular_weight": 60.1,  # g/mol
        "diffusion_coefficient": 0.105e-4,  # m²/s in air at 25°C
        "density": 2.5,  # kg/m³ (gas)
        "air_density_ratio": 2.07,  # ratio to air density
        "volatility": 0.9,  # 0-1 scale
        "reactivity": 0.4,  # 0-1 scale
        "settling_velocity": 0.0001,  # m/s
        "deposition_rate": 0.002,  # fraction deposited per second
        "temperature_scaling": {
            "type": "exponential",
            "description": "Evaporation increases with temperature",
            "reference_curve": [(0, 0.3), (20, 1.0), (40, 3.0), (60, 8.0)],  # temp in °C, scaling factor
        },
        "humidity_effect": 0.1,  # 0-1 scale
        "health_data": {
            "odor_threshold": 22,  # ppm
            "OSHA_PEL": 400,  # ppm (8-hour TWA)
            "NIOSH_CEILING": 500,  # ppm (15-min)
            "ACGIH_TLV": 200,  # ppm (8-hour TWA)
            "IDLH": 2000,  # ppm
        },
        "typical_sources": ["cleaning products", "electronics cleaning", "hand sanitizers", "personal care products"],
        "typical_concentrations": {
            "indoor_residential": 0.05,  # ppm average
            "during_cleaning": 5,  # ppm
            "electronics_repair": 10,  # ppm
            "medical_facilities": 2,  # ppm
        },
    },

    "methyl_methacrylate": {
        "name": "Methyl Methacrylate",
        "formula": "C5H8O2",
        "category": ChemicalCategory.ESTER,
        "molecular_weight": 100.12,  # g/mol
        "diffusion_coefficient": 0.075e-4,  # m²/s in air at 25°C
        "density": 4.16,  # kg/m³ (gas)
        "air_density_ratio": 3.45,  # ratio to air density
        "volatility": 0.8,  # 0-1 scale
        "reactivity": 0.7,  # 0-1 scale
        "settling_velocity": 0.0002,  # m/s
        "deposition_rate": 0.002,  # fraction deposited per second
        "temperature_scaling": {
            "type": "exponential",
            "description": "Released during thermal degradation of plastics and polymers",
            "reference_curve": [(25, 1.0), (100, 2.0), (150, 5.0), (200, 12.0), (250, 25.0)],  # temp in °C, scaling factor
        },
        "humidity_effect": 0.1,  # 0-1 scale
        "health_data": {
            "odor_threshold": 0.05,  # ppm (acrid, fruity odor)
            "OSHA_PEL": 100,  # ppm (8-hour TWA)
            "NIOSH_CEILING": None,
            "ACGIH_TLV": 50,  # ppm (8-hour TWA)
            "IDLH": 1000,  # ppm
        },
        "typical_sources": ["plastic degradation", "polymer combustion", "acrylic materials", "electrical insulation"],
        "typical_concentrations": {
            "normal_background": 0.0,  # ppm
            "heated_plastics": 0.2,  # ppm
            "electrical_insulation_fault": 1.0,  # ppm
            "plastic_fire": 5.0,  # ppm
        },
    },

    "pcb_aroclor_1254": {
        "name": "PCB (Aroclor 1254)",
        "formula": "C12H(10-n)Cln",
        "category": ChemicalCategory.ORGANOCHLORINE,
        "molecular_weight": 327.0,  # g/mol (average)
        "diffusion_coefficient": 0.04e-4,  # m²/s in air at 25°C
        "density": 13.6,  # kg/m³ (gas)
        "air_density_ratio": 11.3,  # ratio to air density
        "volatility": 0.3,  # 0-1 scale (low volatility)
        "reactivity": 0.2,  # 0-1 scale
        "settling_velocity": 0.0005,  # m/s
        "deposition_rate": 0.005,  # fraction deposited per second
        "temperature_scaling": {
            "type": "exponential",
            "description": "Released from older transformers during overheating",
            "reference_curve": [(25, 1.0), (50, 2.0), (100, 10.0), (150, 50.0)],  # temp in °C, scaling factor
        },
        "humidity_effect": 0.05,  # 0-1 scale
        "health_data": {
            "odor_threshold": None,  # typically odorless
            "OSHA_PEL": 0.5,  # mg/m³ (8-hour TWA)
            "NIOSH_CEILING": None,
            "ACGIH_TLV": 0.5,  # mg/m³ (8-hour TWA)
            "IDLH": 5,  # mg/m³
        },
        "typical_sources": ["older transformers", "capacitors", "legacy electrical equipment"],
        "typical_concentrations": {
            "normal_background": 0.0,  # ppb
            "near_old_equipment": 0.01,  # ppb
            "leaking_transformer": 0.1,  # ppb
            "overheating_equipment": 1.0,  # ppb
        },
    },

    "transformer_oil_vapor": {
        "name": "Transformer Oil Vapor",
        "formula": "CnH2n+2",
        "category": ChemicalCategory.HYDROCARBON,
        "molecular_weight": 250.0,  # g/mol (average)
        "diffusion_coefficient": 0.05e-4,  # m²/s in air at 25°C
        "density": 10.4,  # kg/m³ (gas)
        "air_density_ratio": 8.6,  # ratio to air density
        "volatility": 0.4,  # 0-1 scale
        "reactivity": 0.3,  # 0-1 scale
        "settling_velocity": 0.0004,  # m/s
        "deposition_rate": 0.003,  # fraction deposited per second
        "temperature_scaling": {
            "type": "exponential",
            "description": "Evaporation increases dramatically with temperature",
            "reference_curve": [(25, 1.0), (50, 2.0), (80, 5.0), (100, 15.0), (120, 40.0)],  # temp in °C, scaling factor
        },
        "humidity_effect": 0.05,  # 0-1 scale
        "health_data": {
            "odor_threshold": 0.5,  # ppm (varies by composition)
            "OSHA_PEL": None,  # varies by composition
            "NIOSH_CEILING": None,
            "ACGIH_TLV": None,  # varies by composition
            "IDLH": None,
        },
        "typical_sources": ["transformers", "oil-filled electrical equipment", "bushing oil"],
        "typical_concentrations": {
            "normal_background": 0.0,  # ppm
            "near_normal_equipment": 0.01,  # ppm
            "minor_oil_leak": 0.1,  # ppm
            "overheating_transformer": 1.0,  # ppm
        },
    },

    "vinyl_chloride": {
        "name": "Vinyl Chloride",
        "formula": "C2H3Cl",
        "category": ChemicalCategory.ORGANOCHLORINE,
        "molecular_weight": 62.5,  # g/mol
        "diffusion_coefficient": 0.106e-4,  # m²/s in air at 25°C
        "density": 2.6,  # kg/m³ (gas)
        "air_density_ratio": 2.16,  # ratio to air density
        "volatility": 0.95,  # 0-1 scale
        "reactivity": 0.5,  # 0-1 scale
        "settling_velocity": 0.0001,  # m/s
        "deposition_rate": 0.001,  # fraction deposited per second
        "temperature_scaling": {
            "type": "exponential",
            "description": "Released during thermal degradation of PVC insulation",
            "reference_curve": [(25, 1.0), (100, 2.0), (150, 8.0), (200, 20.0), (250, 50.0)],  # temp in °C, scaling factor
        },
        "humidity_effect": 0.1,  # 0-1 scale
        "health_data": {
            "odor_threshold": 3000,  # ppm (sweet odor at high levels)
            "OSHA_PEL": 1,  # ppm (8-hour TWA)
            "NIOSH_CEILING": None,
            "ACGIH_TLV": 1,  # ppm (8-hour TWA)
            "IDLH": None,
        },
        "typical_sources": ["PVC insulation", "wire coatings", "plastic components"],
        "typical_concentrations": {
            "normal_background": 0.0,  # ppm
            "heated_pvc": 0.05,  # ppm
            "electrical_insulation_fault": 0.5,  # ppm
            "burning_wire_insulation": 5.0,  # ppm
        },
    },

    "corona_ozone": {
        "name": "Corona-Generated Ozone",
        "formula": "O3",
        "category": ChemicalCategory.INORGANIC_GAS,
        "molecular_weight": 48.00,  # g/mol
        "diffusion_coefficient": 0.165e-4,  # m²/s in air at 25°C
        "density": 1.96,  # kg/m³ (gas)
        "air_density_ratio": 1.65,  # ratio to air density
        "volatility": 1.0,  # 0-1 scale
        "reactivity": 0.9,  # 0-1 scale (highly reactive)
        "settling_velocity": 0.0,  # m/s (gas doesn't settle)
        "deposition_rate": 0.01,  # fraction deposited per second (higher than ambient ozone due to reactivity)
        "temperature_scaling": {
            "type": "linear",
            "description": "Generated by corona discharge, related to humidity and voltage",
            "reference_curve": [(0, 0.8), (25, 1.0), (50, 1.2)],  # temp in °C, scaling factor
        },
        "humidity_effect": 0.8,  # 0-1 scale (high humidity significantly affects corona discharge)
        "health_data": {
            "odor_threshold": 0.01,  # ppm
            "OSHA_PEL": 0.1,  # ppm (8-hour TWA)
            "NIOSH_CEILING": 0.1,  # ppm (15-min)
            "ACGIH_TLV": 0.05,  # ppm (8-hour TWA)
            "IDLH": 5,  # ppm
        },
        "typical_sources": ["corona discharge", "high-voltage equipment", "transmission lines", "damaged insulators"],
        "typical_concentrations": {
            "normal_background": 0.03,  # ppm
            "near_high_voltage_equipment": 0.1,  # ppm
            "minor_corona_discharge": 0.3,  # ppm
            "severe_insulator_damage": 1.0,  # ppm
        },
    },
}
