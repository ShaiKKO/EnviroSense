"""
Fire precursor generator for Grid Guardian testing

This module provides a data generator for Grid Guardian devices focused on
fire precursor detection. It produces realistic VOC (Volatile Organic Compounds)
sensor readings that simulate various fire precursor conditions.
"""

import datetime
import math
import numpy as np
from typing import Any, Dict, List, Optional, Tuple, Union

from envirosense.testing.framework import DataGenerator, TestScenario


# Constants for Grid Guardian VOC sensor channels and thresholds
# Based on section 5.1.1 of Grid Guardian Firmware & Software Technical Specification
THRESHOLD_FORMALDEHYDE = 25  # ppb
THRESHOLD_ACETALDEHYDE = 30  # ppb
THRESHOLD_ACROLEIN = 5  # ppb
THRESHOLD_PHENOL = 20  # ppb
THRESHOLD_CRESOL = 15  # ppb
THRESHOLD_GUAIACOL = 10  # ppb
THRESHOLD_CO = 5  # ppm
THRESHOLD_NO2 = 100  # ppb

# Expected compound ratios
EXPECTED_RATIO_1_MIN = 0.8  # Formaldehyde to Acetaldehyde ratio min
EXPECTED_RATIO_1_MAX = 1.2  # Formaldehyde to Acetaldehyde ratio max
EXPECTED_RATIO_2_MIN = 40   # CO to NO2 ratio min
EXPECTED_RATIO_2_MAX = 60   # CO to NO2 ratio max

# Scoring weights
WEIGHT_CELLULOSE = 30  # Score for cellulose decomposition pattern
WEIGHT_LIGNIN = 25  # Score for lignin decomposition pattern
WEIGHT_COMBUSTION = 40  # Score for early combustion pattern
WEIGHT_RATIO_1 = 15  # Score for ratio 1 match
WEIGHT_RATIO_2 = 15  # Score for ratio 2 match
MAX_PYROLYSIS_SCORE = 125  # Maximum possible score


