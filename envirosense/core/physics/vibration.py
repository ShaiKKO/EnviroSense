"""
EnviroSense Physics Engine - Vibration Propagation Modeling

This module provides classes and functions for modeling vibration propagation
from utility infrastructure components such as transformers, motors, generators,
and other industrial equipment. It implements multiple vibration source models,
material-dependent propagation, and frequency-based analysis.

Classes:
    VibrationSource: Base class for vibration sources
    TransformerVibration: Models vibration signature of transformers
    MotorVibration: Models vibration signature of electric motors
    GeneratorVibration: Models vibration signature of generators
    CompressorVibration: Models vibration signature of compressors
    VibrationPropagation: Models how vibrations propagate through materials
    VibrationProfile: Manages multiple sources and their composite effects
    VibrationVisualizer: Provides visualization tools for vibration signals
"""

import numpy as np
from scipy import signal, integrate, interpolate
import matplotlib.pyplot as plt
from matplotlib import cm
import time
from typing import Tuple, List, Dict, Optional, Union, Any
from abc import ABC, abstractmethod

from envirosense.core.physics.coordinates import Vector3D

# Constants
EARTH_GRAVITY = 9.81  # Earth's gravity in m/s²


class VibrationSource(ABC):
    """
    Abstract base class for all vibration sources.
    
    Attributes:
        name (str): Unique identifier for the source
        position (Vector3D): 3D position of the source
        enabled (bool): Whether the source is currently active
        amplitude (float): Vibration amplitude in m/s²
        sample_rate (int): Sample rate for vibration signal generation in Hz
    """
    
    def __init__(self, name: str,
                position: Tuple[float, float, float],
                amplitude: float,
                sample_rate: int = 1000):
        """
        Initialize a vibration source.
        
        Args:
            name: Unique identifier for the source
            position: 3D coordinates (x, y, z) of the source in meters
            amplitude: Vibration amplitude in m/s²
            sample_rate: Sample rate for signal generation in Hz (default: 1000)
        """
        self.name = name
        self.position = Vector3D(*position)
        self.enabled = True
        self.amplitude = max(0.0, amplitude)
        self.sample_rate = sample_rate
    
    @abstractmethod
    def generate_spectrum(self, freq_range: Tuple[float, float, int]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate the frequency spectrum for this vibration source.
        
        Args:
            freq_range: Tuple of (min_freq, max_freq, num_points) in Hz
            
        Returns:
            Tuple of (frequencies, amplitudes)
        """
        pass
    
    @abstractmethod
    def generate_time_signal(self, duration: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate a time-domain signal of the vibration source.
        
        Args:
            duration: Signal duration in seconds
            
        Returns:
            Tuple of (time_points, amplitude_values)
        """
        pass
    
    def calculate_amplitude_at(self, 
                             position: Tuple[float, float, float], 
                             material_damping: float = 0.05) -> float:
        """
        Calculate vibration amplitude at a specified position.
        
        Args:
            position: 3D coordinates (x, y, z) to calculate amplitude at
            material_damping: Damping coefficient for the propagation medium
            
        Returns:
            Vibration amplitude in m/s²
        """
        if not self.enabled or self.amplitude <= 0:
            return 0.0
        
        # Calculate distance from source to position
        pos = Vector3D(*position)
        distance = (pos - self.position).magnitude()
        
        # Avoid division by zero
        if distance < 0.1:
            distance = 0.1
            
        # Calculate amplitude using damped propagation model
        # A = A₀ × e^(-α×r) / r
        # where A₀ is source amplitude, α is damping coefficient, r is distance
            
        attenuation = np.exp(-material_damping * distance) / distance
        
        return self.amplitude * attenuation
    
    @property
    @abstractmethod
    def source_type(self) -> str:
        """Return the type of vibration source."""
        pass
    
    def enable(self):
        """Enable this vibration source."""
        self.enabled = True
        
    def disable(self):
        """Disable this vibration source."""
        self.enabled = False


class TransformerVibration(VibrationSource):
    """
    Models vibration signature of transformers.
    
    Attributes:
        name (str): Unique identifier for the source
        position (Vector3D): 3D position of the transformer
        power_rating (float): Power rating in VA
        fundamental_freq (float): Fundamental frequency in Hz (typically 120 Hz)
        load_factor (float): Current load factor (0-1)
        condition (str): Operating condition of the transformer
    """
    
    # Condition constants
    CONDITION_NORMAL = "normal"
    CONDITION_OVERLOADED = "overloaded"
    CONDITION_LOOSE_COMPONENTS = "loose_components"
    CONDITION_COOLING_ISSUE = "cooling_issue"
    CONDITION_AGING = "aging"
    
    def __init__(self, name: str,
                position: Tuple[float, float, float],
                power_rating: float,
                fundamental_freq: float = 120.0,  # 60Hz power -> 120Hz vibration
                load_factor: float = 0.7,
                condition: str = CONDITION_NORMAL):
        """
        Initialize a transformer vibration source.
        
        Args:
            name: Unique identifier for the source
            position: 3D coordinates (x, y, z) of the transformer in meters
            power_rating: Power rating in VA
            fundamental_freq: Fundamental frequency in Hz (default: 120.0)
            load_factor: Current load factor 0-1 (default: 0.7)
            condition: Operating condition (default: CONDITION_NORMAL)
        """
        # Calculate base amplitude based on power rating and empirical formula
        # Transformers typically have vibration levels of 0.05 to 0.5 m/s²
        mva = power_rating / 1e6
        if mva < 0.001:  # Small transformer
            base_amplitude = 0.05 + 0.2 * np.log10(1000 * mva + 1)
        else:  # Large transformer
            base_amplitude = 0.2 + 0.3 * np.log10(mva * 10)
        
        # Apply load factor
        amplitude = base_amplitude * (0.3 + 0.7 * load_factor)
        
        super().__init__(name, position, amplitude, 1000)
        
        self.power_rating = power_rating
        self.fundamental_freq = fundamental_freq
        self.load_factor = min(1.0, max(0.0, load_factor))
        
        if condition not in [self.CONDITION_NORMAL, self.CONDITION_OVERLOADED,
                          self.CONDITION_LOOSE_COMPONENTS, self.CONDITION_COOLING_ISSUE,
                          self.CONDITION_AGING]:
            condition = self.CONDITION_NORMAL
            
        self.condition = condition
        
        # Pre-compute the harmonic profile based on condition
        self._harmonic_profile = self._create_harmonic_profile()
    
    @property
    def source_type(self) -> str:
        return "transformer_vibration"
    
    def set_load_factor(self, load_factor: float):
        """
        Update the transformer's load factor and recalculate amplitude.
        
        Args:
            load_factor: New load factor (0-1)
        """
        self.load_factor = min(1.0, max(0.0, load_factor))
        
        # Recalculate amplitude based on load factor
        mva = self.power_rating / 1e6
        if mva < 0.001:
            base_amplitude = 0.05 + 0.2 * np.log10(1000 * mva + 1)
        else:
            base_amplitude = 0.2 + 0.3 * np.log10(mva * 10)
        
        # Apply load factor - higher loads cause higher vibration
        self.amplitude = base_amplitude * (0.3 + 0.7 * self.load_factor)
        
        # Add extra amplitude for overloaded condition
        if self.condition == self.CONDITION_OVERLOADED:
            self.amplitude *= 1.5
    
    def set_condition(self, condition: str):
        """
        Update the transformer's condition and related vibration characteristics.
        
        Args:
            condition: New operating condition
        """
        if condition not in [self.CONDITION_NORMAL, self.CONDITION_OVERLOADED,
                          self.CONDITION_LOOSE_COMPONENTS, self.CONDITION_COOLING_ISSUE,
                          self.CONDITION_AGING]:
            return
            
        self.condition = condition
        
        # Update amplitude based on condition
        if condition == self.CONDITION_OVERLOADED:
            self.amplitude *= 1.5
        elif condition == self.CONDITION_LOOSE_COMPONENTS:
            self.amplitude *= 1.8
        elif condition == self.CONDITION_AGING:
            self.amplitude *= 1.2
        
        # Update harmonic profile
        self._harmonic_profile = self._create_harmonic_profile()
    
    def _create_harmonic_profile(self) -> Dict[int, float]:
        """
        Create a harmonic profile based on transformer condition.
        
        Returns:
            Dictionary mapping harmonic number to relative amplitude
        """
        # Initialize with default harmonics for transformer
        # Transformers typically have strong 2nd harmonic (120Hz) and even harmonics
        harmonics = {
            1: 1.0,    # Fundamental (typically 120 Hz)
            2: 0.5,    # 240 Hz
            3: 0.1,    # 360 Hz
            4: 0.3,    # 480 Hz
            6: 0.1,    # 720 Hz
            8: 0.05    # 960 Hz
        }
        
        # Modify harmonic profile based on condition
        if self.condition == self.CONDITION_OVERLOADED:
            # Overloaded transformers have stronger higher harmonics
            harmonics[2] *= 1.3
            harmonics[4] *= 1.5
            harmonics[6] *= 1.8
            harmonics[8] *= 2.0
            # Add additional harmonics
            harmonics[10] = 0.1
            harmonics[12] = 0.08
            
        elif self.condition == self.CONDITION_LOOSE_COMPONENTS:
            # Loose components create characteristic resonances and subharmonics
            harmonics[1] *= 1.5  # Stronger fundamental
            # Add subharmonics (half-frequency components)
            harmonics[0.5] = 0.4
            # Add sidebands around main harmonics
            harmonics[0.9] = 0.3
            harmonics[1.1] = 0.3
            harmonics[1.9] = 0.25
            harmonics[2.1] = 0.25
            # Add higher frequency resonance
            harmonics[15] = 0.15
            harmonics[16] = 0.12
            
        elif self.condition == self.CONDITION_COOLING_ISSUE:
            # Cooling issues cause fan-related vibrations
            # Add fan blade passing frequencies (assuming 7-blade fan at 1800 RPM)
            # 1800/60 * 7 = 210 Hz
            harmonics[210/self.fundamental_freq] = 0.4  # Fan fundamental
            harmonics[420/self.fundamental_freq] = 0.25  # Fan harmonic
            harmonics[630/self.fundamental_freq] = 0.15  # Fan harmonic
            
        elif self.condition == self.CONDITION_AGING:
            # Aging transformers have broader spectrum
            harmonics[1] *= 0.9  # Slight decrease in fundamental
            # Increased mid-high frequency components from material degradation
            for i in range(10, 30):
                harmonics[i] = 0.08 * (0.9 ** (i-10))
            # Add specific resonance peaks
            harmonics[7] = 0.15
            harmonics[13] = 0.18
            harmonics[21] = 0.12
        
        return harmonics
    
    def generate_spectrum(self, freq_range: Tuple[float, float, int]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate the frequency spectrum for this transformer vibration.
        
        Args:
            freq_range: Tuple of (min_freq, max_freq, num_points) in Hz
            
        Returns:
            Tuple of (frequencies, amplitudes)
        """
        if not self.enabled:
            return np.linspace(freq_range[0], freq_range[1], freq_range[2]), np.zeros(freq_range[2])
        
        # Create frequency array
        frequencies = np.linspace(freq_range[0], freq_range[1], freq_range[2])
        
        # Initialize amplitudes to small background level
        amplitudes = np.ones_like(frequencies) * 0.001
        
        # Add harmonics based on the source's properties
        for harmonic, amplitude in self._harmonic_profile.items():
            harmonic_freq = harmonic * self.fundamental_freq
            
            if harmonic_freq < freq_range[0] or harmonic_freq > freq_range[1]:
                continue
                
            # Use a narrow Gaussian peak for each harmonic
            peak_width = max(1.0, harmonic_freq * 0.01)  # Width proportional to frequency
            gauss = amplitude * np.exp(-0.5 * ((frequencies - harmonic_freq) / peak_width) ** 2)
            amplitudes += gauss
        
        # Apply overall scaling based on amplitude
        amplitudes *= (self.amplitude / 0.3)  # Normalize to typical amplitude
        
        return frequencies, amplitudes
    
    def generate_time_signal(self, duration: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate a time-domain signal of the transformer vibration.
        
        Args:
            duration: Signal duration in seconds
            
        Returns:
            Tuple of (time_points, amplitude_values)
        """
        if not self.enabled:
            # Return flat line
            time_points = np.linspace(0, duration, int(duration * self.sample_rate))
            return time_points, np.zeros_like(time_points)
        
        # Create time array
        time_points = np.linspace(0, duration, int(duration * self.sample_rate))
        signal_values = np.zeros_like(time_points)
        
        # Add harmonic components
        for harmonic, amplitude in self._harmonic_profile.items():
            harmonic_freq = harmonic * self.fundamental_freq
            # Add sine wave for each harmonic
            signal_values += amplitude * np.sin(2 * np.pi * harmonic_freq * time_points)
        
        # Add some noise based on condition
        noise_level = 0.01
        if self.condition == self.CONDITION_OVERLOADED:
            noise_level = 0.05
        elif self.condition == self.CONDITION_LOOSE_COMPONENTS:
            noise_level = 0.15
        elif self.condition == self.CONDITION_COOLING_ISSUE:
            noise_level = 0.08
        elif self.condition == self.CONDITION_AGING:
            noise_level = 0.1
            
        noise = np.random.normal(0, noise_level, len(time_points))
        signal_values += noise
        
        # Add amplitude modulation for certain conditions
        if self.condition in [self.CONDITION_LOOSE_COMPONENTS, self.CONDITION_AGING]:
            # Add slow amplitude modulation to represent mechanical oscillations
            mod_freq = 5.0  # 5 Hz modulation
            mod_depth = 0.2
            modulation = 1.0 + mod_depth * np.sin(2 * np.pi * mod_freq * time_points)
            signal_values *= modulation
        
        # Normalize signal values to the desired amplitude
        if np.max(np.abs(signal_values)) > 0:
            signal_values = signal_values * (self.amplitude / np.max(np.abs(signal_values)))
        
        return time_points, signal_values


class MotorVibration(VibrationSource):
    """
    Models vibration signature of electric motors.
    
    Attributes:
        name (str): Unique identifier for the source
        position (Vector3D): 3D position of the motor
        power_rating (float): Power rating in watts
        rpm (float): Motor speed in RPM
        num_poles (int): Number of motor poles
        load_factor (float): Current load factor (0-1)
        condition (str): Operating condition of the motor
    """
    
    # Condition constants
    CONDITION_NORMAL = "normal"
    CONDITION_UNBALANCED = "unbalanced"
    CONDITION_MISALIGNED = "misaligned"
    CONDITION_BEARING_WEAR = "bearing_wear"
    CONDITION_ELECTRICAL_ISSUE = "electrical_issue"
    
    def __init__(self, name: str,
                position: Tuple[float, float, float],
                power_rating: float,
                rpm: float,
                num_poles: int = 4,
                load_factor: float = 0.7,
                condition: str = CONDITION_NORMAL):
        """
        Initialize a motor vibration source.
        
        Args:
            name: Unique identifier for the source
            position: 3D coordinates (x, y, z) of the motor in meters
            power_rating: Power rating in watts
            rpm: Motor speed in RPM
            num_poles: Number of motor poles (default: 4)
            load_factor: Current load factor 0-1 (default: 0.7)
            condition: Operating condition (default: CONDITION_NORMAL)
        """
        # Calculate base amplitude based on power rating and empirical formula
        # Motor vibration generally increases with power rating
        # Small motors (~100W) around 0.1 m/s², large motors (50kW+) around 1.0 m/s²
        kw = power_rating / 1000
        base_amplitude = 0.1 + 0.2 * np.log10(kw + 0.1)
        
        # Apply load factor - higher loads cause higher vibration
        amplitude = base_amplitude * (0.4 + 0.6 * load_factor)
        
        super().__init__(name, position, amplitude, 1000)
        
        self.power_rating = power_rating
        self.rpm = rpm
        self.num_poles = num_poles
        self.load_factor = min(1.0, max(0.0, load_factor))
        
        if condition not in [self.CONDITION_NORMAL, self.CONDITION_UNBALANCED,
                          self.CONDITION_MISALIGNED, self.CONDITION_BEARING_WEAR,
                          self.CONDITION_ELECTRICAL_ISSUE]:
            condition = self.CONDITION_NORMAL
            
        self.condition = condition
        
        # Calculate frequencies of interest
        self._calculate_characteristic_frequencies()
        
        # Pre-compute the frequency components based on condition
        self._frequency_components = self._create_frequency_components()
    
    @property
    def source_type(self) -> str:
        return "motor_vibration"
    
    def _calculate_characteristic_frequencies(self):
        """Calculate characteristic frequencies for this motor."""
        # Rotation frequency (Hz)
        self.rotation_freq = self.rpm / 60.0
        
        # Line frequency (Hz) - calculated from poles and RPM
        # f = (RPM * poles) / 120
        self.line_freq = (self.rpm * self.num_poles) / 120.0
        
        # Twice line frequency - often significant in motor vibration
        self.twice_line_freq = 2 * self.line_freq
        
        # Blade/vane passing frequency (if fan/pump attached) - estimate
        # Assume 7 blades as default if attached
        self.blade_passing_freq = self.rotation_freq * 7  # Hz
    
    def set_rpm(self, rpm: float):
        """
        Update the motor RPM and recalculate frequencies.
        
        Args:
            rpm: New motor speed in RPM
        """
        self.rpm = rpm
        
        # Recalculate characteristic frequencies
        self._calculate_characteristic_frequencies()
        
        # Update frequency components
        self._frequency_components = self._create_frequency_components()
    
    def set_load_factor(self, load_factor: float):
        """
        Update the motor's load factor and recalculate amplitude.
        
        Args:
            load_factor: New load factor (0-1)
        """
        self.load_factor = min(1.0, max(0.0, load_factor))
        
        # Recalculate amplitude based on load factor
        kw = self.power_rating / 1000
        base_amplitude = 0.1 + 0.2 * np.log10(kw + 0.1)
        
        # Apply load factor - higher loads cause higher vibration
        self.amplitude = base_amplitude * (0.4 + 0.6 * self.load_factor)
        
        # Add extra amplitude for certain conditions
        if self.condition == self.CONDITION_UNBALANCED:
            self.amplitude *= 1.7
        elif self.condition == self.CONDITION_MISALIGNED:
            self.amplitude *= 1.5
        elif self.condition == self.CONDITION_BEARING_WEAR:
            self.amplitude *= 1.3
    
    def set_condition(self, condition: str):
        """
        Update the motor's condition and related vibration characteristics.
        
        Args:
            condition: New operating condition
        """
        if condition not in [self.CONDITION_NORMAL, self.CONDITION_UNBALANCED,
                          self.CONDITION_MISALIGNED, self.CONDITION_BEARING_WEAR,
                          self.CONDITION_ELECTRICAL_ISSUE]:
            return
            
        self.condition = condition
        
        # Update amplitude based on condition
        self.set_load_factor(self.load_factor)  # This will apply the appropriate multiplier
        
        # Update frequency components
        self._frequency_components = self._create_frequency_components()
    
    def _create_frequency_components(self) -> List[Tuple[float, float]]:
        """
        Create frequency components based on motor condition.
        
        Returns:
            List of tuples (frequency, amplitude)
        """
        components = []
        
        # Add fundamental rotation frequency
        components.append((self.rotation_freq, 0.3))
        
        # Add line frequency component
        components.append((self.line_freq, 0.5))
        
        # Add twice line frequency component - often dominant
        components.append((self.twice_line_freq, 1.0))
        
        # Add some harmonics of rotation frequency
        for i in range(2, 6):
            components.append((self.rotation_freq * i, 0.3 / i))
        
        # Modify or add components based on condition
        if self.condition == self.CONDITION_UNBALANCED:
            # Unbalance causes strong vibration at 1x rotation frequency
            components = [(f, a) if f != self.rotation_freq else (f, 1.5) 
                        for f, a in components]
            
            # Add sidebands around rotation frequency
            components.append((self.rotation_freq * 0.95, 0.2))
            components.append((self.rotation_freq * 1.05, 0.2))
            
        elif self.condition == self.CONDITION_MISALIGNED:
            # Misalignment causes strong vibration at 2x rotation frequency
            # and increased axial vibration (not modeled here)
            components.append((self.rotation_freq * 2, 1.2))
            
            # Also often increases 1x component
            components = [(f, a) if f != self.rotation_freq else (f, 0.8) 
                        for f, a in components]
            
        elif self.condition == self.CONDITION_BEARING_WEAR:
            # Bearing wear creates high-frequency components
            # Add generic bearing frequencies as multiple of rotation frequency
            bearing_freqs = [4.7, 7.6, 10.2, 12.8]  # Typical bearing frequency ratios
            
            for ratio in bearing_freqs:
                components.append((self.rotation_freq * ratio, 0.4))
                
            # Add modulation sidebands
            for ratio in bearing_freqs:
                base_freq = self.rotation_freq * ratio
                components.append((base_freq - self.rotation_freq, 0.2))
                components.append((base_freq + self.rotation_freq, 0.2))
                
            # Add high frequency energy - represented by clusters
            components.append((3000, 0.15))
            components.append((4500, 0.12))
            components.append((6000, 0.08))
            
        elif self.condition == self.CONDITION_ELECTRICAL_ISSUE:
            # Electrical issues often present at line frequency and its harmonics
            # Strengthen line frequency components
            components = [(f, a) if f != self.line_freq else (f, 0.9) 
                        for f, a in components]
            components = [(f, a) if f != self.twice_line_freq else (f, 1.2) 
                        for f, a in components]
            
            # Add higher harmonics of line frequency
            components.append((self.line_freq * 3, 0.5))
            components.append((self.line_freq * 4, 0.3))
            
            # Add sidebands at rotation frequency around line frequency
            components.append((self.line_freq - self.rotation_freq, 0.4))
            components.append((self.line_freq + self.rotation_freq, 0.4))
            components.append((self.twice_line_freq - self.rotation_freq, 0.3))
            components.append((self.twice_line_freq + self.rotation_freq, 0.3))
        
        return components
    
    def generate_spectrum(self, freq_range: Tuple[float, float, int]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate the frequency spectrum for this motor vibration.
        
        Args:
            freq_range: Tuple of (min_freq, max_freq, num_points) in Hz
            
        Returns:
            Tuple of (frequencies, amplitudes)
        """
        if not self.enabled:
            return np.linspace(freq_range[0], freq_range[1], freq_range[2]), np.zeros(freq_range[2])
        
        # Create frequency array
        frequencies = np.linspace(freq_range[0], freq_range[1], freq_range[2])
        
        # Initialize amplitudes to small background level
        amplitudes = np.ones_like(frequencies) * 0.001
        
        # Add spectral components based on motor condition
        for freq, amp in self._frequency_components:
            if freq_range[0] <= freq <= freq_range[1]:
                # Use a narrow peak for each frequency component
                peak_width = max(0.5, freq * 0.01)  # Width proportional to frequency
                gauss = amp * np.exp(-0.5 * ((frequencies - freq) / peak_width) ** 2)
                amplitudes += gauss
        
        # Apply overall scaling based on amplitude
        amplitudes *= (self.amplitude / 0.5)  # Normalize to typical amplitude
        
        return frequencies, amplitudes
    
    def generate_time_signal(self, duration: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate a time-domain signal of the motor vibration.
        
        Args:
            duration: Signal duration in seconds
            
        Returns:
            Tuple of (time_points, amplitude_values)
        """
        if not self.enabled:
            # Return flat line
            time_points = np.linspace(0, duration, int(duration * self.sample_rate))
            return time_points, np.zeros_like(time_points)
        
        # Create time array
        time_points = np.linspace(0, duration, int(duration * self.sample_rate))
        signal_values = np.zeros_like(time_points)
        
        # Add frequency components
        for freq, amp in self._frequency_components:
            # Add sine wave for each component
            # Add random phase to make the signal more realistic
            phase = np.random.uniform(0, 2*np.pi)
            signal_values += amp * np.sin(2 * np.pi * freq * time_points + phase)
        
        # Add appropriate noise based on condition
        noise_level = 0.02
        if self.condition == self.CONDITION_BEARING_WEAR:
            noise_level = 0.15
            # Add high frequency noise for bearing wear
            high_freq_noise = np.random.normal(0, 0.1, len(time_points))
            high_freq_noise = signal.sosfilt(
                signal.butter(4, [1000, 5000], 'bandpass', fs=self.sample_rate, output='sos'),
                high_freq_noise
            )
            signal_values += high_freq_noise
            
        elif self.condition == self.CONDITION_UNBALANCED:
            noise_level = 0.05
            # Modulate with rotation frequency
            mod = 0.15 * np.sin(2 * np.pi * self.rotation_freq * time_points)
            signal_values *= (1 + mod)
            
        elif self.condition == self.CONDITION_ELECTRICAL_ISSUE:
            noise_level = 0.08
            # Add electrical noise - higher frequency components
            electrical_noise = np.random.normal(0, 0.05, len(time_points))
            electrical_noise = signal.sosfilt(
                signal.butter(4, [self.line_freq*2, self.line_freq*10], 'bandpass', fs=self.sample_rate, output='sos'),
                electrical_noise
            )
            signal_values += electrical_noise
        
        # Add base noise
        signal_values += np.random.normal(0, noise_level, len(time_points))
        
      # Normalize signal values to the desired amplitude
        if np.max(np.abs(signal_values)) > 0:
            signal_values = signal_values * (self.amplitude / np.max(np.abs(signal_values)))
        
        return time_points, signal_values


class GeneratorVibration(VibrationSource):
    """
    Models vibration signature of power generators.
    
    Attributes:
        name (str): Unique identifier for the source
        position (Vector3D): 3D position of the generator
        power_rating (float): Power rating in VA
        rpm (float): Generator speed in RPM
        fuel_type (str): Type of fuel (diesel, gas, etc.)
        load_factor (float): Current load factor (0-1)
        condition (str): Operating condition of the generator
    """
    
    # Condition constants
    CONDITION_NORMAL = "normal"
    CONDITION_UNBALANCED = "unbalanced"
    CONDITION_EXHAUST_ISSUE = "exhaust_issue"
    CONDITION_BEARING_WEAR = "bearing_wear"
    CONDITION_FUEL_SYSTEM = "fuel_system_issue"
    
    # Fuel type constants
    FUEL_DIESEL = "diesel"
    FUEL_NATURAL_GAS = "natural_gas"
    FUEL_GASOLINE = "gasoline"
    
    def __init__(self, name: str,
                position: Tuple[float, float, float],
                power_rating: float,
                rpm: float,
                fuel_type: str = FUEL_DIESEL,
                load_factor: float = 0.7,
                condition: str = CONDITION_NORMAL):
        """
        Initialize a generator vibration source.
        
        Args:
            name: Unique identifier for the source
            position: 3D coordinates (x, y, z) of the generator in meters
            power_rating: Power rating in VA
            rpm: Generator speed in RPM
            fuel_type: Type of fuel (default: FUEL_DIESEL)
            load_factor: Current load factor 0-1 (default: 0.7)
            condition: Operating condition (default: CONDITION_NORMAL)
        """
        # Calculate base amplitude based on power rating and fuel type
        # Generally, generators have higher vibration than motors
        kva = power_rating / 1000
        
        # Base amplitude varies by fuel type
        if fuel_type == self.FUEL_DIESEL:
            base_amplitude = 0.3 + 0.4 * np.log10(kva + 0.1)
        elif fuel_type == self.FUEL_NATURAL_GAS:
            base_amplitude = 0.25 + 0.35 * np.log10(kva + 0.1)
        elif fuel_type == self.FUEL_GASOLINE:
            base_amplitude = 0.35 + 0.45 * np.log10(kva + 0.1)
        else:
            fuel_type = self.FUEL_DIESEL
            base_amplitude = 0.3 + 0.4 * np.log10(kva + 0.1)
        
        # Apply load factor - higher loads cause higher vibration
        amplitude = base_amplitude * (0.5 + 0.5 * load_factor)
        
        super().__init__(name, position, amplitude, 1000)
        
        self.power_rating = power_rating
        self.rpm = rpm
        self.fuel_type = fuel_type
        self.load_factor = min(1.0, max(0.0, load_factor))
        
        if condition not in [self.CONDITION_NORMAL, self.CONDITION_UNBALANCED,
                          self.CONDITION_EXHAUST_ISSUE, self.CONDITION_BEARING_WEAR,
                          self.CONDITION_FUEL_SYSTEM]:
            condition = self.CONDITION_NORMAL
            
        self.condition = condition
        
        # Calculate frequencies of interest
        self._calculate_characteristic_frequencies()
        
        # Pre-compute the frequency components based on condition
        self._frequency_components = self._create_frequency_components()
    
    @property
    def source_type(self) -> str:
        return "generator_vibration"
    
    def _calculate_characteristic_frequencies(self):
        """Calculate characteristic frequencies for this generator."""
        # Engine rotation frequency (Hz)
        self.rotation_freq = self.rpm / 60.0
        
        # Firing frequency depends on number of cylinders and engine type
        # Simplified model assuming 4-stroke engine with cylinder count estimated from power
        kva = self.power_rating / 1000
        if kva < 50:
            self.num_cylinders = 4
        elif kva < 200:
            self.num_cylinders = 6
        elif kva < 500:
            self.num_cylinders = 8
        else:
            self.num_cylinders = 12
            
        # For 4-stroke engine: firing_freq = (rpm/60) * (num_cylinders/2)
        self.firing_freq = (self.rpm / 60.0) * (self.num_cylinders / 2.0)
        
        # Frequency of individual cylinder firing
        self.cylinder_freq = self.rotation_freq * 0.5  # Half for 4-stroke
        
        # Exhaust frequency often significant in generators
        self.exhaust_freq = self.firing_freq
        
        # Generator electrical frequency (typically 60Hz in US, 50Hz elsewhere)
        self.electrical_freq = 60.0  # Hz (simplified)
    
    def set_rpm(self, rpm: float):
        """
        Update the generator RPM and recalculate frequencies.
        
        Args:
            rpm: New generator speed in RPM
        """
        self.rpm = rpm
        
        # Recalculate characteristic frequencies
        self._calculate_characteristic_frequencies()
        
        # Update frequency components
        self._frequency_components = self._create_frequency_components()
    
    def set_load_factor(self, load_factor: float):
        """
        Update the generator's load factor and recalculate amplitude.
        
        Args:
            load_factor: New load factor (0-1)
        """
        self.load_factor = min(1.0, max(0.0, load_factor))
        
        # Recalculate amplitude based on load factor
        kva = self.power_rating / 1000
        
        # Base amplitude varies by fuel type
        if self.fuel_type == self.FUEL_DIESEL:
            base_amplitude = 0.3 + 0.4 * np.log10(kva + 0.1)
        elif self.fuel_type == self.FUEL_NATURAL_GAS:
            base_amplitude = 0.25 + 0.35 * np.log10(kva + 0.1)
        else:  # Gasoline or other
            base_amplitude = 0.35 + 0.45 * np.log10(kva + 0.1)
        
        # Apply load factor with condition-based adjustment
        self.amplitude = base_amplitude * (0.5 + 0.5 * self.load_factor)
        
        # Adjust for condition
        if self.condition == self.CONDITION_UNBALANCED:
            self.amplitude *= 1.8
        elif self.condition == self.CONDITION_EXHAUST_ISSUE:
            self.amplitude *= 1.4
        elif self.condition == self.CONDITION_BEARING_WEAR:
            self.amplitude *= 1.3
        elif self.condition == self.CONDITION_FUEL_SYSTEM:
            self.amplitude *= 1.5
    
    def set_condition(self, condition: str):
        """
        Update the generator's condition and related vibration characteristics.
        
        Args:
            condition: New operating condition
        """
        if condition not in [self.CONDITION_NORMAL, self.CONDITION_UNBALANCED,
                          self.CONDITION_EXHAUST_ISSUE, self.CONDITION_BEARING_WEAR,
                          self.CONDITION_FUEL_SYSTEM]:
            return
            
        self.condition = condition
        
        # Update amplitude based on condition - reuse load factor setter
        self.set_load_factor(self.load_factor)
        
        # Update frequency components
        self._frequency_components = self._create_frequency_components()
    
    def _create_frequency_components(self) -> List[Tuple[float, float]]:
        """
        Create frequency components based on generator condition.
        
        Returns:
            List of tuples (frequency, amplitude)
        """
        components = []
        
        # Base components present in all generators
        
        # Add rotation frequency component
        components.append((self.rotation_freq, 0.6))
        
        # Add cylinder frequency
        components.append((self.cylinder_freq, 0.4))
        
        # Add firing frequency - often strong
        components.append((self.firing_freq, 0.8))
        
        # Add electrical frequency
        components.append((self.electrical_freq, 0.3))
        components.append((self.electrical_freq * 2, 0.2))
        
        # Add harmonics of the rotation frequency
        for i in range(2, 6):
            components.append((self.rotation_freq * i, 0.5 / i))
        
        # Modify or add components based on condition
        if self.condition == self.CONDITION_UNBALANCED:
            # Unbalance causes strong vibration at rotation frequency
            components = [(f, a * 2.0) if f == self.rotation_freq else (f, a) 
                        for f, a in components]
            
            # Add stronger harmonics
            components.append((self.rotation_freq * 2, 0.7))
            components.append((self.rotation_freq * 3, 0.4))
            
        elif self.condition == self.CONDITION_EXHAUST_ISSUE:
            # Exhaust issues affect firing and exhaust frequencies
            components.append((self.exhaust_freq, 1.2))
            components.append((self.exhaust_freq * 2, 0.7))
            components.append((self.exhaust_freq * 3, 0.4))
            
            # Add modulation components
            components.append((self.exhaust_freq * 1.05, 0.5))
            components.append((self.exhaust_freq * 0.95, 0.5))
            
        elif self.condition == self.CONDITION_BEARING_WEAR:
            # Similar to motors, but with engine-specific components
            bearing_freqs = [4.7, 7.6, 10.2, 12.8]  # Typical bearing frequency ratios
            
            for ratio in bearing_freqs:
                components.append((self.rotation_freq * ratio, 0.35))
                
            # Add high frequency energy - represented by clusters
            components.append((2000, 0.2))
            components.append((3500, 0.15))
            components.append((5000, 0.1))
            
        elif self.condition == self.CONDITION_FUEL_SYSTEM:
            # Fuel system issues cause combustion irregularities
            # This affects firing frequency and adds randomness
            
            # Modify firing frequency components
            components = [(f, a * 1.5) if f == self.firing_freq else (f, a) 
                        for f, a in components]
            
            # Add irregular combustion components
            for i in range(self.num_cylinders):
                mod_factor = 0.9 + 0.2 * np.random.random()  # Random modulation
                components.append((self.cylinder_freq * mod_factor, 0.3))
        
        # Add fuel-type specific components
        if self.fuel_type == self.FUEL_DIESEL:
            # Diesel engines have characteristic frequencies due to combustion
            components.append((self.firing_freq * 1.5, 0.4))  # Injection component
            components.append((self.firing_freq * 8, 0.15))  # High frequency diesel noise
        
        elif self.fuel_type == self.FUEL_NATURAL_GAS:
            # Natural gas generators tend to have smoother operation
            components.append((self.firing_freq * 0.8, 0.3))  # Gas pressure regulator
            
        elif self.fuel_type == self.FUEL_GASOLINE:
            # Gasoline generators can have carburetor-related frequencies
            components.append((self.firing_freq * 1.2, 0.35))  # Intake component
        
        return components
    
    def generate_spectrum(self, freq_range: Tuple[float, float, int]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate the frequency spectrum for this generator vibration.
        
        Args:
            freq_range: Tuple of (min_freq, max_freq, num_points) in Hz
            
        Returns:
            Tuple of (frequencies, amplitudes)
        """
        if not self.enabled:
            return np.linspace(freq_range[0], freq_range[1], freq_range[2]), np.zeros(freq_range[2])
        
        # Create frequency array
        frequencies = np.linspace(freq_range[0], freq_range[1], freq_range[2])
        
        # Initialize amplitudes to non-zero background level
        amplitudes = np.ones_like(frequencies) * 0.005
        
        # Add spectral components based on generator condition
        for freq, amp in self._frequency_components:
            if freq_range[0] <= freq <= freq_range[1]:
                # Use a narrow peak for each frequency component
                peak_width = max(0.5, freq * 0.02)  # Width proportional to frequency
                gauss = amp * np.exp(-0.5 * ((frequencies - freq) / peak_width) ** 2)
                amplitudes += gauss
        
        # Add broadband noise based on fuel type
        if self.fuel_type == self.FUEL_DIESEL:
            # Diesel has more high-frequency components
            noise_shape = 0.2 * np.exp(-frequencies / 2000)
            amplitudes += noise_shape
            
        elif self.fuel_type == self.FUEL_GASOLINE:
            # Gasoline has mid-range noise
            noise_shape = 0.15 * np.exp(-(frequencies - 1000)**2 / (2*1000**2))
            amplitudes += noise_shape
        
        # Apply overall scaling based on amplitude
        amplitudes *= (self.amplitude / 0.6)  # Normalize to typical amplitude
        
        return frequencies, amplitudes
    
    def generate_time_signal(self, duration: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate a time-domain signal of the generator vibration.
        
        Args:
            duration: Signal duration in seconds
            
        Returns:
            Tuple of (time_points, amplitude_values)
        """
        if not self.enabled:
            # Return flat line
            time_points = np.linspace(0, duration, int(duration * self.sample_rate))
            return time_points, np.zeros_like(time_points)
        
        # Create time array
        time_points = np.linspace(0, duration, int(duration * self.sample_rate))
        signal_values = np.zeros_like(time_points)
        
        # Add frequency components
        for freq, amp in self._frequency_components:
            # Add sine wave for each component
            # Add random phase to make the signal more realistic
            phase = np.random.uniform(0, 2*np.pi)
            signal_values += amp * np.sin(2 * np.pi * freq * time_points + phase)
        
        # Add appropriate noise based on condition and fuel type
        noise_level = 0.05  # Base noise level
        
        if self.condition == self.CONDITION_FUEL_SYSTEM:
            # Add random pulses to simulate combustion irregularities
            num_pulses = int(duration * self.firing_freq * 0.5)  # Reduced frequency of pulses
            for _ in range(num_pulses):
                pos = np.random.randint(0, len(time_points) - int(0.01 * self.sample_rate))
                pulse_width = int(0.01 * self.sample_rate)  # 10ms pulse
                pulse = 0.3 * np.exp(-np.arange(pulse_width) / (0.002 * self.sample_rate))
                signal_values[pos:pos+pulse_width] += pulse
            
            noise_level = 0.1
            
        elif self.condition == self.CONDITION_EXHAUST_ISSUE:
            # Add modulated noise for exhaust issues
            exhaust_mod = 0.2 * np.sin(2 * np.pi * self.exhaust_freq * time_points)
            signal_values *= (1 + exhaust_mod)
            
            # Add specific exhaust resonance
            exhaust_noise = 0.15 * np.sin(2 * np.pi * self.exhaust_freq * 3.5 * time_points)
            signal_values += exhaust_noise
            
            noise_level = 0.08
            
        elif self.condition == self.CONDITION_BEARING_WEAR:
            # Add high frequency components for bearing wear
            bearing_noise = np.random.normal(0, 0.1, len(time_points))
            bearing_noise = signal.sosfilt(
                signal.butter(4, [1000, 6000], 'bandpass', fs=self.sample_rate, output='sos'),
                bearing_noise
            )
            signal_values += bearing_noise
            
            noise_level = 0.12
        
        # Add fuel-specific noise patterns
        if self.fuel_type == self.FUEL_DIESEL:
            # Diesel has distinctive knocking pattern
            diesel_noise = np.random.normal(0, 0.1, len(time_points))
            diesel_noise = signal.sosfilt(
                signal.butter(4, [500, 4000], 'bandpass', fs=self.sample_rate, output='sos'),
                diesel_noise
            )
            # Modulate by firing frequency
            diesel_mod = 0.5 + 0.5 * np.abs(signal.sawtooth(2 * np.pi * self.firing_freq * time_points))
            signal_values += 0.1 * diesel_noise * diesel_mod
            
            noise_level *= 1.2  # Diesel is generally louder
            
        elif self.fuel_type == self.FUEL_GASOLINE:
            # Gasoline has higher frequency components
            gas_noise = np.random.normal(0, 0.08, len(time_points))
            gas_noise = signal.sosfilt(
                signal.butter(4, [800, 3000], 'bandpass', fs=self.sample_rate, output='sos'),
                gas_noise
            )
            signal_values += gas_noise
        
        # Add base noise
        signal_values += np.random.normal(0, noise_level, len(time_points))
        
        # Normalize signal values to the desired amplitude
        if np.max(np.abs(signal_values)) > 0:
            signal_values = signal_values * (self.amplitude / np.max(np.abs(signal_values)))
        
        return time_points, signal_values


class CompressorVibration(VibrationSource):
    """
    Models vibration signature of industrial compressors.
    
    Attributes:
        name (str): Unique identifier for the source
        position (Vector3D): 3D position of the compressor
        power_rating (float): Power rating in watts
        rotation_speed (float): Rotation speed in RPM
        type (str): Type of compressor
        load_factor (float): Current load factor (0-1)
        condition (str): Operating condition of the compressor
    """
    
    # Condition constants
    CONDITION_NORMAL = "normal"
    CONDITION_UNBALANCED = "unbalanced"
    CONDITION_VALVE_ISSUE = "valve_issue"
    CONDITION_BEARING_WEAR = "bearing_wear"
    CONDITION_PRESSURE_ISSUE = "pressure_issue"
    
    # Compressor type constants
    TYPE_RECIPROCATING = "reciprocating"
    TYPE_ROTARY_SCREW = "rotary_screw"
    TYPE_CENTRIFUGAL = "centrifugal"
    TYPE_SCROLL = "scroll"
    
    def __init__(self, name: str,
                position: Tuple[float, float, float],
                power_rating: float,
                rotation_speed: float,
                comp_type: str = TYPE_RECIPROCATING,
                num_cylinders: int = 2,
                load_factor: float = 0.7,
                condition: str = CONDITION_NORMAL):
        """
        Initialize a compressor vibration source.
        
        Args:
            name: Unique identifier for the source
            position: 3D coordinates (x, y, z) of the compressor in meters
            power_rating: Power rating in watts
            rotation_speed: Rotation speed in RPM
            comp_type: Type of compressor (default: TYPE_RECIPROCATING)
            num_cylinders: Number of cylinders for reciprocating compressors (default: 2)
            load_factor: Current load factor 0-1 (default: 0.7)
            condition: Operating condition (default: CONDITION_NORMAL)
        """
        # Calculate base amplitude based on power rating and type
        # Compressor vibration generally increases with power rating
        kw = power_rating / 1000
        
        # Base amplitude varies by compressor type
        if comp_type == self.TYPE_RECIPROCATING:
            base_amplitude = 0.4 + 0.5 * np.log10(kw + 0.1)
        elif comp_type == self.TYPE_ROTARY_SCREW:
            base_amplitude = 0.3 + 0.4 * np.log10(kw + 0.1)
        elif comp_type == self.TYPE_CENTRIFUGAL:
            base_amplitude = 0.2 + 0.35 * np.log10(kw + 0.1)
        elif comp_type == self.TYPE_SCROLL:
            base_amplitude = 0.15 + 0.3 * np.log10(kw + 0.1)
        else:
            comp_type = self.TYPE_RECIPROCATING
            base_amplitude = 0.4 + 0.5 * np.log10(kw + 0.1)
        
        # Apply load factor - higher loads cause higher vibration
        amplitude = base_amplitude * (0.3 + 0.7 * load_factor)
        
        super().__init__(name, position, amplitude, 1000)
        
        self.power_rating = power_rating
        self.rotation_speed = rotation_speed
        self.comp_type = comp_type
        self.num_cylinders = num_cylinders
        self.load_factor = min(1.0, max(0.0, load_factor))
        
        if condition not in [self.CONDITION_NORMAL, self.CONDITION_UNBALANCED,
                          self.CONDITION_VALVE_ISSUE, self.CONDITION_BEARING_WEAR,
                          self.CONDITION_PRESSURE_ISSUE]:
            condition = self.CONDITION_NORMAL
            
        self.condition = condition
        
        # Calculate frequencies of interest
        self._calculate_characteristic_frequencies()
        
        # Pre-compute the frequency components based on condition
        self._frequency_components = self._create_frequency_components()
    
    @property
    def source_type(self) -> str:
        return "compressor_vibration"
    
    def _calculate_characteristic_frequencies(self):
        """Calculate characteristic frequencies for this compressor."""
        # Rotation frequency (Hz)
        self.rotation_freq = self.rotation_speed / 60.0
        
        # Compressor-specific frequencies
        if self.comp_type == self.TYPE_RECIPROCATING:
            # Compression frequency depends on number of cylinders
            # Each cylinder has a compression cycle once per revolution
            self.compression_freq = self.rotation_freq * self.num_cylinders
            
            # Valve frequency - often at harmonics of rotation
            self.valve_freq = self.rotation_freq * 2
            
            # Piston frequency - related to reciprocating mass
            self.piston_freq = self.rotation_freq
            
        elif self.comp_type == self.TYPE_ROTARY_SCREW:
            # For screw compressors, the blade passing frequency is key
            # Typical number of lobes might be 4-6
            num_lobes = 5  # Typical value
            self.blade_passing_freq = self.rotation_freq * num_lobes
            
            # Engagement frequency between male and female rotors
            self.engagement_freq = self.rotation_freq * 1.5
            
        elif self.comp_type == self.TYPE_CENTRIFUGAL:
            # For centrifugal, the impeller blade passing frequency is important
            # Typical number of blades might be 10-20
            num_blades = 12  # Typical value
            self.blade_passing_freq = self.rotation_freq * num_blades
            
            # Vane passing frequency (if inlet guide vanes present)
            self.vane_freq = self.rotation_freq * 7  # Assuming 7 vanes
            
        elif self.comp_type == self.TYPE_SCROLL:
            # Scroll compressors have complex frequency patterns
            # Orbiting scroll frequency
            self.orbiting_freq = self.rotation_freq
            
            # Contact frequency between scrolls
            self.contact_freq = self.rotation_freq * 7  # Approximate value
    
    def set_rotation_speed(self, rotation_speed: float):
        """
        Update the compressor rotation speed and recalculate frequencies.
        
        Args:
            rotation_speed: New rotation speed in RPM
        """
        self.rotation_speed = rotation_speed
        
        # Recalculate characteristic frequencies
        self._calculate_characteristic_frequencies()
        
        # Update frequency components
        self._frequency_components = self._create_frequency_components()
    
    def set_load_factor(self, load_factor: float):
        """
        Update the compressor's load factor and recalculate amplitude.
        
        Args:
            load_factor: New load factor (0-1)
        """
        self.load_factor = min(1.0, max(0.0, load_factor))
        
        # Recalculate amplitude based on load factor
        kw = self.power_rating / 1000
        
        # Base amplitude varies by compressor type
        if self.comp_type == self.TYPE_RECIPROCATING:
            base_amplitude = 0.4 + 0.5 * np.log10(kw + 0.1)
        elif self.comp_type == self.TYPE_ROTARY_SCREW:
            base_amplitude = 0.3 + 0.4 * np.log10(kw + 0.1)
        elif self.comp_type == self.TYPE_CENTRIFUGAL:
            base_amplitude = 0.2 + 0.35 * np.log10(kw + 0.1)
        elif self.comp_type == self.TYPE_SCROLL:
            base_amplitude = 0.15 + 0.3 * np.log10(kw + 0.1)
        
        # Apply load factor - higher loads cause higher vibration
        self.amplitude = base_amplitude * (0.3 + 0.7 * self.load_factor)
        
        # Add extra amplitude for certain conditions
        if self.condition == self.CONDITION_UNBALANCED:
            self.amplitude *= 1.6
        elif self.condition == self.CONDITION_VALVE_ISSUE:
            self.amplitude *= 1.8
        elif self.condition == self.CONDITION_BEARING_WEAR:
            self.amplitude *= 1.4
        elif self.condition == self.CONDITION_PRESSURE_ISSUE:
            self.amplitude *= 1.5
    
    def set_condition(self, condition: str):
        """
        Update the compressor's condition and related vibration characteristics.
        
        Args:
            condition: New operating condition
        """
        if condition not in [self.CONDITION_NORMAL, self.CONDITION_UNBALANCED,
                          self.CONDITION_VALVE_ISSUE, self.CONDITION_BEARING_WEAR,
                          self.CONDITION_PRESSURE_ISSUE]:
            return
            
        self.condition = condition
        
        # Update amplitude based on condition
        self.set_load_factor(self.load_factor)  # This will apply the appropriate multiplier
        
        # Update frequency components
        self._frequency_components = self._create_frequency_components()
    
    def _create_frequency_components(self) -> List[Tuple[float, float]]:
        """
        Create frequency components based on compressor type and condition.
        
        Returns:
            List of tuples (frequency, amplitude)
        """
        components = []
        
        # Add fundamental rotation frequency for all compressor types
        components.append((self.rotation_freq, 0.5))
        
        # Add compressor-type specific components
        if self.comp_type == self.TYPE_RECIPROCATING:
            # Add piston frequency
            components.append((self.piston_freq, 0.7))
            
            # Add compression frequency
            components.append((self.compression_freq, 0.9))
            
            # Add valve frequency
            components.append((self.valve_freq, 0.6))
            
            # Add harmonic components
            for i in range(2, 6):
                components.append((self.rotation_freq * i, 0.4 / i))
                
            # Add harmonics of compression frequency
            for i in range(2, 4):
                components.append((self.compression_freq * i, 0.3 / i))
            
        elif self.comp_type == self.TYPE_ROTARY_SCREW:
            # Add blade passing frequency - typically dominant
            components.append((self.blade_passing_freq, 1.0))
            
            # Add engagement frequency
            components.append((self.engagement_freq, 0.7))
            
            # Add harmonics of rotation
            for i in range(2, 5):
                components.append((self.rotation_freq * i, 0.3 / i))
                
            # Add harmonics of blade passing
            components.append((self.blade_passing_freq * 2, 0.5))
            components.append((self.blade_passing_freq * 3, 0.3))
            
        elif self.comp_type == self.TYPE_CENTRIFUGAL:
            # Add blade passing frequency - typically dominant
            components.append((self.blade_passing_freq, 0.8))
            
           # Add vane frequency if present
            components.append((self.vane_freq, 0.5))
            
            # Add harmonics of rotation
            for i in range(2, 4):
                components.append((self.rotation_freq * i, 0.25 / i))
                
            # Add harmonics of blade passing
            components.append((self.blade_passing_freq * 2, 0.4))
            
        elif self.comp_type == self.TYPE_SCROLL:
            # Add orbiting frequency
            components.append((self.orbiting_freq, 0.6))
            
            # Add contact frequency
            components.append((self.contact_freq, 0.7))
            
            # Add harmonics of orbiting frequency
            for i in range(2, 5):
                components.append((self.orbiting_freq * i, 0.3 / i))
        
        # Modify or add components based on condition
        if self.condition == self.CONDITION_UNBALANCED:
            # Unbalance causes strong vibration at rotation frequency
            components = [(f, a * 2.0) if f == self.rotation_freq else (f, a) 
                        for f, a in components]
            
            # Add stronger harmonics
            components.append((self.rotation_freq * 2, 0.8))
            components.append((self.rotation_freq * 3, 0.5))
            
        elif self.condition == self.CONDITION_VALVE_ISSUE:
            # For reciprocating compressors, valve issues affect valve frequency
            if self.comp_type == self.TYPE_RECIPROCATING:
                # Strengthen valve frequency component
                components = [(f, a * 2.5) if f == self.valve_freq else (f, a) 
                            for f, a in components]
                
                # Add valve impact components
                components.append((self.valve_freq * 1.5, 0.9))
                components.append((self.valve_freq * 2.5, 0.7))
                components.append((self.valve_freq * 3.5, 0.5))
                
                # Add higher frequency components for valve noise
                components.append((1000, 0.3))
                components.append((2000, 0.2))
                components.append((3000, 0.1))
            else:
                # For other compressor types, strengthen higher harmonics
                for i in range(2, 6):
                    components.append((self.rotation_freq * i, 0.6 / i))
            
        elif self.condition == self.CONDITION_BEARING_WEAR:
            # Similar pattern as motors and generators
            bearing_freqs = [4.7, 7.6, 10.2, 12.8]  # Typical bearing frequency ratios
            
            for ratio in bearing_freqs:
                components.append((self.rotation_freq * ratio, 0.4))
                
            # Add high frequency energy - represented by clusters
            components.append((2500, 0.2))
            components.append((4000, 0.15))
            components.append((5500, 0.1))
            
        elif self.condition == self.CONDITION_PRESSURE_ISSUE:
            # Pressure issues affect loading and can cause surging or pulsations
            
            if self.comp_type == self.TYPE_CENTRIFUGAL:
                # For centrifugal, add surge frequency (low frequency pulsation)
                surge_freq = self.rotation_freq * 0.05  # Very low frequency
                components.append((surge_freq, 1.0))
                components.append((surge_freq * 2, 0.6))
                
                # Add blade passing frequency modulation
                components.append((self.blade_passing_freq - surge_freq, 0.4))
                components.append((self.blade_passing_freq + surge_freq, 0.4))
                
            elif self.comp_type == self.TYPE_RECIPROCATING:
                # For reciprocating, add pulsation frequencies
                pulsation_freq = self.compression_freq * 0.8  # Related to discharge pulsation
                components.append((pulsation_freq, 0.9))
                components.append((pulsation_freq * 2, 0.7))
                
                # Add pressure-related harmonics
                components.append((self.compression_freq * 1.5, 0.8))
                components.append((self.compression_freq * 2.5, 0.6))
            
            else:
                # For other types, add general pressure pulsation
                pulse_freq = self.rotation_freq * 0.2
                components.append((pulse_freq, 0.7))
                components.append((self.rotation_freq * 1.5, 0.8))
        
        return components
    
    def generate_spectrum(self, freq_range: Tuple[float, float, int]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate the frequency spectrum for this compressor vibration.
        
        Args:
            freq_range: Tuple of (min_freq, max_freq, num_points) in Hz
            
        Returns:
            Tuple of (frequencies, amplitudes)
        """
        if not self.enabled:
            return np.linspace(freq_range[0], freq_range[1], freq_range[2]), np.zeros(freq_range[2])
        
        # Create frequency array
        frequencies = np.linspace(freq_range[0], freq_range[1], freq_range[2])
        
        # Initialize amplitudes to small background level
        amplitudes = np.ones_like(frequencies) * 0.003
        
        # Add spectral components based on compressor type and condition
        for freq, amp in self._frequency_components:
            if freq_range[0] <= freq <= freq_range[1]:
                # Use a Gaussian peak for each frequency component
                peak_width = max(0.5, freq * 0.02)  # Width proportional to frequency
                gauss = amp * np.exp(-0.5 * ((frequencies - freq) / peak_width) ** 2)
                amplitudes += gauss
        
        # Add compressor-type specific broadband features
        if self.comp_type == self.TYPE_RECIPROCATING:
            # Reciprocating has more low-mid frequency components
            noise_shape = 0.2 * np.exp(-frequencies / 1000)
            amplitudes += noise_shape
            
        elif self.comp_type == self.TYPE_ROTARY_SCREW:
            # Rotary screw has characteristic mid-range noise
            noise_shape = 0.15 * np.exp(-(frequencies - 3000)**2 / (2*2000**2))
            amplitudes += noise_shape
            
        elif self.comp_type == self.TYPE_CENTRIFUGAL:
            # Centrifugal has higher frequency blade passing noise
            noise_shape = 0.1 * np.exp(-(frequencies - 5000)**2 / (2*3000**2))
            amplitudes += noise_shape
        
        # Apply overall scaling based on amplitude
        amplitudes *= (self.amplitude / 0.5)  # Normalize to typical amplitude
        
        return frequencies, amplitudes
    
    def generate_time_signal(self, duration: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate a time-domain signal of the compressor vibration.
        
        Args:
            duration: Signal duration in seconds
            
        Returns:
            Tuple of (time_points, amplitude_values)
        """
        if not self.enabled:
            # Return flat line
            time_points = np.linspace(0, duration, int(duration * self.sample_rate))
            return time_points, np.zeros_like(time_points)
        
        # Create time array
        time_points = np.linspace(0, duration, int(duration * self.sample_rate))
        signal_values = np.zeros_like(time_points)
        
        # Add frequency components
        for freq, amp in self._frequency_components:
            # Add sine wave for each component
            # Add random phase to make the signal more realistic
            phase = np.random.uniform(0, 2*np.pi)
            signal_values += amp * np.sin(2 * np.pi * freq * time_points + phase)
        
        # Add compressor-type specific features
        if self.comp_type == self.TYPE_RECIPROCATING:
            # Add impact transients for reciprocating compressor
            # These occur at the compression frequency
            transient_interval = 1.0 / self.compression_freq
            for t in np.arange(0, duration, transient_interval):
                # Find closest index
                idx = int(t * self.sample_rate)
                if idx + 50 < len(time_points):
                    # Create a decay transient
                    decay = np.exp(-np.arange(50) / 10)
                    signal_values[idx:idx+50] += 0.4 * decay
        
        # Add appropriate noise based on condition
        noise_level = 0.03  # Base noise level
        
        if self.condition == self.CONDITION_VALVE_ISSUE:
            # Add random impacts for valve issues
            num_impacts = int(duration * 10)  # Frequency of impacts
            for _ in range(num_impacts):
                pos = np.random.randint(0, len(time_points) - int(0.005 * self.sample_rate))
                impact_width = int(0.005 * self.sample_rate)  # 5ms impact
                impact = 0.4 * np.exp(-np.arange(impact_width) / (0.001 * self.sample_rate))
                signal_values[pos:pos+impact_width] += impact
            
            noise_level = 0.1
            
        elif self.condition == self.CONDITION_PRESSURE_ISSUE:
            # Add low frequency modulation for pressure issues
            if self.comp_type == self.TYPE_CENTRIFUGAL:
                # Add surge pulsation (very low frequency)
                surge_freq = self.rotation_freq * 0.05
                surge_mod = 0.5 * np.sin(2 * np.pi * surge_freq * time_points)
                signal_values *= (1 + surge_mod)
            else:
                # Add pressure pulsation
                pulse_freq = self.rotation_freq * 0.2
                pulse_mod = 0.3 * np.sin(2 * np.pi * pulse_freq * time_points)
                signal_values *= (1 + pulse_mod)
            
            noise_level = 0.08
            
        elif self.condition == self.CONDITION_BEARING_WEAR:
            # Add high frequency components for bearing wear
            bearing_noise = np.random.normal(0, 0.1, len(time_points))
            bearing_noise = signal.sosfilt(
                signal.butter(4, [1000, 6000], 'bandpass', fs=self.sample_rate, output='sos'),
                bearing_noise
            )
            signal_values += bearing_noise
            
            noise_level = 0.12
        
        # Add base noise
        signal_values += np.random.normal(0, noise_level, len(time_points))
        
        # Normalize signal values to the desired amplitude
        if np.max(np.abs(signal_values)) > 0:
            signal_values = signal_values * (self.amplitude / np.max(np.abs(signal_values)))
        
        return time_points, signal_values


class VibrationPropagation:
    """
    Models how vibrations propagate through different materials and structural elements.
    
    This class calculates attenuation, frequency response changes, and propagation 
    delays as vibrations move through walls, floors, and other building elements.
    
    Attributes:
        materials (Dict[str, Dict]): Dictionary of materials and their properties
    """
    
    # Standard material attenuation coefficients (dB/m)
    MATERIAL_CONCRETE = "concrete"
    MATERIAL_WOOD = "wood"
    MATERIAL_STEEL = "steel"
    MATERIAL_DRYWALL = "drywall"
    MATERIAL_SOIL = "soil"
    MATERIAL_RUBBER = "rubber"
    
    def __init__(self):
        """Initialize the vibration propagation model with default materials."""
        # Material properties:
        # - attenuation_coef: attenuation coefficient in dB/m
        # - speed: propagation speed in m/s
        # - resonant_freqs: list of resonant frequencies in Hz
        # - damping: damping factor (dimensionless)
        self.materials = {
            self.MATERIAL_CONCRETE: {
                "attenuation_coef": 2.0,         # dB/m
                "speed": 3200.0,                 # m/s
                "resonant_freqs": [20, 50, 120], # Hz
                "damping": 0.03                  # damping factor
            },
            self.MATERIAL_WOOD: {
                "attenuation_coef": 4.0,
                "speed": 3500.0,
                "resonant_freqs": [30, 70, 150],
                "damping": 0.05
            },
            self.MATERIAL_STEEL: {
                "attenuation_coef": 0.2,
                "speed": 5000.0,
                "resonant_freqs": [100, 200, 400],
                "damping": 0.001
            },
            self.MATERIAL_DRYWALL: {
                "attenuation_coef": 5.0,
                "speed": 1800.0,
                "resonant_freqs": [40, 90, 180],
                "damping": 0.04
            },
            self.MATERIAL_SOIL: {
                "attenuation_coef": 8.0,
                "speed": 300.0,
                "resonant_freqs": [10, 25, 60],
                "damping": 0.1
            },
            self.MATERIAL_RUBBER: {
                "attenuation_coef": 20.0,
                "speed": 50.0,
                "resonant_freqs": [5, 15, 30],
                "damping": 0.15
            }
        }
        
    def add_material(self, name: str, attenuation_coef: float, speed: float, 
                    resonant_freqs: List[float], damping: float):
        """
        Add a new material to the propagation model.
        
        Args:
            name: Unique name for the material
            attenuation_coef: Attenuation coefficient in dB/m
            speed: Propagation speed in m/s
            resonant_freqs: List of resonant frequencies in Hz
            damping: Damping factor (dimensionless)
        """
        self.materials[name] = {
            "attenuation_coef": attenuation_coef,
            "speed": speed,
            "resonant_freqs": resonant_freqs,
            "damping": damping
        }
    
    def calculate_propagation_delay(self, distance: float, material: str) -> float:
        """
        Calculate the propagation delay through a material.
        
        Args:
            distance: Distance in meters
            material: Material name
            
        Returns:
            Propagation delay in seconds
        """
        if material not in self.materials:
            # Default to concrete if material not found
            material = self.MATERIAL_CONCRETE
            
        speed = self.materials[material]["speed"]
        return distance / speed
    
    def calculate_attenuation(self, distance: float, material: str, frequency: float = None) -> float:
        """
        Calculate attenuation through a material.
        
        Args:
            distance: Distance in meters
            material: Material name
            frequency: Signal frequency in Hz (optional)
            
        Returns:
            Attenuation factor (0-1)
        """
        if material not in self.materials:
            material = self.MATERIAL_CONCRETE
            
        # Get basic attenuation coefficient
        atten_coef = self.materials[material]["attenuation_coef"]
        
        # Calculate attenuation in dB
        atten_db = atten_coef * distance
        
        # Convert to linear factor (e.g. -6dB -> 0.5)
        atten_factor = 10 ** (-atten_db / 20)
        
        # Apply frequency-dependent effects if frequency is provided
        if frequency is not None:
            resonant_freqs = self.materials[material]["resonant_freqs"]
            damping = self.materials[material]["damping"]
            
            # Check for resonance effects
            for res_freq in resonant_freqs:
                # Calculate Q factor (inverse of damping)
                q_factor = 1.0 / damping
                
                # Calculate frequency ratio
                freq_ratio = frequency / res_freq
                
                # Apply resonance model (simplified second-order system)
                # Amplification near resonance, attenuation away from resonance
                resonance_factor = 1.0 / np.sqrt((1 - freq_ratio**2)**2 + (freq_ratio/q_factor)**2)
                
                # Limit maximum amplification
                resonance_factor = min(resonance_factor, 5.0)
                
                # Apply to attenuation factor
                atten_factor *= resonance_factor
        
        # Ensure attenuation is between 0 and 1
        return max(0.0, min(1.0, atten_factor))
    
    def apply_material_transfer_function(self, 
                                       frequencies: np.ndarray, 
                                       amplitudes: np.ndarray,
                                       material: str,
                                       thickness: float) -> np.ndarray:
        """
        Apply material transfer function to modify frequency response.
        
        Args:
            frequencies: Array of frequencies in Hz
            amplitudes: Original amplitude spectrum
            material: Material name
            thickness: Material thickness in meters
            
        Returns:
            Modified amplitude spectrum
        """
        if material not in self.materials:
            material = self.MATERIAL_CONCRETE
            
        # Get material properties
        mat_props = self.materials[material]
        resonant_freqs = mat_props["resonant_freqs"]
        damping = mat_props["damping"]
        
        # Apply basic attenuation
        atten_coef = mat_props["attenuation_coef"]
        atten_db = atten_coef * thickness
        atten_factor = 10 ** (-atten_db / 20)
        
        # Initialize modified amplitudes with basic attenuation
        modified_amps = amplitudes * atten_factor
        
        # Apply frequency-dependent effects
        for i, freq in enumerate(frequencies):
            # Check for resonance effects
            for res_freq in resonant_freqs:
                # Calculate Q factor (inverse of damping)
                q_factor = 1.0 / damping
                
                # Calculate frequency ratio
                freq_ratio = freq / res_freq
                
                # Apply resonance model
                if freq_ratio > 0:
                    resonance_factor = 1.0 / np.sqrt((1 - freq_ratio**2)**2 + (freq_ratio/q_factor)**2)
                    
                    # Limit maximum amplification
                    resonance_factor = min(resonance_factor, 5.0)
                    
                    # Apply to amplitude
                    modified_amps[i] *= resonance_factor
            
            # Apply high-frequency rolloff typical of materials
            # Most materials attenuate high frequencies more strongly
            high_freq_atten = 1.0 / (1.0 + (freq / 2000.0)**2)
            modified_amps[i] *= high_freq_atten
        
        return modified_amps
    
    def propagate_vibration(self, 
                         source: VibrationSource,
                         path: List[Tuple[str, float]],
                         target_position: Tuple[float, float, float],
                         freq_range: Tuple[float, float, int] = (0, 1000, 1000)) -> Dict[str, Any]:
        """
        Calculate vibration propagation from source to target.
        
        Args:
            source: Vibration source object
            path: List of (material, thickness) tuples representing the propagation path
            target_position: 3D coordinates of target position
            freq_range: Tuple of (min_freq, max_freq, num_points) for frequency analysis
            
        Returns:
            Dictionary with propagation results including:
                - delay: Propagation delay in seconds
                - attenuation: Overall attenuation factor
                - frequencies: Frequency array
                - original_amplitudes: Original source spectrum
                - propagated_amplitudes: Spectrum after propagation
        """
        # Calculate direct 3D distance from source to target
        source_pos = source.position
        target_pos = Vector3D(*target_position)
        direct_distance = (target_pos - source_pos).magnitude()
        
        # Generate source vibration spectrum
        frequencies, original_amplitudes = source.generate_spectrum(freq_range)
        
        # Start with unmodified amplitudes
        propagated_amplitudes = np.copy(original_amplitudes)
        
        # Calculate propagation delay and apply attenuation for each material in path
        total_delay = 0
        total_distance = 0
        
        for material, thickness in path:
            # Calculate delay through this material
            delay = self.calculate_propagation_delay(thickness, material)
            total_delay += delay
            total_distance += thickness
            
            # Apply material transfer function
            propagated_amplitudes = self.apply_material_transfer_function(
                frequencies, propagated_amplitudes, material, thickness
            )
        
        # Calculate remaining distance (if path doesn't cover full distance)
        remaining_distance = max(0, direct_distance - total_distance)
        
        # Apply air attenuation for remaining distance
        if remaining_distance > 0:
            # Air attenuates approximately 0.1 dB/m
            air_atten_db = 0.1 * remaining_distance
            air_atten_factor = 10 ** (-air_atten_db / 20)
            
            # Apply frequency-dependent air attenuation (higher frequencies attenuate more)
            for i, freq in enumerate(frequencies):
                # Higher frequency -> stronger attenuation
                freq_factor = 1.0 + (freq / 500.0)**2
                freq_atten = air_atten_factor ** freq_factor
                propagated_amplitudes[i] *= freq_atten
            
            # Add delay through air (speed of sound ~343 m/s)
            air_delay = remaining_distance / 343.0
            total_delay += air_delay
        
        # Apply inverse square law attenuation based on total distance
        # A(d) = A₀ / d²
        if direct_distance > 0.1:  # Avoid division by very small values
            inv_square_factor = 1.0 / (direct_distance ** 2)
            # Normalize to 1.0 at 1 meter
            inv_square_factor *= 1.0 ** 2
            # Apply to all frequencies
            propagated_amplitudes *= inv_square_factor
        
        # Calculate overall attenuation factor (for time domain)
        overall_attenuation = np.mean(propagated_amplitudes) / np.mean(original_amplitudes) if np.mean(original_amplitudes) > 0 else 0
        
        return {
            "delay": total_delay,
            "attenuation": overall_attenuation,
            "frequencies": frequencies,
            "original_amplitudes": original_amplitudes,
            "propagated_amplitudes": propagated_amplitudes,
            "distance": direct_distance
        }


class VibrationProfile:
    """
    Manages multiple vibration sources and calculates their composite effects.
    
    This class handles the combination of multiple vibration sources, accounting
    for propagation effects, to generate comprehensive vibration profiles at 
    specific locations.
    
    Attributes:
        sources (Dict[str, VibrationSource]): Dictionary of vibration sources
        propagation_model (VibrationPropagation): Vibration propagation model
    """
    
    def __init__(self, propagation_model: Optional[VibrationPropagation] = None):
        """
        Initialize a vibration profile manager.
        
        Args:
            propagation_model: VibrationPropagation instance (default: creates new instance)
        """
        self.sources = {}
        self.propagation_model = propagation_model if propagation_model else VibrationPropagation()
    
    def add_source(self, source: VibrationSource):
        """
        Add a vibration source to the profile.
        
        Args:
            source: VibrationSource object to add
        """
        self.sources[source.name] = source
    
    def remove_source(self, source_name: str) -> bool:
        """
        Remove a vibration source from the profile.
        
        Args:
            source_name: Name of the source to remove
            
        Returns:
            True if source was found and removed, False otherwise
        """
        if source_name in self.sources:
            del self.sources[source_name]
            return True
        return False
    
    def calculate_composite_vibration(self, 
                                    position: Tuple[float, float, float],
                                    freq_range: Tuple[float, float, int] = (0, 1000, 1000),
                                    propagation_paths: Optional[Dict[str, List[Tuple[str, float]]]] = None) -> Dict[str, Any]:
        """
        Calculate composite vibration at a specific position.
        
        Args:
            position: 3D coordinates of the target position
            freq_range: Tuple of (min_freq, max_freq, num_points) for frequency analysis
            propagation_paths: Optional dictionary mapping source names to propagation paths
                               Each path is a list of (material, thickness) tuples
            
        Returns:
            Dictionary with vibration analysis results including:
                - frequencies: Frequency array
                - composite_amplitudes: Composite amplitude spectrum
                - source_contributions: Dict mapping source names to their contribution
                - rms_acceleration: RMS acceleration value
                - peak_frequencies: List of dominant frequency peaks
                - sources: List of source information dictionaries
        """
        if not self.sources:
            # No sources, return zeros
            frequencies = np.linspace(freq_range[0], freq_range[1], freq_range[2])
            return {
                "frequencies": frequencies,
                "composite_amplitudes": np.zeros_like(frequencies),
                "source_contributions": {},
                "rms_acceleration": 0.0,
                "peak_frequencies": [],
                "sources": []
            }
        
        # Initialize with the first source to get frequency array
        source_name = next(iter(self.sources))
        source = self.sources[source_name]
        frequencies, _ = source.generate_spectrum(freq_range)
        
        # Initialize composite amplitudes
        composite_amplitudes = np.zeros_like(frequencies)
        source_contributions = {}
        source_info = []
        
        # Calculate contribution from each source
        for name, source in self.sources.items():
            if not source.enabled:
                continue
                
            # Get propagation path for this source if provided
            path = propagation_paths.get(name, []) if propagation_paths else []
            
            # Calculate propagated vibration
            result = self.propagation_model.propagate_vibration(
                source, path, position, freq_range
            )
            
            # Add to composite (using amplitude addition, not power)
            composite_amplitudes += result["propagated_amplitudes"]
            
            # Store source contribution
            source_contributions[name] = {
                "amplitudes": result["propagated_amplitudes"],
                "attenuation": result["attenuation"],
                "delay": result["delay"],
                "distance": result["distance"]
            }
            
            # Store source info
            source_info.append({
                "name": name,
                "type": source.source_type,
                "position": (source.position.x, source.position.y, source.position.z),
                "amplitude": source.amplitude,
                "distance": result["distance"],
                "attenuation": result["attenuation"],
                "delay": result["delay"]
            })
        
        # Calculate RMS acceleration from spectrum
        # RMS = sqrt(sum(amplitude²) / N)
        rms_accel = np.sqrt(np.mean(composite_amplitudes ** 2))
        
        # Identify peak frequencies (local maxima above threshold)
        threshold = 0.1 * np.max(composite_amplitudes) if np.max(composite_amplitudes) > 0 else 0
        peak_indices = signal.find_peaks(composite_amplitudes, height=threshold)[0]
        peak_frequencies = [(frequencies[idx], composite_amplitudes[idx]) for idx in peak_indices]
        
        return {
            "frequencies": frequencies,
            "composite_amplitudes": composite_amplitudes,
            "source_contributions": source_contributions,
            "rms_acceleration": rms_accel,
            "peak_frequencies": peak_frequencies,
            "sources": source_info
        }
    
    def generate_composite_time_signal(self,
                                     position: Tuple[float, float, float],
                                     duration: float,
                                     sample_rate: int = 1000,
                                     propagation_paths: Optional[Dict[str, List[Tuple[str, float]]]] = None) -> Dict[str, Any]:
        """
        Generate composite time-domain vibration signal at a position.
        
        Args:
            position: 3D coordinates of the target position
            duration: Signal duration in seconds
            sample_rate: Sample rate in Hz
            propagation_paths: Optional dictionary mapping source names to propagation paths
            
        Returns:
            Dictionary with time-domain results including:
                - time_points: Time array
                - composite_signal: Composite acceleration signal
                - source_signals: Dict mapping source names to their signals
                - rms_acceleration: RMS acceleration value
                - peak_acceleration: Peak acceleration value
        """
        if not self.sources:
            # No sources, return zeros
            time_points = np.linspace(0, duration, int(duration * sample_rate))
            return {
                "time_points": time_points,
                "composite_signal": np.zeros_like(time_points),
                "source_signals": {},
                "rms_acceleration": 0.0,
                "peak_acceleration": 0.0
            }
        
        # Initialize time array
        time_points = np.linspace(0, duration, int(duration * sample_rate))
        composite_signal = np.zeros_like(time_points)
        source_signals = {}
        
        # Calculate contribution from each source
        for name, source in self.sources.items():
            if not source.enabled: