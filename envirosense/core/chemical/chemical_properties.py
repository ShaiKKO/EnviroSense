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


class ChemicalCategory(Enum):
    """Categories of chemicals for classification purposes."""
    VOC = auto()              # Volatile Organic Compounds
    INORGANIC_GAS = auto()    # Inorganic gases (CO, CO2, NOx, etc.)
    PARTICULATE = auto()      # Particulate matter (PM2.5, PM10, etc.)
    BIOAEROSOL = auto()       # Biological aerosols (pollen, mold, etc.)
    RADIATION = auto()        # Radiation (radon, etc.)
    SEMI_VOLATILE = auto()    # Semi-volatile organic compounds
    OTHER = auto()            # Other chemicals


# Chemical properties database
# All properties use SI units where applicable
CHEMICAL_PROPERTIES = {
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

    "nitrogen_dioxide": {
        "name": "Nitrogen Dioxide",
        "formula": "NO2",
        "category": ChemicalCategory.INORGANIC_GAS,
        "molecular_weight": 46.01,  # g/mol
        "diffusion_coefficient": 0.14e-4,  # m²/s in air at 25°C
        "density": 1.88,  # kg/m³ (gas)
        "air_density_ratio": 1.58,  # ratio to air density
        "volatility": 1.0,  # 0-1 scale
        "reactivity": 0.8,  # 0-1 scale (highly reactive)
        "settling_velocity": 0.0,  # m/s (gas doesn't settle)
        "deposition_rate": 0.004,  # fraction deposited per second (higher due to reactivity)
        "temperature_scaling": {
            "type": "linear",
            "slope": 0.015,  # fractional increase per °C
            "reference_temp": 25.0,  # °C
        },
        "humidity_effect": 0.3,  # 0-1 scale (forms nitric acid with water)
        "health_data": {
            "odor_threshold": 0.1,  # ppm
            "OSHA_PEL": 5,  # ppm (ceiling)
            "NIOSH_REL": 1,  # ppm (15-min)
            "ACGIH_TLV": 0.2,  # ppm (8-hour TWA)
            "EPA_NAAQS": 0.053,  # ppm (annual average)
            "IDLH": 20,  # ppm
        },
        "typical_sources": ["vehicle exhaust", "power plants", "gas stoves", "heaters"],
        "typical_concentrations": {
            "outdoor_urban": 0.02,  # ppm average
            "outdoor_high_traffic": 0.05,  # ppm average
            "indoor_residential": 0.01,  # ppm average
            "indoor_with_gas_stove": 0.04,  # ppm average
        },
    },

    "ozone": {
        "name": "Ozone",
        "formula": "O3",
        "category": ChemicalCategory.INORGANIC_GAS,
        "molecular_weight": 48.00,  # g/mol
        "diffusion_coefficient": 0.165e-4,  # m²/s in air at 25°C
        "density": 1.96,  # kg/m³ (gas)
        "air_density_ratio": 1.65,  # ratio to air density
        "volatility": 1.0,  # 0-1 scale
        "reactivity": 0.9,  # 0-1 scale (highly reactive)
        "settling_velocity": 0.0,  # m/s (gas doesn't settle)
        "deposition_rate": 0.005,  # fraction deposited per second
        "temperature_scaling": {
            "type": "complex",
            "description": "Formation increases with temperature and sunlight",
            "reference_curve": [(0, 0.5), (10, 0.7), (20, 1.0), (30, 1.5), (40, 2.0)],  # temp in °C, scaling factor
        },
        "humidity_effect": 0.2,  # 0-1 scale
        "health_data": {
            "odor_threshold": 0.01,  # ppm
            "OSHA_PEL": 0.1,  # ppm (8-hour TWA)
            "NIOSH_CEILING": 0.1,  # ppm (15-min)
            "ACGIH_TLV": 0.05,  # ppm (8-hour TWA)
            "EPA_NAAQS": 0.07,  # ppm (8-hour average)
            "IDLH": 5,  # ppm
        },
        "typical_sources": ["photochemical reactions", "electrical equipment", "air purifiers"],
        "typical_concentrations": {
            "outdoor_urban_summer": 0.05,  # ppm average
            "outdoor_industrial": 0.03,  # ppm average
            "indoor_residential": 0.01,  # ppm average
            "indoor_with_air_purifier": 0.03,  # ppm average
        },
    },

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

    "radon": {
        "name": "Radon",
        "formula": "Rn",
        "category": ChemicalCategory.RADIATION,
        "molecular_weight": 222.0,  # g/mol
        "diffusion_coefficient": 0.12e-4,  # m²/s in air
        "density": 9.73,  # kg/m³ (gas)
        "air_density_ratio": 8.2,  # ratio to air density
        "volatility": 1.0,  # 0-1 scale
        "reactivity": 0.0,  # 0-1 scale (noble gas)
        "settling_velocity": 0.0,  # m/s (gas doesn't settle)
        "deposition_rate": 0.0,  # fraction deposited per second
        "half_life": 3.8235 * 24 * 3600,  # seconds (3.8235 days)
        "temperature_scaling": {
            "type": "moderate",
            "factor": 0.01,  # fractional change per °C
        },
        "humidity_effect": 0.1,  # 0-1 scale
        "health_data": {
            "EPA_action_level": 4,  # pCi/L
            "WHO_reference_level": 2.7,  # pCi/L (100 Bq/m³)
        },
        "typical_sources": ["soil", "building materials", "well water"],
        "typical_concentrations": {
            "outdoor": 0.4,  # pCi/L average
            "indoor_residential_us_avg": 1.3,  # pCi/L average
            "indoor_high_risk_areas": 4.0,  # pCi/L average
        },
    },

    "toluene": {
        "name": "Toluene",
        "formula": "C7H8",
        "category": ChemicalCategory.VOC,
        "molecular_weight": 92.14,  # g/mol
        "diffusion_coefficient": 0.085e-4,  # m²/s in air at 25°C
        "density": 3.83,  # kg/m³ (gas)
        "air_density_ratio": 3.2,  # ratio to air density
        "volatility": 0.65,  # 0-1 scale
        "reactivity": 0.25,  # 0-1 scale
        "settling_velocity": 0.0,  # m/s (gas doesn't settle)
        "deposition_rate": 0.0004,  # fraction deposited per second
        "temperature_scaling": {
            "type": "linear",
            "slope": 0.025,  # fractional increase per °C
            "reference_temp": 25.0,  # °C
        },
        "humidity_effect": 0.15,  # 0-1 scale
        "health_data": {
            "odor_threshold": 1.0,  # ppm
            "OSHA_PEL": 200,  # ppm (8-hour TWA)
            "OSHA_CEILING": 300,  # ppm
            "NIOSH_REL": 100,  # ppm (8-hour TWA)
            "NIOSH_STEL": 150,  # ppm (15-min)
            "ACGIH_TLV": 20,  # ppm (8-hour TWA)
            "IDLH": 500,  # ppm
        },
        "typical_sources": ["paints", "adhesives", "gasoline", "printing", "leather treatment"],
        "typical_concentrations": {
            "outdoor_urban": 0.003,  # ppm average
            "outdoor_industrial": 0.01,  # ppm average
            "indoor_residential": 0.005,  # ppm average
            "indoor_freshly_painted": 2.0,  # ppm average
        },
    },

    "ethanol": {
        "name": "Ethanol",
        "formula": "C2H5OH",
        "category": ChemicalCategory.VOC,
        "molecular_weight": 46.07,  # g/mol
        "diffusion_coefficient": 0.119e-4,  # m²/s in air at 25°C
        "density": 1.69,  # kg/m³ (gas)
        "air_density_ratio": 1.59,  # ratio to air density
        "volatility": 0.8,  # 0-1 scale
        "reactivity": 0.3,  # 0-1 scale
        "settling_velocity": 0.0,  # m/s (gas doesn't settle)
        "deposition_rate": 0.0008,  # fraction deposited per second
        "temperature_scaling": {
            "type": "linear",
            "slope": 0.03,  # fractional increase per °C
            "reference_temp": 25.0,  # °C
        },
        "humidity_effect": 0.4,  # 0-1 scale (hygroscopic)
        "health_data": {
            "odor_threshold": 10,  # ppm
            "OSHA_PEL": 1000,  # ppm (8-hour TWA)
            "NIOSH_REL": 1000,  # ppm (8-hour TWA)
            "ACGIH_TLV": 1000,  # ppm (8-hour TWA)
            "IDLH": 3300,  # ppm
        },
        "typical_sources": ["alcoholic beverages", "personal care products", "cleaning products", "hand sanitizers"],
        "typical_concentrations": {
            "outdoor": 0.001,  # ppm average
            "indoor_residential": 0.04,  # ppm average
            "indoor_bar": 5.0,  # ppm average
            "indoor_with_sanitizer_use": 10.0,  # ppm average
        },
    },
}


