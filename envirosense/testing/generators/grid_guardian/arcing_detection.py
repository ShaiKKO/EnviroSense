"""
Arcing detection generator for Grid Guardian testing

This module provides a data generator for Grid Guardian devices focused on
electrical arcing detection. It produces realistic EMF, acoustic, and thermal 
data that simulate electrical arcing events on power lines and components.
"""

import datetime
import math
import numpy as np
from scipy import ndimage
from typing import Any, Dict, List, Optional, Tuple, Union

from envirosense.testing.framework import DataGenerator, TestScenario


class ArcingDetectionGenerator(DataGenerator):
    """
    Generates realistic electrical arcing signatures for Grid Guardian testing.
    
    This generator produces EMF, acoustic, and thermal data that simulate
    electrical arcing events on power lines and components, based on the
    arcing detection algorithm in Grid Guardian Firmware & Software Spec.
    """
    
    def __init__(self):
        """Initialize the arcing detection generator with default parameters."""
        super().__init__()
        self.parameters.update({
            'baseline_noise': 0.05,  # Normal baseline noise level
            'scenario_intensity': 1.0,  # Scaling factor for arcing intensity
            'emf_sample_rate': 2000,  # Hz
            'acoustic_sample_rate': 44100,  # Hz
            'thermal_resolution': (80, 60),  # Pixels
            'weather_effect': 0.1,  # Weather interference factor
        })
        
        # Arcing signature parameters - sound frequencies, EMF patterns, heat distribution
        self.arcing_signatures = {
            'corona_discharge': {
                'emf_fluctuation': 0.6,  # Moderate EMF fluctuation
                'acoustic_frequencies': [2000, 4000, 8000],  # Hz
                'acoustic_amplitudes': [0.4, 0.6, 0.3],
                'thermal_peak': 10.0,  # Degrees C above ambient
                'thermal_spread': 0.2,  # Spatial spread factor (0-1)
            },
            'loose_connection': {
                'emf_fluctuation': 0.8,  # High EMF fluctuation
                'acoustic_frequencies': [1000, 3000, 6000, 12000],  # Hz
                'acoustic_amplitudes': [0.5, 0.7, 0.4, 0.2],
                'thermal_peak': 30.0,  # Degrees C above ambient
                'thermal_spread': 0.1,  # Focused hot spot
            },
            'insulation_breakdown': {
                'emf_fluctuation': 0.9,  # Very high EMF fluctuation
                'acoustic_frequencies': [1500, 5000, 10000, 15000],  # Hz
                'acoustic_amplitudes': [0.3, 0.8, 0.5, 0.3],
                'thermal_peak': 50.0,  # Degrees C above ambient
                'thermal_spread': 0.15,  # Medium hot spot
            }
        }
        
    def _generate_emf_data(self, 
                         baseline: float, 
                         duration_sec: float,
                         signature_type: str, 
                         intensity: float,
                         add_noise: bool = True) -> Dict[str, Any]:
        """
        Generate EMF (Electromagnetic Field) data for arcing event.
        
        Args:
            baseline: Baseline EMF value (µT)
            duration_sec: Duration of data in seconds
            signature_type: Type of arcing signature
            intensity: Intensity factor (0-1)
            add_noise: Whether to add noise
            
        Returns:
            Dictionary with EMF data
        """
        sample_rate = self.parameters['emf_sample_rate']
        num_samples = int(duration_sec * sample_rate)
        time_points = np.linspace(0, duration_sec, num_samples)
        values = np.ones(num_samples) * baseline
        
        # Get signature parameters
        signature = self.arcing_signatures.get(signature_type)
        if signature:
            # Add arcing EMF pattern - characteristic fluctuations
            fluctuation = signature['emf_fluctuation'] * intensity * baseline
            
            # Create rapid fluctuations with occasional larger spikes
            fluctuation_pattern = np.zeros(num_samples)
            
            # Base fluctuation - fast changes
            base_freq = 60  # Hz (power line frequency)
            fluctuation_pattern += fluctuation * 0.3 * np.sin(2 * np.pi * base_freq * time_points)
            
            # Add harmonics
            for harmonic in [3, 5, 7]:
                harmonic_amp = fluctuation * 0.2 / harmonic
                fluctuation_pattern += harmonic_amp * np.sin(2 * np.pi * base_freq * harmonic * time_points)
            
            # Add random spikes
            num_spikes = int(duration_sec * 5 * intensity)  # 5 spikes per second at full intensity
            for _ in range(num_spikes):
                spike_loc = self.rng.randint(0, num_samples - 1)
                spike_width = self.rng.randint(5, int(sample_rate/50))  # 20ms max spike at low intensity
                spike_amp = fluctuation * (0.5 + self.rng.random())
                
                # Create exponential decay spike
                for i in range(spike_width):
                    if spike_loc + i < num_samples:
                        decay = np.exp(-i / (spike_width/3))
                        fluctuation_pattern[spike_loc + i] += spike_amp * decay
            
            # Add the fluctuations to the baseline
            values += fluctuation_pattern
        
        # Add noise if requested
        if add_noise:
            noise_level = self.parameters['baseline_noise'] * baseline
            noise = self.rng.normal(0, noise_level, num_samples)
            values += noise
        
        # Ensure values are positive
        values = np.maximum(values, 0)
        
        # Create output
        emf_data = {
            'time_points': time_points.tolist(),
            'values': values.tolist(),
            'baseline': baseline,
            'unit': 'µT',
            'sample_rate': sample_rate,
            'statistics': {
                'min': float(np.min(values)),
                'max': float(np.max(values)),
                'mean': float(np.mean(values)),
                'std_dev': float(np.std(values)),
                'fluctuation_intensity': float(np.std(values) / baseline)
            }
        }
        
        return emf_data
    
    def _generate_acoustic_data(self, 
                              duration_sec: float,
                              signature_type: str, 
                              intensity: float,
                              ambient_noise_level: float = 0.1,
                              add_noise: bool = True) -> Dict[str, Any]:
        """
        Generate acoustic data for arcing event.
        
        Args:
            duration_sec: Duration of data in seconds
            signature_type: Type of arcing signature
            intensity: Intensity factor (0-1)
            ambient_noise_level: Background noise level (0-1)
            add_noise: Whether to add noise
            
        Returns:
            Dictionary with acoustic data
        """
        sample_rate = self.parameters['acoustic_sample_rate']
        num_samples = int(duration_sec * sample_rate)
        time_points = np.linspace(0, duration_sec, num_samples)
        values = np.zeros(num_samples)
        
        # Add ambient background noise
        if add_noise:
            ambient_noise = self.rng.normal(0, ambient_noise_level, num_samples)
            values += ambient_noise
        
        # Get signature parameters
        signature = self.arcing_signatures.get(signature_type)
        if signature:
            # Add characteristic frequencies for this arcing type
            freqs = signature['acoustic_frequencies']
            amps = signature['acoustic_amplitudes']
            
            for freq, base_amp in zip(freqs, amps):
                # Scale amplitude by intensity
                amp = base_amp * intensity
                
                # Add this frequency component
                values += amp * np.sin(2 * np.pi * freq * time_points)
                
                # Add some harmonics with decreasing amplitude
                for harmonic in [2, 3]:
                    h_amp = amp * 0.3 / harmonic
                    values += h_amp * np.sin(2 * np.pi * freq * harmonic * time_points)
            
            # Add random crackling/popping - characteristic of arcing
            num_crackles = int(duration_sec * 20 * intensity)  # 20 crackles per second at full intensity
            for _ in range(num_crackles):
                crackle_loc = self.rng.randint(0, num_samples - 1)
                crackle_width = self.rng.randint(10, int(sample_rate/100))  # 10ms max crackle
                crackle_amp = 0.7 * intensity * (0.5 + self.rng.random())
                
                # Create sharp spike with quick decay
                for i in range(crackle_width):
                    if crackle_loc + i < num_samples:
                        decay = np.exp(-i / (crackle_width/2))
                        values[crackle_loc + i] += crackle_amp * decay
        
        # Normalize to range -1 to 1
        max_val = np.max(np.abs(values))
        if max_val > 0:
            values = values / max_val
        
        # Add DC offset to simulate recording bias
        values += 0.05 * self.rng.random()
        
        # Calculate frequency spectrum for analysis
        if num_samples > 0:
            n_fft = min(2048, num_samples)  # Use 2048 points or fewer if signal is shorter
            frequencies = np.fft.rfftfreq(n_fft, 1/sample_rate)
            spectrum = np.abs(np.fft.rfft(values[:n_fft]))
            
            # Find dominant frequencies
            if len(spectrum) > 0:
                # Get top 5 frequencies
                indices = np.argsort(spectrum)[-5:]
                dominant_freqs = [(float(frequencies[i]), float(spectrum[i])) for i in indices]
            else:
                dominant_freqs = []
        else:
            dominant_freqs = []
        
        # Create output
        acoustic_data = {
            'values': values.tolist()[::100],  # Downsample for storage
            'sample_rate': sample_rate,
            'duration': duration_sec,
            'dominant_frequencies': dominant_freqs,
            'statistics': {
                'rms': float(np.sqrt(np.mean(np.square(values)))),
                'peak': float(np.max(np.abs(values)))
            }
        }
        
        return acoustic_data
    
    def _generate_thermal_image(self, 
                              ambient_temp: float,
                              signature_type: str, 
                              intensity: float,
                              add_noise: bool = True) -> Dict[str, Any]:
        """
        Generate thermal image data for arcing event.
        
        Args:
            ambient_temp: Ambient temperature in Celsius
            signature_type: Type of arcing signature
            intensity: Intensity factor (0-1)
            add_noise: Whether to add noise
            
        Returns:
            Dictionary with thermal image data
        """
        # Get thermal image resolution
        height, width = self.parameters['thermal_resolution']
        
        # Create base thermal image at ambient temperature
        image = np.ones((height, width)) * ambient_temp
        
        # Get signature parameters
        signature = self.arcing_signatures.get(signature_type)
        if signature:
            # Create hot spot
            thermal_peak = signature['thermal_peak'] * intensity
            thermal_spread = signature['thermal_spread'] * max(width, height)
            
            # Position hot spot randomly, but not too close to the edge
            margin = int(thermal_spread)
            center_y = self.rng.randint(margin, height - margin) if height > 2*margin else height//2
            center_x = self.rng.randint(margin, width - margin) if width > 2*margin else width//2
            
            # Create Gaussian hot spot
            y_coords, x_coords = np.ogrid[:height, :width]
            dist_from_center = ((y_coords - center_y) ** 2 + (x_coords - center_x) ** 2) ** 0.5
            
            # Apply Gaussian falloff
            falloff = np.exp(-(dist_from_center ** 2) / (2 * thermal_spread ** 2))
            hot_spot = falloff * thermal_peak
            
            # Add hot spot to base image
            image += hot_spot
        
        # Add noise if requested
        if add_noise:
            noise_level = self.parameters['baseline_noise'] * ambient_temp
            noise = self.rng.normal(0, noise_level, (height, width))
            image += noise
        
        # Create output
        thermal_data = {
            'image': image.tolist(),  # Convert to list for JSON serialization
            'ambient_temperature': ambient_temp,
            'resolution': self.parameters['thermal_resolution'],
            'unit': 'C',
            'statistics': {
                'min': float(np.min(image)),
                'max': float(np.max(image)),
                'mean': float(np.mean(image)),
                'std_dev': float(np.std(image)),
                'hot_spot_location': [center_x, center_y] if signature else None,
                'hot_spot_intensity': float(np.max(image) - ambient_temp) if signature else 0.0
            }
        }
        
        return thermal_data
    
    def _analyze_arcing_evidence(self, 
                               emf_data: Dict[str, Any],
                               acoustic_data: Dict[str, Any],
                               thermal_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze sensor data for evidence of electrical arcing.
        
        Args:
            emf_data: EMF sensor data
            acoustic_data: Acoustic sensor data
            thermal_data: Thermal image data
            
        Returns:
            Dictionary with analysis results
        """
        evidence = []
        confidence_factors = []
        
        # Check EMF data for arcing signatures
        emf_stats = emf_data['statistics']
        emf_fluctuation = emf_stats['fluctuation_intensity']
        
        if emf_fluctuation > 0.5:
            evidence.append({
                'type': 'emf',
                'description': 'High EMF fluctuations detected',
                'value': emf_fluctuation,
                'threshold': 0.5,
                'confidence': min(0.9, emf_fluctuation / 2.0)
            })
            confidence_factors.append(min(0.9, emf_fluctuation / 2.0))
        
        # Check acoustic data for arcing frequencies
        if acoustic_data['statistics']['peak'] > 0.7:
            # Check for high frequency components characteristic of arcing
            has_arcing_freqs = False
            for freq, amp in acoustic_data['dominant_frequencies']:
                if freq > 5000 and amp > 0.4:
                    has_arcing_freqs = True
                    break
            
            if has_arcing_freqs:
                evidence.append({
                    'type': 'acoustic',
                    'description': 'Arcing frequency signature detected',
                    'peak_amplitude': acoustic_data['statistics']['peak'],
                    'high_freq_components': [f for f, a in acoustic_data['dominant_frequencies'] if f > 5000],
                    'confidence': 0.7
                })
                confidence_factors.append(0.7)
        
        # Check thermal data for hot spots
        thermal_stats = thermal_data['statistics']
        temp_range = thermal_stats['max'] - thermal_stats['ambient_temperature']
        
        if temp_range > 15.0:  # More than 15°C above ambient
            evidence.append({
                'type': 'thermal',
                'description': 'Thermal hot spot detected',
                'temperature_delta': temp_range,
                'threshold': 15.0,
                'hot_spot_location': thermal_stats['hot_spot_location'],
                'confidence': min(0.85, temp_range / 50.0)
            })
            confidence_factors.append(min(0.85, temp_range / 50.0))
        
        # Calculate overall arcing probability
        if evidence:
            # Weight EMF evidence most heavily, then thermal, then acoustic
            weights = {'emf': 0.5, 'thermal': 0.3, 'acoustic': 0.2}
            
            # Calculate weighted probability
            total_weight = 0
            weighted_prob = 0
            
            for e in evidence:
                evidence_type = e['type']
                weight = weights.get(evidence_type, 0.1)
                weighted_prob += e['confidence'] * weight
                total_weight += weight
            
            if total_weight > 0:
                arcing_probability = weighted_prob / total_weight
            else:
                arcing_probability = 0.0
                
            # Determine arcing type based on evidence
            arcing_type = None
            if emf_fluctuation > 0.8 and temp_range > 40:
                arcing_type = 'insulation_breakdown'
            elif emf_fluctuation > 0.7 and temp_range > 20:
                arcing_type = 'loose_connection'
            elif emf_fluctuation > 0.5:
                arcing_type = 'corona_discharge'
        else:
            arcing_probability = 0.0
            arcing_type = None
        
        # Return analysis results
        return {
            'arcing_detected': len(evidence) > 0,
            'arcing_probability': arcing_probability if 'arcing_probability' in locals() else 0.0,
            'arcing_type': arcing_type,
            'evidence': evidence,
            'recommendation': 'Maintenance required' if arcing_probability > 0.7 else
                             'Schedule inspection' if arcing_probability > 0.4 else
                             'Normal operation'
        }
    
    def generate(self, scenario: TestScenario, **kwargs) -> Dict[str, Any]:
        """
        Generate arcing detection test data.
        
        Args:
            scenario: Test scenario to generate data for
            **kwargs: Additional parameters
            
        Returns:
            Generated sensor data and analysis results
        """
        # Get scenario parameters
        arcing_type = scenario.parameters.get('arcing_type', 'corona_discharge')
        intensity = scenario.parameters.get('arcing_intensity', 
                                          self.parameters['scenario_intensity'])
        duration = scenario.parameters.get('duration_sec', 2.0)
        ambient_temp = scenario.parameters.get('ambient_temperature', 25.0)
        baseline_emf = scenario.parameters.get('baseline_emf', 0.1)  # µT
        
        # Apply weather effects if specified
        weather_interference = 0.0
        if 'weather_condition' in scenario.parameters:
            weather = scenario.parameters['weather_condition']
            if weather in ['rain', 'snow', 'thunderstorm']:
                weather_interference = self.parameters['weather_effect']
                if weather == 'thunderstorm':
                    weather_interference *= 2.0
        
        # Generate EMF data
        emf_data = self._generate_emf_data(
            baseline=baseline_emf,
            duration_sec=duration,
            signature_type=arcing_type,
            intensity=intensity * (1.0 - weather_interference)
        )
        
        # Generate acoustic data
        acoustic_data = self._generate_acoustic_data(
            duration_sec=duration,
            signature_type=arcing_type,
            intensity=intensity * (1.0 - weather_interference / 2),  # Less affected by weather
            ambient_noise_level=0.1 + 0.3 * weather_interference  # More noise in bad weather
        )
        
        # Generate thermal image
        thermal_data = self._generate_thermal_image(
            ambient_temp=ambient_temp,
            signature_type=arcing_type,
            intensity=intensity  # Barely affected by weather
        )
        
        # Analyze the data for arcing evidence
        analysis = self._analyze_arcing_evidence(emf_data, acoustic_data, thermal_data)
        
        # Format final output
        output = {
            'timestamp': datetime.datetime.now().isoformat(),
            'sensor_data': {
                'emf': emf_data,
                'acoustic': acoustic_data,
                'thermal': thermal_data
            },
            'environmental_context': {
                'temperature': ambient_temp,
                'weather_condition': scenario.parameters.get('weather_condition', 'clear'),
                'weather_interference': weather_interference
            },
            'analysis': analysis
        }
        
        return output