class FirePrecursorGenerator(DataGenerator):
    """
    Generates realistic fire precursor chemical signatures for Grid Guardian testing.
    
    This generator produces VOC (Volatile Organic Compounds) sensor readings that
    simulate various fire precursor conditions, including pyrolysis products
    from different materials like cellulose and lignin.
    """
    
    def __init__(self):
        """Initialize the fire precursor generator with default parameters."""
        super().__init__()
        self.parameters.update({
            'baseline_noise': 0.1,  # Normal baseline noise (fraction of threshold)
            'temperature_effect': 0.05,  # % increase per degree C above 25C
            'humidity_effect': -0.02,  # % change per % RH above 50%
            'scenario_intensity': 1.0,  # Scaling factor for precursor intensity
        })
        
        # VOC channel definitions with baseline values
        self.voc_channels = {
            'FORMALDEHYDE': {'baseline': 5.0, 'threshold': THRESHOLD_FORMALDEHYDE, 'unit': 'ppb'},
            'ACETALDEHYDE': {'baseline': 6.0, 'threshold': THRESHOLD_ACETALDEHYDE, 'unit': 'ppb'},
            'ACROLEIN': {'baseline': 0.5, 'threshold': THRESHOLD_ACROLEIN, 'unit': 'ppb'},
            'PHENOL': {'baseline': 2.0, 'threshold': THRESHOLD_PHENOL, 'unit': 'ppb'},
            'CRESOL': {'baseline': 1.5, 'threshold': THRESHOLD_CRESOL, 'unit': 'ppb'},
            'GUAIACOL': {'baseline': 1.0, 'threshold': THRESHOLD_GUAIACOL, 'unit': 'ppb'},
            'CO': {'baseline': 0.5, 'threshold': THRESHOLD_CO, 'unit': 'ppm'},
            'NO2': {'baseline': 10.0, 'threshold': THRESHOLD_NO2, 'unit': 'ppb'}
        }
        
        # Fire precursor patterns
        self.patterns = {
            'cellulose_decomposition': {
                'FORMALDEHYDE': 2.0,  # Multiplier over threshold
                'ACETALDEHYDE': 1.8,
                'ACROLEIN': 2.5
            },
            'lignin_decomposition': {
                'PHENOL': 1.9,
                'CRESOL': 2.2,
                'GUAIACOL': 3.0
            },
            'early_combustion': {
                'CO': 2.0,
                'NO2': 1.6
            }
        }
        
    def _add_environmental_effects(self, 
                                readings: Dict[str, float], 
                                temperature: float, 
                                humidity: float) -> Dict[str, float]:
        """
        Apply environmental effects to readings.
        
        Args:
            readings: VOC readings to adjust
            temperature: Ambient temperature in Celsius
            humidity: Relative humidity in %
            
        Returns:
            Adjusted VOC readings
        """
        adjusted = {}
        
        # Calculate adjustment factors
        temp_factor = 1.0 + self.parameters['temperature_effect'] * (temperature - 25.0)
        temp_factor = max(0.5, min(2.0, temp_factor))  # Limit to reasonable range
        
        humid_factor = 1.0 + self.parameters['humidity_effect'] * (humidity - 50.0)
        humid_factor = max(0.5, min(1.5, humid_factor))  # Limit to reasonable range
        
        # Apply adjustments to each channel
        for channel, value in readings.items():
            adjusted[channel] = value * temp_factor * humid_factor
            
        return adjusted
    
    def _add_noise(self, readings: Dict[str, float]) -> Dict[str, float]:
        """
        Add realistic noise to readings.
        
        Args:
            readings: VOC readings to add noise to
            
        Returns:
            Readings with noise added
        """
        result = {}
        
        for channel, value in readings.items():
            channel_info = self.voc_channels[channel]
            noise_scale = channel_info['threshold'] * self.parameters['baseline_noise']
            noise = self.rng.normalvariate(0, noise_scale)
            
            # Ensure value doesn't go negative
            result[channel] = max(0, value + noise)
            
        return result
    
    def _apply_pattern(self, 
                     baseline: Dict[str, float], 
                     pattern_name: str, 
                     intensity: float) -> Dict[str, float]:
        """
        Apply a fire precursor pattern to baseline readings.
        
        Args:
            baseline: Baseline readings to modify
            pattern_name: Name of pattern to apply
            intensity: Intensity factor (0.0 to 1.0+)
            
        Returns:
            Modified readings with pattern applied
        """
        result = baseline.copy()
        
        if pattern_name in self.patterns:
            pattern = self.patterns[pattern_name]
            
            for channel, factor in pattern.items():
                threshold = self.voc_channels[channel]['threshold']
                baseline_value = baseline[channel]
                
                # Calculate increase based on pattern and intensity
                increase = (threshold * factor - baseline_value) * intensity
                
                # Apply the increase
                result[channel] = baseline_value + increase
        
        return result
    
    def calculate_pyrolysis_score(self, readings: Dict[str, float]) -> Dict[str, Any]:
        """
        Calculate pyrolysis score based on VOC readings.
        
        Args:
            readings: VOC readings to analyze
            
        Returns:
            Dictionary with score details
        """
        score = 0
        detected_compounds = []
        evidence = []
        
        # Check for cellulose decomposition pattern
        if (readings['FORMALDEHYDE'] > THRESHOLD_FORMALDEHYDE and
            readings['ACETALDEHYDE'] > THRESHOLD_ACETALDEHYDE and
            readings['ACROLEIN'] > THRESHOLD_ACROLEIN):
            score += WEIGHT_CELLULOSE
            detected_compounds.append("cellulose_decomposition")
            evidence.append({
                "type": "chemical_signature",
                "description": "Cellulose decomposition products detected",
                "compounds": ["FORMALDEHYDE", "ACETALDEHYDE", "ACROLEIN"],
                "values": {
                    "FORMALDEHYDE": readings['FORMALDEHYDE'],
                    "ACETALDEHYDE": readings['ACETALDEHYDE'],
                    "ACROLEIN": readings['ACROLEIN']
                }
            })
        
        # Check for lignin decomposition pattern
        if (readings['PHENOL'] > THRESHOLD_PHENOL and
            readings['CRESOL'] > THRESHOLD_CRESOL and
            readings['GUAIACOL'] > THRESHOLD_GUAIACOL):
            score += WEIGHT_LIGNIN
            detected_compounds.append("lignin_decomposition")
            evidence.append({
                "type": "chemical_signature",
                "description": "Lignin decomposition products detected",
                "compounds": ["PHENOL", "CRESOL", "GUAIACOL"],
                "values": {
                    "PHENOL": readings['PHENOL'],
                    "CRESOL": readings['CRESOL'],
                    "GUAIACOL": readings['GUAIACOL']
                }
            })
        
        # Check for early combustion pattern
        if (readings['CO'] > THRESHOLD_CO and
            readings['NO2'] > THRESHOLD_NO2):
            score += WEIGHT_COMBUSTION
            detected_compounds.append("early_combustion")
            evidence.append({
                "type": "chemical_signature",
                "description": "Early combustion products detected",
                "compounds": ["CO", "NO2"],
                "values": {
                    "CO": readings['CO'],
                    "NO2": readings['NO2']
                }
            })
        
        # Check compound ratios
        ratio_1 = readings['FORMALDEHYDE'] / readings['ACETALDEHYDE'] if readings['ACETALDEHYDE'] > 0 else 0
        if EXPECTED_RATIO_1_MIN <= ratio_1 <= EXPECTED_RATIO_1_MAX:
            score += WEIGHT_RATIO_1
            evidence.append({
                "type": "compound_ratio",
                "description": "FORMALDEHYDE/ACETALDEHYDE ratio in expected range",
                "value": ratio_1,
                "expected_range": [EXPECTED_RATIO_1_MIN, EXPECTED_RATIO_1_MAX]
            })
        
        ratio_2 = readings['CO'] / readings['NO2'] if readings['NO2'] > 0 else 0
        if EXPECTED_RATIO_2_MIN <= ratio_2 <= EXPECTED_RATIO_2_MAX:
            score += WEIGHT_RATIO_2
            evidence.append({
                "type": "compound_ratio",
                "description": "CO/NO2 ratio in expected range",
                "value": ratio_2,
                "expected_range": [EXPECTED_RATIO_2_MIN, EXPECTED_RATIO_2_MAX]
            })
        
        # Calculate final probability and confidence
        probability = min(1.0, score / MAX_PYROLYSIS_SCORE)
        
        # Calculate confidence based on evidence strength
        if len(evidence) == 0:
            confidence = 0.0
        else:
            # More evidence types gives higher confidence
            unique_evidence_types = len(set(e["type"] for e in evidence))
            confidence = min(0.95, 0.4 + 0.2 * unique_evidence_types)
        
        # Return final analysis
        return {
            "score": score,
            "probability": probability,
            "confidence": confidence,
            "detected_compounds": detected_compounds,
            "evidence": evidence
        }
    
    def generate(self, scenario: TestScenario, **kwargs) -> Dict[str, Any]:
        """
        Generate fire precursor test data.
        
        Args:
            scenario: Test scenario to generate data for
            **kwargs: Additional parameters
            
        Returns:
            Generated VOC readings and analysis results
        """
        # Get environmental parameters
        temperature = scenario.parameters.get('ambient_temperature', 25.0)
        humidity = scenario.parameters.get('relative_humidity', 50.0)
        intensity = scenario.parameters.get('fire_precursor_intensity', 
                                           self.parameters['scenario_intensity'])
        
        # Get active patterns
        active_patterns = []
        for pattern in self.patterns.keys():
            if scenario.parameters.get(f'{pattern}_active', False):
                active_patterns.append(pattern)
        
        # Start with baseline readings
        readings = {channel: info['baseline'] for channel, info in self.voc_channels.items()}
        
        # Apply each active pattern
        for pattern in active_patterns:
            pattern_intensity = scenario.parameters.get(f'{pattern}_intensity', intensity)
            readings = self._apply_pattern(readings, pattern, pattern_intensity)
        
        # Apply environmental effects
        readings = self._add_environmental_effects(readings, temperature, humidity)
        
        # Add noise
        readings = self._add_noise(readings)
        
        # Calculate pyrolysis score
        analysis = self.calculate_pyrolysis_score(readings)
        
        # Format final output
        output = {
            'timestamp': datetime.datetime.now().isoformat(),
            'readings': {
                channel: {
                    'value': value, 
                    'unit': self.voc_channels[channel]['unit'],
                    'threshold': self.voc_channels[channel]['threshold']
                } 
                for channel, value in readings.items()
            },
            'environmental_context': {
                'temperature': temperature,
                'humidity': humidity
            },
            'analysis': analysis
        }
        
        return output