def get_chemical_property(chemical_id, property_path):
    """
    Retrieve a specific property from the chemical database.
    
    Args:
        chemical_id: The identifier of the chemical
        property_path: A dot-separated path to the property 
                       (e.g., "health_data.odor_threshold")
    
    Returns:
        The property value or None if not found
    """
    if chemical_id not in CHEMICAL_PROPERTIES:
        return None
    
    chemical = CHEMICAL_PROPERTIES[chemical_id]
    path_parts = property_path.split(".")
    
    current = chemical
    for part in path_parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    
    return current


def get_chemicals_by_category(category):
    """
    Retrieve all chemicals matching a specific category.
    
    Args:
        category: A ChemicalCategory enum value
    
    Returns:
        Dictionary of chemicals in the specified category
    """
    result = {}
    for chem_id, props in CHEMICAL_PROPERTIES.items():
        if props.get("category") == category:
            result[chem_id] = props
    return result


def get_diffusion_coefficient(chemical_id, temperature=25.0, pressure=101.325):
    """
    Get temperature and pressure adjusted diffusion coefficient.
    
    Args:
        chemical_id: The identifier of the chemical
        temperature: Temperature in Celsius
        pressure: Pressure in kPa
    
    Returns:
        Adjusted diffusion coefficient in m²/s
    """
    base_coefficient = get_chemical_property(chemical_id, "diffusion_coefficient")
    if base_coefficient is None:
        return None
    
    # Fuller-Schettler-Giddings equation simplified for temperature and pressure adjustment
    # D_AB ∝ T^1.75 / P
    temp_k = temperature + 273.15
    reference_temp_k = 298.15  # 25°C in Kelvin
    reference_pressure = 101.325  # kPa
    
    return base_coefficient * ((temp_k / reference_temp_k) ** 1.75) * (reference_pressure / pressure)
