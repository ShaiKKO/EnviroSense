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
            base_freq = 60  # Hz (power line frequency)+
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
